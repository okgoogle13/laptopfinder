#!/usr/bin/env python3
"""
Forensic Apple Developer / Xcode Audit Sweep
Scans Xcode IDE app, Developer directories, Simulators, DerivedData, and iOS backups.
"""

import os
from pathlib import Path
import json

HOME = Path.home()

TARGETS = [
    Path("/Applications/Xcode.app"),
    HOME / "Library/Developer",
    HOME / "Library/Developer/Xcode",
    HOME / "Library/Developer/Xcode/DerivedData",
    HOME / "Library/Developer/Xcode/iOS DeviceSupport",
    HOME / "Library/Developer/Xcode/Archives",
    HOME / "Library/Developer/CoreSimulator",
    HOME / "Library/Developer/CoreSimulator/Devices",
    HOME / "Library/Developer/CoreSimulator/Caches",
    HOME / "Library/Caches/com.apple.dt.Xcode",
    HOME / "Library/Application Support/MobileSync/Backup",
    HOME / "Library/Logs/CoreSimulator",
]

def get_path_size_mb(p: Path):
    if not p.exists():
        return None
    total = 0
    try:
        if p.is_file():
            return round(p.stat().st_size / (1024 * 1024), 2)
        for sub in p.rglob("*"):
            if sub.is_file() and not sub.is_symlink():
                total += sub.stat().st_size
    except Exception:
        pass
    return round(total / (1024 * 1024), 2)

def scan_apple_dev_targets():
    results = []
    for t in TARGETS:
        size_mb = get_path_size_mb(t)
        if size_mb is not None and size_mb > 0:
            results.append({
                "path": str(t),
                "size_mb": size_mb,
                "size_gb": round(size_mb / 1024, 2)
            })
    return sorted(results, key=lambda x: x["size_mb"], reverse=True)

if __name__ == "__main__":
    findings = scan_apple_dev_targets()
    print(json.dumps(findings, indent=2))
