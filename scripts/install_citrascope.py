#!/usr/bin/env python3
"""
Install Citrascope into a mounted Raspberry Pi image.
This script sets up a Python virtual environment and installs Citrascope with INDI support.
"""

import os
import sys
import subprocess
from contextlib import contextmanager
from config import USERNAME, CITRASCOPE_VENV_PATH, ROOTFS_MOUNT

@contextmanager
def mount_context(rootfs_path):
    """Context manager to handle mounting and unmounting of necessary filesystems"""
    mounted_paths = []

    try:
        mount_points = [
            ('proc', os.path.join(rootfs_path, 'proc'), ['-t', 'proc', 'proc'], False),
            ('sys', os.path.join(rootfs_path, 'sys'), ['--rbind', '/sys'], True),
            ('dev', os.path.join(rootfs_path, 'dev'), ['--rbind', '/dev'], True),
            ('run', os.path.join(rootfs_path, 'run'), ['--rbind', '/run'], True),
        ]

        for name, dest, options, make_rslave in mount_points:
            os.makedirs(dest, exist_ok=True)
            subprocess.run(['mount'] + options + [dest], check=True)
            if make_rslave:
                subprocess.run(['mount', '--make-rslave', dest], check=True)
            mounted_paths.append(dest)

        yield

    finally:
        for path in reversed(mounted_paths):
            try:
                subprocess.run(['umount', '-R', path], check=True)
            except subprocess.CalledProcessError:
                pass

def install_citrascope(rootfs_path, homedir):
    """Install Citrascope and configure it to run on boot"""
    
    print("Creating Citrascope virtual environment...")
    with mount_context(rootfs_path):
        # Create virtual environment
        subprocess.run([
            'chroot', rootfs_path,
            'python3', '-m', 'venv', CITRASCOPE_VENV_PATH
        ], check=True)
        
        print("Installing Citrascope with INDI support...")
        
        # Install citrascope[indi] in the venv
        subprocess.run([
            'chroot', rootfs_path,
            '/bin/bash', '-c',
            f'source {CITRASCOPE_VENV_PATH}/bin/activate && pip install --upgrade pip && pip install citrascope[indi]'
        ], check=True)
        
        print("Citrascope installed successfully")

def create_systemd_service(rootfs_path):
    """Create systemd service for Citrascope"""
    
    service_content = f"""[Unit]
Description=Citrascope Telescope Control Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={USERNAME}
WorkingDirectory=/home/{USERNAME}
ExecStart={CITRASCOPE_VENV_PATH}/bin/citrascope
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
    
    service_path = os.path.join(rootfs_path, 'lib/systemd/system/citrascope.service')
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    print("Created citrascope.service")
    
    # Enable the service
    service_link = os.path.join(rootfs_path, 'etc/systemd/system/multi-user.target.wants/citrascope.service')
    os.makedirs(os.path.dirname(service_link), exist_ok=True)
    
    if not os.path.exists(service_link):
        os.symlink('/lib/systemd/system/citrascope.service', service_link)
    
    print("Enabled citrascope.service")

def set_permissions(rootfs_path, homedir):
    """Set correct ownership for user files"""
    print("Setting file ownership...")
    
    # Change ownership of home directory
    for root, dirs, files in os.walk(homedir):
        for d in dirs:
            os.chown(os.path.join(root, d), 1001, 1001)
        for f in files:
            os.chown(os.path.join(root, f), 1001, 1001)
    
    os.chown(homedir, 1001, 1001)
    
    print("File ownership set")

def main():
    HOMEDIR = os.path.join(ROOTFS_MOUNT, f"home/{USERNAME}")
    
    if not os.path.exists(ROOTFS_MOUNT):
        print(f"Error: Root filesystem path {ROOTFS_MOUNT} does not exist")
        sys.exit(1)
    
    if not os.path.exists(HOMEDIR):
        print(f"Error: Home directory {HOMEDIR} does not exist. User must be created first.")
        sys.exit(1)
    
    try:
        # Ensure DNS resolution works
        resolv_conf = os.path.join(ROOTFS_MOUNT, 'etc/resolv.conf')
        resolv_backup = resolv_conf + '.bak'
        
        if os.path.exists(resolv_conf):
            subprocess.run(['cp', resolv_conf, resolv_backup])
        subprocess.run(['cp', '/etc/resolv.conf', resolv_conf])
        
        # Install Citrascope
        install_citrascope(ROOTFS_MOUNT, HOMEDIR)
        
        # Create systemd service
        create_systemd_service(ROOTFS_MOUNT)
        
        # Set permissions
        set_permissions(ROOTFS_MOUNT, HOMEDIR)
        
        # Restore resolv.conf
        if os.path.exists(resolv_backup):
            subprocess.run(['mv', resolv_backup, resolv_conf])
        
        print("Citrascope installation completed successfully!")
        
    except Exception as e:
        print(f"Error installing Citrascope: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
