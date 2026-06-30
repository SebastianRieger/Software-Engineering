#!/bin/bash
set -euo pipefail

OUTPUT_DIR="/output"
CACHE_DIR="/cache"
IMAGE_NAME="Nimrag_Kiosk"
RPIOS_URL="https://downloads.raspberrypi.com/raspios_arm64_latest"
RPIOS_CACHE="${CACHE_DIR}/rpios-desktop-arm64.img.xz"
ROOTFS="/mnt/pi"
LOOP=""

echo ""
echo "================================================"
echo "   Nimrag Kiosk Image Builder"
echo "================================================"
echo ""

cleanup() {
    echo ""
    echo "Cleaning up mounts..."
    umount "${ROOTFS}/run"           2>/dev/null || true
    umount "${ROOTFS}/dev/pts"       2>/dev/null || true
    umount "${ROOTFS}/dev"           2>/dev/null || true
    umount "${ROOTFS}/sys"           2>/dev/null || true
    umount "${ROOTFS}/proc"          2>/dev/null || true
    umount "${ROOTFS}/boot/firmware" 2>/dev/null || true
    umount "${ROOTFS}"               2>/dev/null || true
    [ -n "${LOOP}" ] && kpartx -d "${LOOP}" 2>/dev/null || true
    [ -n "${LOOP}" ] && losetup -d "${LOOP}" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "${OUTPUT_DIR}" "${CACHE_DIR}" "${ROOTFS}"

# ── 1. Download Pi OS ─────────────────────────────────────────────────────────
if [ ! -f "${RPIOS_CACHE}" ]; then
    echo "Downloading Raspberry Pi OS Desktop (64-bit)..."
    curl -L --progress-bar "${RPIOS_URL}" -o "${RPIOS_CACHE}.tmp"
    mv "${RPIOS_CACHE}.tmp" "${RPIOS_CACHE}"
    echo "Download complete."
else
    echo "Using cached Pi OS image: ${RPIOS_CACHE}"
fi
echo ""

# ── 2. Extract image ──────────────────────────────────────────────────────────
WORK_IMG="${OUTPUT_DIR}/${IMAGE_NAME}.img"
echo "Extracting base image..."
xz -dkc "${RPIOS_CACHE}" > "${WORK_IMG}"
echo "Extracted: $(du -h "${WORK_IMG}" | cut -f1)"
echo ""

# ── 3. Expand image by 4 GB for packages ─────────────────────────────────────
echo "Expanding image by 4 GB..."
truncate -s +4G "${WORK_IMG}"

# ── 4. Attach loop device + partition mappings ────────────────────────────────
LOOP=$(losetup -f --show "${WORK_IMG}")
echo "Loop device: ${LOOP}"
kpartx -a -s "${LOOP}"
MAP="/dev/mapper/$(basename "${LOOP}")"

# ── 5. Resize root partition to fill new space ────────────────────────────────
echo "Resizing root partition..."
parted -s "${LOOP}" resizepart 2 100%
kpartx -u "${LOOP}"
e2fsck -f -y "${MAP}p2" || true
resize2fs "${MAP}p2"
echo ""

# ── 6. Mount filesystems ──────────────────────────────────────────────────────
echo "Mounting filesystems..."
mount "${MAP}p2" "${ROOTFS}"
mount "${MAP}p1" "${ROOTFS}/boot/firmware"
mount -t proc  proc     "${ROOTFS}/proc"
mount -t sysfs sysfs    "${ROOTFS}/sys"
mount -o bind  /dev     "${ROOTFS}/dev"
mount -o bind  /dev/pts "${ROOTFS}/dev/pts"
mount -o bind  /run     "${ROOTFS}/run"

# ── 7. QEMU for ARM64 emulation inside chroot ─────────────────────────────────
cp /usr/bin/qemu-aarch64-static "${ROOTFS}/usr/bin/"

# ── 8. Run customization ──────────────────────────────────────────────────────
echo "Running customization inside chroot..."
echo ""
cp /usr/local/bin/customize.sh "${ROOTFS}/tmp/customize.sh"
chmod +x "${ROOTFS}/tmp/customize.sh"
chroot "${ROOTFS}" /bin/bash /tmp/customize.sh
CUSTOMIZE_EXIT=$?

# ── 9. Cleanup chroot artifacts ───────────────────────────────────────────────
rm -f "${ROOTFS}/tmp/customize.sh"
rm -f "${ROOTFS}/usr/bin/qemu-aarch64-static"

# Explicit unmount (trap is backup)
umount "${ROOTFS}/run"
umount "${ROOTFS}/dev/pts"
umount "${ROOTFS}/dev"
umount "${ROOTFS}/sys"
umount "${ROOTFS}/proc"
umount "${ROOTFS}/boot/firmware"
umount "${ROOTFS}"
kpartx -d "${LOOP}"
losetup -d "${LOOP}"
LOOP=""

if [ "${CUSTOMIZE_EXIT}" -ne 0 ]; then
    echo "Customization failed (exit ${CUSTOMIZE_EXIT})"
    exit "${CUSTOMIZE_EXIT}"
fi

# ── 10. Compress ──────────────────────────────────────────────────────────────
echo ""
echo "Compressing image with pigz (this may take a few minutes)..."
pigz -9 "${WORK_IMG}"

echo ""
echo "================================================"
echo "   Build complete!"
echo "   Image: ${OUTPUT_DIR}/${IMAGE_NAME}.img.gz"
echo "================================================"
echo ""
