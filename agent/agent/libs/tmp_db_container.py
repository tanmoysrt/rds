import time
from typing import Literal

import docker
from docker import DockerClient

from agent.internal.db_client import DatabaseClient


class TmpDBContainer:
    def __init__(self, db_type:Literal["mysql", "mariadb"], tag:str="latest", root_password:str|None=None, db_user:str="test_user", db_password:str="test_password", auto_start:bool=False):
        self._docker_client: DockerClient|None = docker.from_env()
        self._id = None
        self._db_type:str = db_type
        self._image: str = db_type
        self._tag: str = tag
        self._ip: str|None = None
        self._port: int|None = None
        self.root_password: str|None = root_password
        self.db_user: str = db_user
        self.db_password: str = db_password
        if auto_start:
            self.start()
            self.wait_for_db_ready(timeout=60)

    @property
    def environment(self) -> dict[str, str]:
        env = {
            "MYSQL_ALLOW_EMPTY_PASSWORD": "yes" if self.root_password is None else None,
            "MYSQL_ROOT_PASSWORD": self.root_password,
            "MYSQL_USER": self.db_user,
            "MYSQL_PASSWORD": self.db_password,
        }
        return {k: str(v) for k, v in env.items() if v is not None}

    def start(self):
        if self._id:
            raise RuntimeError("Container is already running or has been started.")

        res = self._docker_client.containers.run(
            image=f"{self._image}:{self._tag}",
            environment=self.environment,
            detach=True,
        )
        self._id = res.id
        container_info = self._docker_client.containers.get(self._id)
        self._ip = container_info.attrs['NetworkSettings']['IPAddress']
        self._port = 3306  # Default MySQL port

    def remove(self):
        if not self._docker_client or not self._id:
            raise RuntimeError("Container is not running or has not been started.")
        container = self._docker_client.containers.get(self._id)
        container.remove(force=True, v=True)
        self._id = None

    def wait_for_log(self, log_message:str, timeout:int=60):
        end_time = time.time() + timeout
        while time.time() < end_time:
            logs = self.get_logs()
            if log_message in logs:
                return True
            time.sleep(1)
        raise TimeoutError(f"Log message '{log_message}' not found within {timeout} seconds.")

    def wait_for_db_ready(self, timeout:int=60):
        end_time = time.time() + timeout
        db_client = self.get_db()
        while time.time() < end_time:
            if db_client.is_reachable():
                return True
            time.sleep(1)
        raise TimeoutError(f"Database not ready within {timeout} seconds.")

    def get_logs(self):
        if not self._docker_client or not self._id:
            raise RuntimeError("Container is not running or has not been started.")
        container = self._docker_client.containers.get(self._id)
        return container.logs().decode('utf-8')

    def cleanup(self):
        if self._docker_client:
            try:
                if self._id:
                    self.remove()
                    self._docker_client.close()
            except Exception as e:
                print(f"Error during cleanup: {e}")

        self._docker_client = None
        self._id = None

    def get_db(self, username:str=None, password:str=None, schema:str="") -> DatabaseClient:
        username = username or "root"
        password = password or (self.root_password if username == "root" else self.db_password)

        return DatabaseClient(
            db_type=self._db_type,
            host=self._ip,
            port=self._port,
            autocommit=True,
            user=username,
            password=password,
            schema=schema
        )

    def __enter__(self) -> "TmpDBContainer":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def __del__(self):
        self.cleanup()

