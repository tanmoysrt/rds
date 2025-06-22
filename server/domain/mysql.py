import contextlib
import random
import subprocess
import time
from pathlib import Path
from typing import override

from generated.extras_pb2 import ClusterConfig, ClusterNodeType, DBHealthStatus, DBType
from generated.inter_agent_pb2 import (
    RequestRsyncAccessRequest,
    RequestRsyncAccessResponse,
    RevokeRsyncAccessRequest,
    SyncReplicationUserRequest,
)
from server import ServerConfig
from server.domain.systemd_service import SystemdService
from server.helpers import (
    find_available_port,
    generate_mysql_password_hash,
    render_template,
    wait_for_ssh_daemon,
)
from server.internal.db_client import DatabaseClient
from server.internal.etcd_client import Etcd3Client
from server.internal.utils import get_redis_client


class MySQL(SystemdService):
    @classmethod
    def create(cls, service_id:str, base_path:str, image:str, tag:str, cluster_id:str, root_password:str,etcd_username:str, etcd_password:str, server_id:int|None=None, db_port:int|None=None, service:str="mariadb", **kwargs):
        if service not in ("mariadb", "mysql"):
            raise ValueError(f"Unknown service {service}")

        # Create the base path if it doesn't exist
        path = Path(base_path)
        path.mkdir(parents=True, exist_ok=True)

        # Create necessary directories
        data_path = path / "data"
        data_path.mkdir(parents=True, exist_ok=True)

        config_dir_path = path / "config"
        config_dir_path.mkdir(parents=True, exist_ok=True)

        init_dir_path = path / "init"
        init_dir_path.mkdir(parents=True, exist_ok=True)

        # Find port if not provided
        if not db_port:
            db_port = find_available_port()

        # Use a random server_id if not provided
        if not server_id:
            server_id = random.randint(1, 1000000)

        metadata = {
            "mysql_root_password": root_password,
            "mysql_hashed_root_password": generate_mysql_password_hash(root_password),
            "server_id": server_id,
            "db_port": db_port,
            "base_path": str(path),
            "data_path": str(data_path),
            "config_path": str(config_dir_path),
            "init_path": str(init_dir_path),
        }

        # Fetch cluster configuration
        server_config = ServerConfig()
        etcd_client = Etcd3Client(
            addresses=[f"{server_config.etcd_host}:{server_config.etcd_port}"],
            user=etcd_username,
            password=etcd_password,
        )
        cluster_config = ClusterConfig()
        value = etcd_client.get(server_config.kv_cluster_config_key.format(cluster_id=cluster_id))
        if not value:
            raise ValueError(f"Cluster with ID {cluster_id} does not exist or is not configured properly.")
        cluster_config.ParseFromString(value[0])
        if not cluster_config:
            raise ValueError(f"Cluster with ID {cluster_id} is corrupted or not configured properly.")
        if not cluster_config.proxy:
            raise ValueError("Cluster with ID {cluster_id} does not have a proxy configured. Please configure a proxy for the cluster before creating MySQL instances.")

        # Generate script and initial configuration files
        init_script_path = init_dir_path / "01-secure-mysql-root-user.sql"
        if not init_script_path.exists():
            with open(init_script_path, "w") as f:
                f.write(render_template("mysql/init_scripts/01-secure-mysql-root-user.sql", {
                    **metadata,
                    "replication_user": cluster_config.replication_user,
                    "replication_password": cluster_config.replication_password,
                }))

        mysql_config_path = config_dir_path / "rds.cnf"
        if not mysql_config_path.exists():
            with open(mysql_config_path, "w") as f:
                f.write(render_template("mysql/config/rds.cnf", metadata))

        # Create the service
        record = super().create(
            service_id=service_id,
            service=service,
            image=image,
            tag=tag,
            command=None,
            environment_variables={
                "MARIADB_ALLOW_EMPTY_ROOT_PASSWORD": "1",
                "MYSQL_ALLOW_EMPTY_PASSWORD": "1",
            },
            mounts={
                str(metadata["data_path"]): "/var/lib/mysql",
                str(metadata["config_path"]): "/etc/mysql/conf.d",
                str(metadata["init_path"]): "/docker-entrypoint-initdb.d",
            },
            metadata=metadata,
            podman_args=["--userns=keep-id:uid=999,gid=999"],
            cluster_id=cluster_id,
            etcd_username=etcd_username,
            etcd_password=etcd_password,
        )

        with contextlib.suppress(Exception):
            # Publish the command to pubsub to notify monitoring services to start monitoring this MySQL instance
            redis = get_redis_client()
            server_config = ServerConfig()
            redis.publish(server_config.mysql_monitor_commands_redis_channel, f"add {record.model.id}")
            redis.publish(server_config.etcd_monitor_commands_redis_channel, f"add {record.model.id}")

        return record

    def __init__(self, record_id:str):
        super().__init__(record_id)
        metadata = self.model.metadata_json
        self.server_id = metadata["server_id"]
        self.db_port = metadata["db_port"]
        self.mysql_root_password = metadata["mysql_root_password"]
        self.mysql_hashed_root_password = metadata["mysql_hashed_root_password"]
        self.base_path = metadata["base_path"]
        self.data_path = metadata["data_path"]
        self.config_path = metadata["config_path"]
        self.init_path = metadata["init_path"]

        self._db_instance_for_health_check:DatabaseClient|None = None

    def update_version(self, image:str, tag:str):
        return self.update(image=image, tag=tag)

    def setup_replica(self):
        """
        Replicate this MySQL instance from the one master node.
        """
        config = self.cluster_config
        master_node_id = None
        master_node_config = None

        for node_id in config.nodes:
            if node_id != self.model.id and config.nodes[node_id].type == ClusterNodeType.MASTER:
                master_node_id = node_id
                master_node_config = config.nodes[node_id]
                break

        if not master_node_id or not master_node_config:
            raise Exception("In the cluster no valid master node found for replication.")

        # Ensure that MySQL node is stopped before making changes
        self.stop()

        # Ask for rsync access to the master node
        src_node_agent = self.get_agent_for_node(master_node_id)
        rsync_access: RequestRsyncAccessResponse = src_node_agent.inter_agent_service.RequestRsyncAccess(RequestRsyncAccessRequest(
            cluster_id=self.model.cluster_id,
            node_id=self.model.id,
        ))

        def revoke_rsync_access():
            if rsync_access and rsync_access.instance_id:
                try:
                    src_node_agent.inter_agent_service.RevokeRsyncAccess(RevokeRsyncAccessRequest(
                        cluster_id=self.model.cluster_id,
                        instance_id=rsync_access.instance_id,
                    ))
                except Exception as e:
                    print(f"Failed to revoke rsync access: {e}")

        try:
            wait_for_ssh_daemon(master_node_config.ip, rsync_access.port, rsync_access.username, rsync_access.password, timeout=30)
            # Start copying data from the master node
            command  = [
                "sshpass", "-p", rsync_access.password,
                "rsync", "-rlptvz", "--delete",
                "--rsync-path", "sudo rsync",
                "--exclude", "mysql.sock",
                "--exclude", "mysql.pid",
                "--exclude", "mysql-bin.*",
                "--exclude", "mysql-bin.index",
                "--exclude", "mariadb-bin.*",
                "--exclude", "mariadb-bin.index",
                "--exclude", "galera.*",
                "--exclude", "ib_logfile*",
                "--inplace", # To avoid creating temporary files, for large ibd files it's useful
                "-e", f"ssh -p {rsync_access.port} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null",
                f"{rsync_access.username}@{master_node_config.ip}:/data/", self.data_path
            ]

            # Phase 1 : Copy the data directory from the master node without impacting the running master MySQL instance
            subprocess.run(command, check=True)

            # Ask master to sync the replication user
            src_node_agent.inter_agent_service.SyncReplicationUser(SyncReplicationUserRequest(
                cluster_id=self.model.cluster_id,
                node_id=master_node_id
            ))

            # Establish connection to the master database
            with DatabaseClient(
                db_type=self.model.service,
                host=master_node_config.ip,
                port=master_node_config.db_port,
                user=config.replication_user,
                password=config.replication_password,
            ) as master_db_conn:
                # Phase 2 : Take read lock on the master database and rsync the data directory
                # to ensure that we have a consistent snapshot of the database.
                master_db_conn.query("FLUSH TABLES WITH READ LOCK")
                subprocess.run(command, check=True)

                # Release the read lock
                master_db_conn.query("UNLOCK TABLES")

            self.start()
            self.wait_for_db(timeout=180)
            self.start_replication()
        finally:
            revoke_rsync_access()

    def wait_for_db(self, timeout:int):
        """
        Wait for the MySQL database to be ready.
        This is useful after starting the service or after replication.
        """
        conn = self.db_conn
        start_time = time.time()
        db_active = False
        while  time.time() - start_time < timeout:
            try:
                conn.query("SELECT 1")
                db_active = True
                break
            except:
                time.sleep(1)

        if not db_active:
            raise Exception("Failed to connect to the MySQL database after waiting")

    def start_replication(self, master_node_id:str|None=None):
        config = self.cluster_config
        # Pick the master node
        master_node_config = None
        if master_node_id:
            if master_node_id not in config.nodes:
                raise ValueError("Invalid master node ID provided for replication.")
            master_node_config = config.nodes[master_node_id]
        else:
            # Pick a random master node from the cluster configuration
            for node_id in config.nodes:
                if node_id != self.model.id and config.nodes[node_id].type == ClusterNodeType.MASTER:
                    master_node_config = config.nodes[node_id]
                    break

        if not master_node_config:
            raise Exception("In cluster configuration, no master node found")

        self.stop_replication()
        conn = self.db_conn
        conn.query("RESET SLAVE ALL")  # Reset any previous slave configuration
        conn.query(
            """CHANGE MASTER TO
                            MASTER_HOST = %s,
                            MASTER_PORT = %s,
                            MASTER_USER = %s,
                            MASTER_PASSWORD = %s, 
                            MASTER_USE_GTID = slave_pos""",
            (master_node_config.ip, master_node_config.db_port, config.replication_user, config.replication_password),
        )
        conn.query("START SLAVE")

    def stop_replication(self):
        self.db_conn.query("STOP SLAVE")

    def sync_replica_user(self):
        config = self.cluster_config
        conn = self.db_conn
        # Fetch current hash of the replication user password
        current_hash = conn.query("SELECT authentication_string FROM mysql.user WHERE user = %s AND host = '%%'", (config.replication_user,))
        user_exist = False
        if len(current_hash) == 1:
            user_exist = True
            if current_hash[0]["authentication_string"] == generate_mysql_password_hash(config.replication_password):
                return

        if user_exist:
            conn.query(
                "ALTER USER %s@'%%' IDENTIFIED BY %s", (config.replication_user, config.replication_password)
            )
        else:
            conn.query("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", (config.replication_user, config.replication_password))

        conn.query("GRANT REPLICATION SLAVE, REPLICATION CLIENT, RELOAD ON *.* TO %s@'%%'", (config.replication_user,))
        conn.query("GRANT SELECT ON mysql.user TO %s@'%%'", (config.replication_user,))
        conn.query("FLUSH PRIVILEGES")

    @override
    def delete(self):
        super().delete()
        with contextlib.suppress(Exception):
            # Publish the command to pubsub to notify monitoring services to stop monitoring this MySQL instance
            redis = get_redis_client()
            server_config = ServerConfig()
            redis.publish(server_config.mysql_monitor_commands_redis_channel, f"remove {self.model.id}")
            redis.publish(server_config.etcd_monitor_commands_redis_channel, f"remove {self.model.id}")

    @override
    def get_health_info(self) -> (bool, DBHealthStatus | None):
        """
        Fetch gtid from the database to check health
        + getting the info of replication

        Try to use same db connection rather than creating a new one each time.
        """
        try:
            if not self._db_instance_for_health_check:
                self._db_instance_for_health_check = self.get_db_conn(autocommit=True)

            gtid = self._db_instance_for_health_check.query("SELECT @@gtid_current_pos")[0]["@@gtid_current_pos"]
            return True, DBHealthStatus(
                db_type=DBType.MYSQL if self.model.service == "mysql" else DBType.MARIADB,
                reported_at=time.time_ns() // 1_000_000,
                global_transaction_id=gtid,
            )
        except:
            return False, None

    @staticmethod
    def get_all(**kwargs) -> list[str]:
        return SystemdService.get_all(["mariadb", "mysql"])

    @override
    @property
    def db_conn(self):
        return self.get_db_conn(autocommit=False)

    def get_db_conn(self, autocommit:bool=False) -> DatabaseClient:
        return DatabaseClient(
            db_type=self.model.service,
            host="127.0.0.1", # localhost does not work with same network namespace
            port=self.db_port,
            user="root",
            password=self.mysql_root_password,
            schema="",
            autocommit=autocommit
        )
