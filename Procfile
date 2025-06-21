redis: redis-server
server: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec python -u -m server.main'
worker: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec rq worker'
db-health: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec python -u -m server.monitor.mysql'
kv-watcher: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec python -u -m server.monitor.etcd'