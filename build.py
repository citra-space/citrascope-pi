#!/usr/bin/env python3
"""
Build Raspberry Pi image using Docker with clean spinner-based output.
Replaces build-docker.sh with Python for better control and prettier output.
"""

import subprocess
import sys
import os
import re
from datetime import datetime
from pathlib import Path
import scripts.configure_banner

# Try to import yaspin, fall back to simple output if not available
try:
    from yaspin import yaspin
    HAS_YASPIN = True
except ImportError:
    HAS_YASPIN = False
    print("Note: Install 'yaspin' for prettier output: pip install yaspin")
    print()

# Patterns that indicate OUR build script output (show these in gray)
SHOW_PATTERNS = [
    r'^\s*✓',  # Success markers
    r'^\s*✗',  # Error markers
    r'^\s*⚠',  # Warning markers 
]

def should_show(line):
    """Check if line is from OUR build scripts and should be shown in gray"""
    stripped = line.strip()
    
    # Skip step markers, separators, and completion messages
    if any(x in line for x in ["STEP:", "=====", "completed successfully", "took "]):
        return False
    
    # Skip lines that are just our step checkmarks (we handle those separately)
    if re.match(r'^\s*✓\s+(Configure|Add|Enable|Install|Update)\s+\w+', stripped):
        return False
    
    # Show lines matching our patterns
    for pattern in SHOW_PATTERNS:
        if re.search(pattern, stripped):
            return True
    
    return False

def strip_ansi(text):
    """Strip ANSI escape codes from text"""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

def get_user_ids():
    """Get current user's UID and GID"""
    uid = os.getuid()
    gid = os.getgid()
    return uid, gid

def build_docker_image(uid, gid):
    """Build the Docker image"""
    print("Building Docker image...")
    result = subprocess.run([
        'docker', 'build',
        '--build-arg', f'USER_ID={uid}',
        '--build-arg', f'GROUP_ID={gid}',
        '-t', 'lemon-pi-builder',
        '.'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("✗ Docker build failed")
        print(result.stderr)
        sys.exit(1)
    
    print("✓ Docker image built\n")

def run_build(args, log_file):
    """Run the build inside Docker with spinner and logging"""
    
    # Build docker run command
    cmd = [
        'docker', 'run', '--rm', '--privileged',
        '-v', f'{os.getcwd()}:/workspace',
        '-v', '/dev:/dev',
        'lemon-pi-builder',
        'bash', '-c',
        f'sudo python3 build_image.py {" ".join(args)} && sudo chown builder:builder /workspace/citrascope-pi-*.img'
    ]
    
    # Start subprocess
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # Line buffered
    )
    
    current_step = "Starting build"
    
    # ANSI color codes
    BOLD = '\033[1m'
    GRAY = '\033[90m'
    RESET = '\033[0m'
    
    current_step_display = f"{BOLD}{current_step}{RESET}"
    
    with open(log_file, 'a') as log:
        log.write(f"\n{'='*80}\n")
        log.write(f"Build execution started at {datetime.now()}\n")
        log.write(f"{'='*80}\n\n")
        
        if HAS_YASPIN:
            with yaspin(text=current_step_display, color="cyan") as sp:
                for line in process.stdout:
                    # Write everything to log
                    log.write(line)
                    log.flush()
                    
                    line_stripped = line.rstrip()
                    
                    # Detect build steps and update spinner
                    if "STEP:" in line:
                        step_match = re.search(r'STEP: (.+)', line)
                        if step_match:
                            current_step = step_match.group(1)
                            current_step_display = f"{BOLD}{current_step}{RESET}"
                            sp.text = current_step_display
                    
                    # Show completion messages with bold checkmark
                    elif "completed successfully" in line:
                        # Reset to just step name before showing checkmark
                        sp.text = current_step_display
                        sp.ok(f"{BOLD}✓{RESET}")
                        # Restart spinner for next step
                        sp.text = "Processing..."
                        sp.start()
                    
                    else:
                        # Update spinner with latest line in gray (dynamic, scrolls continuously)
                        latest = strip_ansi(line_stripped)[:60]
                        if latest:
                            sp.text = f"{current_step_display}  {GRAY}{latest}{RESET}"
                        
                        # ALSO show OUR build script messages in gray (persistent)
                        if should_show(line_stripped):
                            sp.write(f"{GRAY}{line_stripped}{RESET}")
        else:
            # Fallback without yaspin
            for line in process.stdout:
                log.write(line)
                log.flush()
                
                line_stripped = line.rstrip()
                
                # Show build steps
                if "STEP:" in line:
                    print(f"\n{BOLD}{line_stripped}{RESET}", flush=True)
                elif "completed successfully" in line:
                    print(f"{BOLD}✓{RESET} {current_step}", flush=True)
                # Show our build script output
                elif should_show(line_stripped):
                    print(f"{GRAY}{line_stripped}{RESET}", flush=True)
    
    # Wait for process to complete
    return_code = process.wait()
    
    if return_code != 0:
        print(f"\n✗ Build failed with exit code {return_code}")
        print(f"See {log_file} for details")
        sys.exit(return_code)

def main():

    # Show banner splash
    print("\n")
    for line in scripts.configure_banner.CITRA_ASCII_LINES:
        # Unescape for display (convert \\033 to \033)
        display_line = line.replace("\\033", "\033")
        print("  " + display_line)
    print("\n  Let's build a CitraScope image!!\n")


    # Get user IDs
    uid, gid = get_user_ids()
    
    # Create timestamped log file in logs/ directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f"build_{timestamp}.log"
    
    with open(log_file, 'w') as f:
        f.write(f"CitraScope Pi Build Log\n")
        f.write(f"Started at {datetime.now()}\n")
        f.write(f"{'='*80}\n\n")
    
    print(f"Build log: {log_file}\n")
    
    # Build Docker image
    build_docker_image(uid, gid)
    
    # Run the build
    print("Running image builder...\n")
    run_build(sys.argv[1:], log_file)
    
    print(f"\n✓ Build complete!")
    print(f"Full log: {log_file}")
    
    print('\a')  # Terminal bell to notify user

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
