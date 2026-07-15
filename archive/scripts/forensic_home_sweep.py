#!/usr/bin/env python3
"""
Forensic Home Directory Sweep (~/)
Identifies root-level bloat, old archives, log dumps, massive caches, and Downloads/Desktop clutter.
"""

import os
from pathlib import Path
import json

HOME = Path.home()

def scan_root_files():
    files = []
    for p in HOME.iterdir():
        if p.is_file() and not p.is_symlink():
            size_mb = p.stat().st_size / (1024 * 1024)
            if size_mb > 0.5 or p.name.startswith(".zshrc.") or p.name.endswith(".log") or p.name.endswith(".zip"):
                files.append({
                    "name": p.name,
                    "size_mb": round(size_mb, 2),
                    "reason": "Large archive/log or redundant shell backup"
                })
    return sorted(files, key=lambda x: x["size_mb"], reverse=True)

def scan_heavy_dirs():
    targets = [
        HOME / "Downloads",
        HOME / "Desktop",
        HOME / ".cache",
        HOME / "Library/Caches",
        HOME / ".npm",
        HOME / "venv",
        HOME / "my_agent",
        HOME / "specs",
        HOME / "mcp-backups",
    ]
    results = []
    for t in targets:
        if not t.exists():
            continue
        total = 0
        try:
            # Shallow or fast sum
            for p in t.rglob("*"):
                if p.is_file() and not p.is_symlink():
                    total += p.stat().st_size
        except Exception:
            pass
        results.append({
            "dir": str(t.relative_to(HOME)),
            "size_mb": round(total / (1024 * 1024), 2)
        })
    return sorted(results, key=lambda x: x["size_mb"], reverse=True)

if __name__ == "__main__":
    data = {
        "root_files": scan_root_files(),
        "heavy_dirs": scan_heavy_dirs()
    }
    print(json.dumps(data, indent=2))
