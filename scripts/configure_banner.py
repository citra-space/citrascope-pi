#!/usr/bin/env python3
"""
Configure login banner with ASCII art and hostname display.
Creates a cool banner that shows on every login.
Uses pixel-perfect representation of citra-tiny.png (6x8 pixels).
"""

import os
import sys
from pathlib import Path

# Import config
from scripts.config import ROOTFS_MOUNT

# Pixel-perfect ASCII art of citra logo (6x8 pixels)
# Brown stem, green leaves, yellow/orange citrus fruit
CITRA_ASCII_LINES = [
    "      \\033[48;5;94m  \\033[0m\\033[48;5;149m  \\033[0m\\033[48;5;149m  \\033[0m",
    "    \\033[48;5;16m  \\033[0m\\033[48;5;16m  \\033[0m\\033[48;5;149m  \\033[0m\\033[48;5;149m  \\033[0m",
    "  \\033[48;5;16m  \\033[0m\\033[48;5;230m  \\033[0m\\033[48;5;220m  \\033[0m\\033[48;5;16m  \\033[0m  ",
    "\\033[48;5;16m  \\033[0m\\033[48;5;230m  \\033[0m\\033[48;5;226m  \\033[0m\\033[48;5;226m  \\033[0m\\033[48;5;220m  \\033[0m\\033[48;5;16m  \\033[0m",
    "\\033[48;5;16m  \\033[0m\\033[48;5;226m  \\033[0m\\033[48;5;226m  \\033[0m\\033[48;5;226m  \\033[0m\\033[48;5;214m  \\033[0m\\033[48;5;16m  \\033[0m",
    "\\033[48;5;16m  \\033[0m\\033[48;5;220m  \\033[0m\\033[48;5;226m  \\033[0m\\033[48;5;214m  \\033[0m\\033[48;5;214m  \\033[0m\\033[48;5;16m  \\033[0m",
    "  \\033[48;5;16m  \\033[0m\\033[48;5;214m  \\033[0m\\033[48;5;214m  \\033[0m\\033[48;5;16m  \\033[0m  ",
    "    \\033[48;5;16m  \\033[0m\\033[48;5;16m  \\033[0m    ",
]

def main():
    """Install login banner script"""
    rootfs = Path(ROOTFS_MOUNT)
    
    # Build ASCII art lines for the bash script
    ascii_lines = "\n".join(f'echo -e "{line}"' for line in CITRA_ASCII_LINES)
    
    # Create the banner display script with pixel-perfect citra logo
    banner_script = f"""#!/bin/bash
# CitraScope login banner
# Displays on every interactive login
# Pixel-perfect ASCII art from citra-tiny.png (6x8 pixels)

# Colors
YELLOW='\\033[1;33m'
GREEN='\\033[1;32m'
CYAN='\\033[1;36m'
RESET='\\033[0m'
BOLD='\\033[1m'

# Get hostname
HOSTNAME=$(hostname)

# Display pixel-perfect citra logo (6px x 8px) - brown stem, green leaves, yellow citrus
echo ""
{ascii_lines}
echo ""

# Display system info
echo -e "${{CYAN}}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${{RESET}}"
echo -e "  ${{BOLD}}${{YELLOW}}CitraScope${{RESET}}"
echo -e "  ${{GREEN}}Hostname:${{RESET}} ${{BOLD}}$HOSTNAME${{RESET}}"
echo -e "  ${{GREEN}}Web UI:${{RESET}}   http://$HOSTNAME.local"
echo -e "${{CYAN}}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${{RESET}}"
echo ""
"""
    
    # Write the banner script to /etc/profile.d/
    profile_d = rootfs / "etc" / "profile.d"
    profile_d.mkdir(parents=True, exist_ok=True)
    
    banner_path = profile_d / "citrascope-banner.sh"
    banner_path.write_text(banner_script)
    banner_path.chmod(0o755)
    
    print(f"✓ Created login banner: {banner_path}")
    print(f"  Banner will display on every interactive login")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
