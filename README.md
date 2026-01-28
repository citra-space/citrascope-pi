# CitraScope Pi

Build custom Raspberry Pi images for telescope operations with [Citrascope](https://github.com/citra-space/citrascope).

Creates a turnkey SD card image with Citrascope telescope control software, INDI hardware support, and automatic WiFi access point.

## Quick Start

**Requirements:** Docker Desktop (Mac/Windows/Linux)

```bash
# Build image using Docker (auto-downloads Raspberry Pi OS)
./build-docker.sh

# Flash to SD card using Raspberry Pi Imager or Balena Etcher
```

**Note on Docker:** The build requires `--privileged` mode to access loop devices needed for mounting disk images. The container runs as your user (not root) to avoid permission issues. All dependencies (kpartx, qemu, Python) are handled inside the container—no manual installation required.

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
./build-docker.sh path/to/raspios.img

# Custom output name
./build-docker.sh -o custom-name.img

# Only customize base (skip Citrascope)
./build-docker.sh existing.img --customize-only

# Only install Citrascope (assumes customized)
./build-docker.sh customized.img --citrascope-only
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

The build process runs entirely in Docker:

1. **Downloads** Raspberry Pi OS Lite (Trixie ARM64, Debian 13)
2. **Mounts** the image using loop devices (kpartx inside container)
3. **Customizes** via direct file operations and chroot:
   - Creates `citra` user with sudo access
   - Sets hostname to `citrascope`
   - Enables SSH
   - Installs system packages (INDI, Python, build tools)
4. **Installs** Citrascope in Python venv with systemd service
5. **Configures** WiFi AP fallback for field use
6. **Unmounts** and outputs ready-to-flash image

All modifications happen in the Docker container on your machine—the Pi receives a complete, pre-configured image.

## Resources

- [Citrascope](https://github.com/citra-space/citrascope) - Telescope control software
- [Citra.space](https://citra.space/) - Project website
- [INDI Library](https://www.indilib.org/) - Hardware control protocol

## License

MIT License. Built on open-source tools following their respective licenses.
