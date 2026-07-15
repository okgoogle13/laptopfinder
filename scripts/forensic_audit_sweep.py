#!/usr/bin/env python3
"""
Forensic Local Workspace Audit Sweep
Scans ~/Projects to identify concrete evidence for deletion, cache bloat,
remote synchronization (GitHub), and cloud backup presence.
"""

import os
import subprocess
import datetime
import json
from pathlib import Path

PROJECTS_ROOT = Path.home() / "Projects"
GDRIVE_ROOT = Path.home() / "Library/CloudStorage/GoogleDrive-nishantdougall@gmail.com"
ICLOUD_ROOTS = list(Path.home().glob("Library/CloudStorage/iCloudDrive*"))

CACHE_DIRS = {"node_modules", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "dist", "build", ".next"}

def get_dir_size(path: Path):
    total = 0
    cache_total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file() and not p.is_symlink():
                size = p.stat().st_size
                total += size
                # Check if file is inside a cache dir
                parts = p.relative_to(path).parts
                if any(part in CACHE_DIRS for part in parts):
                    cache_total += size
    except Exception:
        pass
    return total, cache_total

def get_git_info(path: Path):
    if not (path / ".git").exists():
        return {"is_git": False}
    
    def run_git(args):
        try:
            res = subprocess.run(["git", "-C", str(path)] + args, capture_output=True, text=True, timeout=5)
            return res.stdout.strip()
        except Exception:
            return ""

    remote = run_git(["remote", "get-url", "origin"])
    status_porcelain = run_git(["status", "--porcelain"])
    last_commit_date = run_git(["log", "-1", "--format=%cd", "--date=short"])
    last_commit_msg = run_git(["log", "-1", "--format=%s"])
    
    # Check if synced with upstream
    unpushed = run_git(["log", "@{u}..", "--oneline"])
    
    is_clean = len(status_porcelain) == 0
    is_pushed = len(unpushed) == 0 and bool(remote)

    return {
        "is_git": True,
        "remote": remote,
        "is_clean": is_clean,
        "is_pushed": is_pushed,
        "uncommitted_files": len(status_porcelain.splitlines()) if status_porcelain else 0,
        "last_commit_date": last_commit_date,
        "last_commit_msg": last_commit_msg,
    }

def check_cloud_backups(name: str):
    backups = []
    if GDRIVE_ROOT.exists():
        matches = list(GDRIVE_ROOT.rglob(name))
        if matches:
            backups.append(f"Google Drive ({len(matches)} match)")
    for icloud in ICLOUD_ROOTS:
        if icloud.exists():
            matches = list(icloud.rglob(name))
            if matches:
                backups.append(f"iCloud ({len(matches)} match)")
    return backups

def scan_workspace():
    results = []
    if not PROJECTS_ROOT.exists():
        return results

    for item in sorted(PROJECTS_ROOT.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue

        total_bytes, cache_bytes = get_dir_size(item)
        git_info = get_git_info(item)
        backups = check_cloud_backups(item.name)

        # Concrete Verdict & Evidence Analysis
        verdict = []
        evidence = []

        # Check if project is nested inside Projects/Projects
        if item.name == "Projects":
            verdict.append("DUPLICATE/NESTED DIRECTORY")
            evidence.append("Folder named 'Projects' nested inside ~/Projects")

        if git_info.get("is_git"):
            if git_info.get("is_clean") and git_info.get("is_pushed"):
                evidence.append(f"100% committed & pushed to {git_info.get('remote')}")
            elif not git_info.get("is_clean"):
                evidence.append(f"{git_info.get('uncommitted_files')} uncommitted files")

            if git_info.get("last_commit_date"):
                evidence.append(f"Last commit: {git_info.get('last_commit_date')}")
        else:
            evidence.append("Not tracked by Git")

        if backups:
            evidence.append("Backed up to: " + ", ".join(backups))

        cache_pct = (cache_bytes / total_bytes * 100) if total_bytes > 0 else 0
        if cache_pct > 50:
            evidence.append(f"{cache_pct:.1f}% of disk space is recreatable cache (.venv/node_modules)")

        results.append({
            "name": item.name,
            "path": str(item),
            "size_mb": round(total_bytes / (1024 * 1024), 2),
            "cache_mb": round(cache_bytes / (1024 * 1024), 2),
            "cache_pct": round(cache_pct, 1),
            "git": git_info,
            "backups": backups,
            "evidence": evidence
        })

    return results

if __name__ == "__main__":
    scan_data = scan_workspace()
    print(json.dumps(scan_data, indent=2))
