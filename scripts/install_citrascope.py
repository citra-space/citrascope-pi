#!/usr/bin/env python3
"""
Install Citrascope into a mounted Raspberry Pi image.
This script sets up a Python virtual environment and installs Citrascope with INDI support.

SECURITY NOTE: This script avoids shell injection vulnerabilities by:
- Using subprocess.run() with list arguments (NOT shell=True with f-strings)
- Writing complex commands to temporary script files instead of inline strings
- Calling executables directly instead of using 'bash -c' with variable interpolation
- Validating config values in config.py to reject shell metacharacters
"""

import os
import sys
import subprocess
from contextlib import contextmanager
from build_result import BuildResult
from config import USERNAME, CITRASCOPE_VENV_PATH, ROOTFS_MOUNT, USER_UID, USER_GID

@contextmanager
def mount_context(rootfs_path):
    """Context manager to handle mounting and unmounting of necessary filesystems"""
    mounted_paths = []

    try:
        mount_points = [
            ('proc', os.path.join(rootfs_path, 'proc'), ['-t', 'proc', 'proc'], False),
            ('sys', os.path.join(rootfs_path, 'sys'), ['--rbind', '/sys'], True),
            ('dev', os.path.join(rootfs_path, 'dev'), ['--rbind', '/dev'], True),
            ('run', os.path.join(rootfs_path, 'run'), ['--rbind', '/run'], True),
        ]

        for name, dest, options, make_rslave in mount_points:
            os.makedirs(dest, exist_ok=True)
            subprocess.run(['mount'] + options + [dest], check=True)
            if make_rslave:
                subprocess.run(['mount', '--make-rslave', dest], check=True)
            mounted_paths.append(dest)

        yield

    finally:
        for path in reversed(mounted_paths):
            try:
                subprocess.run(['umount', '-R', path], check=True)
            except subprocess.CalledProcessError:
                pass

