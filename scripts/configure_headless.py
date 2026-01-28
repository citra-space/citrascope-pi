#!/usr/bin/env python3
"""
Configure headless Raspberry Pi settings to skip first-boot wizard.
Sets locale, timezone, keyboard layout, WiFi country, and disables interactive prompts.
"""

import os
import sys
import subprocess
from pathlib import Path
from config import LOCALE, TIMEZONE, KEYBOARD_LAYOUT, WIFI_COUNTRY, ROOTFS_MOUNT, BOOT_MOUNT

def configure_locale(rootfs_path):
    """Configure system locale"""
    print(f"Configuring locale: {LOCALE}...")
    
    # Update /etc/locale.gen
    locale_gen_path = Path(rootfs_path) / 'etc/locale.gen'
    
    # Read existing content
    with open(locale_gen_path, 'r') as f:
        lines = f.readlines()
    
    # Uncomment the desired locale (format in file is "# en_US.UTF-8 UTF-8")
    locale_base = LOCALE.split('.')[0]  # en_US
    locale_encoding = LOCALE.split('.')[1] if '.' in LOCALE else 'UTF-8'  # UTF-8
    locale_line = f'{locale_base}.{locale_encoding} {locale_encoding}'
    
    with open(locale_gen_path, 'w') as f:
        for line in lines:
            stripped = line.strip()
            # Check if this is our locale line (commented or not)
            if stripped == f'# {locale_line}' or stripped == f'#{locale_line}':
                f.write(f'{locale_line}\n')
            elif stripped == locale_line:
                f.write(line)  # Already uncommented
            else:
                f.write(line)
    
    # Create /etc/default/locale
    default_locale_path = Path(rootfs_path) / 'etc/default/locale'
    with open(default_locale_path, 'w') as f:
        f.write(f'LANG={LOCALE}\n')
        f.write(f'LC_ALL={LOCALE}\n')
    
    # Generate locale
    try:
        subprocess.run(['chroot', rootfs_path, 'locale-gen'], check=True, capture_output=True)
        print(f"  ✓ Locale configured: {LOCALE}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to generate locale: {e}")
        return False
    
    return True

