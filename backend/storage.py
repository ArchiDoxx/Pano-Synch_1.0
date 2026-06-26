"""
Central, cloud-sync-safe storage paths + stale-data cleanup for PanoSync.

Why this module exists
----------------------
PanoSync generates a DZI tile pyramid per uploaded image — easily tens of
thousands of small JPEG files per upload. The old code wrote these (plus the
uploaded originals and session JSON) *into the program folder*. When a user
installs/runs PanoSync from inside a OneDrive-synced location (e.g. the
Desktop), OneDrive mirrors every single tile to the cloud, and nothing is ever
deleted — the folder grows without bound ("tile flood").

Fix: write all large, regenerable artifacts to a per-user *local* application
directory that consumer cloud-sync clients never mirror, regardless of where
the program itself lives:

    Windows : %LOCALAPPDATA%\\PanoSync           (outside OneDrive's reach)
    macOS   : ~/Library/Caches/PanoSync          (not synced by iCloud Drive)
    Linux   : $XDG_CACHE_HOME/PanoSync or ~/.cache/PanoSync

The location can be overridden with the PANOSYNC_DATA_DIR environment variable
(used by tests and power users). Paths are resolved per-call (not cached at
import) so the override and platform can be changed/tested at runtime.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

APP_NAME = "PanoSync"

# Transient, regenerable buckets that the cleanup is allowed to delete.
# NOTE: "calibrations" is intentionally absent — it is the only persistent,
# non-regenerable data and must survive cleanup.
_TRANSIENT_BUCKETS = ("sessions", "tiles", "uploads")

# Substrings that flag a path as living inside a consumer cloud-sync folder.
# Matched case-insensitively against each path component, so "OneDrive" and
# "OneDrive - Onsite" both hit; macOS iCloud lives under "Mobile Documents".
_CLOUD_SYNC_MARKERS = (
    "onedrive", "icloud", "dropbox", "google drive", "googledrive",
    "mobile documents",
)


def data_root() -> Path:
    """Resolve the per-user PanoSync data root (never inside a cloud-sync folder)."""
    override = os.environ.get("PANOSYNC_DATA_DIR")
    if override:
        return Path(override)

    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / APP_NAME

    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / APP_NAME


def uploads_dir() -> Path:
    return data_root() / "uploads"


def tiles_dir() -> Path:
    return data_root() / "tiles"


def sessions_dir() -> Path:
    return data_root() / "sessions"


def calibrations_dir() -> Path:
    return data_root() / "calibrations"


def ensure_dirs() -> None:
    """Create all data subdirectories if missing (idempotent)."""
    for d in (uploads_dir(), tiles_dir(), sessions_dir(), calibrations_dir()):
        d.mkdir(parents=True, exist_ok=True)


def is_cloud_synced(path) -> str | None:
    """Return the matched marker if ``path`` looks like it sits inside a
    consumer cloud-sync folder (OneDrive/iCloud/Dropbox/Google Drive), else None.

    Used only to warn the operator — PanoSync's data already lives outside any
    sync folder; this just nudges users not to run the *program* from one.
    """
    for part in Path(path).parts:
        lowered = part.lower()
        for marker in _CLOUD_SYNC_MARKERS:
            if marker in lowered:
                return marker
    return None


def cleanup_stale(max_age_hours: float = 24.0, now: float | None = None) -> dict:
    """Delete sessions/tiles/uploads whose mtime is older than ``max_age_hours``.

    Calibrations are never touched (persistent, keyed by filename). Returns a
    per-bucket count of removed top-level entries. Robust against missing dirs
    and transient OS errors (best-effort).
    """
    if now is None:
        now = time.time()
    cutoff = now - max_age_hours * 3600.0
    removed = {bucket: 0 for bucket in _TRANSIENT_BUCKETS}

    bases = {
        "sessions": sessions_dir(),
        "tiles": tiles_dir(),
        "uploads": uploads_dir(),
    }
    for bucket, base in bases.items():
        if not base.exists():
            continue
        for entry in base.iterdir():
            try:
                if entry.stat().st_mtime >= cutoff:
                    continue
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink()
                removed[bucket] += 1
            except OSError:
                continue  # in use / permission — skip, try again next start

    return removed
