#!/bin/bash
# Test Raspberry Pi image by mounting and validating contents

set -e

# Get current user's UID/GID to match Docker user
USER_ID=$(id -u)
GROUP_ID=$(id -g)

# Find image file
if [ -n "$1" ]; then
    IMAGE_PATH="$1"
else
    # Find latest citrascope image
    IMAGE_PATH=$(ls -t *-citrascope.img 2>/dev/null | head -1)
    if [ -z "$IMAGE_PATH" ]; then
        echo "Error: No *-citrascope.img found. Build an image first or specify path."
        exit 1
    fi
fi

if [ ! -f "$IMAGE_PATH" ]; then
    echo "Error: Image file not found: $IMAGE_PATH"
    exit 1
fi

echo "Testing image: $IMAGE_PATH"
echo ""

# Build Docker image if needed
if ! docker images lemon-pi-builder | grep -q lemon-pi-builder; then
    echo "Building Docker image..."
    docker build \
        --build-arg USER_ID=${USER_ID} \
        --build-arg GROUP_ID=${GROUP_ID} \
        -t lemon-pi-builder . > /dev/null
fi

# Run tests inside Docker container
docker run --rm --privileged \
    -v "$(pwd):/workspace" \
    -v /dev:/dev \
    lemon-pi-builder \
    bash -c "
set -e

IMAGE=\"/workspace/$IMAGE_PATH\"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Mount points
BOOT_MOUNT=\"/tmp/test_boot\"
ROOTFS_MOUNT=\"/tmp/test_rootfs\"

cleanup() {
    echo -e \"\${YELLOW}Cleaning up...\${NC}\"
    if mountpoint -q \"\$ROOTFS_MOUNT\" 2>/dev/null; then
        sudo umount \"\$ROOTFS_MOUNT\" || true
    fi
    if mountpoint -q \"\$BOOT_MOUNT\" 2>/dev/null; then
        sudo umount \"\$BOOT_MOUNT\" || true
    fi
    sudo kpartx -d \"\$IMAGE\" 2>/dev/null || true
    rm -rf \"\$BOOT_MOUNT\" \"\$ROOTFS_MOUNT\"
}

trap cleanup EXIT

echo -e \"\${YELLOW}Mounting image...\${NC}\"

# Create mount points
mkdir -p \"\$BOOT_MOUNT\" \"\$ROOTFS_MOUNT\"

