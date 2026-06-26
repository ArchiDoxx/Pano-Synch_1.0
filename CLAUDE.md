# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Was ist PanoSync

Lokales (Cloud-freies), browserbasiertes Tool von OnsiteAI für die Mikroskopie-Partikelanalyse. Es legt zwei Panorama-Scans derselben Probe übereinander — **Panorama A** (Original, grau) und **Panorama B** (BWB-Kontrast, gefärbt) — und ermöglicht synchronisierte Navigation: Klick in A springt zur korrespondierenden Stelle in B (und umgekehrt). Die Zuordnung wird aus manuell gesetzten Referenzpunkt-Paaren als **affine Transformation + Thin-Plate-Spline (TPS)** berechnet.

> **Domänen-Konstraint:** Panorama B ist immer das BWB-/blaue Bild. Dieser Constraint ist im UI und in der Bedienlogik fest verankert.

## Starten & Entwickeln

```bash
# Abhängigkeiten installieren
python -m pip install -r requirements.txt

# Server starten (MUSS aus dem Repo-Root laufen — siehe Gotchas)
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
# → http://localhost:8001
```

Endnutzer starten per Doppelklick auf `(MICROSOFT)PanoSync starten.bat` (Windows) bzw. `(APPLE)PanoSync starten.command` (macOS). Diese Skripte installieren Deps, beenden einen evtl. alten Listener auf Port 8001, öffnen den Browser und starten uvicorn. Port **8001** ist überall fest verdrahtet.

**Es gibt keine Tests und keinen Linter** im Repo (`requirements.txt` enthält weder pytest noch ruff). Manuelle Verifikation läuft über den laufenden Server im Browser.

## Architektur (Big Picture)

Klassische server-rendered Webapp ohne Build-Step. FastAPI-Backend + Jinja2-Templates; das gesamte Frontend-JS steht **inline** in den Templates, OpenSeadragon kommt per CDN.

### Backend (`backend/`, relative Imports → als Package)
- **`app.py`** — alle Routen + `_process_session` (asyncio-Background-Task). Definiert `app`.
- **`session.py`** — Session-State als JSON-Dateien unter `data/sessions/{uuid}.json` (`save/load/update/delete`).
- **`registration.py`** — die gesamte Mathematik: affine Anpassung (`np.linalg.lstsq`) + TPS-Fit/-Auswertung.
- **`pyramid.py`** — `generate_dzi`: erzeugt aus großen Bildern eine Deep-Zoom-Image-Kachelpyramide (PIL, 256er-Tiles, JPEG q85) für OpenSeadragon.
- **`storage.py`** — zentrale, cloud-sync-sichere Datenpfade (`%LOCALAPPDATA%` / `~/Library/Caches` / XDG, Override `PANOSYNC_DATA_DIR`) + `cleanup_stale()` (Startup-Aufräumen alter Sessions/Tiles/Uploads, >24 h) + `is_cloud_synced()` (Bereitstellungs-Warnung) + `migrate_legacy_data()` (Start-Migration: löscht den alten `<Programmordner>/data` an der Quelle, rettet vorher `calibrations`) + `purge_data_dir()`/`find_install_data_dirs()` (Bausteine für die Mehrkopien-Bereinigung). Siehe **„Das OneDrive-Tile-Flood-Problem"**.
- **`bereinigen.py`** (Repo-Root, eigenständiges CLI) + `(MICROSOFT/APPLE)PanoSync bereinigen.bat/.command` — einmaliges Aufräum-Tool: scannt OneDrive nach **allen** PanoSync-Installationen (Marker `backend/app.py`) und räumt jede `data/` (für mehrere heruntergeladene Kopien). Listet erst auf, löscht nur nach Bestätigung, rettet Kalibrierungen. Getestet in `tests/test_storage.py`.

### Frontend (`frontend/templates/`)
- **`upload.html`** — Upload zweier Bilder, pollt `/api/status` und leitet bei `ready` nach `/calibrate/{id}` weiter.
- **`calibrate.html`** — Kern-UI (813 Z.): zwei OpenSeadragon-Viewer, Punktpaar-Setzen, Sync-/Zoom-Sync-Modus, SVG-Overlays.
- **`hilfe.html`** — rendert `README-Anleitung.md` (von `/hilfe` zur Laufzeit als Markdown → HTML).

