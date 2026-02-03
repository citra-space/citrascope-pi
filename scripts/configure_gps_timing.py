#!/usr/bin/env python3
"""
Configure GPS time synchronization with chrony and gpsd.
Supports USB GPS, UART GPS, and PPS for microsecond-level accuracy.

=== GPS TIME SYNCHRONIZATION DOCUMENTATION ===

OVERVIEW
--------
This script configures automatic GPS-based time synchronization using:
- gpsd: GPS hardware management and data extraction
- chrony: NTP daemon that uses GPS as a Stratum 1 time source
- Automatic fallback to internet NTP when GPS unavailable

SUPPORTED HARDWARE
------------------
USB GPS:
  - Plug and play, monitored on /dev/ttyUSB0 and /dev/ttyACM0
  - Any generic NMEA GPS (Adafruit Ultimate GPS, GlobalSat BU-353, etc.)
  - u-blox NEO series (6M, 7M, 8M, 9M) - typically /dev/ttyACM0
  - FTDI/Prolific USB-to-serial GPS - typically /dev/ttyUSB0

UART GPS:
  - Default: GPIO 14/15 (/dev/ttyAMA0) - most common
  - Alternative: GPIO 12/13 (/dev/ttyAMA5) - pre-enabled
  - Other pins: GPIO 4/5 or 8/9 (requires config.txt edit)

PPS (Pulse Per Second):
  - Default: GPIO 18 (configurable in scripts/config.py)
  - Provides microsecond-level accuracy (vs ~50ms without PPS)
  - Optional but recommended for observatory use

GPIO PINOUT FOR UART GPS
-------------------------
Default pins (GPIO 14/15):
  Pin 8  (GPIO 14) → GPS TX (transmit)
  Pin 10 (GPIO 15) → GPS RX (receive)
  Pin 12 (GPIO 18) → GPS PPS (pulse per second, optional)
  Pin 6  (Ground)  → GPS GND
  Pin 2 or 4 (5V)  → GPS VCC

Alternative pins (GPIO 12/13):
  Pin 32 (GPIO 12) → GPS TX
  Pin 33 (GPIO 13) → GPS RX
  Requires manual config.txt edit (see CONFIGURATION section)
  Edit /etc/default/gpsd: DEVICES="/dev/ttyAMA5 /dev/pps0"
  Run: sudo systemctl restart gpsd

QUICK START
-----------
USB GPS:
  1. Plug into any USB port
  2. Wait 30-60 seconds for GPS lock
  3. Verify: chronyc sources -v

UART GPS:
  1. Wire up GPS module to GPIO pins (see pinout above)
  2. Reboot (UART enabled via /boot/firmware/config.txt)
  3. Verify: cgps -s

VERIFICATION COMMANDS
---------------------
Check GPS data:           cgps -s
Monitor GPS details:      gpsmon
Test PPS signal:          sudo ppstest /dev/pps0
View time sources:        chronyc sources -v
Check sync status:        chronyc tracking

Expected output when GPS locked:
  - chronyc sources: GPS shows * (selected) or + (combined)
  - Reference ID: NMEA or PPS
  - Stratum: 1 (Stratum 1 time source)
  - System time accuracy: <1μs with PPS, ~50ms without

CONFIGURATION
-------------
Change PPS GPIO pin:
  Edit /boot/firmware/config.txt:
    dtoverlay=pps-gpio,gpiopin=22  # change from default 18
  Reboot

Use different UART pins:
  Pi 3/4: Edit /boot/firmware/config.txt:
    dtoverlay=uart3   # GPIO 4/5
    dtoverlay=uart4   # GPIO 8/9
  Pi 5: Different UART configuration, consult Pi 5 documentation
  Reboot after changes

Disable serial console (if needed):
  Automatically done for primary UART (GPIO 14/15)
  Manual: edit /boot/firmware/cmdline.txt, remove console=serial0,115200

TROUBLESHOOTING
---------------
GPS not detected:
  - Check device exists: ls -l /dev/ttyAMA* /dev/ttyUSB* /dev/pps*
  - Check gpsd: sudo systemctl status gpsd
  - Monitor GPS directly: gpsmon
  - USB GPS: Try different USB port, check dmesg for errors

No PPS signal:
  - Test: sudo ppstest /dev/pps0
  - Verify wiring on GPIO 18 (or configured pin)
  - Some GPS modules need PPS enabled via configuration

Time not syncing:
  - Wait 5-10 minutes for GPS lock and chrony convergence
  - GPS needs clear sky view for satellite lock
  - Check chrony using GPS: chronyc sources -v (should show * or +)
  - Check for errors: journalctl -u chronyd -u gpsd

No GPS hardware connected:
  - System works normally with internet NTP
  - gpsd runs but uses minimal resources (~2-5 MB RAM)
  - Plug in GPS anytime - detected instantly, no reboot needed

COMMON GPS MODULES
------------------
These work out of box with default configuration:
  - Adafruit Ultimate GPS (UART or USB versions)
  - u-blox NEO-6M, NEO-7M, NEO-8M, NEO-9M
  - GlobalSat BU-353 (USB)
  - SparkFun GPS modules
  - Any generic NMEA GPS module

TECHNICAL DETAILS
-----------------
How it works:
  1. gpsd reads GPS NMEA sentences and PPS pulses
  2. gpsd exposes time data via shared memory (SHM 0 = NMEA, SHM 1 = PPS)
  3. chrony reads SHM segments as reference clocks
  4. chrony disciplines system clock using GPS time
  5. If GPS unavailable, chrony falls back to internet NTP pools

Accuracy:
  - Internet NTP only: ~10-50ms typical
  - GPS (NMEA) only: ~50ms (limited by NMEA sentence timing)
  - GPS + PPS: <1μs (sub-microsecond possible)

Configuration files modified:
  - /boot/firmware/config.txt: UART and PPS overlays
  - /boot/firmware/cmdline.txt: Disable serial console
  - /etc/default/gpsd: Device list and options
  - /etc/chrony/chrony.conf: GPS reference clocks

Services:
  - gpsd.service: GPS daemon, auto-starts on boot
  - chronyd.service: NTP daemon, already running by default
"""

