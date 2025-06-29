import contextlib
import random
import subprocess
import time
from pathlib import Path
from typing import override

from agent.libs.mysql_config_validator import validate_config
from generated.extras_pb2 import DBHealthStatus, DBType
from generated.inter_agent_pb2 import (
    RequestRsyncAccessRequest,
    RequestRsyncAccessResponse,
    RevokeRsyncAccessRequest,
    SyncReplicationUserRequest,
)
from agent import ServerConfig
from agent.domain.systemd_service import SystemdService
from agent.helpers import (
    find_available_port,
    generate_mysql_password_hash,
    render_template,
    wait_for_ssh_daemon,
)
from agent.internal.config import ClusterConfig
from agent.internal.db_client import DatabaseClient
from agent.internal.etcd_client import Etcd3Client
from agent.internal.utils import get_redis_client


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
            "db_options": {}
        }

        # Fetch cluster configuration
        server_config = ServerConfig()
        etcd_client = Etcd3Client(
            addresses=[f"{server_config.etcd_host}:{server_config.etcd_port}"],
            user=etcd_username,
            password=etcd_password,
        )
        cluster_config = ClusterConfig(etcd_client=etcd_client, cluster_id=cluster_id)
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
            redis.publish(server_config.etcd_monitor_commands_redis_channel, f"add {record.model.cluster_id}")

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
        self.db_options = metadata.get("db_options", {})

        self._db_instance_for_health_check:DatabaseClient|None = None

    def update_version(self, image:str, tag:str):
        return self.update(image=image, tag=tag, deploy=True)

    def setup_replica(self):
        """
        Replicate this MySQL instance from the one master node.
        """
        if len(self.cluster_config.online_master_node_ids) == 0:
            raise Exception("No online master node found in the cluster configuration for replication.")

        master_node_id = self.cluster_config.online_master_node_ids[0]
        master_node_config = self.cluster_config.get_node(master_node_id)

        # Ensure that MySQL node is stopped before making changes
        self.stop()

        # Ask for rsync access to the master node
        src_node_agent = self.get_agent_for_node(master_node_id)
        rsync_access: RequestRsyncAccessResponse = src_node_agent.inter_agent_service.RequestRsyncAccess(RequestRsyncAccessRequest(
            cluster_id=self.model.cluster_id,
            node_id=master_node_id
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
                "--exclude", "ibtmp1",
                "--exclude", "mysqld-relay-bin.*",
                "--exclude", "relay-log.info",
                "--exclude", "mysql-error.log",
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
                user=self.cluster_config.replication_user,
                password=self.cluster_config.replication_password,
            ) as master_db_conn:
                # Phase 2 : Take read lock on the master database and rsync the data directory
                # to ensure that we have a consistent snapshot of the database.
                master_db_conn.query("FLUSH LOGS")
                master_db_conn.query("FLUSH TABLES WITH READ LOCK")

                # Final copy
                subprocess.run(command, check=True)

                # Record the current GTID position
                slave_pos_res = master_db_conn.query("SELECT @@GLOBAL.gtid_current_pos")
                slave_pos = slave_pos_res[0].get("@@GLOBAL.gtid_current_pos","") if len(slave_pos_res) >= 1 else ""

                # Release the read lock
                master_db_conn.query("UNLOCK TABLES")

            self.start()
            self.wait_for_db(timeout=180)
            self.configure_as_replica(slave_pos=slave_pos)
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

    def configure_as_replica(self, slave_pos:str|None=None):
        if len(self.cluster_config.online_master_node_ids) == 0:
            raise Exception("No online master node found in the cluster configuration for replication.")

        master_node_id = self.cluster_config.online_master_node_ids[0]
        master_node_config = self.cluster_config.get_node(master_node_id)

        with self.db_conn as conn:
            self.enable_read_only_mode()
            conn.query("STOP SLAVE")
            conn.query("RESET SLAVE ALL")
            # Set the slave_pos if provided, otherwise use the current GTID position
            if slave_pos:
                conn.query("SET GLOBAL gtid_slave_pos = %s", (slave_pos,))

            conn.query(
                f"""CHANGE MASTER TO
                                MASTER_HOST = %s,
                                MASTER_PORT = %s,
                                MASTER_USER = %s,
                                MASTER_PASSWORD = %s, 
                                MASTER_USE_GTID = {"current_pos" if slave_pos else "slave_pos"}""",
                (master_node_config.ip, master_node_config.db_port, self.cluster_config.replication_user, self.cluster_config.replication_password),
            )
            self.modify_db_options_and_restart_if_required({
                "rpl_semi_sync_slave_enabled": 1,
                "rpl_semi_sync_master_enabled": 0
            })
            conn.query("START SLAVE")

    def configure_as_master(self):
        if self.model.id not in self.cluster_config.online_master_node_ids:
            raise Exception(f"Node {self.model.id} is not an online master node in the cluster configuration.")

        self.enable_read_only_mode()

        with self.db_conn as conn:
            conn.query("STOP SLAVE")
            conn.query("RESET SLAVE ALL")

        self.modify_db_options_and_restart_if_required({
            "rpl_semi_sync_master_enabled": 1,
            "rpl_semi_sync_slave_enabled": 0,
            "rpl_semi_sync_master_wait_point": "AFTER_SYNC",
            "rpl_semi_sync_master_wait_no_slave": 1,
        })
        self.disable_read_only_mode()

    def sync_replication_config(self, cluster_config:ClusterConfig=None):
        """
        This will verify whether the nodes replication configuration is in sync with the cluster configuration.
        If there is any change in cluster configuration, it should be act like that

        1. If master has changed, then stop replication and reconfigure it, then start
        2. If current node become new master, then stop replication and reconfigure it to act as master
        """
        if not cluster_config:
            cluster_config = self.cluster_config
        # Current State
        with self.db_conn as conn:
            slave_info = conn.query("SHOW SLAVE STATUS", as_dict=True)
            is_current_node_master = len(slave_info) == 0
            master_host = None
            master_port = None
            if not is_current_node_master:
                info = slave_info[0]
                master_host = info.get("Master_Host", None)
                master_port = int(info.get("Master_Port", "0"))

        # Expected State
        is_current_node_should_be_master = self.model.id in cluster_config.online_master_node_ids
        expected_master_node = cluster_config.get_node(cluster_config.online_master_node_ids[0]) if cluster_config.online_master_node_ids else None
        expected_master_host = expected_master_node.ip if expected_master_node else None
        expected_master_port = expected_master_node.db_port if expected_master_node else None

        if is_current_node_should_be_master != is_current_node_master or \
           (not is_current_node_should_be_master and (master_host != expected_master_host or master_port != expected_master_port)):
            # If current node should be master but it's not, or if current node is not master but the master has changed
            if is_current_node_should_be_master:
                self.configure_as_master()
            else:
                self.configure_as_replica()

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

        conn.query("GRANT REPLICATION SLAVE, REPLICATION CLIENT, RELOAD, READ_ONLY ADMIN ON *.* TO %s@'%%'", (config.replication_user,))
        conn.query("GRANT SELECT ON mysql.user TO %s@'%%'", (config.replication_user,))
        conn.query("FLUSH PRIVILEGES")

    def enable_read_only_mode(self):
        """
        Update the read-only mode of the MySQL instance.

        NOTE: Users with `SUPER` privilege can still write to the database even in read-only mode.
        So be cautious while granting `SUPER` privilege to users + avoid syncing them on ProxySQL.
        """
        self.modify_db_options_and_restart_if_required({
            "read_only": 1,
        })

    def disable_read_only_mode(self):
        self.modify_db_options_and_restart_if_required({
            "read_only": 0,
        })

    @override
    def delete(self):
        super().delete()
        with contextlib.suppress(Exception):
            # Publish the command to pubsub to notify monitoring services to stop monitoring this MySQL instance
            redis = get_redis_client()
            server_config = ServerConfig()
            redis.publish(server_config.mysql_monitor_commands_redis_channel, f"remove {self.model.id}")
            redis.publish(server_config.etcd_monitor_commands_redis_channel, f"remove {self.model.cluster_id}")

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
    def sync_replication_config_for_all_servers(cluster_id:str|None=None, config:ClusterConfig=None):
        if cluster_id is None and config is not None:
            raise Exception("if config is provided, cluster_id must be provided as well")

        # Fetch all available ProxySQL instances
        server_ids = MySQL.get_all(cluster_id=cluster_id)
        for server_id in server_ids:
            if server_id in (config.offline_replica_node_ids + config.offline_standby_node_ids + config.offline_master_node_ids + config.offline_read_only_node_ids):
                continue
            try:
                db = MySQL(server_id)
                db.sync_replication_config(cluster_config=config)
            except Exception as e:
                print(f"Failed to sync replication config for server {server_id}: {e}")

    def modify_db_options_and_restart_if_required(self, updates:dict, remove_keys:list[str]|None=None, restart_timeout:int=180):
        """
        In this case, we will use `modify_db_options` method to apply the changes.
        Then, restart the MySQL instance if required.
        Then, wait for the MySQL instance to be ready.
        And refresh the db_conn so that next operation doesn't fail
        """
        is_restart_required = self.modify_db_options(updates, remove_keys)
        if is_restart_required:
            self.restart()
            self.wait_for_db(timeout=restart_timeout)
            self._db_instance_for_health_check = None
        else:
            self._db_instance_for_health_check = None


    def modify_db_options(self, updates:dict, remove_keys:list[str]|None=None) -> bool:
        """
        Modify the database options for this MySQL instance.
        This will update the rds.cnf file and apply the changes to the running instance.

        :param updates: Dictionary of options to update, e.g. {"read_only": True, "innodb_flush_log_at_trx_commit": 2}
        :param remove_keys: List of keys to remove from the db_options
        :return:
            bool: indicating whether db restart is required or not
        """
        if remove_keys is None:
            remove_keys = []

        existing_options = self.db_options.copy()

        is_valid, updated_config, errors, restart_required = validate_config(existing_options, updates, remove_keys, self.model.service, self.minor_version)
        if not is_valid:
            error_msg = "Invalid configuration changes:\n"
            for var_name, error in errors.items():
                error_msg += f"{var_name}: {error}\n"
            raise ValueError(error_msg)

        # Write in rds.conf file
        mysql_config_path = Path(self.config_path) / "rds.cnf"
        with open(mysql_config_path, "w") as f:
            f.write(render_template("mysql/config/rds.cnf", {
            **self.model.metadata_json,
            "db_options": updated_config,
        }))

        # Update in backend db
        self.update(metadata={
            **self.model.metadata_json,
            "db_options": updated_config,
        })
        self.db_options = updated_config

        if restart_required:
            return True

        if not updated_config:
            return False

        try:
            # Open a new connection to apply the changes
            with self.db_conn as conn:
                for key, value in updated_config.items():
                    conn.query(f"SET GLOBAL {key} = %s", (value,))
            # As most of the changes are dynamic, we don't need to restart the MySQL instance.
            return False
        except Exception as e:
            print(f"Failed to apply changes to the running MySQL instance: {e}")
            # As it is failed to apply changes, we will return True to indicate that restart is required.
            return True

    @property
    def minor_version(self) -> str:
        if not self.model.tag or self.model.tag == "latest":
            return "latest"
        parts = self.model.tag.split(".")
        if len(parts) < 2:
            return "latest"
        return parts[0] + "." + parts[1]

    @staticmethod
    def get_all(**kwargs) -> list[str]:
        return SystemdService.get_all(["mariadb", "mysql"],  **kwargs)

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
