#!/usr/bin/env python3
"""
Install native hardware driver libraries (Moravian, ZWO EAF) into the rootfs.

Downloads official SDK packages, extracts the ARM64 shared libraries,
installs them to /usr/local/lib, writes udev rules, and runs ldconfig.
"""

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from config import (
    DRIVER_LIB_DIR,
    HARDWARE_DRIVERS,
    ROOTFS_MOUNT,
    UDEV_RULE_TEMPLATE,
    UDEV_RULES_DIR,
)
from update_upgrade_chroot import mount_context

# Subdirectory names that indicate ARM64 / AArch64 binaries
_ARM64_DIR_NAMES = {"armv8", "aarch64", "arm64", "linux_arm64"}


# Persistent cache inside the bind-mounted workspace so downloads survive between builds.
_CACHE_DIR = "/workspace/.cache/drivers"


def _download(url, name):
    """Download a URL, caching in the workspace. Returns the local file path."""
    os.makedirs(_CACHE_DIR, exist_ok=True)

    # Use the driver name + URL-derived extension for a stable cache key
    basename = url.rsplit("/", 1)[-1].split("?")[0] or "sdk_download"
    ext = ""
    for suffix in (".tar.gz", ".tgz", ".tar.bz2", ".zip", ".tar"):
        if basename.endswith(suffix):
            ext = suffix
            break
    if not ext:
        ext = ".tar.gz"
    cached_path = os.path.join(_CACHE_DIR, f"{name}{ext}")

    if os.path.exists(cached_path):
        size = os.path.getsize(cached_path)
        print(f"  Using cached SDK: {cached_path} ({size} bytes)")
        return cached_path

    print(f"  Downloading {url}")
    urllib.request.urlretrieve(url, cached_path)
    print(f"  Saved to {cached_path} ({os.path.getsize(cached_path)} bytes)")
    return cached_path


def _matches_lib(name, lib_name):
    """True if *name* is *lib_name* or a versioned variant (e.g. libFoo.so.1.2)."""
    return name == lib_name or name.startswith(lib_name + ".")


def _is_arm64_path(path):
    """True if any path component is a known ARM64 directory name."""
    return any(part in _ARM64_DIR_NAMES for part in Path(path).parts)


def _safe_write_member(data, filename, dest_dir):
    """Write *data* to *dest_dir*/*filename*, rejecting path traversal."""
    safe_name = os.path.basename(filename)
    dest = os.path.join(dest_dir, safe_name)
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def _extract_lib_from_tar(archive_path, dest_dir, lib_name):
    """Extract only *lib_name* (preferring ARM64) from a tarball. Returns extracted path or None."""
    with tarfile.open(archive_path) as tf:
        candidates = [m for m in tf.getmembers() if m.isfile() and _matches_lib(os.path.basename(m.name), lib_name)]
        if not candidates:
            return None
        arm64 = [m for m in candidates if _is_arm64_path(m.name)]
        pick = arm64[0] if arm64 else candidates[0]
        print(f"  Extracting {pick.name} from {os.path.basename(archive_path)}")
        reader = tf.extractfile(pick)
        if reader is None:
            return None
        return _safe_write_member(reader.read(), pick.name, dest_dir)


def _extract_lib_from_zip(archive_path, dest_dir, lib_name):
    """Extract only *lib_name* (preferring ARM64) from a zip. Returns extracted path or None."""
    with zipfile.ZipFile(archive_path) as zf:
        candidates = [n for n in zf.namelist() if not n.endswith("/") and _matches_lib(os.path.basename(n), lib_name)]
        if not candidates:
            return None
        arm64 = [n for n in candidates if _is_arm64_path(n)]
        pick = arm64[0] if arm64 else candidates[0]
        print(f"  Extracting {pick} from {os.path.basename(archive_path)}")
        return _safe_write_member(zf.read(pick), pick, dest_dir)


def _find_lib_in_archive(archive_path, dest_dir, lib_name):
    """Try to extract *lib_name* from *archive_path*. Returns path or None."""
    if tarfile.is_tarfile(archive_path):
        return _extract_lib_from_tar(archive_path, dest_dir, lib_name)
    if zipfile.is_zipfile(archive_path):
        return _extract_lib_from_zip(archive_path, dest_dir, lib_name)
    return None


