#!/usr/bin/env python3
import os
import sys
import subprocess
from contextlib import contextmanager
from config import SYSTEM_PACKAGES, ROOTFS_MOUNT

# Adapted from cedar-server create_cedar_image scripts

@contextmanager
def mount_context(rootfs_path):
    """Context manager to handle mounting and unmounting of necessary filesystems"""
    mounted_paths = []

    try:
        # Define mount points: (name, destination, mount_args, make_rslave)
        mount_points = [
            ('proc', os.path.join(rootfs_path, 'proc'), ['-t', 'proc', 'proc'], False),
            ('sys', os.path.join(rootfs_path, 'sys'), ['--rbind', '/sys'], True),
            ('dev', os.path.join(rootfs_path, 'dev'), ['--rbind', '/dev'], True),
            ('run', os.path.join(rootfs_path, 'run'), ['--rbind', '/run'], True),
        ]

        # Perform mounts
        for name, dest, options, make_rslave in mount_points:
            os.makedirs(dest, exist_ok=True)
            subprocess.run(['mount'] + options + [dest], check=True)
            if make_rslave:
                subprocess.run(['mount', '--make-rslave', dest], check=True)
            mounted_paths.append(dest)
            print(f"Mounted {name} at {dest}")

        yield

    finally:
        # Unmount in reverse order
        for path in reversed(mounted_paths):
            try:
                subprocess.run(['umount', '-R', path], check=True)
                print(f"Unmounted {path}")
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to unmount {path}: {e}")

def update_system(rootfs_path):
    """Run apt update and upgrade in chroot environment"""
    if not os.path.isdir(rootfs_path):
        raise ValueError(f"Root filesystem path {rootfs_path} does not exist")

    print(f"Updating system packages in {rootfs_path}")

    # Ensure DNS resolution works in chroot
    resolv_conf = os.path.join(rootfs_path, 'etc/resolv.conf')
    resolv_backup = resolv_conf + '.bak'
    
    # Backup existing resolv.conf
    if os.path.exists(resolv_conf):
        subprocess.run(['cp', resolv_conf, resolv_backup])

    # Copy host's resolv.conf
    subprocess.run(['cp', '/etc/resolv.conf', resolv_conf])

    try:
        with mount_context(rootfs_path):
            # Update package lists
            print("Running apt update...")
            subprocess.run([
                'chroot', rootfs_path,
                'apt-get', 'update'
            ], check=True)

            # Upgrade packages
            print("Running apt upgrade...")
            subprocess.run([
                'chroot', rootfs_path,
                'apt-get', 'upgrade', '-y'
            ], check=True)

            # Install essential packages for Citrascope
            subprocess.run([
                'chroot', rootfs_path,
                'apt-get', 'install', '-y'
            ] + SYSTEM_PACKAGES, check=True)

            # Clean up
            print("Cleaning up...")
            subprocess.run([
                'chroot', rootfs_path,
                'apt-get', 'clean'
            ], check=True)

            print("System update completed successfully")

    finally:
        # Restore original resolv.conf
        if os.path.exists(resolv_backup):
            subprocess.run(['mv', resolv_backup, resolv_conf])

def main():
    try:
        # Create policy-rc.d to prevent services from starting
        policy_file = os.path.join(ROOTFS_MOUNT, 'usr/sbin/policy-rc.d')
        os.makedirs(os.path.dirname(policy_file), exist_ok=True)
        with open(policy_file, 'w') as f:
            f.write('#!/bin/sh\nexit 101\n')
        os.chmod(policy_file, 0o755)
        print(f"Created policy-rc.d")

        update_system(ROOTFS_MOUNT)
        print("Successfully updated and installed packages")
    except Exception as e:
        print(f"Error updating packages: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
