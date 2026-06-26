r"""
PanoSync-Bereinigung — einmaliges Aufräum-Tool für mehrere heruntergeladene Kopien.

Hintergrund: Alte PanoSync-Builds haben ihre Bilddaten (Tiles) *in den
Programmordner* geschrieben. Lag PanoSync in einem OneDrive-Ordner, wurde jeder
einzelne Tile in die Cloud gespiegelt und nie gelöscht ("Tile-Flut"). Hat man
PanoSync mehrfach heruntergeladen, hat jede Kopie ihren eigenen data\-Ordner.

Dieses Tool durchsucht den OneDrive (bzw. übergebene Ordner) nach *allen*
PanoSync-Installationen und räumt in jeder den data\-Ordner weg. Gespeicherte
Kalibrierungen werden vorher in den neuen, cloud-sicheren Datenordner gerettet.
Das Löschen geschieht lokal an der Quelle — der OneDrive-Client überträgt es
danach nach oben, sodass die Dateien auch aus der Cloud verschwinden.

Bedienung (Endnutzer): Doppelklick auf "(MICROSOFT)PanoSync bereinigen.bat"
bzw. "(APPLE)PanoSync bereinigen.command".
Direkt:  python bereinigen.py [PFAD ...] [--yes]
  PFAD    optionale Suchordner (Standard: OneDrive-Ordner, sonst Benutzerordner)
  --yes   ohne Rückfrage löschen (für unbeaufsichtigte Ausführung)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow "python bereinigen.py" from the repo root to import the backend package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from backend import storage  # noqa: E402

# Make German output safe regardless of the Windows console code page.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def _summarize(data_dir: Path) -> tuple[int, int]:
    """Return (file_count, total_bytes) for a directory tree (best-effort)."""
    files = 0
    total = 0
    for _dirpath, _dirnames, filenames in os.walk(data_dir, onerror=lambda _e: None):
        for name in filenames:
            files += 1
            try:
                total += (Path(_dirpath) / name).stat().st_size
            except OSError:
                pass
    return files, total


def _search_roots(args: list[str]) -> list[Path]:
    explicit = [Path(a) for a in args if not a.startswith("-")]
    if explicit:
        return explicit

    roots: list[Path] = []
    for env in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer"):
        val = os.environ.get(env)
        if val:
            roots.append(Path(val))
    if not roots:
        roots.append(Path.home())
    return roots


def main(argv: list[str]) -> int:
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0

    assume_yes = "--yes" in argv or "-y" in argv
    roots = _search_roots(argv)

    print("PanoSync-Bereinigung")
    print("=" * 60)
    print(f"Neuer Datenordner (cloud-sicher): {storage.data_root()}")
    for r in roots:
        print(f"Durchsuche: {r}")
    print("Suche nach PanoSync-Installationen ... (kann etwas dauern)")
    print()

    # Collect all PanoSync data dirs across all roots, de-duplicated.
    seen: set[str] = set()
    data_dirs: list[Path] = []
    for root in roots:
        for d in storage.find_install_data_dirs(root):
            key = str(d.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            data_dirs.append(d)

    if not data_dirs:
        print("Keine alten PanoSync-Datenordner gefunden — nichts zu tun. ✔")
        return 0

    total_files = 0
    total_bytes = 0
    print(f"{len(data_dirs)} alte(r) Datenordner gefunden:")
    print()
    for d in data_dirs:
        files, size = _summarize(d)
        total_files += files
        total_bytes += size
        print(f"  • {d}")
        print(f"      {files:,} Dateien, {_human_size(size)}")
    print()
    print(f"Insgesamt: {total_files:,} Dateien, {_human_size(total_bytes)}")
    print()

    if not assume_yes:
        print("Diese Ordner werden gelöscht (Kalibrierungen werden vorher gesichert).")
        answer = input("Fortfahren? [j/N] ").strip().lower()
        if answer not in ("j", "ja", "y", "yes"):
            print("Abgebrochen — nichts wurde verändert.")
            return 1

    print()
    removed = 0
    rescued = 0
    for d in data_dirs:
        report = storage.purge_data_dir(d)
        if report["removed"]:
            removed += 1
            rescued += report["calibrations_migrated"]
            print(f"  ✔ entfernt: {d}")
        else:
            print(f"  ⚠ übersprungen (in Benutzung oder gesperrt): {d}")

    print()
    print("=" * 60)
    print(f"Fertig: {removed}/{len(data_dirs)} Ordner entfernt, "
          f"{rescued} Kalibrierung(en) gesichert nach {storage.calibrations_dir()}")
    print()
    print("Hinweis: Lasse OneDrive jetzt fertig synchronisieren — das Löschen "
          "wird in die Cloud übertragen. Prüfe danach den OneDrive-Papierkorb, "
          "falls Speicherplatz sofort frei werden soll.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
