#!/usr/bin/env python3
"""Configure Comitup WiFi provisioning - bare minimum"""
import os, sys
from pathlib import Path
from config import WIFI_AP_PASSWORD, WIFI_AP_SSID_PREFIX, ROOTFS_MOUNT

def configure_comitup(rootfs_path):
    print("Configuring Comitup...")
    config = f"""# Comitup configuration
ap_name: {WIFI_AP_SSID_PREFIX}
ap_password: {WIFI_AP_PASSWORD}
web_service: citrascope.service
enable_appliance_mode: true
"""
    (Path(rootfs_path) / 'etc/comitup.conf').write_text(config)
    print("  ✓ Created /etc/comitup.conf (ap_name will be updated on first boot)")
    return True

def enable_comitup_service(rootfs_path):
    print("Enabling Comitup service...")
    link = Path(rootfs_path) / 'etc/systemd/system/multi-user.target.wants/comitup.service'
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink(): 
        link.unlink()
    link.symlink_to('/lib/systemd/system/comitup.service')
    print("  ✓ Enabled comitup.service")
    return True

def fix_service_conflicts(rootfs_path):
    print("Fixing service conflicts...")
    wpa = Path(rootfs_path) / 'etc/systemd/system/multi-user.target.wants/wpa_supplicant.service'
    if wpa.exists() or wpa.is_symlink():
        wpa.unlink()
        print("  ✓ Disabled wpa_supplicant.service")
    for svc in ["dhcpcd.service", "systemd-resolved.service"]:
        link = Path(rootfs_path) / f'etc/systemd/system/{svc}'
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.exists() or link.is_symlink(): 
            link.unlink()
        link.symlink_to('/dev/null')
        print(f"  ✓ Masked {svc}")
    if (Path(rootfs_path) / 'lib/systemd/system/dnsmasq.service').exists():
        link = Path(rootfs_path) / 'etc/systemd/system/dnsmasq.service'
        if link.exists() or link.is_symlink(): 
            link.unlink()
        link.symlink_to('/dev/null')
        print("  ✓ Masked dnsmasq.service")
    return True

def main():
    if not os.path.exists(ROOTFS_MOUNT):
        print(f"Error: {ROOTFS_MOUNT} does not exist")
        return False
    try:
        configure_comitup(ROOTFS_MOUNT)
        enable_comitup_service(ROOTFS_MOUNT)
        fix_service_conflicts(ROOTFS_MOUNT)
        print("Comitup configuration completed!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