### Datenfluss (eine Session)
1. `POST /api/upload` speichert `panoA.png`/`panoB.png`, legt Session an, prüft auf gespeicherte Kalibrierung (s. u.) und startet `_process_session` als Background-Task. Antwort: `session_id`.
2. Background: `generate_dzi` für A und B → `initial_transform` (reines Skalieren) → speichert `width/height`, `transform`, 5 verteilte `suggestions`; Status wird `ready`.
3. Frontend pollt `GET /api/status/{id}` (In-Memory-`processing_status`-Dict) bis `ready`, dann Redirect zur Kalibrierseite.
4. Nutzer setzt ≥3 Punktpaare → `POST /api/calibrate/{id}` → `compute_transform` liefert affine Parameter **inkl. vorberechneter TPS-Gewichte** zurück.
5. Das Frontend wertet die Transformation **clientseitig** aus (`applyFwd`/`applyInv` in `calibrate.html`) für jede Sync-Navigation.
6. `POST /api/calibration/persist/{id}` sichert die Kalibrierung dateinamen-basiert (s. u.).

## Zentrale Verträge & nicht-offensichtliche Punkte

**Das `transform`-Dict ist der Dreh- und Angelpunkt.** Form: `{a,b,tx,c,d,ty, inv_a…inv_ty, rmse, residuals, tps}`. `tps` ist ein verschachteltes Dict vorberechneter Gewichte (`fwd_cx/fwd_wx/fwd_ax`, `inv_*`). Es wird in `registration.py` erzeugt und an **drei** Stellen konsumiert: in `app.py` (Suggestions) und in `calibrate.html`-JS (`applyFwd`/`applyInv`).

**Die TPS-Auswertung ist doppelt implementiert.** Python `_compute_tps`/`_fit_tps_axis`/`_tps_kernel` (Fit) und JS `_tpsApply` (Auswertung) müssen mathematisch konsistent bleiben — beide nutzen den Radialkern `U(r²) = r²·log(r²)`. Ändert man die eine Seite, muss die andere mit. Affine = globaler Fit (für RMSE-Anzeige + Eckanker); TPS = lokale Interpolation, die die per-Streifen-Stitching-Versätze ausgleicht, indem die Nutzerpaare um ein **dichtes virtuelles Anker-Gitter** (aus der Affine berechnet) ergänzt werden, damit TPS an den Bildrändern fixiert ist.

**Zwei Koordinatensysteme:** Bildkoordinaten (Pixel) vs. OpenSeadragon-Viewport-Koordinaten. Alle Marker werden in Bildkoordinaten gehalten und pro Frame über `imageToViewportCoordinates` neu gezeichnet. Pan-/Zoom-Sync benutzt gerichtete Locks (`lockAtoB`/`lockBtoA`) gegen Feedback-Schleifen.

**Persistenz / Wiederherstellung:** Kalibrierungen liegen unter `data/calibrations/{key}.json`, wobei `key = md5("nameA|||nameB")[:16]` aus den **Original-Dateinamen**. Lädt man exakt dieselben Dateinamen erneut hoch, werden Punktpaare + Transformation automatisch restauriert.

**Laufzeit-State:** Alle erzeugten Daten liegen seit dem Cloud-Safe-Fix in einem **nutzer-lokalen** Verzeichnis außerhalb jeder Cloud-Sync (`%LOCALAPPDATA%\PanoSync` / `~/Library/Caches/PanoSync`, Override `PANOSYNC_DATA_DIR`) — aufgelöst in `backend/storage.py`, **nicht** mehr im Programmordner. `tiles`/`uploads`/`sessions` werden beim Serverstart aufgeräumt (älter als 24 h); `calibrations` bleiben dauerhaft. `processing_status` ist nur In-Memory und geht beim Neustart verloren.

## Das OneDrive-Tile-Flood-Problem (das Live-Problem — Root-Cause & Fix)

**Das prägendste Live-Problem dieses Projekts. Wer hier etwas an `storage.py`/`pyramid.py`/Start-Skripten ändert, muss diese Story kennen.**

**Symptom:** Die Firmen-Cloud (OneDrive/SharePoint von OnsiteAI) füllte sich mit **500K+ Tile-Einzelbildern**, die nach dem Löschen **immer wieder zurückkehrten** — auffällig: alle mit **demselben Uploaddatum**.

**Root-Cause (vollständig geklärt 2026-06):**
1. Mind. eine Nutzerin hatte den **kompletten PanoSync-Programmordner im OneDrive/SharePoint** liegen und startete die `.bat` **direkt von dort**.
2. Altes PanoSync schrieb seine DZI-Tiles nach `<Programmordner>/data/tiles/...`. Liegt der Programmordner im Sync-Bereich, spiegelt OneDrive **jeden** Tile in die Cloud.
3. Jeder Upload erzeugt einen **kompletten neuen** Tile-Satz unter neuer Session-UUID; altes PanoSync **räumte nie auf** → unbegrenztes Anhäufen über Monate → die 500K. (Kein Schreib-Bug — **korrekte Tiles, falscher Ort, viele Male, kein Cleanup**.)
4. **Wiederkehr nach dem Löschen:** **PanoSync hat keinerlei Netzwerk-/Cloud-/Upload-Code** — es schreibt nur lokale Dateien. Es kann sich also **nicht selbst** „wieder hochladen". Die Wiederkehr ist reines **OneDrive/SharePoint-Sync-Verhalten**: ein Sync-Client hält die Dateien noch **lokal** und schiebt sie nach dem zentralen Löschen wieder hoch („alle vom selben Datum" = der Tag, an dem diese Maschine wieder synchron war).

