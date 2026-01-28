#!/usr/bin/env python3
import subprocess
import os
import re
import sys
from config import BOOT_MOUNT, ROOTFS_MOUNT

class ImageMounter:
    def __init__(self, image_path):
        self.image_path = image_path
        self.loop_devices = []
        self.mount_points = [BOOT_MOUNT, ROOTFS_MOUNT]
    
    def __enter__(self):
        """Context manager entry - setup and mount"""
        self.setup_loop_devices()
        self.mount_partitions(readonly=False)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.cleanup()
        return False  # Don't suppress exceptions

    def setup_loop_devices(self):
        """Run kpartx and capture the loop device names"""
        try:
            result = subprocess.run(['sudo', 'kpartx', '-av', self.image_path],
                                    capture_output=True, text=True, check=True)
            
            # Parse output to get loop device names
            # Example: "add map loop0p1 (254:0): 0 1048576 linear 7:0 8192"
            for line in result.stdout.split('\n'):
                match = re.search(r'add map (\S+)', line)
                if match:
                    self.loop_devices.append(match.group(1))
            
            if len(self.loop_devices) < 2:
                print(f"Warning: Expected 2 partitions, found {len(self.loop_devices)}")
                return False
            
            print(f"Created loop devices: {self.loop_devices}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating loop devices: {e}")
            return False

    def mount_partitions(self, readonly):
        """Mount the partitions at specified mount points"""
        try:
            # Create mount points if they don't exist
            for mount_point in self.mount_points:
                os.makedirs(mount_point, exist_ok=True)

            # Mount the partitions
            for loop_dev, mount_point in zip(self.loop_devices, self.mount_points):
                dev_path = f"/dev/mapper/{loop_dev}"
                if readonly:
                    subprocess.run(['sudo', 'mount', '-r', dev_path, mount_point], check=True)
                else:
                    subprocess.run(['sudo', 'mount', dev_path, mount_point], check=True)
                print(f"Mounted {dev_path} at {mount_point}")

            return True

        except subprocess.CalledProcessError as e:
            print(f"Error mounting partitions: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error while mounting: {e}")
            return False

    def cleanup(self):
        """Unmount everything and remove loop devices"""
        # Unmount in reverse order
        for mount_point in reversed(self.mount_points):
            if os.path.ismount(mount_point):
                try:
                    subprocess.run(['sudo', 'umount', mount_point], check=True)
                    print(f"Unmounted {mount_point}")
                except subprocess.CalledProcessError as e:
                    print(f"Error unmounting {mount_point}: {e}")

        # Remove loop devices (may already be removed by umount, so don't fail on error)
        result = subprocess.run(['sudo', 'kpartx', '-d', self.image_path], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("Removed loop devices")
        else:
            # This is often benign - loop devices may already be removed
            print("Loop devices cleanup complete (may have been auto-removed)")

def main():
    # Check for sudo privileges first
    if os.geteuid() != 0:
        print("This script must be run with sudo")
        sys.exit(1)

    # Remove script name from args
    args = sys.argv[1:]

    # Check for readonly flag
    readonly_mode = False
    if '--readonly' in args:
        readonly_mode = True
        args.remove('--readonly')

    # Check for cleanup flag
    cleanup_mode = False
    if '--cleanup' in args:
        cleanup_mode = True
        args.remove('--cleanup')

    # Check remaining arguments
    if len(args) != 1:
        print("Usage: sudo python3 mount_img.py [--cleanup] [--readonly] <image_file>")
        sys.exit(1)

    image_path = args[0]
    if not os.path.exists(image_path):
        print(f"Image file {image_path} not found")
        sys.exit(1)

    mounter = ImageMounter(image_path)

    if not cleanup_mode:
        try:
            if not mounter.setup_loop_devices():
                sys.exit(1)

            if not mounter.mount_partitions(readonly_mode):
                mounter.cleanup()
                sys.exit(1)

            print("\nMounting completed successfully!")
            print("Loop devices:", mounter.loop_devices)
            print("Mount points:", mounter.mount_points)
            print("\nTo unmount when finished, run:")
            print(f"sudo python3 {sys.argv[0]} --cleanup {image_path}")

        except KeyboardInterrupt:
            print("\nOperation interrupted by user")
            mounter.cleanup()
            sys.exit(1)
    else:
        # Handle cleanup mode
        mounter.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    main()