import os
import sys
from pathlib import Path
from config import (
    ROOTFS_MOUNT, 
    BOOT_MOUNT,
    GPS_PPS_GPIO,
    GPS_ENABLE_PRIMARY_UART
)

def configure_boot_config(boot_path):
    """Configure UART and PPS in /boot/firmware/config.txt"""
    print("Configuring GPS hardware in boot config...")
    
    config_txt_path = Path(boot_path) / 'config.txt'
    
    if not config_txt_path.exists():
        print(f"  ✗ config.txt not found at {config_txt_path}")
        return False
    
    with open(config_txt_path, 'r') as f:
        content = f.read()
    
    # Prepare GPS configuration section
    gps_config = '\n# GPS Time Synchronization\n'
    
    if GPS_ENABLE_PRIMARY_UART:
        gps_config += '# Enable hardware UART for GPS (works on all Pi models)\n'
        gps_config += 'enable_uart=1\n'
    
    # Enable PPS support
    gps_config += f'# Enable PPS (Pulse Per Second) on GPIO {GPS_PPS_GPIO}\n'
    gps_config += f'dtoverlay=pps-gpio,gpiopin={GPS_PPS_GPIO}\n'
    
    # Check if GPS config already exists
    if 'GPS Time Synchronization' not in content:
        with open(config_txt_path, 'a') as f:
            f.write(gps_config)
        print("  ✓ Added GPS hardware configuration to config.txt")
    else:
        print("  ✓ GPS configuration already present in config.txt")
    
    return True

def configure_serial_console(boot_path):
    """Disable serial console to free UART for GPS"""
    print("Configuring serial console...")
    
    cmdline_txt_path = Path(boot_path) / 'cmdline.txt'
    
    if not cmdline_txt_path.exists():
        print(f"  ✗ cmdline.txt not found at {cmdline_txt_path}")
        return False
    
    with open(cmdline_txt_path, 'r') as f:
        cmdline = f.read().strip()
    
    # Remove console=serial0,115200 and console=ttyAMA0,115200
    original_cmdline = cmdline
    cmdline = ' '.join([
        param for param in cmdline.split()
        if not param.startswith('console=serial0') and 
           not param.startswith('console=ttyAMA0')
    ])
    
    if cmdline != original_cmdline:
        with open(cmdline_txt_path, 'w') as f:
            f.write(cmdline + '\n')
        print("  ✓ Disabled serial console in cmdline.txt")
    else:
        print("  ✓ Serial console already disabled")
    
    return True

