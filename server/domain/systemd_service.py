import enum
import os
import subprocess
import uuid
from pathlib import Path

from jinja2 import Template

from server.helpers import modify_systemctl_commands_for_user_mode
from server.internal.db.models import SystemdServiceModel


class ServiceStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"

class SystemdService:
    @classmethod
    def create(cls, image:str, tag:str, environment_variables:dict[str, str], mounts:dict[str,str], podman_args:list[str], service_id:str|None=None):
        service = SystemdServiceModel.create(
            id=service_id or str(uuid.uuid4()),
            image=image,
            tag=tag,
            environment_variables_json=environment_variables,
            mounts_json=mounts,
            podman_args_json=podman_args
        )
        return cls(service.id)

    def __init__(self, record_id:str):
        self.model: SystemdServiceModel = SystemdServiceModel.get_by_id(record_id)

    def start(self):
        return self._deploy()

    def stop(self):
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

    def update(self, image:str|None=None, tag:str|None=None, environment_variables:dict[str,str]|None=None, mounts:dict[str,str]|None=None, podman_args:list[str]|None=None):
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
        self.model.save()
        self._deploy()


    def _deploy(self):
        # Create the service file
        quadlet_path = self.quadlet_file_path
        quadlet_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.service_file_content
        with open(quadlet_path, "w") as f:
            f.write(content)

        # Deploy the service using systemctl
        commands = [
            ["systemctl", "daemon-reload", True],
            ["systemctl", "restart", self.model.id, True],
        ]
        modify_systemctl_commands_for_user_mode(commands)
        for command in commands:
            subprocess.run(command[:-1], check=command[-1])


    @property
    def quadlet_file_path(self) -> Path:
        return Path(f"~/.config/containers/systemd/{self.model.id}.container").expanduser()

    @property
    def service_file_content(self):
        args = {
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
        }
        template_path = Path(__file__).parent.parent / "templates/quadlet.container"
        template_text = template_path.read_text()
        template = Template(template_text)
        return template.render(**args)


