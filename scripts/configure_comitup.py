#!/usr/bin/env python3
"""Configure Comitup WiFi provisioning"""
import os, sys, re
from pathlib import Path
from config import WIFI_AP_PASSWORD, WIFI_AP_SSID_PREFIX, ROOTFS_MOUNT

# Pre-encoded Citra logo (base64) - from assets/citra-reasonable.png
CITRA_LOGO_BASE64 = """iVBORw0KGgoAAAANSUhEUgAAASwAAAGQCAYAAAAUdV17AAAFpGlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4KPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS41LjAiPgogPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4KICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIgogICAgeG1sbnM6cGhvdG9zaG9wPSJodHRwOi8vbnMuYWRvYmUuY29tL3Bob3Rvc2hvcC8xLjAvIgogICAgeG1sbnM6ZGM9Imh0dHA6Ly9wdXJsLm9yZy9kYy9lbGVtZW50cy8xLjEvIgogICAgeG1sbnM6ZXhpZj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iCiAgICB4bWxuczp0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyIKICAgIHhtbG5zOnhtcE1NPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvbW0vIgogICAgeG1sbnM6c3RFdnQ9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZUV2ZW50IyIKICAgeG1wOkNyZWF0ZURhdGU9IjIwMjYtMDItMDRUMTM6MzY6MjMtMDc6MDAiCiAgIHhtcDpNb2RpZnlEYXRlPSIyMDI2LTAyLTA0VDEzOjM4OjMzLTA3OjAwIgogICB4bXA6TWV0YWRhdGFEYXRlPSIyMDI2LTAyLTA0VDEzOjM4OjMzLTA3OjAwIgogICBwaG90b3Nob3A6RGF0ZUNyZWF0ZWQ9IjIwMjYtMDItMDRUMTM6MzY6MjMtMDc6MDAiCiAgIHBob3Rvc2hvcDpDb2xvck1vZGU9IjMiCiAgIHBob3Rvc2hvcDpJQ0NQcm9maWxlPSJzUkdCIElFQzYxOTY2LTIu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"""

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

def customize_comitup_logo(rootfs_path):
    """Replace Comitup logo with Citra logo"""
    print("Customizing Comitup logo...")
    comitup_html = Path(rootfs_path) / "usr" / "share" / "comitup" / "web" / "templates" / "index.html"
    
    if not comitup_html.exists():
        print(f"  ✗ Comitup index.html not found at {comitup_html}")
        return False
    
    # Read Comitup HTML
    html_content = comitup_html.read_text()
    
    # Replace the UIkit icon with our base64 image
    # Original: <span class="" uk-icon="icon: world; ratio: 5"></span>
    pattern = r'<span class="" uk-icon="icon: world; ratio: 5"></span>'
    replacement = f'<img src="data:image/png;base64,{CITRA_LOGO_BASE64}" alt="CitraScope!" style="width: 60px; height: 80px;">'
    new_html = html_content.replace(pattern, replacement)
    
    if new_html == html_content:
        print("  ✗ Could not find Comitup logo icon in index.html")
        print("  Comitup HTML format may have changed")
        return False
    
    # Write modified HTML
    comitup_html.write_text(new_html)
    print("  ✓ Customized Comitup captive portal logo")
    return True

def main():
    if not os.path.exists(ROOTFS_MOUNT):
        print(f"Error: {ROOTFS_MOUNT} does not exist")
        return False
    try:
        if not configure_comitup(ROOTFS_MOUNT):
            return False
        if not enable_comitup_service(ROOTFS_MOUNT):
            return False
        if not fix_service_conflicts(ROOTFS_MOUNT):
            return False
        if not customize_comitup_logo(ROOTFS_MOUNT):
            return False
        print("Comitup configuration completed!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
