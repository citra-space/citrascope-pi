#!/usr/bin/env python3
import os
import sys
import crypt
import shutil
from config import USERNAME, PASSWORD, USER_UID, USER_GID, USER_GROUPS, ROOTFS_MOUNT

def generate_password_hash(password):
    """Generate SHA-512 password hash."""
    return crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))

def add_user_to_passwd(rootfs_path, username, uid, gid):
    """Add user entry to /etc/passwd"""
    passwd_file = os.path.join(rootfs_path, 'etc/passwd')
    entry = f"{username}:x:{uid}:{gid}::/home/{username}:/bin/bash\n"
    
    with open(passwd_file, 'a') as f:
        f.write(entry)

def add_user_to_shadow(rootfs_path, username, password_hash):
    """Add user entry to /etc/shadow"""
    shadow_file = os.path.join(rootfs_path, 'etc/shadow')
    # Format: username:password:lastchange:min:max:warn:inactive:expire:
    # lastchange is days since epoch
    import time
    days_since_epoch = int(time.time() / 86400)
    entry = f"{username}:{password_hash}:{days_since_epoch}:0:99999:7:::\n"
    
    with open(shadow_file, 'a') as f:
        f.write(entry)

def add_user_group(rootfs_path, username, gid):
    """Add user's primary group to /etc/group"""
    group_file = os.path.join(rootfs_path, 'etc/group')
    entry = f"{username}:x:{gid}:\n"
    
    with open(group_file, 'a') as f:
        f.write(entry)

def add_user_to_supplementary_groups(rootfs_path, username):
    """Add user to supplementary groups (sudo, video, gpio, etc.)"""
    group_file = os.path.join(rootfs_path, 'etc/group')
    
    # Groups to add user to
    groups_to_add = USER_GROUPS
    
    with open(group_file, 'r') as f:
        lines = f.readlines()
    
    with open(group_file, 'w') as f:
        for line in lines:
            line = line.rstrip('\n')
            for group in groups_to_add:
                if line.startswith(f"{group}:"):
                    # Add username to the group members list
                    if line.endswith(':'):
                        line = f"{line}{username}"
                    else:
                        line = f"{line},{username}"
                    break
            f.write(line + '\n')

def create_home_directory(rootfs_path, username, uid, gid):
    """Create and setup home directory for the new user."""
    home_path = os.path.join(rootfs_path, f'home/{username}')
    skel_path = os.path.join(rootfs_path, 'etc/skel')

    # Create home directory
    os.makedirs(home_path, exist_ok=True)

    # Copy skel files
    if os.path.exists(skel_path):
        for item in os.listdir(skel_path):
            s = os.path.join(skel_path, item)
            d = os.path.join(home_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

    # Set ownership
    for root, dirs, files in os.walk(home_path):
        for d in dirs:
            os.chown(os.path.join(root, d), uid, gid)
        for f in files:
            os.chown(os.path.join(root, f), uid, gid)

    os.chown(home_path, uid, gid)

def configure_sudo_nopasswd(rootfs_path, username):
    """Configure sudo without password for the user."""
    sudoers_dir = os.path.join(rootfs_path, 'etc/sudoers.d')
    os.makedirs(sudoers_dir, exist_ok=True)
    
    sudoers_file = os.path.join(sudoers_dir, f'010_{username}-nopasswd')
    with open(sudoers_file, 'w') as f:
        f.write(f'{username} ALL=(ALL) NOPASSWD: ALL\n')
    
    # Set correct permissions (must be 0440)
    os.chmod(sudoers_file, 0o440)

def add_user(rootfs_path, username, password, uid, gid):
    """Add a new user to the mounted Raspberry Pi image."""
    if not os.path.isdir(rootfs_path):
        raise ValueError(f"Root filesystem path {rootfs_path} does not exist")

    print(f"Creating user {username}")

    # Generate password hash
    password_hash = generate_password_hash(password)

    # Add user entries to system files
    add_user_to_passwd(rootfs_path, username, uid, gid)
    print("Added user to passwd file")

    add_user_to_shadow(rootfs_path, username, password_hash)
    print("Added user to shadow file")

    add_user_group(rootfs_path, username, gid)
    print("Created primary group")

    add_user_to_supplementary_groups(rootfs_path, username)
    print("Added user to supplementary groups")

    # Setup home directory
    create_home_directory(rootfs_path, username, uid, gid)
    print("Created home directory")

    # Configure sudo without password
    configure_sudo_nopasswd(rootfs_path, username)
    print("Configured sudo access")

def main():
    try:
        add_user(ROOTFS_MOUNT, USERNAME, PASSWORD, USER_UID, USER_GID)
        print(f"Successfully added user {USERNAME}")
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
