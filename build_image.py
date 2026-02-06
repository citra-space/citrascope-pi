#!/usr/bin/env python3
"""
Lemon Pi Image Builder
Build a complete Raspberry Pi image with Citrascope telescope control software.

Requires Python 3.10+ (uses only standard library).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
import shutil
import urllib.request
import lzma
import time
from datetime import datetime
from dataclasses import dataclass, field

# Check Python version
if sys.version_info < (3, 10):
    print("Error: Python 3.10 or higher required", flush=True)
    print(f"Current version: {sys.version}", flush=True)
    sys.exit(1)

# BuildResult dataclass for build steps that return metadata
@dataclass
class BuildResult:
    success: bool
    data: dict = field(default_factory=dict)

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Now import from scripts directory
from scripts.config import HOSTNAME_PREFIX
from scripts.mount_img import ImageMounter
import scripts.add_user
import scripts.enable_ssh
import scripts.configure_headless
import scripts.configure_hostname
import scripts.update_upgrade_chroot
import scripts.configure_gps_timing
import scripts.configure_banner
import scripts.install_citrascope
import scripts.configure_comitup
import scripts.enable_wifi

# Build step definitions
BUILD_STEPS = [
    ("Configure hostname/identity", scripts.configure_hostname.main),
    ("Add user", scripts.add_user.main),
    ("Enable SSH", scripts.enable_ssh.main),
    ("Configure headless settings", scripts.configure_headless.main),
    ("Update packages", scripts.update_upgrade_chroot.main),
    ("Configure GPS timing", scripts.configure_gps_timing.main),
    ("Install Citrascope", scripts.install_citrascope.main),
    ("Configure Comitup WiFi", scripts.configure_comitup.main),
    ("Enable WiFi hardware", scripts.enable_wifi.main),
    ("Configure login banner", scripts.configure_banner.main),
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
        
        last_reported_percent = -1
        
        def progress(block_num, block_size, total_size):
            nonlocal last_reported_percent
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100)
            # Only report at 10% intervals
            current_threshold = int(percent / 10) * 10
            if current_threshold > last_reported_percent:
                mb_downloaded = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                print(f"Progress: {current_threshold}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", flush=True)
                last_reported_percent = current_threshold
        
        try:
            urllib.request.urlretrieve(RASPIOS_URL, xz_path, reporthook=progress)
            print("✓ Download complete")
        except Exception as e:
            print(f"\n✗ Download failed: {e}")
            sys.exit(1)
    
    # Extract .xz file
    print(f"\nExtracting {xz_path.name}...")
    try:
        # Get uncompressed size estimate (compressed size * ~2.5 typical ratio)
        compressed_size = xz_path.stat().st_size
        estimated_size = compressed_size * 2.5
        last_reported_percent = -1
        
        with lzma.open(xz_path, 'rb') as f_in:
            with open(img_path, 'wb') as f_out:
                chunk_size = 1024 * 1024  # 1MB chunks
                while True:
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    # Show progress at 10% intervals
                    mb_written = f_out.tell() / (1024 * 1024)
                    percent = min(100, (f_out.tell() / estimated_size) * 100)
                    current_threshold = int(percent / 10) * 10
                    if current_threshold > last_reported_percent:
                        print(f"Extracted: {mb_written:.1f} MB (~{current_threshold}%)", flush=True)
                        last_reported_percent = current_threshold
        
        print("✓ Extraction complete")
        
        # Remove .xz file to save space
        xz_path.unlink()
        print(f"✓ Removed {xz_path.name} to save space")
        
        return str(img_path)
        
    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        sys.exit(1)

# Global list to track completed build steps for summary
BUILD_RESULTS = []

def run_step(name, func, *args, **kwargs):
    """Run a build step with error handling and timing"""
    import time
    
    print(f"\n{'='*60}", flush=True)
    print(f"STEP: {name}", flush=True)
    print(f"{'='*60}", flush=True)
    
    start_time = time.time()
    step_result = {'name': name, 'success': False, 'elapsed': 0}
    
    try:
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        step_result['elapsed'] = elapsed
        
        # Handle both BuildResult and legacy bool returns
        if isinstance(result, BuildResult):
            success = result.success
            data = result.data
        else:
            success = bool(result)
            data = {}
        
        # Check if function failed
        if not success:
            print(f"✗ {name} failed (took {elapsed:.1f}s)", flush=True)
            BUILD_RESULTS.append(step_result)
            sys.exit(1)
        
        step_result['success'] = True
        BUILD_RESULTS.append(step_result)
        
        minutes, seconds = divmod(int(elapsed), 60)
        if minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{elapsed:.1f}s"
        print(f"✓ {name} completed successfully (took {time_str})", flush=True)
        return data
    except Exception as e:
        elapsed = time.time() - start_time
        step_result['elapsed'] = elapsed
        BUILD_RESULTS.append(step_result)
        
        print(f"✗ {name} failed after {elapsed:.1f}s: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def print_build_summary():
    """Print a summary of all build steps"""
    if not BUILD_RESULTS:
        return
    
    print(f"\n{'='*60}", flush=True)
    print("BUILD SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    
    # Calculate column widths
    max_name_len = max(len(step['name']) for step in BUILD_RESULTS)
    col_width = max(max_name_len, 20)
    
    # Print header
    print(f"\n{'Step':<{col_width}}  {'Status':<10}  {'Time'}", flush=True)
    print(f"{'-'*col_width}  {'-'*10}  {'-'*15}", flush=True)
    
    # Print each step
    total_time = 0
    for step in BUILD_RESULTS:
        status = "✓ SUCCESS" if step['success'] else "✗ FAILED"
        elapsed = step['elapsed']
        total_time += elapsed
        
        minutes, seconds = divmod(int(elapsed), 60)
        if minutes > 0:
            time_str = f"{minutes}m {seconds}s"
        else:
            time_str = f"{elapsed:.1f}s"
        
        print(f"{step['name']:<{col_width}}  {status:<10}  {time_str}", flush=True)
    
    # Print total
    print(f"{'-'*col_width}  {'-'*10}  {'-'*15}", flush=True)
    total_minutes, total_seconds = divmod(int(total_time), 60)
    if total_minutes > 0:
        total_time_str = f"{total_minutes}m {total_seconds}s"
    else:
        total_time_str = f"{total_time:.1f}s"
    print(f"{'Total':<{col_width}}             {total_time_str}", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"Build completed: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}\n", flush=True)

def customize_image(image_path):
    """Customize Raspberry Pi OS image with all build steps"""
    metadata = {}
    
    with ImageMounter(image_path):
        for name, func in BUILD_STEPS:
            data = run_step(name, func)
            if name == "Install Citrascope":
                print(f"DEBUG: Install Citrascope returned data: {data}", flush=True)
                if 'version' in data:
                    metadata['citrascope_version'] = data['version']
                    print(f"DEBUG: Captured Citrascope version: {data['version']}", flush=True)
                else:
                    print(f"DEBUG: No version in data dict!", flush=True)
    
    return metadata

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
    
    # Remove existing output file if it exists
    if output_path.exists():
        output_path.unlink()
    
    shutil.copy2(base_image_path, output_path)
    print(f"✓ Image copied\n", flush=True)
    
    # Expand image to have room for packages (add 2GB)
    print(f"Expanding image to accommodate packages...", flush=True)
    expand_start = time.time()
    current_size = output_path.stat().st_size
    additional_space = 2 * 1024 * 1024 * 1024  # 2GB
    new_size = current_size + additional_space
    
    # Truncate extends the file
    with open(output_path, 'ab') as f:
        f.truncate(new_size)
    
    # Expand the root partition to use the new space
    try:
        # Use parted to resize partition
        subprocess.run(['sudo', 'parted', str(output_path), 'resizepart', '2', '100%'], 
                      check=True, capture_output=True)
        
        # Now resize the filesystem using e2fsck and resize2fs
        # First, setup loop device to access partition
        result = subprocess.run(['sudo', 'kpartx', '-av', str(output_path)],
                               capture_output=True, text=True, check=True)
        
        # Extract loop device name (e.g., loop0p2)
        import re
        loop_devs = []
        for line in result.stdout.split('\n'):
            match = re.search(r'add map (\S+)', line)
            if match:
                loop_devs.append(match.group(1))
        
        if len(loop_devs) >= 2:
            rootfs_dev = f"/dev/mapper/{loop_devs[1]}"
            
            # Check and resize filesystem
            subprocess.run(['sudo', 'e2fsck', '-f', '-y', rootfs_dev], 
                          capture_output=True)
            subprocess.run(['sudo', 'resize2fs', rootfs_dev], 
                          check=True, capture_output=True)
            
            # Clean up loop devices
            subprocess.run(['sudo', 'kpartx', '-d', str(output_path)], 
                          capture_output=True)
            
        expand_elapsed = time.time() - expand_start
        BUILD_RESULTS.append({'name': 'Expand image', 'success': True, 'elapsed': expand_elapsed})
        print(f"✓ Image expanded by {additional_space // (1024*1024*1024)}GB\n", flush=True)
    except Exception as e:
        expand_elapsed = time.time() - expand_start
        BUILD_RESULTS.append({'name': 'Expand image', 'success': False, 'elapsed': expand_elapsed})
        print(f"Warning: Could not resize filesystem: {e}", flush=True)
        print(f"Filesystem will auto-expand on first boot\n", flush=True)
    
    # Customize image with all build steps
    print(f"{'='*60}", flush=True)
    print(f"Customizing image...", flush=True)
    print(f"{'='*60}\n", flush=True)
    metadata = customize_image(str(output_path))
    
    # Rename output file to include both versions if Citrascope version was captured
    if 'citrascope_version' in metadata:
        citrascope_version = metadata['citrascope_version']
        image_version = os.environ.get('IMAGE_VERSION', 'dev')
        
        # Generate new filename with dual version
        new_name = f"citrascope-pi-{image_version}-cs{citrascope_version}.img"
        new_output_path = output_path.parent / new_name
        
        # Rename the file
        output_path.rename(new_output_path)
        output_path = new_output_path
        
        print(f"\n✓ Image renamed to include Citrascope version: {citrascope_version}", flush=True)
    
    print(f"\n{'='*60}")
    print(f"✓ BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"Output image: {output_path}")
    print(f"Flash to SD card with:")
    print(f"  sudo dd if={output_path} of=/dev/sdX bs=4M status=progress")
    print(f"\nOr use Raspberry Pi Imager.")
    
    # Print summary of all steps
    print_build_summary()

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
        """
    )
    
    parser.add_argument('image', nargs='?', help='Path to Raspberry Pi OS image file (auto-downloads if not provided)')
    parser.add_argument('-o', '--output', help='Output image path (default: adds -citrascope suffix)')
    
    args = parser.parse_args()
    
    try:
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
        
        # Build complete image
        print("\n>>> Building complete Citrascope image\n", flush=True)
        build_complete_image(image_path, args.output)
    
    except SystemExit:
        # Print summary even on failure
        print_build_summary()
        raise
    except Exception as e:
        # Print summary on unexpected errors
        print(f"\nUnexpected error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        print_build_summary()
        sys.exit(1)

if __name__ == '__main__':
    main()
