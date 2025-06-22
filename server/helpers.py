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
from typing import Literal

import paramiko
from etcd3.events import Event as ETcd3Event
from jinja2 import Template

from generated.extras_pb2 import DBHealthStatus
from server import ServerConfig
from server.internal.config import ClusterConfig
from server.internal.db.models import SystemdServiceModel
from server.internal.db_client import DatabaseClient
from server.internal.etcd_client import Etcd3Client


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


def is_cluster_in_use(cluster_id:str) -> bool:
    return SystemdServiceModel.select(SystemdServiceModel.id).where(SystemdServiceModel.cluster_id != cluster_id).exists()

def get_working_etcd_cred_of_cluster(cluster_id: str) -> tuple[str, str]:
    """
    Retrieves the etcd username and password for a given cluster ID.
    Returns a tuple of (username, password).
    """

    credentials = SystemdServiceModel.select(SystemdServiceModel.etcd_username, SystemdServiceModel.etcd_password).where(SystemdServiceModel.cluster_id == cluster_id).tuples()
    if not credentials:
        raise ValueError(f"No etcd credentials found for cluster ID: {cluster_id}")

    server_config = ServerConfig()

    # Now, try each one until we find a working one
    def is_etcd_cred_working(cred_username: str, cred_password: str) -> bool:
        try:
            # Attempt to connect to etcd with the provided credentials
            with Etcd3Client(
                addresses=[f"{server_config.etcd_host}:{server_config.etcd_port}"],
                user=cred_username,
                password=password,
                timeout=2,
            ) as client:
                status = client.status()
                assert(status.version is not None), "Failed to get etcd status"
                assert(status.leader is not None), "Failed to get etcd leader"
                return True
        except Exception:
            return False

    for username, password in credentials:
        if is_etcd_cred_working(username, password):
            return username, password

    raise ValueError(f"No working etcd credentials found for cluster ID: {cluster_id}")


class KVEvent:
    def __init__(self, action:Literal["update", "delete"], cluster_id:str):
        self.action = action # type: Literal["update", "delete"]
        self.cluster_id = cluster_id
        self.event_type = None # type: Literal["config", "status"] | None
        self.data: ClusterConfig|DBHealthStatus|None= None
        self.node_id: str|None = None

    def __repr__(self):
        return f"""
KVEvent - {self.action} - {self.event_type}
Cluster : {self.cluster_id}
Node : {self.node_id}
Data : {self.data}
"""


def parse_etcd_watch_event(event:ETcd3Event) -> KVEvent|None:
    try:
        key:str = event.key.decode('utf-8')
        key_parts = key.split('/')
        if len(key_parts) < 4:
            return None

        cluster_id = key_parts[2]
        subject = key_parts[3]

        e = KVEvent(
            action="update" if event.__class__.__name__ == "PutEvent" else "delete",
            cluster_id=cluster_id,
        )

        if subject == "config":
            e.event_type = "config"
            e.data = ClusterConfig.from_serialized_string(event.value, cluster_id)
            return e

        if subject == "nodes" and len(key_parts) == 6:
            e.node_id = key_parts[4]
            e.event_type = key_parts[5]
            if e.event_type == "status":
                status = DBHealthStatus()
                status.ParseFromString(event.value)
                e.data = status
            return e
    except Exception as e:
        print(f"Failed to parse watch event: {e}")
        return None


def get_db_client_from_cluster_config(
    cluster_config:ClusterConfig, node_id:str, timeout:int=5, autocommit:bool=False
) -> DatabaseClient:
    """
    Returns a database client for the given node_id and db_type.
    If the node_id is not found in the cluster config, raises ValueError.
    """
    node = cluster_config.get_node(node_id)
    return DatabaseClient(
        db_type="mysql", # TODO: cluster config need to have the type
        autocommit=autocommit,
        host=node.ip,
        port=node.db_port,
        user=cluster_config.replication_user,
        password=cluster_config.replication_password,
    )