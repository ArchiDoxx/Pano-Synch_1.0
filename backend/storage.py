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


def purge_data_dir(data_dir) -> dict:
    """Rescue calibrations from a PanoSync ``data/`` folder, then delete it.

    This is the core cleanup step behind both the on-start migration and the
    multi-copy sweep tool. For users who ran PanoSync from inside a cloud-sync
    folder, such a ``data/`` is the lingering source of the cloud "tile flood":
    still mirrored to the cloud, it keeps coming back after central deletion.
    Deleting it *at the source* lets the user's own sync client propagate the
    deletion upward (the correct direction).

    Deliberately conservative:
      - no-op if ``data_dir`` doesn't exist
      - skipped if it doesn't look like PanoSync's data (no known bucket) — we
        never blindly delete an arbitrary folder that happens to be named "data"
      - skipped if it *is* the active data root (self-protection)
      - existing calibrations in the active root are never overwritten

    Returns ``{"removed": bool, "calibrations_migrated": int}``.
    """
    data_dir = Path(data_dir)
    report = {"removed": False, "calibrations_migrated": 0}

    if not data_dir.is_dir():
        return report

    # Self-protection: never delete the currently active data directory.
    try:
        if data_dir.resolve() == data_root().resolve():
            return report
    except OSError:
        return report

    # Only act if it carries a PanoSync bucket — guards against deleting an
    # unrelated "data" folder the program happens to sit next to.
    known_buckets = ("calibrations",) + _TRANSIENT_BUCKETS
    if not any((data_dir / bucket).exists() for bucket in known_buckets):
        return report

    # Rescue persistent calibrations into the active root (never clobber newer ones).
    src_calib = data_dir / "calibrations"
    if src_calib.is_dir():
        dest = calibrations_dir()
        dest.mkdir(parents=True, exist_ok=True)
        for src in src_calib.iterdir():
            if not src.is_file():
                continue
            target = dest / src.name
            if target.exists():
                continue
            try:
                shutil.copy2(src, target)
                report["calibrations_migrated"] += 1
            except OSError:
                continue  # best-effort — a single bad file must not abort cleanup

    # Delete the folder at the source → the user's sync client removes the
    # mirrored copy from the cloud.
    shutil.rmtree(data_dir, ignore_errors=True)
    report["removed"] = not data_dir.exists()
    return report


def migrate_legacy_data(program_dir) -> dict:
    """One-time, on-start cleanup of the old in-program ``<program>/data`` folder.

    Thin wrapper over :func:`purge_data_dir`. Idempotent: a no-op once the legacy
    folder is gone. Handles only the copy the program was launched from — use
    :func:`find_install_data_dirs` + :func:`purge_data_dir` to sweep several
    downloaded copies.
    """
    return purge_data_dir(Path(program_dir) / "data")


def find_install_data_dirs(search_root) -> list:
    """Find every PanoSync installation under ``search_root`` and return its
    ``data/`` directory (only those that actually exist).

    An installation is identified unambiguously by a ``backend/app.py`` marker —
    this avoids ever flagging an unrelated folder merely named "data". The
    currently active data root is excluded (self-protection). Robust against
    permission errors while walking a large sync tree (they are skipped).

    Used by the sweep tool to clean up after multiple downloaded copies.
    """
    search_root = Path(search_root)
    found: list[Path] = []
    if not search_root.is_dir():
        return found

    try:
        active = data_root().resolve()
    except OSError:
        active = None

    for dirpath, _dirnames, filenames in os.walk(search_root, onerror=lambda _e: None):
        here = Path(dirpath)
        # Installation marker: <install>/backend/app.py
        if here.name != "backend" or "app.py" not in filenames:
            continue
        data_dir = here.parent / "data"
        if not data_dir.is_dir():
            continue
        try:
            resolved = data_dir.resolve()
        except OSError:
            continue
        if active is not None and resolved == active:
            continue
        found.append(data_dir)

    return found
