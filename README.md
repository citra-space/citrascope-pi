# CitraScope Pi

Build custom Raspberry Pi images for telescope operations with [Citrascope](https://github.com/citra-space/citrascope).

Creates a turnkey SD card image with Citrascope telescope control software, INDI hardware support, and automatic WiFi access point.

## Quick Start

### Building on Linux

**Requirements:** Linux machine with Python 3.10+, kpartx, qemu-user-static

```bash
# Install dependencies (Ubuntu/Debian)
sudo apt-get install kpartx python3 qemu-user-static

# Build image (auto-downloads Raspberry Pi OS)
sudo ./build_image.py

# Flash to SD card
sudo dd if=2025-12-04-raspios-trixie-arm64-lite-citrascope.img of=/dev/sdX bs=4M status=progress
```

### Building on Mac/Windows (Docker)

**Requirements:** Docker Desktop

```bash
# Build image using Docker
./build-docker.sh

# Flash to SD card (use Raspberry Pi Imager or Balena Etcher)
```

**Note on Docker Security:** The build requires `--privileged` mode to access loop devices (needed for mounting disk images). The container runs as your user (not root) to avoid permission issues. This is standard practice for disk image manipulation in containers.

**Build time:** 15-30 minutes. **Final image:** ~3-4GB.

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

## How It Works

The build process:

1. **Downloads** Raspberry Pi OS Lite (Trixie ARM64, Debian 13)
2. **Mounts** the image using loop devices (kpartx)
3. **Customizes** via direct file operations and chroot:
   - Creates `citra` user with sudo access
   - Sets hostname to `citrascope`
   - Enables SSH
   - Installs system packages (INDI, Python, build tools)
4. **Installs** Citrascope in Python venv with systemd service
5. **Configures** WiFi AP fallback for field use
6. **Unmounts** and outputs ready-to-flash image

All modifications happen on your build machine - the Pi receives a complete, pre-configured image.

## Resources

- [Citrascope](https://github.com/citra-space/citrascope) - Telescope control software
- [Citra.space](https://citra.space/) - Project website
- [INDI Library](https://www.indilib.org/) - Hardware control protocol

## License

MIT License. Built on open-source tools following their respective licenses.
