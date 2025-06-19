import contextlib
import random
import time
from pathlib import Path
from typing import override

from generated.extras_pb2 import DBHealthStatus, DBType
from server import ServerConfig
from server.domain.systemd_service import SystemdService
from server.helpers import (
    find_available_port,
    generate_mysql_password_hash,
    render_template,
)
from server.internal.db_client import DatabaseClient
from server.internal.utils import get_redis_client


class MySQL(SystemdService):
    @classmethod
    def create(cls, service_id:str, base_path:str, image:str, tag:str, cluster_id:str, root_password:str, server_id:int|None=None, db_port:int|None=None, service:str="mariadb", etcd_username:str|None=None, etcd_password:str|None=None, **kwargs):
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

        # Generate script and initial configuration files
        init_script_path = init_dir_path / "01-secure-mysql-root-user.sql"
        if not init_script_path.exists():
            with open(init_script_path, "w") as f:
                f.write(render_template("mysql/init_scripts/01-secure-mysql-root-user.sql", metadata))

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
            redis.publish(ServerConfig().mysql_monitor_commands_redis_channel, f"add {record.model.id}")

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

    @override
    def delete(self):
        super().delete()
        with contextlib.suppress(Exception):
            # Publish the command to pubsub to notify monitoring services to stop monitoring this MySQL instance
            redis = get_redis_client()
            redis.publish(ServerConfig().mysql_monitor_commands_redis_channel, f"remove {self.model.id}")

    @override
    def get_health_info(self) -> (bool, DBHealthStatus | None):
        """
        Fetch gtid from the database to check health
        + getting the info of replication

        Try to use same db connection rather than creating a new one each time.
        """
        try:
            if not self._db_instance_for_health_check:
                self._db_instance_for_health_check = self.db_conn

            gtid = self._db_instance_for_health_check.query("SELECT @@gtid_current_pos")[0]["@@gtid_current_pos"]
            return True, DBHealthStatus(
                db_type=DBType.MYSQL if self.model.service == "mysql" else DBType.MARIADB,
                reported_at=time.time_ns() // 1_000_000,
                global_transaction_id=gtid,
            )
        except Exception as e:
            print(e)
            return False, None

    @staticmethod
    def get_all(**kwargs) -> list[str]:
        return SystemdService.get_all(["mariadb", "mysql"])

    @override
    @property
    def db_conn(self):
        return DatabaseClient(
            db_type=self.model.service,
            host="127.0.0.1", # localhost does not work with same network namespace
            port=self.db_port,
            user="root",
            password=self.mysql_root_password,
            schema=""
        )
