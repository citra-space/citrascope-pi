#!/usr/bin/env python3
"""
Install the WiFi AP setup scripts and services into the target image.
"""

from pathlib import Path
import shutil
import sys
from config import HOSTNAME, ROOTFS_MOUNT

# Adapted from cedar-server create_cedar_image scripts

def install_ap_setup(root_mount):
    """Install AP setup script and systemd services"""
    
    # Create directories if needed
    sbin_path = Path(root_mount) / 'usr/local/sbin'
    systemd_path = Path(root_mount) / 'etc/systemd/system'
    sbin_path.mkdir(parents=True, exist_ok=True)
    systemd_path.mkdir(parents=True, exist_ok=True)

    # Copy the AP setup script and config.py
    script_name = f'{HOSTNAME}-ap-setup.py'
    shutil.copy2('citrascope-ap-setup.py', sbin_path / script_name)
    shutil.copy2('config.py', sbin_path / 'config.py')  # Copy config for runtime use

    # Ensure script is executable
    script_path = sbin_path / script_name
    script_path.chmod(0o755)

    # Create systemd service file for AP setup
    service_content = f"""[Unit]
Description={HOSTNAME.title()} WiFi Access Point Setup
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/sbin/{script_name}
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
    
    service_name = f'{HOSTNAME}-ap-setup.service'
    service_file = systemd_path / service_name
    with open(service_file, 'w') as f:
        f.write(service_content)
    
    # Enable the service
    enable_path = Path(root_mount) / 'etc/systemd/system/multi-user.target.wants'
    enable_path.mkdir(parents=True, exist_ok=True)
    
    link_path = enable_path / service_name
    if not link_path.exists():
        link_path.symlink_to(f'/etc/systemd/system/{service_name}')
    
    print(f"Installed and enabled {service_name}")

def main():
    try:
        # Change to scripts directory
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        install_ap_setup(ROOTFS_MOUNT)
        print(f"Successfully installed AP setup")
    except Exception as e:
        print(f"Error installing AP setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
