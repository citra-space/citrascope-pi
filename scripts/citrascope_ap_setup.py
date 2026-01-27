#!/usr/bin/env python3
"""
WiFi Access Point setup for Citrascope
This script configures a WiFi access point using NetworkManager when no network is available.
This file should be installed to /usr/local/sbin/citrascope-ap-setup.py on the target system.
"""

import subprocess
import sys
import logging
from pathlib import Path
import random
import time

# Import from parent directory (when installed, this will be in /usr/local/sbin)
try:
    from config import WIFI_AP_PASSWORD, WIFI_AP_SSID_PREFIX, AP_GATEWAY, AP_CHANNEL, HOSTNAME
except ImportError:
    # Fallback to defaults if config not available (when installed on target)
    WIFI_AP_PASSWORD = "citrascope"
    WIFI_AP_SSID_PREFIX = "citrascope"
    AP_GATEWAY = "10.42.0.1"
    AP_CHANNEL = 6
    HOSTNAME = "citrascope"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'/var/log/{HOSTNAME}-ap-setup.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_serial_number():
    """Get the Raspberry Pi serial number, trying multiple methods."""
    try:
        # Try cpuinfo first
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    serial = line.split(':')[1].strip()
                    if serial and serial != '0000000000000000':
            f'/etc/{HOSTNAME}-ap-configured').exists():
        logging.info("Access point already configured, skipping setup")
        return True

    serial = get_serial_number()
    ap_ssid = f"{WIFI_AP_SSID_PREFIX}-{serial}"
    ap_password = WIFI_AP_PASSWORD

    logging.info(f"Setting up access point: {ap_ssid}")

    connection_name = f"{HOSTNAME}-ap"
    
    try:
        # Check if connection already exists
        result = subprocess.run(['nmcli', 'con', 'show', connection_name],
                                capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info(f"Connection '{connection_name}' already exists, deleting it")
            subprocess.run(['nmcli', 'con', 'delete', connection_name], check=True)

        # Create the access point connection
        logging.info("Creating access point connection")
        subprocess.run([
            'nmcli', 'con', 'add',
            'type', 'wifi',
            'ifname', 'wlan0',
            'con-name', connection_name,
            'autoconnect', 'yes',
            'ssid', ap_ssid,
            'mode', 'ap',
            '802-11-wireless.band', 'bg',
            '802-11-wireless.channel', str(AP_CHANNEL),
            'ipv4.method', 'shared',
            'ipv4.addresses', f'{AP_GATEWAY}/24',
            'wifi-sec.key-mgmt', 'wpa-psk',
            'wifi-sec.psk', ap_password
        ], check=True)

        # Set autoconnect to true
        subprocess.run([
            'nmcli', 'con', 'modify', connection_name,
            'connection.autoconnect', 'true'
        ], check=True)

        # Try to bring up the connection
        logging.info("Activating access point")
        result = subprocess.run(['nmcli', 'con', 'up', connection_name],
                                capture_output=True, text=True)

        if result.returncode != 0:
            logging.error(f"Error bringing up access point: {result.stderr}")
            return False

        # Create flag file to indicate successful setup
        Path(f'/etc/{HOSTNAME}
        # Try to bring up the connection
        logging.info("Activating access point")
        result = subprocess.run(['nmcli', 'con', 'up', 'citrascope-ap'],
                                capture_output=True, text=True)

        if result.returncode != 0:
            logging.error(f"Error bringing up access point: {result.stderr}")
            return False

        # Create flag file to indicate successful setup
        Path('/etc/citrascope-ap-configured').touch()
        logging.info("Access point setup completed successfully")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"Command failed: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return False
f"Starting {HOSTNAME}
if __name__ == '__main__':
    logging.info("Starting citrascope-ap setup script")
    if setup_access_point():
        sys.exit(0)
    else:
        sys.exit(1)
