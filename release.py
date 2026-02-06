#!/usr/bin/env python3
"""
Release automation for CitraScope Pi.
Handles version bumping, tagging, and pushing releases.
"""

import subprocess
import sys
import re
from pathlib import Path

VERSION_FILE = Path("VERSION")

def get_current_version():
    """Read current version from VERSION file"""
    if not VERSION_FILE.exists():
        print(f"Error: {VERSION_FILE} not found")
        sys.exit(1)
    return VERSION_FILE.read_text().strip()

def validate_version(version):
    """Validate semantic version format"""
    if not re.match(r'^\d+\.\d+(\.\d+)?$', version):
        return False, "Version must be MAJOR.MINOR or MAJOR.MINOR.PATCH (e.g., 0.3)"
    return True, None

def compare_versions(v1, v2):
    """Returns True if v2 > v1"""
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]
    
    # Pad to same length
    while len(parts1) < len(parts2):
        parts1.append(0)
    while len(parts2) < len(parts1):
        parts2.append(0)
    
    return parts2 > parts1

def prompt_for_version(current):
    """Prompt user for new version"""
    while True:
        new = input(f"Enter new version (e.g., 0.3): ").strip()
        
        valid, error = validate_version(new)
        if not valid:
            print(f"Invalid: {error}")
            continue
        
        if not compare_versions(current, new):
            print(f"Error: New version must be greater than {current}")
            continue
        
        return new

def main():
    # Parse arguments
    new_version = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("CitraScope Pi Release Automation\n")
    
    # Check git status is clean
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: Not a git repository")
        sys.exit(1)
    if result.stdout.strip():
        print("Error: Working directory has uncommitted changes")
        print(result.stdout)
        print("Commit or stash changes before releasing.")
        sys.exit(1)
    
    # Check on main branch
    result = subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: Could not determine current branch")
        sys.exit(1)
    if result.stdout.strip() != 'main':
        print(f"Error: Must be on main branch (currently on: {result.stdout.strip()})")
        sys.exit(1)
    
    # Get current version
    current = get_current_version()
    print(f"Current version: {current}\n")
    
    # Determine new version
    if new_version:
        valid, error = validate_version(new_version)
        if not valid:
            print(f"Error: {error}")
            sys.exit(1)
        if not compare_versions(current, new_version):
            print(f"Error: New version must be greater than {current}")
            sys.exit(1)
    else:
        new_version = prompt_for_version(current)
    
    tag = f"v{new_version}"
    
    # Show changes
    print(f"\nChanges to be made:")
    print(f"  - Update VERSION: {current} -> {new_version}")
    print(f"  - Create commit: \"Release v{new_version}\"")
    print(f"  - Create tag: {tag}")
    print(f"  - Push to origin")
    print()
    
    # Confirm
    response = input("Proceed? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted")
        sys.exit(0)
    
    print()
    
    # Update VERSION file
    VERSION_FILE.write_text(new_version + '\n')
    print(f"✓ Updated VERSION to {new_version}")
    
    # Commit
    subprocess.run(['git', 'add', 'VERSION'], check=True)
    subprocess.run(['git', 'commit', '-m', f'Release v{new_version}'], check=True)
    print(f"✓ Created commit: Release v{new_version}")
    
    # Create tag (will fail if exists)
    subprocess.run(['git', 'tag', tag], check=True)
    print(f"✓ Created tag: {tag}")
    
    # Push
    print("Pushing to origin...")
    subprocess.run(['git', 'push', 'origin', 'main', tag], check=True)
    print(f"✓ Pushed to origin")
    
    # Success
    print(f"\n✓ Release v{new_version} created successfully!")
    print(f"\nGitHub Actions will now build citrascope-pi-{tag}.img.xz")
    print(f"View build: https://github.com/citra-space/citrascope-pi/actions")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(130)
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Git command failed")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
