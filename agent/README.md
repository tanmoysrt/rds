RDS

```bash
podman run --rm -it \
  -v /run/user/1000/bus:/run/user/1000/bus \
  -v /run/user/1000/systemd:/run/user/1000/systemd \
  -e DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  -v $XDG_RUNTIME_DIR/podman/podman.sock:/run/podman/podman.sock \
  -e CONTAINER_HOST=unix:/run/podman/podman.sock \
  -v <agent-config-folder>:/app/data/agent \
  -v <sevrice-data-folder>:/app/data/services \
  cargo-agent:latest
```


podman run --rm -it \
  --net host \
  -v /run/user/1000/bus:/run/user/1000/bus \
  -v /run/user/1000/systemd:/run/user/1000/systemd \
  -e DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
  -v $XDG_RUNTIME_DIR/podman/podman.sock:/run/podman/podman.sock \
  -e CONTAINER_HOST=unix:/run/podman/podman.sock \
  -v /home/tanmoy/Desktop/frappe/test/test/agent:/app/data/agent \
  -v /home/tanmoy/Desktop/frappe/test/test/services:/app/data/services \
  cargo-agent:latest