"""
Tests for backend.storage — the central, cloud-sync-safe data directory
resolution and the startup cleanup of stale sessions/tiles/uploads.

Root-cause being fixed: large regenerable artifacts (DZI tiles, uploads,
session JSON) used to be written into the program folder. When the program
sits in a OneDrive-synced folder, every tile gets uploaded to the cloud and
nothing is ever deleted. These tests pin the new behavior:
  1. data lives in a per-user *local* app dir OneDrive never mirrors
  2. an override env var exists (for tests / power users)
  3. stale sessions/tiles/uploads are cleaned, calibrations are NEVER touched
"""

import os
import sys
import time
from pathlib import Path

import pytest

from backend import storage


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PANOSYNC_DATA_DIR", str(tmp_path))
    return tmp_path


# ── Path resolution ───────────────────────────────────────────────────────────

def test_override_env_wins(data_dir):
    assert storage.data_root() == data_dir


def test_subdirs_live_under_root(data_dir):
    assert storage.uploads_dir() == data_dir / "uploads"
    assert storage.tiles_dir() == data_dir / "tiles"
    assert storage.sessions_dir() == data_dir / "sessions"
    assert storage.calibrations_dir() == data_dir / "calibrations"


def test_windows_uses_localappdata(monkeypatch, tmp_path):
    monkeypatch.delenv("PANOSYNC_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    assert storage.data_root() == tmp_path / "Local" / "PanoSync"


def test_macos_uses_caches(monkeypatch):
    monkeypatch.delenv("PANOSYNC_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    assert storage.data_root() == Path.home() / "Library" / "Caches" / "PanoSync"


def test_linux_uses_xdg_cache(monkeypatch, tmp_path):
    monkeypatch.delenv("PANOSYNC_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    assert storage.data_root() == tmp_path / "cache" / "PanoSync"


def test_ensure_dirs_creates_all(data_dir):
    storage.ensure_dirs()
    for d in (storage.uploads_dir(), storage.tiles_dir(),
              storage.sessions_dir(), storage.calibrations_dir()):
        assert d.is_dir()


# ── Cleanup ───────────────────────────────────────────────────────────────────

def _set_age(path: Path, hours: float) -> None:
    old = time.time() - hours * 3600.0
    os.utime(path, (old, old))


def test_cleanup_removes_old_keeps_recent(data_dir):
    storage.ensure_dirs()
    sessions, tiles, uploads = (
        storage.sessions_dir(), storage.tiles_dir(), storage.uploads_dir())

    # Old triplet — 26h
    (sessions / "old.json").write_text("{}")
    (tiles / "old").mkdir()
    (tiles / "old" / "panoA").mkdir()
    (uploads / "old").mkdir()
    for p in (sessions / "old.json", tiles / "old", uploads / "old"):
        _set_age(p, 26)

    # Recent triplet — 1h
    (sessions / "new.json").write_text("{}")
    (tiles / "new").mkdir()
    (uploads / "new").mkdir()
    for p in (sessions / "new.json", tiles / "new", uploads / "new"):
        _set_age(p, 1)

    report = storage.cleanup_stale(max_age_hours=24)

    assert not (sessions / "old.json").exists()
    assert not (tiles / "old").exists()
    assert not (uploads / "old").exists()
    assert (sessions / "new.json").exists()
    assert (tiles / "new").exists()
    assert (uploads / "new").exists()
    assert report["sessions"] >= 1 and report["tiles"] >= 1 and report["uploads"] >= 1


def test_cleanup_never_touches_calibrations(data_dir):
    storage.ensure_dirs()
    calib = storage.calibrations_dir() / "deadbeef.json"
    calib.write_text('{"pairs": []}')
    _set_age(calib, 9999)  # ancient on purpose
    storage.cleanup_stale(max_age_hours=24)
    assert calib.exists()


# ── Cloud-sync folder detection (deployment guard A) ──────────────────────────

def test_detects_onedrive_personal():
    assert storage.is_cloud_synced(r"C:\Users\x\OneDrive\Desktop\PanoSync") == "onedrive"


def test_detects_onedrive_business_folder():
    assert storage.is_cloud_synced(r"C:\Users\x\OneDrive - Onsite\PanoSync") == "onedrive"


def test_detects_icloud_mobile_documents():
    assert storage.is_cloud_synced(
        "/Users/x/Library/Mobile Documents/com~apple~CloudDocs/PanoSync"
    ) == "mobile documents"


def test_local_paths_not_flagged():
    assert storage.is_cloud_synced(r"C:\Users\x\AppData\Local\PanoSync") is None
    assert storage.is_cloud_synced("/Users/x/Desktop/PanoSync") is None