def configure_keyboard(rootfs_path):
    """Configure keyboard layout"""
    print(f"Configuring keyboard layout: {KEYBOARD_LAYOUT}...")
    
    # Create /etc/default/keyboard
    keyboard_config = f'''XKBLAYOUT="{KEYBOARD_LAYOUT}"
XKBMODEL="pc105"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
'''
    
    keyboard_path = Path(rootfs_path) / 'etc/default/keyboard'
    with open(keyboard_path, 'w') as f:
        f.write(keyboard_config)
    
    # Set debconf selections to prevent prompts
    debconf_commands = [
        f'keyboard-configuration keyboard-configuration/layoutcode string {KEYBOARD_LAYOUT}',
        'keyboard-configuration keyboard-configuration/variantcode string',
        'keyboard-configuration keyboard-configuration/modelcode string pc105',
    ]
    
    for cmd in debconf_commands:
        try:
            subprocess.run(
                ['chroot', rootfs_path, 'bash', '-c', f'echo "{cmd}" | debconf-set-selections'],
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # Continue if debconf fails
    
    # Reconfigure keyboard-configuration non-interactively
    try:
        env = os.environ.copy()
        env['DEBIAN_FRONTEND'] = 'noninteractive'
        subprocess.run(
            ['chroot', rootfs_path, 'dpkg-reconfigure', '-f', 'noninteractive', 'keyboard-configuration'],
            check=True, capture_output=True, env=env
        )
        print(f"  ✓ Keyboard configured: {KEYBOARD_LAYOUT}")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to configure keyboard: {e}")
        return False
    
    return True

def configure_timezone(rootfs_path):
    """Configure timezone"""
    print(f"Configuring timezone: {TIMEZONE}...")
    
    # Create /etc/timezone
    timezone_path = Path(rootfs_path) / 'etc/timezone'
    with open(timezone_path, 'w') as f:
        f.write(f'{TIMEZONE}\n')
    
    # Create symlink /etc/localtime -> /usr/share/zoneinfo/{TIMEZONE}
    localtime_path = Path(rootfs_path) / 'etc/localtime'
    zoneinfo_path = f'/usr/share/zoneinfo/{TIMEZONE}'
    
    # Remove existing file/link
    if localtime_path.exists() or localtime_path.is_symlink():
        localtime_path.unlink()
    
    # Create symlink
    localtime_path.symlink_to(zoneinfo_path)
    
    print(f"  ✓ Timezone configured: {TIMEZONE}")
    return True

def configure_wifi_country(rootfs_path, boot_path):
    """Configure WiFi country code (required for WiFi to work)"""
    print(f"Configuring WiFi country code: {WIFI_COUNTRY}...")
    
    # Add country code to /boot/firmware/config.txt
    config_txt_path = Path(boot_path) / 'config.txt'
    
    if config_txt_path.exists():
        with open(config_txt_path, 'r') as f:
            content = f.read()
        
        # Check if country code already set
        if 'country=' not in content.lower():
            # Add WiFi country configuration
            with open(config_txt_path, 'a') as f:
                f.write(f'\n# WiFi Country Code\n')
                f.write(f'country={WIFI_COUNTRY}\n')
            print(f"  ✓ Added WiFi country to config.txt: {WIFI_COUNTRY}")
        else:
            print(f"  ✓ WiFi country already configured in config.txt")
    else:
        print(f"  ✗ config.txt not found at {config_txt_path}")
        return False
    
    return True

def create_setup_marker(rootfs_path):
    """Create marker file to indicate setup is complete"""
    print("Creating setup completion marker...")
    
    marker_path = Path(rootfs_path) / 'etc/rpi-initial-setup'
    marker_path.touch()
    
    print("  ✓ Created /etc/rpi-initial-setup")
    return True

def remove_wizard(rootfs_path):
    """Remove first-boot wizard and disable userconfig service"""
    print("Disabling first-boot setup...")
    
    # Remove GUI wizard if present
    piwiz_path = Path(rootfs_path) / 'etc/xdg/autostart/piwiz.desktop'
    if piwiz_path.exists():
        piwiz_path.unlink()
        print("  ✓ Removed piwiz.desktop")
    
    # Disable userconfig service (handles first-boot user rename/setup)
    userconfig_service = Path(rootfs_path) / 'etc/systemd/system/multi-user.target.wants/userconfig.service'
    if userconfig_service.exists() or userconfig_service.is_symlink():
        userconfig_service.unlink()
        print("  ✓ Disabled userconfig.service")
    
    # Also remove the userconfig script itself to be safe
    userconfig_script = Path(rootfs_path) / 'usr/lib/userconf-pi/userconf'
    if userconfig_script.exists():
        userconfig_script.unlink()
        print("  ✓ Removed userconfig script")
    
    return True

def main():
    """Main configuration function"""
    if not os.path.exists(ROOTFS_MOUNT):
        print(f"Error: Root filesystem path {ROOTFS_MOUNT} does not exist")
        return False
    
    if not os.path.exists(BOOT_MOUNT):
        print(f"Error: Boot filesystem path {BOOT_MOUNT} does not exist")
        return False
    
    try:
        # Configure locale
        if not configure_locale(ROOTFS_MOUNT):
            return False
        
        # Configure keyboard
        if not configure_keyboard(ROOTFS_MOUNT):
            return False
        
        # Configure timezone
        if not configure_timezone(ROOTFS_MOUNT):
            return False
        
        # Configure WiFi country
        if not configure_wifi_country(ROOTFS_MOUNT, BOOT_MOUNT):
            return False
        
        # Create setup marker
        if not create_setup_marker(ROOTFS_MOUNT):
            return False
        
        # Remove wizard
        if not remove_wizard(ROOTFS_MOUNT):
            return False
        
        print("Headless configuration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error configuring headless settings: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
