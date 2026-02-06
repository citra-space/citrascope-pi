# CitraScope Pi

Turnkey Raspberry Pi image for telescope operations with [Citrascope](https://github.com/citra-space/citrascope).

Pre-configured SD card image with Citrascope telescope control software, INDI hardware support, and automatic WiFi provisioning.

## What You Get

- **User:** `citra` / `citra` (sudo enabled)
- **Hostname:** `citrascope-{satellite}.local` - Each device gets a unique name from famous space missions (e.g., `citrascope-voyager.local`)
- **SSH:** Enabled on port 22
- **Citrascope:** Auto-starts on boot, web UI at port 80
- **WiFi Provisioning:** Captive portal for easy WiFi setup, automatic AP fallback
- **INDI drivers:** Pre-installed for telescope/camera hardware (Citrascope starts drivers as needed)
- **GPS Time Sync:** Automatic GPS detection for microsecond-accurate timekeeping (optional hardware)

**Note:** Your device's unique name (like "voyager", "hubble", or "apollo") is randomly assigned on first boot and appears as both the WiFi access point name and the network hostname.

## First Boot

### WiFi Setup (First Time)

On first boot, if not connected via Ethernet:

1. **Pi creates WiFi hotspot:** Look for `citrascope-{name}` in your WiFi list (e.g., `citrascope-voyager`, `citrascope-hubble`)
2. **Connect with your phone/laptop** using password: `citra`
3. **Captive portal appears automatically** showing available WiFi networks
4. **Select your network** and enter password
5. **Pi connects to your WiFi** and disables the hotspot

**Your device's unique name** (the part after "citrascope-") is randomly selected from famous space missions and stays the same forever. Remember it—that's how you'll find your device on the network!

**Automatic Fallback:** If your WiFi becomes unavailable (field use, power outage), the Pi automatically re-enables the hotspot so you can always connect.

### After WiFi Setup

**Via Network:**
```bash
# Replace {name} with your device's name (e.g., voyager, hubble, apollo)
ssh citra@citrascope-{name}.local
# Browser: http://citrascope-{name}.local
```

**Via Hotspot (field use when no WiFi):**
- Connect to WiFi: `citrascope-{name}` (password: `citra`)

## Supported Hardware

- **Pi Models:** Raspberry Pi 4 (2GB+), Pi 5
- **Cameras:** ZWO ASI, Pi HQ Camera, USB cameras
- **Mounts:** INDI-compatible telescope mounts
- See [Citrascope docs](https://docs.citra.space/citrascope/) for full hardware support

## GPS Support (Optional)

**Location data:** Any USB or UART GPS provides position and velocity for telescope tracking and logging.

**High-precision timing:** UART GPS with PPS output on GPIO 18 provides microsecond-accurate timekeeping (Stratum 1). USB GPS lacks PPS and won't improve timing beyond internet NTP.

Check GPS: `cgps -s` | Check time sources: `chronyc sources -v`

See [scripts/configure_gps_timing.py](scripts/configure_gps_timing.py) for GPIO pinouts, hardware setup, and troubleshooting.

## Troubleshooting

**Can't connect to citrascope-{name}.local:**
```bash
# Find IP address and connect directly
ssh citra@<pi-ip>
# Or check your WiFi list for the hotspot name to remind you which device it is
```

**WiFi not appearing:**
- Wait a couple minutes after power-on for hotspot to start
- Check that WiFi isn't disabled in your device settings
- Try rebooting the Pi

**Forgot device name:**
- Check your WiFi list - the hotspot shows the name
- Connect via ethernet and run: `hostname`

---

## Building Your Own Image

Want to customize the image or build from source? Read on.

### Requirements

**Docker Desktop** (Mac/Windows/Linux) - all other dependencies handled automatically

### Quick Build

```bash
# Build image using Docker (auto-downloads Raspberry Pi OS)
./build.py

# Flash to SD card using Raspberry Pi Imager or Balena Etcher
```

### Development Setup (one-time)

Install dev dependencies for prettier build output and release automation:
```bash
pip install -e ".[dev]"
```

This installs yaspin (spinners) and bump-my-version (releases).

**Note on Docker:** The build requires `--privileged` mode to access loop devices needed for mounting disk images. The container runs as your user (not root) to avoid permission issues. All dependencies (kpartx, qemu, Python) are handled inside the container—no manual installation required.

**Build time:** 15-30 minutes first run to build the docker layer, ~4 minutes each time after that.
**Final image:** ~5GB.

### Configuration

Edit [scripts/config.py](scripts/config.py) to customize:
- Username/password
- Hostname prefix
- WiFi hotspot password
- System packages
- Device name pool (satellite names)
- GPS timing options (PPS GPIO pin, UART configuration)

### Advanced Build Options

```bash
# Use existing image file
./build.py path/to/raspios.img

# Custom output name
./build.py -o custom-name.img

# Test a built image
./test.py                    # Tests latest *-citrascope.img
./test.py path/to/image.img  # Test specific image
```

## How It Works

The build process runs entirely in Docker via `./build.py`, which provides logging and progress output:

1. **Downloads** Raspberry Pi OS Lite (Trixie ARM64, Debian 13)
2. **Mounts** the image using loop devices (kpartx inside container)
3. **Customizes** via direct file operations and chroot:
   - Creates `citra` user with sudo access
   - Generates unique device name from satellite pool
   - Enables SSH and WiFi
   - Installs system packages (INDI, Python, build tools, GPS timing)
4. **Configures** GPS time synchronization with automatic hardware detection
5. **Installs** Citrascope in Python venv with systemd service
6. **Configures** Comitup for WiFi provisioning with automatic AP fallback
7. **Unmounts** and outputs ready-to-flash image

All modifications happen in the Docker container on your machine—the Pi receives a complete, pre-configured image.


## Releasing a New Version

Use bump-my-version to create a release:

```bash
bump-my-version bump patch  # 0.1.3 → 0.1.4
bump-my-version bump minor  # 0.1.3 → 0.2.0
bump-my-version bump major  # 0.1.3 → 1.0.0
git push && git push --tags
```

This automatically:
- Updates version in `pyproject.toml`
- Creates commit and tag
- Triggers GitHub Actions to build and release the image

### Versioning Strategy

Release images use **dual versioning** to track both components:

**Format:** `citrascope-pi-v{PI_VERSION}-cs{CITRASCOPE_VERSION}.img.xz`

**Examples:**
- `citrascope-pi-v0.2-cs1.3.0.img.xz` - Pi image v0.2 with Citrascope v1.3.0
- `citrascope-pi-main-20260206-a1b2c3d-cs1.4.2.img.xz` - Dev build

**What each version means:**
- **Pi Version** (`v0.2`): Version of this repository - image configuration, WiFi provisioning, GPS setup, etc.
- **Citrascope Version** (`cs1.3.0`): Version of the telescope control software installed from PyPI

The build always installs the latest Citrascope version available at build time. Both versions are included in the filename so you know exactly what you're getting.

## Resources

- [Citrascope](https://github.com/citra-space/citrascope) - Telescope control software
- [Citra.space](https://citra.space/) - Project website
- [INDI Library](https://www.indilib.org/) - Hardware control protocol

## License

MIT License. Built on open-source tools following their respective licenses.