def install_citrascope(rootfs_path, homedir):
    """Install Citrascope and configure it to run on boot"""
    
    print("Installing pyenv and Python 3.12...")
    with mount_context(rootfs_path):
        # Install pyenv for the citra user
        pyenv_root = os.path.join(homedir, '.pyenv')
        subprocess.run([
            'chroot', rootfs_path, 'su', '-', USERNAME, '-c',
            'curl https://pyenv.run | bash'
        ], check=True)
        
        # Add pyenv to shell profile
        bashrc_path = os.path.join(homedir, '.bashrc')
        with open(bashrc_path, 'a') as f:
            f.write('\n# pyenv configuration\n')
            f.write('export PYENV_ROOT="$HOME/.pyenv"\n')
            f.write('export PATH="$PYENV_ROOT/bin:$PATH"\n')
            f.write('eval "$(pyenv init -)"\n')
        
        # Install Python 3.12 using pyenv
        # Use a script file to avoid shell injection
        pyenv_script_path = os.path.join(homedir, '.pyenv_install.sh')
        with open(pyenv_script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('set -e\n')
            f.write('export PYENV_ROOT="$HOME/.pyenv"\n')
            f.write('export PATH="$PYENV_ROOT/bin:$PATH"\n')
            f.write('pyenv install 3.12\n')
            f.write('pyenv global 3.12\n')
        os.chmod(pyenv_script_path, 0o755)
        
        subprocess.run([
            'chroot', rootfs_path,
            'su', '-', USERNAME, '-c',
            '/home/' + USERNAME + '/.pyenv_install.sh'
        ], check=True)
        
        # Clean up script
        os.remove(pyenv_script_path)
    
    print("Creating Citrascope virtual environment...")
    with mount_context(rootfs_path):
        # Create virtual environment using pyenv's Python 3.12 directly
        # Build python path - pyenv installs to 3.12.x, find the exact version
        pyenv_versions_dir = os.path.join(homedir, '.pyenv/versions')
        python_path = None
        if os.path.exists(pyenv_versions_dir):
            for version_dir in os.listdir(pyenv_versions_dir):
                if version_dir.startswith('3.12'):
                    python_path = os.path.join('/home', USERNAME, '.pyenv/versions', version_dir, 'bin/python3')
                    break
        
        if not python_path:
            raise RuntimeError("Python 3.12 not found in pyenv versions")
        
        subprocess.run([
            'chroot', rootfs_path,
            'su', '-', USERNAME, '-c',
            python_path + ' -m venv ' + CITRASCOPE_VENV_PATH
        ], check=True)
        
        print("Installing Citrascope with INDI support...")
        
        # Install citrascope[indi] in the venv
        # Use pip directly from venv instead of sourcing activate
        pip_path = os.path.join(CITRASCOPE_VENV_PATH, 'bin', 'pip')
        subprocess.run([
            'chroot', rootfs_path,
            pip_path, 'install', '--upgrade', 'pip'
        ], check=True)
        
        subprocess.run([
            'chroot', rootfs_path,
            pip_path, 'install', 'citrascope[indi]'
        ], check=True)
        
        # Get installed version
        result = subprocess.run([
            'chroot', rootfs_path,
            pip_path, 'show', 'citrascope'
        ], capture_output=True, text=True, check=True)
        
        # Parse version from pip show output
        version = None
        for line in result.stdout.split('\n'):
            if line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
                break
        
        if version:
            print(f"  ✓ Citrascope v{version} installed successfully")
            return version
        else:
            print("  ✓ Citrascope installed successfully")
            return "unknown"

def create_systemd_service(rootfs_path):
    """Create systemd service for Citrascope"""
    
    service_content = f"""[Unit]
Description=Citrascope Telescope Control Daemon
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={USERNAME}
WorkingDirectory=/home/{USERNAME}
ExecStart={CITRASCOPE_VENV_PATH}/bin/citrascope --web-port 80
Restart=on-failure
# Allow binding to privileged port 80 without running as root
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
"""
    
    service_path = os.path.join(rootfs_path, 'etc/systemd/system/citrascope.service')
    with open(service_path, 'w') as f:
        f.write(service_content)
    
    print("Created citrascope.service")
    
    # Enable the service
    service_link = os.path.join(rootfs_path, 'etc/systemd/system/multi-user.target.wants/citrascope.service')
    os.makedirs(os.path.dirname(service_link), exist_ok=True)
    
    if not os.path.exists(service_link):
        os.symlink('/etc/systemd/system/citrascope.service', service_link)
    
    print("Enabled citrascope.service")

def set_permissions(rootfs_path, homedir):
    """Set correct ownership for user files"""
    print("Setting file ownership...")
    
    # Change ownership of home directory recursively
    # Use chown -R to handle symlinks and special files properly
    try:
        subprocess.run([
            'chown', '-R',
            str(USER_UID) + ':' + str(USER_GID),
            homedir
        ], check=True)
        print("File ownership set")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Some files could not have ownership changed: {e}")
        # Still return success as this is not critical
        print("File ownership partially set")

def main():
    HOMEDIR = os.path.join(ROOTFS_MOUNT, f"home/{USERNAME}")
    
    if not os.path.exists(ROOTFS_MOUNT):
        print(f"Error: Root filesystem path {ROOTFS_MOUNT} does not exist")
        return BuildResult(success=False)
    
    if not os.path.exists(HOMEDIR):
        print(f"Error: Home directory {HOMEDIR} does not exist. User must be created first.")
        return BuildResult(success=False)
    
    try:
        # Ensure DNS resolution works
        resolv_conf = os.path.join(ROOTFS_MOUNT, 'etc/resolv.conf')
        resolv_backup = resolv_conf + '.bak'
        
        if os.path.exists(resolv_conf):
            subprocess.run(['cp', resolv_conf, resolv_backup])
        subprocess.run(['cp', '/etc/resolv.conf', resolv_conf])
        
        # Install Citrascope and get version
        citrascope_version = install_citrascope(ROOTFS_MOUNT, HOMEDIR)
        
        # Create systemd service
        create_systemd_service(ROOTFS_MOUNT)
        
        # Set permissions
        set_permissions(ROOTFS_MOUNT, HOMEDIR)
        
        # Restore resolv.conf
        if os.path.exists(resolv_backup):
            subprocess.run(['mv', resolv_backup, resolv_conf])
        
        print(f"Citrascope installation completed successfully!")
        print(f"Installed version: {citrascope_version}")
        print(f"DEBUG: citrascope_version type: {type(citrascope_version)}, value: '{citrascope_version}', bool: {bool(citrascope_version)}")
        
        # Only include version if we actually got one
        if citrascope_version and citrascope_version != "unknown":
            print(f"DEBUG: Returning BuildResult with version data")
            return BuildResult(success=True, data={'version': citrascope_version})
        else:
            print(f"WARNING: Could not determine Citrascope version (got: {repr(citrascope_version)})")
            return BuildResult(success=True)
        
    except Exception as e:
        print(f"Error installing Citrascope: {e}")
        return BuildResult(success=False)

if __name__ == "__main__":
    result = main()
    # Handle both BuildResult and legacy bool for backward compatibility
    if isinstance(result, BuildResult):
        sys.exit(0 if result.success else 1)
    else:
        sys.exit(0 if result else 1)