def _extract_and_find(archive_path, dest_dir, lib_name):
    """Extract *lib_name* from *archive_path*, handling one level of nesting.

    Some SDKs (e.g. ZWO) ship an outer zip containing inner platform tarballs.
    If the library isn't directly in the outer archive, we look inside any
    nested archives for it.
    """
    # Try the outer archive first
    result = _find_lib_in_archive(archive_path, dest_dir, lib_name)
    if result:
        return result

    # Not found directly -- extract everything from the outer archive,
    # then check nested archives (one level deep, no recursion).
    print(f"  Library not in outer archive, checking nested archives...")
    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path) as tf:
            tf.extractall(dest_dir, filter="data")
    elif zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path) as zf:
            for member in zf.namelist():
                if ".." in member or os.path.isabs(member):
                    continue
                zf.extract(member, dest_dir)

    for root, _dirs, files in os.walk(dest_dir):
        for fname in files:
            nested = os.path.join(root, fname)
            if nested == archive_path:
                continue
            if tarfile.is_tarfile(nested) or zipfile.is_zipfile(nested):
                result = _find_lib_in_archive(nested, dest_dir, lib_name)
                if result:
                    return result

    return None


def _install_library(so_path, lib_name, rootfs_path):
    """Copy *so_path* into the rootfs lib dir, creating a symlink if versioned."""
    lib_dir = os.path.join(rootfs_path, DRIVER_LIB_DIR.lstrip("/"))
    os.makedirs(lib_dir, exist_ok=True)

    basename = os.path.basename(so_path)
    dest = os.path.join(lib_dir, basename)
    shutil.copy2(so_path, dest)
    os.chmod(dest, 0o755)
    print(f"  Installed {basename} -> {dest}")

    # If the file is versioned (e.g. libgxccd.so.1.2), create an unversioned symlink
    if basename != lib_name:
        link = os.path.join(lib_dir, lib_name)
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(basename, link)
        print(f"  Symlinked {lib_name} -> {basename}")


def _install_udev_rule(vendor_id, rule_file, rootfs_path):
    """Write a udev rule granting plugdev group access for *vendor_id*."""
    rules_dir = os.path.join(rootfs_path, UDEV_RULES_DIR.lstrip("/"))
    os.makedirs(rules_dir, exist_ok=True)

    rule_path = os.path.join(rules_dir, rule_file)
    rule_text = UDEV_RULE_TEMPLATE.format(vendor=vendor_id) + "\n"
    with open(rule_path, "w") as f:
        f.write(rule_text)
    print(f"  Wrote {rule_path}")


def _run_ldconfig(rootfs_path):
    """Run ldconfig inside the rootfs chroot so libraries are discoverable."""
    print("Running ldconfig in chroot...")
    with mount_context(rootfs_path):
        subprocess.run(["chroot", rootfs_path, "ldconfig"], check=True)
    print("ldconfig complete")


def install_driver(name, driver_cfg, rootfs_path, tmp_dir):
    """Download, extract, and install a single driver."""
    print(f"\n--- Installing {name} driver ---")

    url = driver_cfg["url"]
    if url == "TODO":
        print(f"  SKIPPING {name}: download URL not yet configured")
        return True

    archive = _download(url, name)
    extract_dir = os.path.join(tmp_dir, f"{name}_sdk")
    os.makedirs(extract_dir)

    lib_name = driver_cfg["lib_name"]
    so_path = _extract_and_find(archive, extract_dir, lib_name)
    if not so_path:
        print(f"  ERROR: could not find {lib_name} in downloaded SDK")
        return False

    _install_library(so_path, lib_name, rootfs_path)
    _install_udev_rule(driver_cfg["usb_vendor_id"], driver_cfg["udev_rule_file"], rootfs_path)
    return True


def main():
    rootfs_path = ROOTFS_MOUNT
    if not os.path.isdir(rootfs_path):
        print(f"Error: rootfs {rootfs_path} does not exist")
        return False

    try:
        with tempfile.TemporaryDirectory(prefix="hw_drivers_") as tmp_dir:
            for name, cfg in HARDWARE_DRIVERS.items():
                if not install_driver(name, cfg, rootfs_path, tmp_dir):
                    return False

        _run_ldconfig(rootfs_path)
        print("\nAll hardware drivers installed successfully")
        return True

    except Exception as e:
        print(f"Error installing hardware drivers: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
