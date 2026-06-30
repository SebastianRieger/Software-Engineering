#!/bin/bash
# Runs inside chroot (ARM64 Raspberry Pi OS environment)
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export HOME=/root
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

KIOSK_USER="nimrag"
KIOSK_PASS="Nimrag"

echo "=== [0/10] Creating user ${KIOSK_USER} ==="
# Remove default pi user if present
if id "pi" &>/dev/null; then
    userdel -r pi 2>/dev/null || true
fi
# Disable Pi OS first-boot user-setup wizard
systemctl disable userconfig.service  2>/dev/null || true
systemctl disable userconf.service    2>/dev/null || true
rm -f /etc/systemd/system/getty@tty1.service.d/autologin.conf 2>/dev/null || true

# Create kiosk user
useradd -m -s /bin/bash "${KIOSK_USER}"
echo "${KIOSK_USER}:${KIOSK_PASS}" | chpasswd

# Set hostname
echo "${KIOSK_USER}" > /etc/hostname
sed -i "s/raspberrypi/${KIOSK_USER}/g" /etc/hosts 2>/dev/null || true

echo "=== [1/10] Updating packages ==="
apt-get update -qq
apt-get upgrade -y -qq

echo "=== [2/10] Installing packages ==="
apt-get install -y --no-install-recommends \
    git \
    curl \
    gnupg \
    openbox \
    xinit \
    x11-xserver-utils \
    unclutter \
    x11vnc \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    postgresql \
    postgresql-client \
    cloud-guest-utils \
    libicu-dev

# Node.js 20 via NodeSource
echo "=== [3/10] Installing Node.js 20 ==="
mkdir -p /etc/apt/keyrings
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list
apt-get update -qq
apt-get install -y nodejs

echo "=== [4/10] Configuring network ==="
# Static IP on eth0, DHCP on wlan0
cat >> /etc/dhcpcd.conf << 'DHCPCD'

# Static IP on Ethernet
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

# DHCP on WiFi (lower priority)
interface wlan0
metric 200
DHCPCD

# WiFi: copy wpa_supplicant.conf from /boot/firmware on first boot if present
cat > /etc/systemd/system/wifi-provision.service << 'EOF'
[Unit]
Description=Import WiFi credentials from boot partition
ConditionPathExists=/boot/firmware/wpa_supplicant.conf
DefaultDependencies=no
Before=wpa_supplicant.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c '\
    cp /boot/firmware/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf && \
    chmod 600 /etc/wpa_supplicant/wpa_supplicant.conf && \
    rm /boot/firmware/wpa_supplicant.conf'

[Install]
WantedBy=multi-user.target
EOF
systemctl enable wifi-provision.service

echo "=== [5/10] Configuring kiosk display ==="
# Disable default desktop manager, use TTY1 autologin + startx instead
systemctl disable lightdm.service 2>/dev/null || true

mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin nimrag --noclear %I $TERM
EOF

# Start X automatically on TTY1 login
cat > "/home/${KIOSK_USER}/.bash_profile" << 'EOF'
if [ "$(tty)" = "/dev/tty1" ]; then
    exec startx -- -nocursor 2>/tmp/x11.log
fi
EOF
chown "${KIOSK_USER}:${KIOSK_USER}" "/home/${KIOSK_USER}/.bash_profile"

# Kiosk session: wait for backend + frontend, then launch Chromium
cat > "/home/${KIOSK_USER}/.xinitrc" << 'XINITRC'
#!/bin/bash

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide cursor after 0.5s inactivity
unclutter -idle 0.5 -root &

# Minimal window manager
openbox &

# VNC access (port 5900, no password)
x11vnc -display :0 -forever -nopw -rfbport 5900 -o /tmp/x11vnc.log &

# Wait for backend (FastAPI on port 8000)
echo "Waiting for Nimrag backend..."
until curl -s http://localhost:8000 > /dev/null 2>&1; do sleep 3; done

# Wait for frontend (Vite on port 5173)
echo "Waiting for Nimrag frontend..."
until curl -s http://localhost:5173 > /dev/null 2>&1; do sleep 3; done

# Launch Chromium in kiosk mode, restart on crash
while true; do
    chromium-browser \
        --kiosk \
        --no-sandbox \
        --disable-infobars \
        --disable-session-crashed-bubble \
        --disable-restore-session-state \
        --disable-background-networking \
        --disable-default-apps \
        --no-first-run \
        --app=http://localhost:5173
    sleep 5
