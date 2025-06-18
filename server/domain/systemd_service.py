import enum
import os
import subprocess
import uuid
from pathlib import Path

import etcd3

from server import ServerConfig
from server.domain.db_client import DatabaseClient
from server.helpers import modify_systemctl_commands_for_user_mode, render_template
from server.internal.db.models import SystemdServiceModel


class ServiceStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FAILED = "FAILED"

class SystemdService:
    @classmethod
    def create(cls, image:str, tag:str, environment_variables:dict[str, str], mounts:dict[str,str], podman_args:list[str], service_id:str|None=None, service:str="", metadata:dict[str, str]|None=None):
        if not isinstance(environment_variables, dict):
            raise ValueError("environment_variables must be a dictionary")
        if not isinstance(mounts, dict):
            raise ValueError("mounts must be a dictionary")
        if not isinstance(podman_args, list):
            raise ValueError("podman_args must be a list")

        service = SystemdServiceModel.create(
            id=service_id or str(uuid.uuid4()),
            image=image,
            tag=tag,
            environment_variables_json=environment_variables,
            mounts_json=mounts,
            podman_args_json=podman_args,
            metadata_json=metadata or {},
        )
        return cls(service.id)

    @classmethod
    def exists(cls, service_id:str) -> bool:
        return SystemdServiceModel.get_or_none(SystemdServiceModel.id == service_id) is not None

    def __init__(self, record_id:str):
        try:
            self.model: SystemdServiceModel = SystemdServiceModel.get_by_id(record_id)
        except SystemdServiceModel.DoesNotExist:
            raise ValueError(f"Service with id {record_id} does not exist")
        except Exception as e:
            raise e

    def start(self) -> None:
        self._deploy()

    def stop(self) -> None:
        commands = [
            ["systemctl", "stop", self.model.id, False],
            ["systemctl", "daemon-reload", True]
        ]
        modify_systemctl_commands_for_user_mode(commands)
        # Stop it
        subprocess.run(commands[0][:-1], check=commands[0][-1])
        # Remove file
        if self.quadlet_file_path.exists():
            os.remove(str(self.quadlet_file_path))
        # Daemon  reload
        subprocess.run(commands[1][:-1], check=commands[1][-1])

    def restart(self) -> None:
        commands = [
            ["systemctl", "daemon-reload", True],
            ["systemctl", "restart", self.model.id, True],        ]
        modify_systemctl_commands_for_user_mode(commands)
        for command in commands:
            subprocess.run(command[:-1], check=command[-1])

    @property
    def status(self):
        commands = [["systemctl", "show", self.model.id, "--property=ActiveState", "--value"]]
        modify_systemctl_commands_for_user_mode(commands)
        status = subprocess.run(commands[0], check=False, capture_output=True, text=True).stdout.strip()
        return {
            "active": ServiceStatus.ACTIVE,
            "inactive": ServiceStatus.INACTIVE,
            "activating": ServiceStatus.INACTIVE,
            "failed": ServiceStatus.FAILED,
        }.get(status, ServiceStatus.FAILED)

    def update(self, image:str|None=None, tag:str|None=None, environment_variables:dict[str,str]|None=None, mounts:dict[str,str]|None=None, podman_args:list[str]|None=None, metadata:dict[str,str]|None=None):
        if image is not None:
            self.model.image = image
        if tag is not None:
            self.model.tag = tag
        if environment_variables is not None:
            self.model.environment_variables_json = environment_variables
        if mounts is not None:
            self.model.mounts_json = mounts
        if podman_args is not None:
            self.model.podman_args_json = podman_args
        if metadata is not None:
            self.model.metadata_json = metadata
        self.model.save()
        self._deploy()

    def delete(self):
        if self.status == ServiceStatus.ACTIVE:
            raise Exception("Service is running, stop it before deleting")
        self.model.delete_instance()
        """
        Please Note:
        It's intentional to not removing the folders used by volume mount
        To prevent accidental data loss.
        
        Ansible should handle these cleanups.
        """

    def _deploy(self):
        # Create the service file
        quadlet_path = self.quadlet_file_path
        quadlet_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.service_file_content
        with open(quadlet_path, "w") as f:
            f.write(content)

        # Start the service
        self.restart()

    @property
    def quadlet_file_path(self) -> Path:
        return Path(f"~/.config/containers/systemd/{self.model.id}.container").expanduser()

    @property
    def service_file_content(self):
        return  render_template("quadlet.container", payload={
            "id": self.model.id,
            "image": self.model.image,
            "tag": self.model.tag if self.model.tag else "latest",
            "mounts": [{
                "source": i[0],
                "target": i[1]
            } for i in self.model.mounts_json.items()],
            "environment_variables": [{
                "key": i[0],
                "value": i[1]
            } for i in self.model.environment_variables_json.items()],
            "podman_args": self.model.podman_args_json,
        })

    @property
    def kv(self):
        config = ServerConfig()
        return etcd3.client(
            host=config.etcd_host,
            port=config.etcd_port,
            user=self.model.etcd_username,
            password=self.model.etcd_password
        )

    @property
    def db_conn(self) -> DatabaseClient:
        """
        Returns the instance of database client used by this service.
        """
        raise NotImplementedError("You must implement this method in the subclass")

    def check_health(self) -> (bool, dict):
        """
        Check the health of the service.
        :return:
            first value is a boolean indicating if the service is healthy
            second value is a dictionary containing health status information
        """
        raise NotImplementedError("You must implement this method in the subclass")

