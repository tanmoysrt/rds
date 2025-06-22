redis: redis-server
worker: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec rq worker'
scheduler: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec rqscheduler -H localhost -p 6379 -d 0 --interval 60'
server: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec python -u -m server.main'
health-monitor: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec python -u -m server.monitor.health'
state-monitor: bash -c 'until nc -z localhost 6379; do echo "Waiting for Redis..."; sleep 1; done; exec python -u -m server.monitor.state'
