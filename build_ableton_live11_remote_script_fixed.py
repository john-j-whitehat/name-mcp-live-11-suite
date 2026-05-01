#!/usr/bin/env python3
"""Build and install the AbletonMCP Remote Script package for Ableton Live 11."""

from __future__ import annotations

import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(r"C:\Users\DAW11\Desktop\MCP Live 11 Copy")
SOURCE_RUNTIME = WORKSPACE_ROOT / "AbletonMCP_RemoteScript_runtime.py"
BUILD_ROOT = WORKSPACE_ROOT / "build" / "live11_remote_script"
BUILD_PACKAGE_DIR = BUILD_ROOT / "AbletonMCP"
BUILD_INIT_PATH = BUILD_PACKAGE_DIR / "__init__.py"
TARGET_PACKAGE_DIR = Path(r"C:\ProgramData\Ableton\Live 11 Suite\Resources\MIDI Remote Scripts\AbletonMCP")
TARGET_INIT_PATH = TARGET_PACKAGE_DIR / "__init__.py"
BACKUP_ROOT = WORKSPACE_ROOT / "runtime_backups"

def sha256_of(path: Path):
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def backup_existing_target():
    if not TARGET_PACKAGE_DIR.exists():
        return None
    ensure_dir(BACKUP_ROOT)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUP_ROOT / f"{timestamp}-AbletonMCP"
    shutil.copytree(TARGET_PACKAGE_DIR, backup_dir)
    return backup_dir

def build_package():
    if not SOURCE_RUNTIME.exists():
        print(f"ERROR: Source runtime not found: {SOURCE_RUNTIME}")
        return 1
    ensure_dir(BUILD_PACKAGE_DIR)
    shutil.copy2(SOURCE_RUNTIME, BUILD_INIT_PATH)
    print("Live 11 remote script package built.")
    print(f"Source      : {SOURCE_RUNTIME}")
    print(f"Build output: {BUILD_INIT_PATH}")
    print(f"SHA256      : {sha256_of(BUILD_INIT_PATH)}")
    return 0

def install_package():
    build_result = build_package()
    if build_result != 0:
        return build_result
    backup_dir = backup_existing_target()
    ensure_dir(TARGET_PACKAGE_DIR)
    shutil.copy2(BUILD_INIT_PATH, TARGET_INIT_PATH)
    print("Live 11 remote script package installed.")
    print(f"Installed to: {TARGET_INIT_PATH}")
    if backup_dir is not None:
        print(f"Backup      : {backup_dir}")
    print(f"SHA256      : {sha256_of(TARGET_INIT_PATH)}")
    print("NEXT STEP   : Restart Ableton Live 11 so the remote script is reloaded.")
    return 0

def print_status():
    source_hash = sha256_of(SOURCE_RUNTIME)
    build_hash = sha256_of(BUILD_INIT_PATH)
    target_hash = sha256_of(TARGET_INIT_PATH)
    print("Ableton Live 11 Remote Script Status")
    print("====================================")
    print(f"Source exists : {SOURCE_RUNTIME.exists()}")
    print(f"Source path   : {SOURCE_RUNTIME}")
    print(f"Source hash   : {source_hash}")
    print()
    print(f"Build exists  : {BUILD_INIT_PATH.exists()}")
    print(f"Build path    : {BUILD_INIT_PATH}")
    print(f"Build hash    : {build_hash}")
    print()
    print(f"Target exists : {TARGET_INIT_PATH.exists()}")
    print(f"Target path   : {TARGET_INIT_PATH}")
    print(f"Target hash   : {target_hash}")
    print()
    print(f"Build in sync : {bool(source_hash and build_hash and source_hash == build_hash)}")
    print(f"Live11 synced : {bool(source_hash and target_hash and source_hash == target_hash)}")
    return 0

def print_usage():
    print("Usage: build_ableton_live11_remote_script.py [build|install|status]")
    print("  build   : build the Live 11 AbletonMCP package in the workspace")
    print("  install : build and install the Live 11 package into ProgramData")
    print("  status  : compare source, build output, and installed Live 11 package")
    return 1

def main(argv):
    if len(argv) != 2:
        return print_usage()
    command = argv[1].strip().lower()
    if command == "build":
        return build_package()
    if command == "install":
        return install_package()
    if command == "status":
        return print_status()
    return print_usage()

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
