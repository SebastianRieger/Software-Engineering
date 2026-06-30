# Nimrag Kiosk Image — Build Details

This document describes the internal build mechanics for developers who need to debug, extend, or understand the image creation process.

---

## Table of contents

1. [Overview](#overview)
2. [Entry points (build.sh / start.ps1)](#entry-points)
3. [Docker Compose setup](#docker-compose-setup)
4. [Dockerfile](#dockerfile)
5. [run-build.sh — step by step](#run-buildsh--step-by-step)
6. [customize.sh — step by step](#customizesh--step-by-step)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The build pipeline takes the official Raspberry Pi OS Desktop (arm64) image and customizes it inside a Docker container using QEMU emulation and chroot. No custom bootstrap tooling is used — Pi OS is the base, not a minimal rootfs.

**Tool chain:**
- **Docker + Docker Compose** — container runtime
- **QEMU user-static** — ARM64 emulation inside the x86_64 container
- **loop device + kpartx** — access to raw `.img` partitions
- **chroot** — in-image customization

**Why this approach instead of mmdebstrap/genimage:**  
Pi OS Desktop ships with all Raspberry Pi firmware, GPU drivers, and hardware support already configured. Starting from Pi OS avoids having to replicate that setup manually.

---

## Entry points

### `build.sh` (Linux)
```bash
#!/bin/bash
set -eu
mkdir -p Kiosk_Image_Files/images Kiosk_Image_Files/logs
docker compose up --build
```
Creates local directories and delegates to Docker Compose.

### `start.ps1` (Windows)
```powershell
New-Item -ItemType Directory -Force -Path ".\Kiosk_Image_Files\images" | Out-Null
New-Item -ItemType Directory -Force -Path ".\Kiosk_Image_Files\logs"  | Out-Null
docker compose up --build
```
Same logic, PowerShell syntax for Windows + Docker Desktop.

---

## Docker Compose setup

`docker-compose.yml`:
```yaml
services:
  kiosk_imagegen:
    build: .
    image: nimrag-imagegen:latest
    privileged: true
    user: root
    environment:
      - DEBIAN_FRONTEND=noninteractive
    volumes:
      - ./output:/output
      - ./cache:/cache
```

| Setting | Reason |
|---|---|
| `privileged: true` | Required for `losetup`, `kpartx`, `mount` inside the container |
| `user: root` | Required for chroot and mount operations |
| `./output:/output` | The final `.img.gz` appears here on the host |
| `./cache:/cache` | Pi OS download cache — persists between builds |

---

## Dockerfile

```dockerfile
FROM debian:bookworm

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    qemu-user-static \
    binfmt-support \
    util-linux \
    parted \
    e2fsprogs \
    dosfstools \
    kpartx \
    curl \
    xz-utils \
    pigz \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN dpkg-reconfigure qemu-user-static 2>/dev/null || true

COPY run-build.sh  /usr/local/bin/run-build.sh
COPY customize.sh  /usr/local/bin/customize.sh
RUN sed -i 's/\r$//' /usr/local/bin/run-build.sh /usr/local/bin/customize.sh \
    && chmod +x   /usr/local/bin/run-build.sh /usr/local/bin/customize.sh

CMD ["/usr/local/bin/run-build.sh"]
```

**`dpkg-reconfigure qemu-user-static`** registers the ARM64 binary format with the kernel's `binfmt_misc`, enabling transparent execution of ARM64 binaries via QEMU inside the container.

**`sed -i 's/\r$//'`** strips Windows-style CRLF line endings so scripts work correctly on Linux even if edited on Windows.

---

## run-build.sh — step by step

### Variables
```bash
OUTPUT_DIR="/output"          # mapped to ./output/ on host
CACHE_DIR="/cache"            # mapped to ./cache/ on host
IMAGE_NAME="Nimrag_Kiosk"
RPIOS_URL="https://downloads.raspberrypi.com/raspios_arm64_latest"
RPIOS_CACHE="${CACHE_DIR}/rpios-desktop-arm64.img.xz"
ROOTFS="/mnt/pi"
LOOP=""                       # populated by losetup, used by cleanup trap
```

### Cleanup trap
```bash
cleanup() {
    umount "${ROOTFS}/run" "${ROOTFS}/dev/pts" "${ROOTFS}/dev" \
           "${ROOTFS}/sys" "${ROOTFS}/proc" "${ROOTFS}/boot/firmware" \
           "${ROOTFS}" 2>/dev/null || true
    [ -n "${LOOP}" ] && kpartx -d "${LOOP}" 2>/dev/null || true
    [ -n "${LOOP}" ] && losetup -d "${LOOP}" 2>/dev/null || true
}
trap cleanup EXIT
```
Ensures all mounts and loop devices are released even if the build fails.

### Step 1 — Download Pi OS
Downloads `rpios-desktop-arm64.img.xz` from the official Raspberry Pi URL. Writes to a `.tmp` file first to avoid a partial download being treated as a valid cache hit.

### Step 2 — Extract image
```bash
xz -dkc "${RPIOS_CACHE}" > "${WORK_IMG}"
```
`-k` keeps the source file; `-c` writes to stdout (into the output file).

### Step 3 — Expand image by 4 GB
```bash
truncate -s +4G "${WORK_IMG}"
```
The Pi OS image is sized to fit its content. Packages installed by `customize.sh` need ~4 GB of additional space.

### Step 4 — Attach loop device + partitions
```bash
LOOP=$(losetup -f --show "${WORK_IMG}")
kpartx -a -s "${LOOP}"
MAP="/dev/mapper/$(basename "${LOOP}")"
```
`kpartx` exposes each partition as `/dev/mapper/loopXpY`.

### Step 5 — Resize root partition
```bash
parted -s "${LOOP}" resizepart 2 100%
kpartx -u "${LOOP}"
e2fsck -f -y "${MAP}p2" || true
resize2fs "${MAP}p2"
```
Extends partition 2 (the root ext4) to fill the extra 4 GB. `kpartx -u` updates the partition map after resizing.

### Step 6 — Mount filesystems
```bash
mount "${MAP}p2" "${ROOTFS}"
mount "${MAP}p1" "${ROOTFS}/boot/firmware"
mount -t proc  proc     "${ROOTFS}/proc"
mount -t sysfs sysfs    "${ROOTFS}/sys"
mount -o bind  /dev     "${ROOTFS}/dev"
mount -o bind  /dev/pts "${ROOTFS}/dev/pts"
mount -o bind  /run     "${ROOTFS}/run"
```
Binding `/proc`, `/sys`, `/dev`, `/dev/pts`, and `/run` is required for `apt-get`, `systemctl`, and PostgreSQL to work correctly inside the chroot.

### Step 7 — QEMU binary
```bash
cp /usr/bin/qemu-aarch64-static "${ROOTFS}/usr/bin/"
```
The `binfmt_misc` kernel subsystem redirects ARM64 binary execution to this binary, enabling transparent emulation inside the chroot.

### Step 8 — Run customization
```bash
cp /usr/local/bin/customize.sh "${ROOTFS}/tmp/customize.sh"
chroot "${ROOTFS}" /bin/bash /tmp/customize.sh
```

### Step 9 — Cleanup chroot artifacts
Removes `customize.sh` and `qemu-aarch64-static` from the rootfs — these must not end up in the final image.

### Step 10 — Compress
```bash
pigz -9 "${WORK_IMG}"
```
`pigz` is a parallel gzip implementation. `-9` is maximum compression. The output file is `Nimrag_Kiosk.img.gz`.

---

## customize.sh — step by step

Runs inside the ARM64 chroot as root. All commands target the Pi's rootfs.

### Step 0 — User setup
- Removes the default `pi` user (`userdel -r pi`)
- Disables Pi OS first-boot user-setup wizard (`userconfig.service`, `userconf.service`)
- Creates user `nimrag` with password `Nimrag`
- Sets hostname to `nimrag`

### Step 1 — Package update
```bash
apt-get update -qq
apt-get upgrade -y -qq
```

### Step 2 — Package installation
```
git, curl, gnupg,
openbox, xinit, x11-xserver-utils, unclutter, x11vnc,
python3-pip, python3-venv, python3-dev, build-essential,
postgresql, postgresql-client,
cloud-guest-utils, libicu-dev
```

### Step 3 — Node.js 20
Installed via the NodeSource repository. The GPG key is added to `/etc/apt/keyrings/nodesource.gpg`.

### Step 4 — Network
**eth0** gets a static IP via `/etc/dhcpcd.conf`:
```
ip_address=192.168.1.100/24
routers=192.168.1.1
domain_name_servers=8.8.8.8 8.8.4.4
```

**wlan0** uses DHCP with `metric 200` (lower priority than eth0).

**WiFi provisioning service** (`wifi-provision.service`): on first boot, if `/boot/firmware/wpa_supplicant.conf` exists, it is moved to `/etc/wpa_supplicant/wpa_supplicant.conf` and deleted from the boot partition.

### Step 5 — Kiosk display
- `lightdm` is disabled
- TTY1 autologin is configured for user `nimrag`
- `~nimrag/.bash_profile` starts X11 automatically on TTY1
- `~nimrag/.xinitrc` runs the kiosk session:
  - Screen blanking disabled (`xset s off -dpms`)
  - `unclutter` hides cursor after 0.5 s
  - `openbox` (minimal window manager)
  - `x11vnc` on port 5900 (no password)
  - Waits for backend (port 8000) and frontend (port 5173) via `curl` polling
  - `chromium-browser --kiosk --app=http://localhost:5173` (restarts on crash)

### Step 6 — Clone repository
```bash
git clone --depth 1 -b dev \
    https://github.com/SebastianRieger/Software-Engineering \
    /opt/nimrag
```
The backend `.env` is written at this point.

### Step 7 — Python dependencies
- Creates a venv at `/opt/nimrag/venv`
- Strips hash-pinning from `requirements.txt` (pip inside chroot doesn't support `--require-hashes` well)
- Skips `mediapipe` and `aubio` (no ARM64 wheels available)
- Uses `piwheels.org` as extra index for pre-built ARM64 wheels

### Step 8 — Frontend dependencies
```bash
cd /opt/nimrag/Frontend/nimrag-frontend
npm install
```

### Step 9 — PostgreSQL
- Starts the cluster temporarily to run setup commands
- Creates user `nimrag` with password `nimrag`
- Creates database `nimrag_db` owned by `nimrag`
- Runs `alembic upgrade head` (looks for `alembic.ini` in `Backend/` or `Backend/src/`)
- Stops the cluster (systemd will manage it at runtime)

### Step 10 — Systemd services
Enables:
- `postgresql.service`
- `nimrag-backend.service` — `ExecStart=/opt/nimrag/venv/bin/python main.py` (WorkingDirectory: `/opt/nimrag/Backend/src`)
- `nimrag-frontend.service` — `ExecStart=/usr/bin/npm run dev` (WorkingDirectory: `/opt/nimrag/Frontend/nimrag-frontend`)
- `avahi-daemon.service`

Adds `nimrag` to groups: `adm audio video sudo plugdev input netdev dialout`

---

## Troubleshooting

### `Operation not permitted` / loop device errors
The container must be `privileged: true`. Verify `docker-compose.yml`.

### `exec format error` inside chroot
`qemu-aarch64-static` is not registered. The Dockerfile runs `dpkg-reconfigure qemu-user-static`. If this fails, try rebuilding the Docker image with `--no-cache`:
```bash
docker compose build --no-cache
docker compose up
```

### Pi OS cache is corrupted
Delete `./cache/rpios-desktop-arm64.img.xz` and rebuild.

### Alembic migrations fail during build
The build prints `WARNING: migrations skipped` and continues. The DB structure is missing at runtime — check if `alembic.ini` is present in the repository and whether the migration scripts are compatible with the installed database.

### Debug the chroot interactively
```bash
# On the host, extract the Pi OS image manually
xz -dkc cache/rpios-desktop-arm64.img.xz > /tmp/pi.img
losetup -f --show /tmp/pi.img         # note the loop device, e.g. /dev/loop0
kpartx -a /dev/loop0
mount /dev/mapper/loop0p2 /mnt/pi
mount /dev/mapper/loop0p1 /mnt/pi/boot/firmware
# ... mount proc/sys/dev as shown in run-build.sh
cp /usr/bin/qemu-aarch64-static /mnt/pi/usr/bin/
chroot /mnt/pi /bin/bash
```

### View build output
All Docker output is printed to the terminal during `docker compose up`. Redirect to a file if needed:
```bash
bash build.sh 2>&1 | tee build.log
```

---

## Further documentation

- **Main README:** [../README.md](../README.md)
- **Raspberry Pi OS:** https://www.raspberrypi.com/software/operating-systems/
- **piwheels:** https://www.piwheels.org
- **QEMU user emulation:** https://www.qemu.org/docs/master/user/main.html
- **binfmt_misc:** https://www.kernel.org/doc/html/latest/admin-guide/binfmt-misc.html
- **NodeSource:** https://github.com/nodesource/distributions
