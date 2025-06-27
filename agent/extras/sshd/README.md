It's a minimal docker image with openssh server installed.

# Usage

```bash
podman run -it --rm \
 -p 2222:2222 \
 -e SSH_PORT=2222 \
 -e USER_NAME=testuser \
 -e USER_PASSWORD=testpassword \
 -e USER_UID=1000 \
 -e USER_GID=1000 \
 -v ./:/data
 minimal-sshd
```

Mount the required files to `/data` directory to access them via SSH / Rsync.

This image supports `rsync`. `scp` or `sftp` will not work.

**NOTE :** Don't use `--userns=keep-id` for user namespace mapping because sshd does not perfectly work with non-root
user in rootless mode.
And you need to provide mapping for `root` user too.