def configure_gpsd(rootfs_path):
    """Configure gpsd to monitor GPS devices"""
    print("Configuring gpsd...")
    
    gpsd_default_path = Path(rootfs_path) / 'etc/default/gpsd'
    
    # Build device list based on configuration
    devices = []
    # USB GPS devices (common types)
    devices.append('/dev/ttyUSB0')  # USB-to-serial GPS (FTDI, Prolific, etc.)
    devices.append('/dev/ttyACM0')  # USB CDC ACM GPS (u-blox, etc.)
    # UART GPS devices
    if GPS_ENABLE_PRIMARY_UART:
        devices.append('/dev/ttyAMA0')  # Primary UART (all Pi models)
    # PPS device
    devices.append('/dev/pps0')
    
    devices_str = ' '.join(devices)
    
    gpsd_config = f'''# Automatically start gpsd
# Note: gpsd will run even without GPS hardware, consuming minimal resources
# It automatically detects when GPS hardware is connected
START_DAEMON="true"

# Auto-detect USB GPS devices (via udev rules)
USBAUTO="true"

# Static devices (USB, UART GPS, and PPS)
# These devices are monitored continuously; GPS data appears immediately when connected
# Non-existent devices are harmlessly ignored
DEVICES="{devices_str}"

# Start immediately, don't wait for clients (-n flag)
GPSD_OPTIONS="-n"
'''
    
    with open(gpsd_default_path, 'w') as f:
        f.write(gpsd_config)
    
    print(f"  ✓ Configured gpsd to monitor: {devices_str}")
    return True

def configure_chrony(rootfs_path):
    """Configure chrony to use GPS/PPS as time reference"""
    print("Configuring chrony for GPS time sources...")
    
    chrony_conf_path = Path(rootfs_path) / 'etc/chrony/chrony.conf'
    
    if not chrony_conf_path.exists():
        print(f"  ✗ chrony.conf not found at {chrony_conf_path}")
        return False
    
    with open(chrony_conf_path, 'r') as f:
        content = f.read()
    
    # Check if GPS config already exists
    if 'GPS Time Synchronization' in content:
        print("  ✓ GPS configuration already present in chrony.conf")
        return True
    
    # Append GPS configuration
    gps_config = '''
# GPS Time Synchronization
# GPS via GPSD shared memory (SHM 0)
# noselect: don't use for sync until PPS is available
refclock SHM 0 refid NMEA offset 0.5 delay 0.2 noselect

# PPS via GPSD shared memory (SHM 1)
# prefer: use this as primary time source when available
# lock NMEA: only use PPS when GPS (NMEA) time is valid
refclock SHM 1 refid PPS lock NMEA prefer

# Allow local time serving even without network
# Stratum 10 prevents this system from being preferred over internet NTP
local stratum 10

# Enable hardware timestamping if available (improves accuracy)
hwtimestamp *
'''
    
    with open(chrony_conf_path, 'a') as f:
        f.write(gps_config)
    
    print("  ✓ Added GPS reference clocks to chrony.conf")
    print("  ✓ Chrony will use GPS/PPS when available, fall back to network NTP")
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
        # Configure boot settings (UART, PPS)
        if not configure_boot_config(BOOT_MOUNT):
            return False
        
        # Disable serial console if using primary UART
        if GPS_ENABLE_PRIMARY_UART:
            if not configure_serial_console(BOOT_MOUNT):
                return False
        
        # Configure gpsd
        if not configure_gpsd(ROOTFS_MOUNT):
            return False
        
        # Configure chrony
        if not configure_chrony(ROOTFS_MOUNT):
            return False
        
        print("\nGPS timing configuration completed successfully!")
        print("GPS hardware will be automatically detected when connected:")
        print("  - USB GPS: /dev/ttyUSB0 (FTDI/Prolific) or /dev/ttyACM0 (u-blox)")
        if GPS_ENABLE_PRIMARY_UART:
            print("  - UART GPS: GPIO 14/15 (/dev/ttyAMA0)")
        print(f"  - PPS: GPIO {GPS_PPS_GPIO}")
        print("\nConfiguration is compatible with all Raspberry Pi models (3/4/5).")
        print("System will fall back to network NTP if no GPS is present.")
        print("\nNote: USB GPS without PPS provides ~50-200ms accuracy.")
        print("For microsecond-level timing, use UART GPS with PPS output.")
        return True
        
    except Exception as e:
        print(f"Error configuring GPS timing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
