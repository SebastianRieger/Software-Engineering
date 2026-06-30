# Nimrag Kiosk Image Builder

## For users (download and flash the image)

This repository produces a preconfigured Raspberry Pi OS image for the Nimrag Kiosk system. If you only want to flash the image onto an SD card, you do not need to build it yourself.

### What the image contains

- **User:** `nimrag` / password `Nimrag` (the default `pi` user is removed)
- **Hostname:** `nimrag`
- **Static IP on eth0:** `192.168.1.100/24`, gateway `192.168.1.1`, DNS `8.8.8.8` / `8.8.4.4`
- **WiFi:** DHCP (credentials can be provisioned via `/boot/firmware/wpa_supplicant.conf`)
- **Stack:** PostgreSQL, FastAPI backend, Vite/Node.js frontend, Chromium in kiosk mode
- **VNC access:** port 5900, no password (`x11vnc`)
- **Output file:** `output/Nimrag_Kiosk.img.gz`

### Connect to the Pi

Connect the Pi via LAN (eth0):

- SSH: `ssh nimrag@192.168.1.100`
- Password: `Nimrag`
- VNC: `192.168.1.100:5900`

Your PC network adapter must be in the `192.168.1.x` subnet (e.g. `192.168.1.10/24`).

### Provision WiFi credentials

Place a `wpa_supplicant.conf` on the boot partition (`/boot/firmware/`) before first boot.  
The `wifi-provision.service` copies it to `/etc/wpa_supplicant/wpa_supplicant.conf` automatically on startup and then removes it from the boot partition.

```ini
country=DE
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="YourSSID"
    psk="YourPassword"
}
```

---

## For developers (build, extend, architecture)

### 1. Architecture overview

The build runs entirely inside Docker on Linux. It takes the official Raspberry Pi OS Desktop image, mounts it via a loop device, customizes the rootfs using QEMU ARM64 emulation, and produces a compressed `.img.gz`.

```
start.ps1 / build.sh
    ↓
docker compose up --build
    ↓
Dockerfile  →  nimrag-imagegen:latest
    ↓
run-build.sh  (inside container, as root)
    ├── Download Raspberry Pi OS Desktop (arm64) [cached in ./cache/]
    ├── Extract + expand image (+4 GB)
    ├── losetup / kpartx → attach partitions
    ├── resize2fs → extend root partition
    ├── Mount rootfs + proc/sys/dev/run
    ├── Copy qemu-aarch64-static → chroot ARM64 emulation
    ├── chroot → customize.sh
    │       ├── [0] Create user nimrag, remove pi, set hostname
    │       ├── [1] apt-get upgrade
    │       ├── [2] Install packages (openbox, x11vnc, postgresql, …)
    │       ├── [3] Install Node.js 20 (NodeSource)
    │       ├── [4] Configure network (static eth0, DHCP wlan0)
    │       ├── [5] Configure kiosk display (autologin TTY1, Chromium)
    │       ├── [6] Clone Nimrag repository → /opt/nimrag
    │       ├── [7] Install Python dependencies (piwheels)
    │       ├── [8] npm install (frontend)
    │       ├── [9] Setup PostgreSQL (user + DB + migrations)
    │       └── [10] Enable systemd services
    ├── Unmount + detach loop
    └── pigz -9 → Nimrag_Kiosk.img.gz
```

Output: `output/Nimrag_Kiosk.img.gz`

---

### 2. Prerequisites

**Linux host (or WSL2 with Docker Desktop):**

- Docker + Docker Compose v2
- The host kernel must support `loop` devices and `kpartx` (standard on Linux; provided by Docker Desktop on Windows)

**Windows:**

Run `start.ps1` — Docker Desktop handles the rest.

---

### 3. Build

**Linux:**
```bash
cd raspi_image_creation/art_image_creator
bash build.sh
```

**Windows (PowerShell):**
```powershell
cd raspi_image_creation\art_image_creator
.\start.ps1
```

Both scripts create the output directories and run `docker compose up --build`.

**First build:** downloads Raspberry Pi OS Desktop (~1 GB) and all packages (~20 min).  
**Subsequent builds:** Pi OS is cached in `./cache/`; only Docker image rebuild + customization (~10–15 min).

The finished image is at: `art_image_creator/output/Nimrag_Kiosk.img.gz`

---

### 4. Important files

#### 4.1 `build.sh`
Entry point on Linux. Creates directories, then calls `docker compose up --build`.

#### 4.2 `start.ps1`
Entry point on Windows. Same as `build.sh` but PowerShell syntax.

#### 4.3 `docker-compose.yml`
Defines the build service `kiosk_imagegen` (image `nimrag-imagegen:latest`).

Key settings:
- `privileged: true` — required for loop devices and chroot
- `user: root` — required for mount operations
- Volume `./output:/output` — build artifacts appear here on the host
- Volume `./cache:/cache` — Pi OS download cache

#### 4.4 `Dockerfile`
Builds the tool container from `debian:bookworm`. Installs:
`qemu-user-static`, `binfmt-support`, `kpartx`, `parted`, `e2fsprogs`, `dosfstools`, `pigz`, `xz-utils`

Copies `run-build.sh` and `customize.sh` into the image.

#### 4.5 `run-build.sh`
Main build logic (runs as root inside the container). Downloads Pi OS if not cached, extracts it, expands and resizes the image, mounts all filesystems, runs `customize.sh` inside chroot, then compresses the result.

