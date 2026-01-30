#!/usr/bin/env python3
import os
import sys
from config import ROOTFS_MOUNT

def enable_ssh_service(rootfs_path):
    """
    Enable SSH service in root filesystem
    """
    if not os.path.isdir(rootfs_path):
        print(f"Error: {rootfs_path} does not exist or is not a directory")
        return False

    # Create systemd symlink to enable SSH
    systemd_path = os.path.join(rootfs_path, 'etc/systemd/system/sshd.service')
    ssh_service = os.path.join(rootfs_path, 'lib/systemd/system/ssh.service')
    multi_user_target = os.path.join(rootfs_path, 'etc/systemd/system/multi-user.target.wants')
    
    os.makedirs(multi_user_target, exist_ok=True)
    
    ssh_service_link = os.path.join(multi_user_target, 'ssh.service')
    
    if os.path.exists(ssh_service):
        try:
            if not os.path.exists(ssh_service_link):
                os.symlink('/lib/systemd/system/ssh.service', ssh_service_link)
            print("Enabled SSH service")
            return True
        except Exception as e:
            print(f"Error enabling SSH service: {e}")
            return False
    else:
        print(f"Warning: SSH service file not found at {ssh_service}")
        return False

def main(rootfs_path=None):
    if rootfs_path is None:
        rootfs_path = ROOTFS_MOUNT

    if not os.path.exists(rootfs_path):
        print(f"Error: Root filesystem path {rootfs_path} does not exist")
        return False

    if enable_ssh_service(rootfs_path):
        print("Successfully enabled SSH")
        return True
    else:
        print("Failed to enable SSH")
        return False

if __name__ == "__main__":
    # Only parse sys.argv when run directly
    rootfs_path = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(0 if main(rootfs_path) else 1)
