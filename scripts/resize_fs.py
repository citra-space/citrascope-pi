#!/usr/bin/env python3
import subprocess
import os
import re
import sys
import time
from contextlib import contextmanager

# Adapted from cedar-server create_cedar_image scripts

class DeviceManager:
    def __init__(self, image_path):
        self.image_path = image_path
        self.loop_devices = []

    def setup_loop_devices(self):
        """Run kpartx and capture the loop device names"""
        try:
            result = subprocess.run(['sudo', 'kpartx', '-av', self.image_path],
                                    capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n'):
                match = re.search(r'add map (\S+)', line)
                if match:
                    self.loop_devices.append(match.group(1))
            
            print(f"Created loop devices: {self.loop_devices}")
            return len(self.loop_devices) >= 2
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating loop devices: {e}")
            return False

    def cleanup(self):
        """Remove loop devices"""
        try:
            subprocess.run(['sudo', 'kpartx', '-d', self.image_path], check=True)
            print("Removed loop devices")
        except subprocess.CalledProcessError as e:
            print(f"Error removing loop devices: {e}")

    def get_root_partition(self):
        """Get the root partition device (typically the second one)"""
        if len(self.loop_devices) < 2:
            return None
        return f"/dev/mapper/{self.loop_devices[1]}"

@contextmanager
def loop_device_context(image_path):
    """Context manager for loop device setup/cleanup"""
    manager = DeviceManager(image_path)
    try:
        if not manager.setup_loop_devices():
            raise RuntimeError("Failed to setup loop devices")
        yield manager
    finally:
        manager.cleanup()

def resize_filesystem(image_path):
    """Resize the filesystem on the root partition"""
    print(f"Resizing filesystem in {image_path}")
    
    with loop_device_context(image_path) as manager:
        root_device = manager.get_root_partition()
        if not root_device:
            print("Error: Could not find root partition")
            return False
        
        print(f"Root partition: {root_device}")
        
        # Check filesystem before resize
        print("Checking filesystem...")
        try:
            subprocess.run(['sudo', 'e2fsck', '-f', '-p', root_device], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Filesystem check failed: {e}")
            return False
        
        # Resize filesystem to fill partition
        print("Resizing filesystem...")
        try:
            subprocess.run(['sudo', 'resize2fs', root_device], check=True)
            print("Filesystem resized successfully")
        except subprocess.CalledProcessError as e:
            print(f"Filesystem resize failed: {e}")
            return False
        
        return True

def main():
    if len(sys.argv) != 2:
        print("Usage: sudo python3 resize_fs.py <image_file>")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        print(f"Image file {image_path} not found")
        sys.exit(1)

    success = resize_filesystem(image_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
