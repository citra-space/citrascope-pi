# CitraScope Pi

Build custom Raspberry Pi images for telescope operations with [Citrascope](https://github.com/citra-space/citrascope).

Creates a turnkey SD card image with Citrascope telescope control software, INDI hardware support, and automatic WiFi access point.

## Quick Start

**Requirements:** Linux machine with Python 3.10+, kpartx, qemu-user-static

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install kpartx python3 qemu-user-static

# Build image (auto-downloads Raspberry Pi OS)
sudo ./build_image.py

# Flash to SD card
sudo dd if=raspios-bookworm-arm64-lite-citrascope.img of=/dev/sdX bs=4M status=progress
```

**Build time:** 15-30 minutes. **Final image:** ~5-6GB.

## What You Get

- **User:** `citra` / `citra` (sudo enabled)
- **Hostname:** `citrascope.local` (mDNS enabled)
- **SSH:** Enabled on port 22
- **Citrascope:** Auto-starts on boot, web UI at port 24872
- **WiFi AP:** Auto-creates `citrascope-{serial}` network if no ethernet
- **INDI Server:** Pre-installed for telescope/camera control

## First Boot

**Via Network:**
```bash
ssh citra@citrascope.local
# Browser: http://citrascope.local:24872
```

**Via WiFi AP (if no network):**
- Connect to WiFi: `citrascope-XXXXXXXX` (password: `citrascope`)
- Browser: `http://10.42.0.1:24872`

## Configuration

Edit [scripts/config.py](scripts/config.py) to customize:
- Username/password
- Hostname
- WiFi AP settings
- System packages

## Advanced Usage

```bash
# Use existing image file
sudo ./build_image.py path/to/raspios.img

# Custom output name
sudo ./build_image.py -o custom-name.img

# Only customize base (skip Citrascope)
sudo ./build_image.py existing.img --customize-only

# Only install Citrascope (assumes customized)
sudo ./build_image.py customized.img --citrascope-only
```

## Supported Hardware

- **Pi Models:** Raspberry Pi 4 (2GB+), Pi 5
- **Cameras:** ZWO ASI, Pi HQ Camera, USB cameras
- **Mounts:** INDI-compatible telescope mounts
- See [Citrascope docs](https://docs.citra.space/citrascope/) for full hardware support

## Troubleshooting

**Can't connect to citrascope.local:**
```bash
# Find IP address and connect directly
ssh citra@<pi-ip>
```

**Citrascope not starting:**
```bash
sudo systemctl status citrascope
sudo journalctl -u citrascope -f
```

**WiFi AP not appearing:**
```bash
sudo systemctl status citrascope-ap-setup
sudo journalctl -u citrascope-ap-setup
```

## Project Structure

```
lemon-pi/
├── build_image.py          # Main build script
├── scripts/
│   ├── config.py          # Centralized configuration
│   ├── mount_img.py       # Image mounting utilities
│   ├── resize_fs.py       # Filesystem resizing
│   ├── add_user.py        # User creation
│   ├── set_hostname.py    # Hostname configuration
│   ├── enable_ssh.py      # SSH enablement
│   ├── update_upgrade_chroot.py  # Package installation
│   ├── install_citrascope.py     # Citrascope installation
│   └── citrascope-ap-setup.py    # WiFi AP setup (runs on Pi)
└── README.md
```

## Resources

- [Citrascope](https://github.com/citra-space/citrascope) - Telescope control software
- [Citra.space](https://citra.space/) - Project website
- [INDI Library](https://www.indilib.org/) - Hardware control protocol

## License

MIT License. Built on open-source tools following their respective licenses.
