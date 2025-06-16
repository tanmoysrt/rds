import os
import random
import secrets
import socket
import string
from pathlib import Path

from jinja2 import Template


def render_template(template:str, payload:dict) -> str:
    template_path = Path(__file__).parent / "templates" / template
    template = Template(template_path.read_text())
    return template.render(**payload)

def modify_systemctl_commands_for_user_mode( commands:list[list[str]]):
    uid = os.getuid()
    if uid == 0:
        return

    for command in commands:
        command.insert(1, "--user")

def generate_random_password(length:int=16) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def find_available_port(start_port:int=0, end_port:int=30000, exclude_ports:set[int]=None) -> int:
    if not start_port:
        start_port = random.randint(10000, 20000)

    if end_port < start_port:
        raise ValueError("end_port must be greater than or equal to start_port")

    for port in range(start_port, end_port + 1):
        if exclude_ports and port in exclude_ports:
            continue
        if is_port_available(port):
            return port

    raise RuntimeError(f"No available ports found between {start_port} and {end_port}.")

def is_port_available(port:int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

