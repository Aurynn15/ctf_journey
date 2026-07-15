#!/bin/sh
set -eu

mkdir -p /run/sshd /opt/ad/state
chown -R archivedesk:archivedesk /opt/ad/state

if command -v ssh-keygen >/dev/null 2>&1; then
  ssh-keygen -A >/dev/null 2>&1 || true
fi

cat >/etc/ssh/sshd_config.d/adplatform.conf <<'EOF'
PermitRootLogin yes
PasswordAuthentication yes
UsePAM no
ChallengeResponseAuthentication no
KbdInteractiveAuthentication no
PidFile /run/sshd.pid
EOF

if [ -n "${AD_PLATFORM_ROOT_PASSWORD:-}" ]; then
  printf 'root:%s\n' "$AD_PLATFORM_ROOT_PASSWORD" | chpasswd
elif [ -n "${AD_ROOT_PASSWORD:-}" ]; then
  printf 'root:%s\n' "$AD_ROOT_PASSWORD" | chpasswd
else
  passwd -l root >/dev/null 2>&1 || true
fi

printf '%s\n' "${AD_PLATFORM_UNLOCK_PROOF:-missing-unlock-proof}" >/proof.txt
chown root:root /proof.txt
chmod 0400 /proof.txt
touch /flag.txt
chown archivedesk:archivedesk /flag.txt
chmod 0600 /flag.txt

unset AD_PLATFORM_ROOT_PASSWORD AD_ROOT_PASSWORD AD_PLATFORM_UNLOCK_PROOF

/usr/sbin/sshd
exec su archivedesk -s /bin/sh -c "/app/archivedesk"
