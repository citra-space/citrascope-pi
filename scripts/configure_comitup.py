#!/usr/bin/env python3
"""
Configure Comitup WiFi provisioning for Citrascope
This replaces the custom AP setup with Comitup's captive portal approach.
"""

import os
import sys
import shutil
from pathlib import Path
from config import WIFI_AP_PASSWORD, WIFI_AP_SSID_PREFIX, ROOTFS_MOUNT

# Path to assets directory (relative to this script)
ASSETS_DIR = Path(__file__).parent.parent / 'assets'

def copy_branding_assets(rootfs_path):
    """Copy Citrascope logo and favicon from local assets"""
    print("Copying Citrascope branding assets...")
    
    # Local asset files
    assets = {
        'logo.png': ASSETS_DIR / 'citra.png',
        'favicon.png': ASSETS_DIR / 'favicon.png',
    }
    
    # Create destination directory
    comitup_static = Path(rootfs_path) / 'usr/share/comitup/web/static'
    comitup_static.mkdir(parents=True, exist_ok=True)
    
    # Copy each asset
    for filename, source in assets.items():
        dest = comitup_static / filename
        try:
            if source.exists():
                shutil.copy2(source, dest)
                print(f"  ✓ Copied {filename}")
            else:
                print(f"  ✗ Asset not found: {source}")
        except Exception as e:
            print(f"  ✗ Failed to copy {filename}: {e}")
            # Continue anyway - comitup will work without custom branding
    
    return True

def create_custom_template(rootfs_path):
    """Create custom HTML template with Citrascope branding"""
    print("Creating custom Comitup template...")
    
    template_dir = Path(rootfs_path) / 'usr/share/comitup/web/templates'
    template_dir.mkdir(parents=True, exist_ok=True)
    
    # Custom HTML template with Citrascope branding
    template_content = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Citrascope WiFi Setup</title>
    <link rel="icon" type="image/png" href="/static/favicon.png">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            text-align: center;
            padding: 20px 0;
        }
        .header img {
            max-width: 200px;
            height: auto;
        }
        .header h1 {
            color: #333;
            margin: 10px 0;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .network-list {
            list-style: none;
            padding: 0;
        }
        .network-item {
            padding: 12px;
            margin: 8px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        }
        .network-item:hover {
            background: #f0f0f0;
        }
        .network-name {
            font-weight: 500;
            color: #333;
        }
        .network-strength {
            font-size: 0.9em;
            color: #666;
        }
        input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
        }
        button:hover {
            background: #0056b3;
        }
        .info {
            color: #666;
            font-size: 0.9em;
            text-align: center;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <img src="/static/logo.png" alt="Citrascope" onerror="this.style.display='none'">
        <h1>Citrascope WiFi Setup</h1>
        <p>Configure your telescope controller to connect to WiFi</p>
    </div>
    
    <div class="card">
        {{ content }}
    </div>
    
    <div class="info">
        <p>After connecting, access Citrascope at <strong>citrascope.local:24872</strong></p>
    </div>
</body>
</html>
'''
    
    template_file = template_dir / 'index.html'
    with open(template_file, 'w') as f:
        f.write(template_content)
    
    print("  ✓ Created custom template")
    return True

def configure_comitup(rootfs_path):
    """Write comitup configuration file"""
    print("Configuring Comitup...")
    
    # Use <nnnn> which comitup will replace with a persistent random 4-digit number
    config_content = f'''# Comitup configuration for Citrascope

# Access point name (SSID)
# <nnnn> will be replaced by comitup with a persistent random 4-digit number
ap_name: {WIFI_AP_SSID_PREFIX}-<nnnn>

# Access point password
ap_password: {WIFI_AP_PASSWORD}

# Service to check after WiFi connection
# Comitup will verify this service is running
web_service: citrascope.service

# Enable the web interface
enable_appliance_mode: true

# Timeout before falling back to AP mode (seconds)
# If no WiFi connection after this time, create AP
# 0 = infinite (keep trying)
# 30 = fallback to AP after 30 seconds
timeout: 30
'''
    
    config_path = Path(rootfs_path) / 'etc/comitup.conf'
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"  ✓ Created /etc/comitup.conf (SSID: {WIFI_AP_SSID_PREFIX}-<nnnn>)")
    return True

def enable_comitup_service(rootfs_path):
    """Enable comitup systemd service"""
    print("Enabling Comitup service...")
    
    # Comitup package installs service to /lib/systemd/system/comitup.service
    # We just need to enable it
    service_link = Path(rootfs_path) / 'etc/systemd/system/multi-user.target.wants/comitup.service'
    service_link.parent.mkdir(parents=True, exist_ok=True)
    
    # Remove existing link if present (handles both symlinks and files)
    if service_link.exists() or service_link.is_symlink():
        service_link.unlink()
    
    service_link.symlink_to('/lib/systemd/system/comitup.service')
    print("  ✓ Enabled comitup.service")
    
    return True

def main():
    """Main configuration function"""
    if not os.path.exists(ROOTFS_MOUNT):
        print(f"Error: Root filesystem path {ROOTFS_MOUNT} does not exist")
        return False
    
    try:
        # Copy branding assets
        copy_branding_assets(ROOTFS_MOUNT)
        
        # Create custom template
        create_custom_template(ROOTFS_MOUNT)
        
        # Configure comitup
        configure_comitup(ROOTFS_MOUNT)
        
        # Enable service
        enable_comitup_service(ROOTFS_MOUNT)
        
        print("Comitup configuration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error configuring Comitup: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
