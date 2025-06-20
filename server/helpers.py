import contextlib
import hashlib
import logging
import os
import random
import secrets
import socket
import string
import time
from pathlib import Path

import paramiko
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

def generate_random_string(length:int=32) -> str:
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

def generate_mysql_password_hash(password:str, append_asterisk:bool=True) -> str:
    first_hash = hashlib.sha1(password.encode()).digest()
    second_hash = hashlib.sha1(first_hash).digest()
    actual_hash = second_hash.hex().upper()
    if append_asterisk:
        """
        In MySQL, the password hash is typically stored with an asterisk at the start
        to indicate that it is a hashed password. This is a convention used by MySQL/MariaDB/ProxySQL.
        """
        actual_hash = '*' + actual_hash
    return actual_hash

def _is_port_open(ip: str, port: int, timeout_sec: float = 1.0) -> bool:
    """Fast port connectivity check using raw socket."""
    try:
        with socket.create_connection((ip, port), timeout=timeout_sec):
            return True
    except (socket.timeout, OSError):
        return False

paramiko_fake_logger = logging.getLogger("paramiko_fake_logger")
paramiko_fake_logger.disabled = True


def wait_for_ssh_daemon(ip: str, port: int, username: str, password: str, timeout: int):
    """
    Waits for the SSH daemon to become active by attempting to connect repeatedly
    until a successful connection is made or the timeout is reached.
    """
    ssh_connection_active = False
    start_time = time.time()

    while time.time() - start_time < timeout:
        if _is_port_open(ip, port, timeout_sec=0.5):
            break
        time.sleep(0.5)
    else:
        raise Exception(f"Port {port} did not open within {timeout} seconds")

    ssh = paramiko.SSHClient()
    ssh.set_log_channel(paramiko_fake_logger.name)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    while time.time() - start_time < timeout:
        try:
            ssh.connect(
                hostname=ip,
                port=port,
                username=username,
                password=password,
                timeout=1,
                auth_timeout=1,
                banner_timeout=1,
                look_for_keys=False,
                allow_agent=False,
                key_filename=None
            )
            ssh.close()
            ssh_connection_active = True
            break
        except Exception:
            time.sleep(0.2)  # Retry after 1 second
            print(f"Failed to connect to {ip}:{port}")
        finally:
            if 'sock' in locals():
                with contextlib.suppress(Exception):
                    sock.close()

    if not ssh_connection_active:
        raise Exception(f"SSH daemon did not become active within {timeout} seconds")

