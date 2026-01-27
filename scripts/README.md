# Scripts Directory

This directory contains Python utilities for building Lemon Pi images.

## Configuration

**[config.py](config.py)** - Centralized configuration for all build scripts. Edit this file to customize usernames, passwords, hostnames, WiFi settings, and more.

## Core Image Manipulation

- **mount_img.py** - Mount/unmount Raspberry Pi image partitions using kpartx
- **resize_fs.py** - Extend image file and resize the root filesystem
- **update_upgrade_chroot.py** - Run apt update/upgrade inside chroot environment

## System Configuration

- **add_user.py** - Create the `citra` user with sudo access and proper groups
- **set_hostname.py** - Configure hostname to `lemon` with mDNS support
- **enable_ssh.py** - Enable SSH service on first boot

## Citrascope Installation

- **install_citrascope.py** - Install Citrascope in Python venv, create systemd service
- **citrascope-ap-setup.py** - WiFi access point setup script (runs on target system)
- **install-citrascope-ap-setup.py** - Install AP scripts into image

## Usage

These scripts are called by the main orchestration scripts (`customize-pi-image.sh` and `install_lemon.sh`) and should not typically be run directly. However, they can be useful for debugging:

```bash
# Mount an image
sudo python3 mount_img.py ../path/to/image.img

# View mounted partitions
ls /mnt/part1  # boot partition
ls /mnt/part2  # root partition

# Unmount when done
sudo python3 mount_img.py --cleanup ../path/to/image.img
```

## Requirements

All scripts require:
- Python 3.6+
- sudo privileges
- kpartx installed
- Running on Linux (chroot operations)
