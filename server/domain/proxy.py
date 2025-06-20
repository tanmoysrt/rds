from pathlib import Path
from typing import override

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


    @staticmethod
    def get_all(**kwargs) -> list[str]:
        return super().get_all(["proxysql"])

    @override
    @property
    def db_conn(self):
        return DatabaseClient(
            db_type=self.model.service,
            host="localhost",
            port=self.admin_port,
            user="admin",
            password=self.admin_password,
            schema=""
        )

