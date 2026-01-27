#!/usr/bin/env python3
"""
Script to set Raspberry Pi hostname to 'citrascope' and configure for citrascope.local mDNS

Usage:
  sudo python3 set_hostname.py /path/to/mounted/rootfs
"""

import os
import sys
import subprocess
import re
from config import HOSTNAME, ROOTFS_MOUNT

def set_hostname(rootfs_path, hostname="citrascope"):
    """
    Set the hostname in the mounted Raspberry Pi image
    """
    if not os.path.isdir(rootfs_path):
        print(f"Error: {rootfs_path} does not exist or is not a directory")
        return False

    # Update /etc/hostname
    hostname_file = os.path.join(rootfs_path, 'etc', 'hostname')
    try:
        with open(hostname_file, 'w') as f:
            f.write(f"{hostname}\n")
        print(f"Updated {hostname_file}")
    except Exception as e:
        print(f"Error writing hostname file: {e}")
        return False

    # Update /etc/hosts
    hosts_file = os.path.join(rootfs_path, 'etc', 'hosts')
    try:
        with open(hosts_file, 'r') as f:
            lines = f.readlines()

        with open(hosts_file, 'w') as f:
            for line in lines:
                # Replace old hostname with new one in 127.0.1.1 line
                if line.startswith('127.0.1.1'):
                    f.write(f"127.0.1.1\t{hostname}\n")
                else:
                    f.write(line)
        print(f"Updated {hosts_file}")
    except Exception as e:
        print(f"Error writing hosts file: {e}")
        return False

    # Ensure avahi-daemon is installed and enabled for mDNS
    # The service will be enabled during the system update phase
    print(f"Hostname set to '{hostname}' (will be accessible as {hostname}.local)")
    
    return True

def main():
    rootfs_path = ROOTFS_MOUNT
    hostname = HOSTNAME

    if len(sys.argv) > 1:
        rootfs_path = sys.argv[1]

    if len(sys.argv) > 2:
        hostname = sys.argv[2]

    if not os.path.exists(rootfs_path):
        print(f"Error: Root filesystem path {rootfs_path} does not exist")
        sys.exit(1)

    if set_hostname(rootfs_path, hostname):
        print(f"Successfully set hostname to {hostname}")
        sys.exit(0)
    else:
        print("Failed to set hostname")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())
