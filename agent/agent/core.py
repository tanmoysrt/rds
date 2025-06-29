import asyncio
import logging
import signal
import sys
import threading

from agent import ServerConfig


class GracefulShutdown:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.async_loop = None

    def signal_handler(self, signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        self.shutdown_event.set()
        if self.async_loop and self.async_loop.is_running():
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)


def run_grpc_server(shutdown_event: threading.Event, server_holder: dict):
    from agent.internal.server import init_server

    try:
        server = init_server()
        server_holder['server'] = server
        server.start()

        config = ServerConfig()
        logging.info(f"gRPC server started on port {config.grpc_port}")

        while not shutdown_event.is_set():
            try:
                if hasattr(server, 'wait_for_termination'):
                    server.wait_for_termination(timeout=1.0)
                else:
                    shutdown_event.wait(1.0)
            except Exception as e:
                logging.error(f"gRPC server error: {e}")
                break

        logging.info("Stopping gRPC server...")
        if hasattr(server, 'stop'):
            server.stop(grace=5.0)

    except Exception as e:
        logging.error(f"Failed to start gRPC server: {e}")
        shutdown_event.set()


async def run_state_managers(shutdown_event: threading.Event):
    from agent.monitor.health import MySQLHealthCheckMonitor
    from agent.monitor.state import EtcdStateMonitor

    state_monitor = EtcdStateMonitor()
    health_monitor = MySQLHealthCheckMonitor()

    state_monitor.schedule_auto_sync_proxysql_backend_servers()
    state_monitor.schedule_auto_sync_proxysql_users()

    tasks = [
        asyncio.create_task(health_monitor.run(), name="health_monitor"),
        asyncio.create_task(state_monitor.run(), name="state_monitor"),
    ]

    async def check_shutdown():
        while not shutdown_event.is_set():
            await asyncio.sleep(0.1)
        logging.info("Shutdown requested, cancelling tasks...")

    shutdown_task = asyncio.create_task(check_shutdown(), name="shutdown_monitor")
    all_tasks = tasks + [shutdown_task]

    try:
        done, pending = await asyncio.wait(all_tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        if pending:
            await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)

        for task in done:
            if not task.cancelled() and task.exception():
                logging.error(f"Task {task.get_name()} failed: {task.exception()}")
                raise task.exception()

    except asyncio.CancelledError:
        logging.info("Tasks cancelled during shutdown")
    except Exception as e:
        logging.error(f"Fatal error in state managers: {e}")
        shutdown_event.set()
        raise


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    shutdown_handler = GracefulShutdown()
    server_holder = {}

    signal.signal(signal.SIGINT, shutdown_handler.signal_handler)
    signal.signal(signal.SIGTERM, shutdown_handler.signal_handler)

    grpc_thread = threading.Thread(
        target=run_grpc_server,
        args=(shutdown_handler.shutdown_event, server_holder),
        name="grpc-server",
        daemon=True
    )

    exit_code = 0
    try:
        grpc_thread.start()
        logging.info("Started gRPC server thread")

        shutdown_handler.async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(shutdown_handler.async_loop)

        shutdown_handler.async_loop.run_until_complete(
            run_state_managers(shutdown_handler.shutdown_event)
        )
        logging.info("Async managers completed")

    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        exit_code = 1
    finally:
        logging.info("Cleaning up...")
        shutdown_handler.shutdown_event.set()

        if grpc_thread.is_alive():
            grpc_thread.join(timeout=10.0)
            if grpc_thread.is_alive():
                logging.warning("gRPC thread did not terminate")

        if 'server' in server_holder and hasattr(server_holder['server'], 'stop'):
            try:
                server_holder['server'].stop(grace=0)
            except Exception as e:
                logging.error(f"Error stopping gRPC server: {e}")

        logging.info("Shutdown complete")
        if exit_code != 0:
            sys.exit(exit_code)


if __name__ == "__main__":
    main()
