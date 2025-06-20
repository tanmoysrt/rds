#!/bin/sh

set -euxo pipefail

: "${USER_NAME:?Must set USER_NAME}"
: "${USER_UID:?Must set USER_UID}"
: "${USER_GID:?Must set USER_GID}"
: "${USER_PASSWORD:?Must set USER_PASSWORD}"
: "${SSH_PORT:?Must set SSH_PORT}"

# Create group if missing
if ! getent group "$USER_GID" >/dev/null; then
  addgroup -g "$USER_GID" "$USER_NAME"
fi

# Create user if missing
if ! id "$USER_NAME" >/dev/null 2>&1; then
  adduser -D -u "$USER_UID" -G "$USER_NAME" -s /bin/sh "$USER_NAME"
fi

# Set password
echo "$USER_NAME:$USER_PASSWORD" | chpasswd

# Prepare .ssh and generate host keys if missing
gosu "$USER_NAME" mkdir -p /home/"$USER_NAME"/.ssh

if [ ! -f /home/"$USER_NAME"/.ssh/ssh_host_rsa_key ]; then
  gosu "$USER_NAME" ssh-keygen -t rsa -f /home/"$USER_NAME"/.ssh/ssh_host_rsa_key -N ''
  gosu "$USER_NAME" ssh-keygen -t ecdsa -f /home/"$USER_NAME"/.ssh/ssh_host_ecdsa_key -N ''
  gosu "$USER_NAME" ssh-keygen -t ed25519 -f /home/"$USER_NAME"/.ssh/ssh_host_ed25519_key -N ''
fi

# Write sshd_config dynamically
cat >/home/"$USER_NAME"/sshd_config <<EOF
Port $SSH_PORT
HostKey /home/$USER_NAME/.ssh/ssh_host_rsa_key
HostKey /home/$USER_NAME/.ssh/ssh_host_ecdsa_key
HostKey /home/$USER_NAME/.ssh/ssh_host_ed25519_key
PermitRootLogin no
PasswordAuthentication yes
ChallengeResponseAuthentication no
AllowUsers $USER_NAME
EOF

# Create writable run dir for sshd
RUN_DIR="/tmp/sshd_run"
mkdir -p "$RUN_DIR"
chown "$USER_UID:$USER_GID" "$RUN_DIR"

# Allow custom user to use sudo rsync
echo "$USER_NAME ALL=(ALL) NOPASSWD: /usr/bin/rsync" > /etc/sudoers.d/rsync_user
chmod 440 /etc/sudoers.d/rsync_user

# Lock root user
passwd -l root

# Run sshd as user with the generated config
exec /usr/sbin/sshd -D -e -f /home/"$USER_NAME"/sshd_config -o PidFile="$RUN_DIR/sshd.pid"