**Key variables (top of file):**
```bash
IMAGE_NAME="Nimrag_Kiosk"
RPIOS_URL="https://downloads.raspberrypi.com/raspios_arm64_latest"
RPIOS_CACHE="${CACHE_DIR}/rpios-desktop-arm64.img.xz"
```

#### 4.6 `customize.sh`
Runs inside the ARM64 chroot. Contains all system configuration in 10 numbered steps (see architecture overview above).

**Key variables (top of file):**
```bash
KIOSK_USER="nimrag"
KIOSK_PASS="Nimrag"
```

---

### 5. Services on the Pi

After boot the following systemd services are active:

| Service | Description |
|---|---|
| `postgresql.service` | PostgreSQL database |
| `nimrag-backend.service` | FastAPI/Uvicorn backend on port 8000 |
| `nimrag-frontend.service` | Vite dev server on port 5173 |
| `avahi-daemon.service` | mDNS/Bonjour for network discovery |
| `wifi-provision.service` | Copies WiFi credentials from boot partition |

The Chromium kiosk session (in `~nimrag/.xinitrc`) waits for the backend (port 8000) and frontend (port 5173) to respond before launching.

---

### 6. Application

The Nimrag application is cloned from:
```
https://github.com/SebastianRieger/Software-Engineering  (branch: dev)
```
Target directory on the Pi: `/opt/nimrag/`

**Structure:**
```
/opt/nimrag/
├── Backend/          ← FastAPI app
│   ├── .env          ← database URL, JWT config
│   └── src/main.py   ← Uvicorn entry point
└── Frontend/
    └── nimrag-frontend/  ← Vite app (npm run dev)
```

**Backend `.env` (baked in at build time):**
```env
DATABASE_URL=postgresql+asyncpg://nimrag:nimrag@localhost/nimrag_db
JWT_SECRET_KEY=change-me-before-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**PostgreSQL:**
- User: `nimrag` / password `nimrag`
- Database: `nimrag_db`
- Alembic migrations run automatically during the build

---

### 7. Change users or credentials

All credentials are hardcoded in [art_image_creator/customize.sh](art_image_creator/customize.sh). Edit the variables at the top:

```bash
KIOSK_USER="nimrag"
KIOSK_PASS="Nimrag"
```

For the database/JWT credentials, change the `.env` block in Step 6 of `customize.sh`:
```bash
cat > /opt/nimrag/Backend/.env << 'ENVFILE'
DATABASE_URL=postgresql+asyncpg://nimrag:nimrag@localhost/nimrag_db
JWT_SECRET_KEY=your-secret-here
...
ENVFILE
```

Then rebuild the image.

---

### 8. Change the network configuration

Edit the network block in Step 4 of [art_image_creator/customize.sh](art_image_creator/customize.sh):

```bash
# Static IP on Ethernet
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4
```

**Use DHCP on eth0 instead:**
Remove the `interface eth0` block entirely and keep only the `wlan0` section.

---

### 9. Add or change packages

#### APT packages
Add to the `apt-get install` block in Step 2 of [art_image_creator/customize.sh](art_image_creator/customize.sh):
```bash
apt-get install -y --no-install-recommends \
    ...
    your-new-package
```

#### Python packages
Add to `/tmp/req.txt` processing in Step 7, or add a separate pip install line:
```bash
/opt/nimrag/venv/bin/pip install --prefer-binary \
    --extra-index-url https://www.piwheels.org/simple \
    your-package
```

Note: `mediapipe` and `aubio` are explicitly excluded because they have no ARM64 wheels.

#### Node.js packages
Add them to the `Frontend/nimrag-frontend/package.json` in the repository before building, or add an `npm install <pkg>` line after Step 8 in `customize.sh`.

---

### 10. Troubleshooting

#### Build fails with "Operation not permitted" or loop device errors
The container must run with `privileged: true`. Check `docker-compose.yml`.

#### `exec format error` inside chroot
`qemu-user-static` is not registered with `binfmt_misc`. This is handled by `dpkg-reconfigure qemu-user-static` in the Dockerfile. Rebuild the Docker image.

#### Pi OS download is slow / fails
The image is cached in `./cache/rpios-desktop-arm64.img.xz` after the first download.  
If the file is corrupted, delete it and rebuild.

#### Chromium does not start
- Backend may not be running: `systemctl status nimrag-backend`
- Frontend may not be running: `systemctl status nimrag-frontend`
- Check X11 log: `cat /tmp/x11.log`
- Check kiosk: `DISPLAY=:0 chromium-browser --version`

#### PostgreSQL errors during build
Alembic migrations run during image build. If they fail, a warning is printed but the build continues. Check if `alembic.ini` is in `/opt/nimrag/Backend/` or `/opt/nimrag/Backend/src/`.

#### VNC connection refused
`x11vnc` starts only after X11 is running. Log in via SSH first and check: `systemctl status nimrag-frontend`.

---

### 11. Further documentation

- **rpi-image-gen (original tool, not used here):** https://github.com/gounthar/rpi-image-gen
- **Raspberry Pi OS downloads:** https://www.raspberrypi.com/software/operating-systems/
- **piwheels (ARM64 Python wheels):** https://www.piwheels.org
- **NodeSource (Node.js packages):** https://github.com/nodesource/distributions
- **Build script details:** [art_image_creator/BUILD_README.md](art_image_creator/BUILD_README.md)

---