**Fix (umgesetzt, getestet — `tests/test_storage.py`, 21 Tests):**
- **Schreibort entkoppelt:** `storage.data_root()` → alle Daten nach `%LOCALAPPDATA%\PanoSync` (Win) / Caches (Mac) / XDG (Linux), **unabhängig vom Programmort**. Selbst beim Start **aus** dem Cloud-Ordner landet **nichts Neues** mehr in der Cloud.
- **`cleanup_stale()`** beim Start: sessions/tiles/uploads >24 h weg; `calibrations` bleiben.
- **`migrate_legacy_data()`** beim Start: löscht den alten `<Programmordner>/data` **an der Quelle** (Kalibrierungen vorher gerettet) → die Löschung **synct nach oben**. ⇒ Die neue Version **aus demselben Cloud-Ordner** zu starten = **Selbstheilung** für genau dieses Szenario.
- **`bereinigen.py`** + Doppelklick-Wrapper: für den Fall **mehrerer heruntergeladener Kopien** — scannt OneDrive nach allen Installationen und räumt jede `data/`.
- **`SETUP-Anleitung.md`:** Endnutzer-Doku (Update + Bereinigung) für die betroffene Kollegin.

**Diagnose-Hinweis für die Zukunft:** Der direkte Cloud-Zugriff per Microsoft-Graph/SharePoint-API ist **nicht autonom möglich** — der Verursacher-Account (`Lucas.Voehringer@onsite.ai`) ist nur **Gast** im onsiteai-Tenant (`cb428c53…`); `Sites.Read.All` braucht **Admin-Consent** (nur der CEO). Die Diagnose lief deshalb über die **SharePoint-Web-UI-Metadaten** („Geändert von" / Versionsverlauf). Zur Bestätigung des re-uploadenden Geräts: „Geändert von" einer wiedergekehrten Datei prüfen.

**Status (2026-06-26):** Fix-Code fertig + grün, aber **noch nicht committet** und **noch nicht an die Kollegin verteilt**. Nächste Schritte: Branch + Commit (kein direkter `main`-Push), ZIP/Release, Kollegin lässt neue Version **über den alten Cloud-Ordner** laufen.

## Gotchas

- **Immer aus dem Repo-Root als Modul starten** (`python -m uvicorn backend.app:app …`). `backend/` nutzt relative Imports (`from .session import …`); `python backend/app.py` schlägt fehl.
- Das Datenverzeichnis ist **nicht** der Programmordner, sondern `storage.data_root()` (`%LOCALAPPDATA%`/Caches). Beim Debuggen von Tiles/Sessions dort suchen, nicht im Repo.
- Mindestens **3 Punktpaare** sind Pflicht (`/api/calibrate` gibt sonst 400).
- DZI-Deskriptor deklariert `Format="jpeg"`; Kachel-Endung und -Format müssen zusammenpassen, wenn an `pyramid.py` etwas geändert wird.

## Backlog / geplante Folgearbeiten

- **On-the-fly-Tiles (Ticket D):** Kacheln nicht mehr als Dateien schreiben, sondern zur Laufzeit aus dem Original servieren (`/tiles/.../{level}/{col}_{row}.jpeg` → on demand). Eliminiert die Einzeldatei-Flut vollständig (nichts, was Cloud-Sync je spiegeln könnte) und spart Disk-I/O. Größerer Umbau an `pyramid.py` + neuem Serving-Endpoint.
- **Distribution als Single-Binary (Ticket C):** PanoSync via PyInstaller als eine `.exe` ausliefern (Daten weiter in LOCALAPPDATA), Bereitstellung über GitHub/SharePoint-ZIP — senkt das Risiko, dass der ganze Quellbaum in einem Sync-Ordner landet.
- **✅ Gelöst — Schritt 2 (Cloud-Bereinigung):** Warum kehren die Tiles nach dem Löschen zurück? → **Geklärt:** Programm lief aus dem Cloud-Ordner; Wiederkehr = Sync-Client mit lokaler Kopie schiebt nach jedem zentralen Löschen wieder hoch (PanoSync selbst hat keinen Upload-Code). Vollständige Analyse + Fix siehe **„Das OneDrive-Tile-Flood-Problem"**. Operativer Rest: neue Version auf dem/den betroffenen Gerät(en) laufen lassen bzw. `bereinigen.py`, dann zentral löschen.
