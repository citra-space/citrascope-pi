#!/usr/bin/env python3
"""
Lemon Pi Image Builder
Build a complete Raspberry Pi image with Citrascope telescope control software.

Requires Python 3.10+ (uses only standard library).
"""

import argparse
import subprocess
import sys
from pathlib import Path
import shutil
import urllib.request
import lzma

# Check Python version
if sys.version_info < (3, 10):
    print("Error: Python 3.10 or higher required", flush=True)
    print(f"Current version: {sys.version}", flush=True)
    sys.exit(1)

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Now import from scripts directory
from scripts.config import HOSTNAME
from scripts.mount_img import ImageMounter
import scripts.add_user
import scripts.set_hostname
import scripts.enable_ssh
import scripts.update_upgrade_chroot
import scripts.install_citrascope
import scripts.install_citrascope_ap_setup

# Build step definitions
CUSTOMIZE_STEPS = [
    ("Add user", scripts.add_user.main),
    ("Set hostname", scripts.set_hostname.main),
    ("Enable SSH", scripts.enable_ssh.main),
    ("Update packages", scripts.update_upgrade_chroot.main),
]

CITRASCOPE_STEPS = [
    ("Install Citrascope", scripts.install_citrascope.main),
    ("Install WiFi AP setup", scripts.install_citrascope_ap_setup.main),
]

# Latest Raspberry Pi OS Lite (ARM64) download URL
# Check https://www.raspberrypi.com/software/operating-systems/ for current version
RASPIOS_URL = "https://downloads.raspberrypi.com/raspios_lite_arm64/images/raspios_lite_arm64-2025-12-04/2025-12-04-raspios-trixie-arm64-lite.img.xz"

def download_raspios(output_dir="."):
    """Download and extract the latest Raspberry Pi OS Lite image"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Extract filename from URL
    filename = RASPIOS_URL.split('/')[-1]
    xz_path = output_path / filename
    img_path = output_path / filename.replace('.xz', '')
    
    # Check if already extracted
    if img_path.exists():
        print(f"Image already exists: {img_path}")
        return str(img_path)
    
    # Download if needed
    if not xz_path.exists():
        print(f"\nDownloading Raspberry Pi OS Lite (ARM64)...")
        print(f"URL: {RASPIOS_URL}")
        print(f"This may take several minutes (~500MB)...\n")
        
        def progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\rProgress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='', flush=True)
        
        try:
            urllib.request.urlretrieve(RASPIOS_URL, xz_path, reporthook=progress)
            print("\n✓ Download complete")
        except Exception as e:
            print(f"\n✗ Download failed: {e}")
            sys.exit(1)
    
    # Extract .xz file
    print(f"\nExtracting {xz_path.name}...")
    try:
        with lzma.open(xz_path, 'rb') as f_in:
            with open(img_path, 'wb') as f_out:
                chunk_size = 1024 * 1024  # 1MB chunks
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    # Show progress
                    mb_written = f_out.tell() / (1024 * 1024)
                    print(f"\rExtracted: {mb_written:.1f} MB", end='', flush=True)
        
        print("\n✓ Extraction complete")
        
        # Remove .xz file to save space
        xz_path.unlink()
        print(f"✓ Removed {xz_path.name} to save space")
        
        return str(img_path)
        
    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        sys.exit(1)

def run_step(name, func, *args, **kwargs):
    """Run a build step with error handling"""
    print(f"\n{'='*60}", flush=True)
    print(f"STEP: {name}", flush=True)
    print(f"{'='*60}", flush=True)
    try:
        result = func(*args, **kwargs)
        print(f"✓ {name} completed successfully", flush=True)
        return result
    except Exception as e:
        print(f"✗ {name} failed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def customize_base_image(image_path):
    """Customize the base Raspberry Pi OS image"""
    
    with ImageMounter(image_path):
        for name, func in CUSTOMIZE_STEPS:
            run_step(name, func)

def install_citrascope_software(image_path):
    """Install Citrascope and WiFi AP setup"""
    
    with ImageMounter(image_path):
        for name, func in CITRASCOPE_STEPS:
            run_step(name, func)

def build_complete_image(base_image_path, output_path):
    """Build a complete Citrascope image from base Raspberry Pi OS"""
    # Generate default output path if not provided
    if output_path is None:
        base_path = Path(base_image_path)
        output_path = base_path.parent / f"{base_path.stem}-citrascope{base_path.suffix}"
    else:
        output_path = Path(output_path)
    
    # Copy base image to output
    print(f"Source: {base_image_path}", flush=True)
    print(f"Output: {output_path}", flush=True)
    print(f"\nCopying base image...", flush=True)
    shutil.copy2(base_image_path, output_path)
    print(f"✓ Image copied\n", flush=True)
    
    # Customize base image
    customize_base_image(str(output_path))
    
    # Install Citrascope
    install_citrascope_software(str(output_path))
    
    print(f"\n{'='*60}")
    print(f"✓ BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"Output image: {output_path}")
    print(f"Flash to SD card with:")
    print(f"  sudo dd if={output_path} of=/dev/sdX bs=4M status=progress")
    print(f"\nOr use Raspberry Pi Imager.")

def main():
    parser = argparse.ArgumentParser(
        description='Build Raspberry Pi images with Citrascope telescope control software',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build complete image (auto-downloads if needed)
  sudo ./build_image.py

  # Build from existing image
  sudo ./build_image.py raspios-bookworm-arm64-lite.img

  # Build with custom output name
  sudo ./build_image.py -o citrascope-v1.0.img
  
  # Only customize base (no Citrascope)
  sudo ./build_image.py existing.img --customize-only
  
  # Only install Citrascope (assumes already customized)
  sudo ./build_image.py customized.img --citrascope-only
        """
    )
    
    parser.add_argument('image', nargs='?', help='Path to Raspberry Pi OS image file (auto-downloads if not provided)')
    parser.add_argument('-o', '--output', help='Output image path (default: adds -citrascope suffix)')
    parser.add_argument('--customize-only', action='store_true', 
                        help='Only customize base image (skip Citrascope installation)')
    parser.add_argument('--citrascope-only', action='store_true',
                        help='Only install Citrascope (assumes image already customized)')
    
    args = parser.parse_args()
    
    # Check if running as root
    if subprocess.run(['id', '-u'], capture_output=True, text=True).stdout.strip() != '0':
        print("Error: This script must be run as root (use sudo)", flush=True)
        sys.exit(1)
    
    # Handle image path - download if not provided or doesn't exist
    image_path = args.image
    if not image_path or not Path(image_path).exists():
        if image_path:
            print(f"Image file not found: {image_path}", flush=True)
        print("Downloading Raspberry Pi OS Lite (ARM64)...", flush=True)
        image_path = download_raspios()
    
    # Run appropriate build steps
    if args.customize_only:
        print("\n>>> Mode: Customize base image only\n", flush=True)
        customize_base_image(image_path)
    elif args.citrascope_only:
        print("\n>>> Mode: Install Citrascope only\n", flush=True)
        install_citrascope_software(image_path)
    else:
        print("\n>>> Mode: Complete build\n", flush=True)
        build_complete_image(image_path, args.output)

if __name__ == '__main__':
    main()
