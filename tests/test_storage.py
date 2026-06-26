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


# ── Legacy data migration (one-time cleanup of the old in-program data dir) ────
#
# Old builds wrote data/ into the program folder. For users who ran PanoSync
# from inside OneDrive, that data/ is the source of the "tile flood" still in
# the cloud. On first start of the new build we rescue the (persistent)
# calibrations and delete the legacy data/ *at the source*, so the user's own
# sync client propagates the deletion upward.

def test_migrate_rescues_calibrations_and_removes_legacy(data_dir, tmp_path):
    program_dir = tmp_path / "prog"
    legacy = program_dir / "data"
    (legacy / "tiles" / "sess" / "panoA").mkdir(parents=True)
    (legacy / "sessions").mkdir(parents=True)
    (legacy / "calibrations").mkdir(parents=True)
    (legacy / "calibrations" / "deadbeef.json").write_text('{"pairs": [1]}')

    report = storage.migrate_legacy_data(program_dir)

    assert not legacy.exists()
    rescued = storage.calibrations_dir() / "deadbeef.json"
    assert rescued.exists()
    assert rescued.read_text() == '{"pairs": [1]}'
    assert report["removed"] is True
    assert report["calibrations_migrated"] == 1


def test_migrate_noop_when_no_legacy(data_dir, tmp_path):
    program_dir = tmp_path / "prog"
    program_dir.mkdir()
    report = storage.migrate_legacy_data(program_dir)
    assert report["removed"] is False
    assert report["calibrations_migrated"] == 0


def test_migrate_skips_unrelated_data_dir(data_dir, tmp_path):
    # A 'data' folder that doesn't look like PanoSync's must never be deleted.
    program_dir = tmp_path / "prog"
    legacy = program_dir / "data"
    legacy.mkdir(parents=True)
    (legacy / "random.txt").write_text("not panosync")
    report = storage.migrate_legacy_data(program_dir)
    assert report["removed"] is False
    assert legacy.exists()


def test_migrate_does_not_overwrite_existing_calibration(data_dir, tmp_path):
    storage.ensure_dirs()
    existing = storage.calibrations_dir() / "key.json"
    existing.write_text("NEW")
    program_dir = tmp_path / "prog"
    legacy = program_dir / "data"
    (legacy / "calibrations").mkdir(parents=True)
    (legacy / "calibrations" / "key.json").write_text("OLD")

    report = storage.migrate_legacy_data(program_dir)

    assert existing.read_text() == "NEW"  # never clobber a newer calibration
    assert not legacy.exists()
    assert report["removed"] is True
    assert report["calibrations_migrated"] == 0


def test_migrate_skips_when_legacy_equals_data_root(monkeypatch, tmp_path):
    # Self-protection: if the active data dir IS the legacy path, never delete it.
    program_dir = tmp_path / "prog"
    legacy = program_dir / "data"
    (legacy / "tiles").mkdir(parents=True)
    monkeypatch.setenv("PANOSYNC_DATA_DIR", str(legacy))
    report = storage.migrate_legacy_data(program_dir)
    assert report["removed"] is False
    assert legacy.exists()


# ── Multi-copy scan & purge (the cleanup tool for several downloaded copies) ───
#
# A user may have downloaded PanoSync several times (Desktop, Downloads,
# "PanoSync (1)", ...). Each copy has its own data/ — so the one-time
# migration on start only clears the copy it was launched from. The sweep tool
# finds *every* installation under a search root and purges each data/.

def _make_install(root: Path, name: str, with_data: bool = True) -> Path:
    inst = root / name
    (inst / "backend").mkdir(parents=True)
    (inst / "backend" / "app.py").write_text("# app")
    if with_data:
        (inst / "data" / "tiles" / "s").mkdir(parents=True)
        (inst / "data" / "calibrations").mkdir(parents=True)
    return inst


def test_find_install_data_dirs_finds_all_copies(data_dir, tmp_path):
    onedrive = tmp_path / "OneDrive"
    _make_install(onedrive / "Desktop", "PanoSync", with_data=True)
    _make_install(onedrive / "Downloads", "PanoSync (1)", with_data=True)
    # An unrelated folder that merely has a 'data' dir but no backend/app.py.
    (onedrive / "other" / "data").mkdir(parents=True)

    found = {p.resolve() for p in storage.find_install_data_dirs(onedrive)}

    assert (onedrive / "Desktop" / "PanoSync" / "data").resolve() in found
    assert (onedrive / "Downloads" / "PanoSync (1)" / "data").resolve() in found
    assert (onedrive / "other" / "data").resolve() not in found
    assert len(found) == 2


def test_find_skips_install_without_data(data_dir, tmp_path):
    onedrive = tmp_path / "OneDrive"
    _make_install(onedrive, "PanoSync", with_data=False)
    assert storage.find_install_data_dirs(onedrive) == []


def test_find_excludes_active_data_root(monkeypatch, tmp_path):
    onedrive = tmp_path / "OneDrive"
    inst = _make_install(onedrive, "PanoSync", with_data=True)
    monkeypatch.setenv("PANOSYNC_DATA_DIR", str(inst / "data"))  # active == this data
    assert storage.find_install_data_dirs(onedrive) == []


def test_purge_data_dir_rescues_and_removes(data_dir, tmp_path):
    inst = _make_install(tmp_path, "PanoSync", with_data=True)
    (inst / "data" / "calibrations" / "k.json").write_text('{"pairs":[]}')

    report = storage.purge_data_dir(inst / "data")

    assert not (inst / "data").exists()
    assert (storage.calibrations_dir() / "k.json").exists()
    assert report["removed"] is True
    assert report["calibrations_migrated"] == 1
