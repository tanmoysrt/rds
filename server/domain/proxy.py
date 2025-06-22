import contextlib
from pathlib import Path
from typing import override

from generated.extras_pb2 import ClusterNodeType
from server.domain.systemd_service import SystemdService
from server.helpers import (
    find_available_port,
    generate_random_string,
    is_port_available,
    render_template,
)
from server.internal.db_client import DatabaseClient


class Proxy(SystemdService):
    @classmethod
    def create(cls, service_id:str, base_path:str, image:str, tag:str, cluster_id:str, db_readwrite_port:int|None=None, db_readonly_port:int|None=None, etcd_username:str|None=None, etcd_password:str|None=None, **kwargs):
        # Create the base path if it doesn't exist
        path = Path(base_path)
        path.mkdir(parents=True, exist_ok=True)

        # Create a data directory inside the base path
        data_path = path / "data"
        data_path.mkdir(parents=True, exist_ok=True)

        # Find ports if not provided
        if not db_readwrite_port:
            db_readwrite_port = find_available_port()
        if not db_readonly_port:
            db_readonly_port = find_available_port(start_port=db_readwrite_port, exclude_ports={db_readwrite_port})

        # Validate ports
        if db_readwrite_port == db_readonly_port:
            raise ValueError("db_readwrite_port and db_readonly_port must be different")

        if not is_port_available(db_readwrite_port):
            raise RuntimeError(f"Port {db_readwrite_port} is not available for db_readwrite_port")
        if not is_port_available(db_readonly_port):
            raise RuntimeError(f"Port {db_readonly_port} is not available for db_readonly_port")

        # Create the configuration file
        config_path = path / "proxysql.cnf"
        metadata = {
            "db_readwrite_port": db_readwrite_port,
            "db_readonly_port":  db_readonly_port,
            "admin_port":        find_available_port(exclude_ports={db_readonly_port, db_readwrite_port}),
            "admin_password":    generate_random_string(),
            "monitor_password":  generate_random_string(),
            "base_path":         str(path),
            "data_path":         str(data_path),
            "config_path":       str(config_path),
        }
        with open(config_path, "w") as f:
            f.write(render_template("proxy/proxysql.cnf", metadata))

        # Create the service
        return super().create(
            service_id=service_id,
            service="proxysql",
            image=image,
            tag=tag,
            command="proxysql -f --idle-threads -D /var/lib/proxysql --no-monitor",
            environment_variables={},
            mounts={
                str(metadata["data_path"]): "/var/lib/proxysql",
                str(metadata["config_path"]): "/etc/proxysql.cnf",
            },
            metadata=metadata,
            podman_args=["--userns=keep-id"],
            cluster_id=cluster_id,
            etcd_username=etcd_username,
            etcd_password=etcd_password,
        )

    def __init__(self, record_id:str):
        super().__init__(record_id)
        metadata = self.model.metadata_json
        self.db_readwrite_port = metadata["db_readwrite_port"]
        self.db_readonly_port = metadata["db_readonly_port"]
        self.admin_port = metadata["admin_port"]
        self.admin_password = metadata["admin_password"]
        self.monitor_password = metadata["monitor_password"]
        self.base_path = metadata["base_path"]
        self.data_path = metadata["data_path"]
        self.config_path = metadata["config_path"]

    def update_version(self, image:str, tag:str):
        return self.update(image=image, tag=tag)

    def sync_users(self, users_to_sync:list[str]|None=None, exclude_users:list[str]|None=None) -> tuple[list[str], list[str], list[str]]:
        """
        Sync users from the MySQL database to ProxySQL.
        
        :param users_to_sync:
        :param exclude_users:
        :return:
            A tuple containing three lists:
            - added_users: List of users to be added to ProxySQL
            - removed_users: List of users to be removed from ProxySQL
            - updated_users: List of users whose passwords need to be updated in ProxySQL
        """
        if not users_to_sync:
            users_to_sync = []
        if not exclude_users:
            exclude_users = []
        exclude_users.extend(["root", "mysql.sys", "mysql.infoschema", "mysql.session"])

        config = self.cluster_config
        exclude_users.append(config.replication_user)
        # Try to find a working master
        if not config.nodes:
            return [], [], []
        
        db_client:DatabaseClient|None = None
        for node_id in config.nodes:
            node = config.nodes[node_id]
            if node.type != ClusterNodeType.MASTER:
                continue
            with contextlib.suppress(Exception):
                db_client = DatabaseClient(
                    db_type="mysql",
                    host=node.ip,
                    port=node.db_port,
                    user=config.replication_user,
                    password=config.replication_password,
                    schema=""
                )
                db_client.query("SELECT 1")  # Simple query to check connection
                break

        if not db_client:
            raise RuntimeError(f"No database node is reachable to sync")

        # Open db connection to proxy
        proxy_client = self.db_conn
        proxy_client.query("SELECT 1")  # check connection

        # Fetch all users from the database
        placeholders = ", ".join(["%s"] * len(exclude_users))
        query = f"""SELECT
                       User, authentication_string
                    FROM mysql.user
                   WHERE 
                       authentication_string IS NOT NULL AND
                       authentication_string != '' AND
                       Host NOT IN ('localhost', '127.0.0.1', '::1') AND
                       User NOT IN ({placeholders})"""
        if users_to_sync:
            placeholders = ", ".join(["%s"] * len(users_to_sync))
            query += f" AND User IN ({placeholders})"

        all_users = db_client.query(query, tuple(exclude_users) + tuple(users_to_sync), as_dict=False)[1:]

        query = "SELECT username, password FROM mysql_users"
        if users_to_sync:
            placeholders = ", ".join(["%s"] * len(users_to_sync))
            query += f" WHERE username IN ({placeholders})"
        current_users_in_proxysql = proxy_client.query(query, as_dict=False)[1:]
        current_users_in_proxysql = {user[0]: user[1] for user in current_users_in_proxysql} # username -> password mapping

        # Now figure out which users to add / remove / update
        users_to_add = []
        users_to_remove = []
        users_to_update = []
        all_users_set = set()

        for user in all_users:
            username, password = user
            all_users_set.add(username)
            if username in current_users_in_proxysql:
                if current_users_in_proxysql[username] != password:
                    users_to_update.append((username, password))
            else:
                users_to_add.append((username, password))

        for username in current_users_in_proxysql:
            if username not in all_users_set:
                users_to_remove.append(username)

        # Prepare the queries to execute
        queries = []
        if users_to_add:
            # Default hostgroup is set to 1 for all new users [1 is writer hostgroup]
            queries.append("INSERT INTO mysql_users (username, password, default_hostgroup) VALUES " +
                           ", ".join(f"('{user[0]}', '{user[1]}', 1)" for user in users_to_add))

        if users_to_remove:
            queries.append("DELETE FROM mysql_users WHERE username IN (" +
                           ", ".join(f"'{user}'" for user in users_to_remove) + ")")

        if users_to_update:
            queries.append("UPDATE mysql_users SET password = CASE username " +
                           " ".join(f"WHEN '{user[0]}' THEN '{user[1]}'" for user in users_to_update) +
                           " END WHERE username IN (" +
                           ", ".join(f"'{user[0]}'" for user in users_to_update) + ")")

        if not queries:
            return [], [], []

        queries.append("LOAD MYSQL USERS TO RUNTIME")
        queries.append("SAVE MYSQL USERS TO DISK")

        # Execute the queries
        # ProxySQL admin interface does not support transactions, so we execute them one by one
        for query in queries:
            try:
                proxy_client.query(query)
            except Exception as e:
                raise RuntimeError(f"Failed to execute query: {e}")
    
        return [user[0] for user in users_to_add], \
                [user[0] for user in users_to_remove], \
                [user[0] for user in users_to_update]


    @staticmethod
    def get_all(**kwargs) -> list[str]:
        return super().get_all(["proxysql"])

    @override
    @property
    def db_conn(self):
        return DatabaseClient(
            db_type=self.model.service,
            host="127.0.0.1",
            port=self.admin_port,
            user="admin",
            password=self.admin_password,
            schema=""
        )

