redis: redis-server
server: python -u -m server.main
worker: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; rq worker'
db-health: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; python -u -m server.monitor.mysql'