#!/usr/bin/env python3
"""
Test Raspberry Pi image by mounting and validating contents.
Replaces test-docker.sh with Python for cleaner output.
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Try to import yaspin for prettier output
try:
    from yaspin import yaspin
    HAS_YASPIN = True
except ImportError:
    HAS_YASPIN = False

def get_user_ids():
    """Get current user's UID and GID"""
    uid = os.getuid()
    gid = os.getgid()
    return uid, gid

def find_image(specified_path=None):
    """Find the image file to test"""
    if specified_path:
        image_path = Path(specified_path)
        if not image_path.exists():
            print(f"Error: Image file not found: {image_path}")
            sys.exit(1)
        return image_path
    
    # Find latest citrascope image
    images = sorted(Path('.').glob('*-citrascope.img'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not images:
        print("Error: No *-citrascope.img found. Build an image first or specify path.")
        sys.exit(1)
    
    return images[0]

def ensure_docker_image(uid, gid):
    """Build Docker image if it doesn't exist"""
    result = subprocess.run(
        ['docker', 'images', 'lemon-pi-builder'],
        capture_output=True,
        text=True
    )
    
    if 'lemon-pi-builder' not in result.stdout:
        print("Building Docker image...")
        subprocess.run([
            'docker', 'build',
            '--build-arg', f'USER_ID={uid}',
            '--build-arg', f'GROUP_ID={gid}',
            '-t', 'lemon-pi-builder',
            '.'
        ], stdout=subprocess.DEVNULL, check=True)
        print("✓ Docker image built\n")

def run_tests(image_path):
    """Run tests inside Docker container"""
    
    test_script = f"""
set -e

IMAGE="/workspace/{image_path.name}"

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m'

# Mount points
BOOT_MOUNT="/tmp/test_boot"
ROOTFS_MOUNT="/tmp/test_rootfs"

cleanup() {{
    if mountpoint -q "$ROOTFS_MOUNT" 2>/dev/null; then
        sudo umount "$ROOTFS_MOUNT" || true
    fi
    if mountpoint -q "$BOOT_MOUNT" 2>/dev/null; then
        sudo umount "$BOOT_MOUNT" || true
    fi
    sudo kpartx -d "$IMAGE" 2>/dev/null || true
    rm -rf "$BOOT_MOUNT" "$ROOTFS_MOUNT"
}}

trap cleanup EXIT

# Create mount points
mkdir -p "$BOOT_MOUNT" "$ROOTFS_MOUNT"

# Setup loop devices
KPARTX_OUTPUT=$(sudo kpartx -av "$IMAGE")
LOOP_DEVS=$(echo "$KPARTX_OUTPUT" | grep -o 'loop[0-9]*p[0-9]*')

# Extract device names
BOOT_DEV="/dev/mapper/$(echo "$LOOP_DEVS" | sed -n '1p')"
ROOTFS_DEV="/dev/mapper/$(echo "$LOOP_DEVS" | sed -n '2p')"

# Mount partitions
sudo mount "$BOOT_DEV" "$BOOT_MOUNT"
sudo mount "$ROOTFS_DEV" "$ROOTFS_MOUNT"

# Run tests
test_passed=0
test_failed=0

run_test() {{
    echo "  Testing: $1"
    if eval "$2"; then
        echo -e "  ${{GREEN}}✓${{NC}} $1"
        test_passed=$((test_passed + 1))
    else
        echo -e "  ${{RED}}✗${{NC}} $1"
        test_failed=$((test_failed + 1))
    fi
}}

run_test "User 'citra' exists" "grep -q '^citra:' '$ROOTFS_MOUNT/etc/passwd'"
run_test "User has correct UID (1001)" "grep '^citra:' '$ROOTFS_MOUNT/etc/passwd' | cut -d: -f3 | grep -q '^1001$'"
run_test "User in sudo group" "grep '^sudo:' '$ROOTFS_MOUNT/etc/group' | grep -q 'citra'"
run_test "SSH service enabled" "[ -e '$ROOTFS_MOUNT/etc/systemd/system/multi-user.target.wants/ssh.service' ]"
run_test "Hostname set" "[ -f '$ROOTFS_MOUNT/etc/hostname' ]"
run_test "Citrascope venv exists" "[ -d '$ROOTFS_MOUNT/home/citra/.citrascope_venv' ]"
run_test "Citrascope binary exists" "[ -f '$ROOTFS_MOUNT/home/citra/.citrascope_venv/bin/citrascope' ]"
run_test "Citrascope service exists" "[ -f '$ROOTFS_MOUNT/etc/systemd/system/citrascope.service' ]"
run_test "Citrascope service enabled" "[ -e '$ROOTFS_MOUNT/etc/systemd/system/multi-user.target.wants/citrascope.service' ]"
run_test "Comitup config exists" "[ -f '$ROOTFS_MOUNT/etc/comitup.conf' ]"
run_test "Comitup service enabled" "[ -e '$ROOTFS_MOUNT/etc/systemd/system/multi-user.target.wants/comitup.service' ]"
run_test "Login banner installed" "[ -f '$ROOTFS_MOUNT/etc/profile.d/citrascope-banner.sh' ]"

# Summary
echo ""
if [ $test_failed -eq 0 ]; then
    echo -e "${{GREEN}}========================================${{NC}}"
    echo -e "${{GREEN}}✓ All $test_passed tests passed!${{NC}}"
    echo -e "${{GREEN}}========================================${{NC}}"
    echo ""
    echo "Image is ready to flash to SD card."
else
    echo -e "${{RED}}========================================${{NC}}"
    echo -e "${{RED}}✗ $test_failed test(s) failed${{NC}}"
    echo -e "${{GREEN}}✓ $test_passed test(s) passed${{NC}}"
    echo -e "${{RED}}========================================${{NC}}"
    exit 1
fi
"""
    
    cmd = [
        'docker', 'run', '--rm', '--privileged',
        '-v', f'{os.getcwd()}:/workspace',
        '-v', '/dev:/dev',
        'lemon-pi-builder',
        'bash', '-c', test_script
    ]
    
    if HAS_YASPIN:
        with yaspin(text="Running tests...", color="cyan") as sp:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            for line in process.stdout:
                line_stripped = line.rstrip()
                if line_stripped:
                    sp.write(line_stripped)
            
            return_code = process.wait()
            
            if return_code == 0:
                sp.ok("✓")
            else:
                sp.fail("✗")
            
            return return_code
    else:
        # Fallback without spinner
        result = subprocess.run(cmd)
        return result.returncode

def main():
    # Parse arguments
    image_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Find image
    image = find_image(image_path)
    print(f"Testing image: {image}\n")
    
    # Ensure Docker image exists
    uid, gid = get_user_ids()
    ensure_docker_image(uid, gid)
    
    # Run tests
    return_code = run_tests(image)
    
    if return_code == 0:
        print("\n✓ Test completed successfully!")
    else:
        sys.exit(return_code)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
