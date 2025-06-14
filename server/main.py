import signal
import sys

from server import ServerConfig
from server.internal.server import init_server


def shutdown(signum, frame):
    print(f"\nReceived signal {signum}, shutting down server")
    server.stop(grace=0)
    sys.exit(0)

if __name__ == "__main__":
    server = init_server()
    config = ServerConfig()
    server.add_insecure_port(f"[::]:{config.grpc_port}")
    server.start()
    print("Server running on port ", config.grpc_port)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.wait_for_termination()