# Setup loop devices
KPARTX_OUTPUT=\$(sudo kpartx -av \"\$IMAGE\")
LOOP_DEVS=\$(echo \"\$KPARTX_OUTPUT\" | grep -o 'loop[0-9]*p[0-9]*')

# Extract device names
BOOT_DEV=\"/dev/mapper/\$(echo \"\$LOOP_DEVS\" | sed -n '1p')\"
ROOTFS_DEV=\"/dev/mapper/\$(echo \"\$LOOP_DEVS\" | sed -n '2p')\"

# Mount partitions
sudo mount \"\$BOOT_DEV\" \"\$BOOT_MOUNT\"
sudo mount \"\$ROOTFS_DEV\" \"\$ROOTFS_MOUNT\"

echo -e \"\${GREEN}✓ Image mounted\${NC}\"
echo \"\"

# Test 1: User exists
echo \"Checking user 'citra' exists...\"
if ! grep -q '^citra:' \"\$ROOTFS_MOUNT/etc/passwd\"; then
    echo -e \"\${RED}✗ User 'citra' not found in /etc/passwd\${NC}\"
    exit 1
fi

# Verify UID
USER_LINE=\$(grep '^citra:' \"\$ROOTFS_MOUNT/etc/passwd\")
USER_UID=\$(echo \"\$USER_LINE\" | cut -d: -f3)
if [ \"\$USER_UID\" != \"1001\" ]; then
    echo -e \"\${RED}✗ User 'citra' has wrong UID: \$USER_UID (expected 1001)\${NC}\"
    exit 1
fi
echo -e \"\${GREEN}✓ User 'citra' exists with correct UID\${NC}\"

# Test 2: User in correct groups
echo \"Checking user groups...\"
GROUPS_TO_CHECK=\"sudo video plugdev netdev\"
for group in \$GROUPS_TO_CHECK; do
    if ! grep \"^\$group:\" \"\$ROOTFS_MOUNT/etc/group\" | grep -q \"citra\"; then
        echo -e \"\${RED}✗ User 'citra' not in group: \$group\${NC}\"
        exit 1
    fi
done
echo -e \"\${GREEN}✓ User 'citra' in required groups\${NC}\"

# Test 3: Hostname
echo \"Checking hostname...\"
HOSTNAME=\$(cat \"\$ROOTFS_MOUNT/etc/hostname\" | tr -d '[:space:]')
if [ \"\$HOSTNAME\" != \"citrascope\" ]; then
    echo -e \"\${RED}✗ Hostname is '\$HOSTNAME' (expected 'citrascope')\${NC}\"
    exit 1
fi
echo -e \"\${GREEN}✓ Hostname set to 'citrascope'\${NC}\"

# Test 4: SSH enabled
echo \"Checking SSH service...\"
SSH_SERVICE=\"\$ROOTFS_MOUNT/etc/systemd/system/multi-user.target.wants/ssh.service\"
if [ ! -L \"\$SSH_SERVICE\" ] && [ ! -f \"\$SSH_SERVICE\" ]; then
    echo -e \"\${RED}✗ SSH service not enabled\${NC}\"
    exit 1
fi
echo -e \"\${GREEN}✓ SSH service enabled\${NC}\"

# Test 5: Citrascope venv exists
echo \"Checking Citrascope installation...\"
VENV_PATH=\"\$ROOTFS_MOUNT/home/citra/.citrascope_venv\"
if [ ! -d \"\$VENV_PATH\" ]; then
    echo -e \"\${RED}✗ Citrascope venv not found at /home/citra/.citrascope_venv\${NC}\"
    exit 1
fi

# Check for citrascope binary in venv
if [ ! -f \"\$VENV_PATH/bin/citrascope\" ]; then
    echo -e \"\${RED}✗ Citrascope binary not found in venv\${NC}\"
    exit 1
fi
echo -e \"\${GREEN}✓ Citrascope venv installed\${NC}\"

# Test 6: Citrascope systemd service
echo \"Checking Citrascope service...\"
SERVICE_FILE=\"\$ROOTFS_MOUNT/etc/systemd/system/citrascope.service\"
if [ ! -f \"\$SERVICE_FILE\" ]; then
    echo -e \"\${RED}✗ Citrascope systemd service file not found at /etc/systemd/system/citrascope.service\${NC}\"
    exit 1
fi

# Check if service is enabled
SERVICE_LINK=\"\$ROOTFS_MOUNT/etc/systemd/system/multi-user.target.wants/citrascope.service\"
if [ ! -L \"\$SERVICE_LINK\" ] && [ ! -f \"\$SERVICE_LINK\" ]; then
    echo -e \"\${RED}✗ Citrascope service not enabled\${NC}\"
    exit 1
fi
echo -e \"\${GREEN}✓ Citrascope service configured and enabled\${NC}\"

# Test 7: Comitup WiFi provisioning
echo \"Checking Comitup configuration...\"
COMITUP_CONF=\"\$ROOTFS_MOUNT/etc/comitup.conf\"
if [ ! -f \"\$COMITUP_CONF\" ]; then
    echo -e \"\${RED}✗ Comitup configuration file not found at /etc/comitup.conf\${NC}\"
    exit 1
fi

# Check if comitup service is enabled
COMITUP_LINK=\"\$ROOTFS_MOUNT/etc/systemd/system/multi-user.target.wants/comitup.service\"
if [ ! -L \"\$COMITUP_LINK\" ] && [ ! -f \"\$COMITUP_LINK\" ]; then
    echo -e \"\${RED}✗ Comitup service not enabled\${NC}\"
    exit 1
fi

# Check if serial script exists
SERIAL_SCRIPT=\"\$ROOTFS_MOUNT/usr/local/sbin/get-serial.sh\"
if [ ! -f \"\$SERIAL_SCRIPT\" ]; then
    echo -e \"\${RED}✗ Serial extraction script not found\${NC}\"
    exit 1
fi
echo -e \"\${GREEN}✓ Comitup WiFi provisioning configured\${NC}\"

# Test 8: Headless configuration
echo \"Checking headless settings...\"

# Check locale configuration
LOCALE_FILE=\"\$ROOTFS_MOUNT/etc/default/locale\"
if [ ! -f \"\$LOCALE_FILE\" ]; then
    echo -e \"\${RED}✗ Locale configuration file not found at /etc/default/locale\${NC}\"
    exit 1
fi

# Check keyboard configuration
KEYBOARD_FILE=\"\$ROOTFS_MOUNT/etc/default/keyboard\"
if [ ! -f \"\$KEYBOARD_FILE\" ]; then
    echo -e \"\${RED}✗ Keyboard configuration file not found at /etc/default/keyboard\${NC}\"
    exit 1
fi

# Check timezone symlink
LOCALTIME_LINK=\"\$ROOTFS_MOUNT/etc/localtime\"
if [ ! -L \"\$LOCALTIME_LINK\" ]; then
    echo -e \"\${RED}✗ Timezone symlink not found at /etc/localtime\${NC}\"
    exit 1
fi

# Check setup marker
SETUP_MARKER=\"\$ROOTFS_MOUNT/etc/rpi-initial-setup\"
if [ ! -f \"\$SETUP_MARKER\" ]; then
    echo -e \"\${RED}✗ Setup marker file not found at /etc/rpi-initial-setup\${NC}\"
    exit 1
fi
echo -e \"\${GREEN}✓ Headless settings configured\${NC}\"

# All tests passed
echo \"\"
echo -e \"\${GREEN}========================================\${NC}\"
echo -e \"\${GREEN}✓ All tests passed!\${NC}\"
echo -e \"\${GREEN}========================================\${NC}\"
echo \"\"
echo \"Image is ready to flash to SD card.\"
"

echo ""
echo "Test completed successfully!"
