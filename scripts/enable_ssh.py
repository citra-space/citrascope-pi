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

def main():
    rootfs_path = ROOTFS_MOUNT

    if len(sys.argv) > 1:
        rootfs_path = sys.argv[1]

    if not os.path.exists(rootfs_path):
        print(f"Error: Root filesystem path {rootfs_path} does not exist")
        sys.exit(1)

    if enable_ssh_service(rootfs_path):
        print("Successfully enabled SSH")
        sys.exit(0)
    else:
        print("Failed to enable SSH")
        sys.exit(1)

if __name__ == "__main__":
    main()