done
XINITRC
chmod +x "/home/${KIOSK_USER}/.xinitrc"
chown "${KIOSK_USER}:${KIOSK_USER}" "/home/${KIOSK_USER}/.xinitrc"

echo "=== [6/10] Cloning Nimrag repository ==="
git clone --depth 1 -b dev \
    https://github.com/SebastianRieger/Software-Engineering \
    /opt/nimrag
chown -R "${KIOSK_USER}:${KIOSK_USER}" /opt/nimrag

# Backend .env
cat > /opt/nimrag/Backend/.env << 'ENVFILE'
DATABASE_URL=postgresql+asyncpg://nimrag:nimrag@localhost/nimrag_db
JWT_SECRET_KEY=change-me-before-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVFILE
chown "${KIOSK_USER}:${KIOSK_USER}" /opt/nimrag/Backend/.env

echo "=== [7/10] Installing Python dependencies ==="
python3 -c "
import re
txt = open('/opt/nimrag/Backend/requirements.txt').read()
# Strip hash verification
txt = re.sub(r'[ \t]*\\\\\n[ \t]*--hash=sha256:[0-9a-f]+', '', txt)
txt = re.sub(r'^--require-hashes\n?', '', txt, flags=re.MULTILINE)
# Remove packages with no ARM64 wheels
no_arm64 = ['mediapipe', 'aubio']
lines = [l for l in txt.splitlines() if not any(l.strip().startswith(p) for p in no_arm64)]
open('/tmp/req.txt', 'w').write('\n'.join(lines))
" && echo "Skipped (no ARM64 wheels): mediapipe, aubio"

python3 -m venv /opt/nimrag/venv
/opt/nimrag/venv/bin/pip install --upgrade pip wheel
/opt/nimrag/venv/bin/pip install --prefer-binary \
    --extra-index-url https://www.piwheels.org/simple \
    numpy
/opt/nimrag/venv/bin/pip install --prefer-binary \
    --extra-index-url https://www.piwheels.org/simple \
    -r /tmp/req.txt

echo "=== [8/10] Installing Node.js dependencies ==="
cd /opt/nimrag/Frontend/nimrag-frontend
npm install
chown -R "${KIOSK_USER}:${KIOSK_USER}" /opt/nimrag

echo "=== [9/10] Setting up PostgreSQL ==="
PGVER=$(ls /var/lib/postgresql/ | sort -V | tail -1)
mkdir -p /run/postgresql
chown postgres:postgres /run/postgresql
su -s /bin/bash postgres -c "pg_ctlcluster ${PGVER} main start"
sleep 3

su -s /bin/bash postgres -c "
    psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='nimrag'\" | grep -q 1 \
        || psql -c \"CREATE USER nimrag WITH PASSWORD 'nimrag';\"
    psql -lqt | cut -d'|' -f1 | grep -qw nimrag_db \
        || psql -c \"CREATE DATABASE nimrag_db OWNER nimrag;\"
"

if [ -f /opt/nimrag/Backend/alembic.ini ]; then
    cd /opt/nimrag/Backend
elif [ -f /opt/nimrag/Backend/src/alembic.ini ]; then
    cd /opt/nimrag/Backend/src
fi
DATABASE_URL=postgresql+asyncpg://nimrag:nimrag@localhost/nimrag_db \
    /opt/nimrag/venv/bin/alembic upgrade head || echo "WARNING: migrations skipped"

su -s /bin/bash postgres -c "pg_ctlcluster ${PGVER} main stop" || true
sleep 2

echo "=== [10/10] Enabling services ==="
cat > /etc/systemd/system/nimrag-backend.service << 'EOF'
[Unit]
Description=Nimrag Backend (FastAPI/Uvicorn)
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=nimrag
WorkingDirectory=/opt/nimrag/Backend/src
EnvironmentFile=/opt/nimrag/Backend/.env
ExecStart=/opt/nimrag/venv/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/nimrag-frontend.service << 'EOF'
[Unit]
Description=Nimrag Frontend (Vite dev server)
After=network.target

[Service]
Type=simple
User=nimrag
WorkingDirectory=/opt/nimrag/Frontend/nimrag-frontend
Environment=HOME=/home/nimrag
ExecStart=/usr/bin/npm run dev
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl enable postgresql.service
systemctl enable nimrag-backend.service
systemctl enable nimrag-frontend.service
systemctl enable avahi-daemon.service

for GRP in adm audio video sudo plugdev input netdev dialout; do
    adduser "${KIOSK_USER}" "${GRP}" 2>/dev/null || true
done

# Cleanup
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -f /tmp/req.txt

echo ""
echo "=== Customization complete ==="
