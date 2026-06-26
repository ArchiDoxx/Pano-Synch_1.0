# PanoSync — Agenten-Anleitung

> Diese Datei richtet sich an KI-Coding-Agenten, die am PanoSync-Projekt arbeiten. Sie basiert ausschließlich auf dem tatsächlichen Projektinhalt.

---

## 1. Projektübersicht

**PanoSync** ist ein lokal laufendes, browserbasiertes Analyse-Werkzeug von OnsiteAI für Mikrobiolog:innen. Es synchronisiert zwei Mikroskopie-Panorama-Scans derselben Probe:

- **Panorama A:** Original/ungefärbt (grau)
- **Panorama B:** BWB-Kontrast/gefärbt (blau)

Kernziel: Ein Klick in Panorama A springt automatisch zur korrespondierenden Position in Panorama B (und umgekehrt), trotz lokaler Stitching-Versätze zwischen den beiden Scans.

### Wichtige Randbedingungen

- **Lokale Anwendung ohne Cloud:** Das Tool läuft vollständig lokal (`127.0.0.1:8001`).
- **Panorama B ist immer das BWB-Bild:** Diese Zuordnung ist fest im Workflow verankert.
- **Keine Authentifizierung:** Das System ist für den lokalen Einzelnutzerbetrieb gedacht.
- **Keine automatischen Tests vorhanden:** Das Projekt verfügt aktuell über kein Test-Setup.

---

## 2. Technologie-Stack

### Backend

- **Python 3.10 oder neuer**
- **FastAPI** — Web-Framework
- **Uvicorn** — ASGI-Server
- **Pillow (PIL)** — Bildverarbeitung und DZI-Tile-Generierung
- **NumPy** — Numerik für affinierte Transformation und Thin-Plate-Spline (TPS)
- **Pydantic** — Request-Validierung
- **Jinja2** — Template-Rendering
- **python-multipart** — Datei-Uploads
- **markdown** — Rendern der Hilfeseite aus `README-Anleitung.md`

### Frontend

- **Vanilla JavaScript** (kein Build-Step, kein Framework)
- **OpenSeadragon 4.1.1** (via CDN) — Deep-Zoom-Bildbetrachter für die DZI-Kacheln
- **HTML + CSS** — Direkt in den Templates unter `frontend/templates/`

### Bildformate

Unterstützte Upload-Formate: `.png`, `.jpg`, `.tif`, `.tiff`

---

## 3. Projektstruktur

```
Pano-Synch_1.0/
├── backend/                    # Python-Backend
│   ├── __init__.py             # Leer
│   ├── app.py                  # FastAPI-App, Endpunkte, Routing
│   ├── pyramid.py              # DZI-Tile-Pyramiden-Generierung mit PIL
│   ├── registration.py         # Affine Transformation + Thin-Plate-Spline
│   └── session.py              # JSON-basierte Session-Persistenz
├── frontend/
│   ├── static/
│   │   └── onsite-logo.jpg     # Logo
│   └── templates/
│       ├── upload.html         # Startseite mit Bild-Upload
│       ├── calibrate.html      # Kalibrierungs- und Sync-Oberfläche
│       └── hilfe.html          # Hilfeseite (rendert README-Anleitung.md)
├── data/                       # Wird zur Laufzeit angelegt
│   ├── uploads/                # Hochgeladene Originalbilder
│   ├── tiles/                  # Generierte DZI-Kacheln
│   ├── sessions/               # Session-JSON-Dateien
│   └── calibrations/           # Persistierte Kalibrierungen
├── requirements.txt            # Python-Abhängigkeiten
├── (MICROSOFT)PanoSync starten.bat   # Windows-Doppelklick-Starter
├── (APPLE)PanoSync starten.command   # macOS-Doppelklick-Starter
├── README.md                   # Englische Projektbeschreibung
├── README-Anleitung.md         # Deutsche Bedienungsanleitung
├── PanoSync_ROI.md             # Projektdarstellung nach STAR
└── Licence/PanoSync_LICENSE.md # Lizenz
```

---

## 4. Starten und Ausführen

### Für Endnutzer (empfohlen)

- **Windows:** Doppelklick auf `(MICROSOFT)PanoSync starten.bat`
- **macOS:** Rechtsklick → „Öffnen" auf `(APPLE)PanoSync starten.command`

Die Starter erledigen automatisch:

1. Prüfung/Installation der Python-Abhängigkeiten (`pip install -r requirements.txt`)
2. Beenden eines bereits laufenden Servers auf Port 8001
3. Starten des Uvicorn-Servers
4. Öffnen des Browsers unter `http://localhost:8001`

### Für Entwickler (manuell)

```bash
# Abhängigkeiten installieren
python -m pip install -r requirements.txt

# Server starten
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Anschließend im Browser: `http://localhost:8001`

### Hinweise zum Betrieb

- Das Terminal-Fenster muss geöffnet bleiben, solange PanoSync läuft.
- Der Browser ist nur die GUI; der Server läuft im Terminal.
- Bei „Port bereits belegt": Starter erneut ausführen — der alte Prozess wird beendet.

---

## 5. Code-Organisation und Hauptmodule

### `backend/app.py`

FastAPI-Hauptanwendung. Zuständigkeiten:

- Servieren von Static Files (`/static`, `/tiles`)
- HTML-Seiten: `/`, `/hilfe`, `/calibrate/{session_id}`
- API-Endpunkte:
  - `POST /api/upload` — Bilder empfangen, Session anlegen, DZI-Generierung im Hintergrund starten
  - `GET /api/status/{session_id}` — Verarbeitungsstatus abfragen
  - `GET /api/session/{session_id}` — Session-Daten laden
  - `POST /api/calibrate/{session_id}` — Transformation aus Referenzpunktpaaren berechnen
  - `POST /api/calibration/persist/{session_id}` — Kalibrierung persistieren
- Wiederherstellung gespeicherter Kalibrierungen anhand eines MD5-Schlüssels aus den Originaldateinamen

### `backend/pyramid.py`

- Generiert Deep-Zoom-Image-(DZI-)Pyramiden aus hochaufgelösten Bildern.
- Erzeugt `.dzi`-Deskriptoren und JPEG-Kacheln pro Zoom-Level.
- Verwendet `PIL.Image.LANCZOS` für das Downsampling.
- Entlädt `Image.MAX_IMAGE_PIXELS`, um sehr große Bilder zu erlauben.
- Parameter: `tile_size=256`, `overlap=1`, JPEG-Qualität `85`.

### `backend/registration.py`

Mathematischer Kern der Synchronisation:

- **Affine Transformation (6 Parameter):** Least-Squares-Fit aus mindestens 3 Punktpaaren. Liefert Parameter `a, b, tx, c, d, ty`, Inverse, RMSE und Residuen pro Punktpaar.
- **Thin-Plate-Spline (TPS):** Nicht-parametrische Interpolation, die jedes Referenzpaar exakt trifft und lokalen Stitching-Versatz ausgleicht.
- **Virtuelle Gitteranker:** Automatisch generierte Ankerpunkte (Raster ca. 1500 px × 600 px) aus der affinen Transformation, um TPS-Extrapolationsdrift an den Bildrändern zu verhindern.
- `initial_transform(w_a, h_a, w_b, h_b)` — initiale Skalierung beim ersten Upload.

### `backend/session.py`

Einfache JSON-basierte Session-Persistenz unter `data/sessions/{session_id}.json`.

Funktionen: `new_session_id`, `save_session`, `load_session`, `update_session`, `delete_session`.

---

## 6. Build-, Test- und Deployment-Prozess

### Build-Prozess

- **Kein Build-Step** für Frontend oder Backend erforderlich.
- Backend wird direkt mit Uvicorn ausgeführt.
- Frontend-Templates werden serverseitig mit Jinja2 gerendert.

### Tests

- **Aktuell sind keine automatisierten Tests vorhanden.**
- Es gibt kein `pytest`, kein `tox`, keine Test-Dateien und keine CI-Konfiguration.
- Wenn Tests hinzugefügt werden sollen, empfiehlt sich:
  - `pytest` für `backend/registration.py` (affine Transformation + TPS)
  - `pytest`/`httpx` für die FastAPI-Endpunkte
  - Manuelle End-to-End-Tests über die Browser-Oberfläche

### Deployment

- **Kein formelles Deployment.**
- Verteilung erfolgt durch Kopieren des Projektordners plus Doppelklick-Start.
- Keine Containerisierung, kein Cloud-Deploy, keine CI/CD-Pipeline.

---

## 7. Code-Style-Richtlinien

Bisher gibt es **keine formalisierten Linter-/Formatter-Konfigurationen** (kein `pyproject.toml`, `.flake8`, `.black`, `ruff.toml` o. Ä.). Befolge beim Bearbeiten folgende Konventionen, die sich aus dem bestehenden Code ergeben:

- **Sprache:** Kommentare, Docstrings und User-facing-Texte auf **Deutsch**. Code-Bezeichner auf Englisch.
- **Formatierung:** 4 Leerzeichen Einrückung, ca. 100 Zeichen Zeilenlänge.
- **Benennung:**
  - Funktionen/Variablen: `snake_case`
  - Module: `snake_case`
  - Konstanten: `UPPER_SNAKE_CASE` (wo vorhanden)
- **Docstrings:** Modul- und Funktions-Docstrings in dreifachen Anführungszeichen.
- **Imports:** Standardbibliothek zuerst, dann Drittanbieter, dann eigene Module.
- **Dateigröße:** Backend-Module sind bewusst klein gehalten (< 300 Zeilen).
- **Keine Magic Numbers:** Werte wie Tile-Größe, Overlap oder JPEG-Qualität sollten als benannte Konstanten definiert werden, wenn sie hinzugefügt oder geändert werden.
- **Explizites Error-Handling:** Fehler im Backend sollten nicht still verschluckt werden (siehe `app.py` `_process_session` als Vorbild).

---

## 8. Testing-Anleitung

Da keine Tests existieren, hier das empfohlene Vorgehen für manuelle und zukünftige automatisierte Tests:

### Manuelle Tests

1. Server starten (`PanoSync starten.bat`/`.command` oder `uvicorn`).
2. Zwei Test-Panoramen hochladen (Pano A = grau, Pano B = blau/BWB).
3. Warten, bis die Tile-Generierung abgeschlossen ist (Progress-Bar auf 100 %).
4. Mindestens 3 Referenzpunktpaare setzen und „Neu berechnen" klicken.
5. RMSE anzeigen lassen, TPS prüfen.
6. „Speichern" klicken, Server neu starten, dieselben Bilder erneut hochladen → Kalibrierung muss wiederhergestellt werden.
7. Sync-Modus testen: Klick in A springt zu B und umgekehrt.

### Zukünftige automatisierte Tests (Empfehlung)

- **Unit-Tests für `registration.py`:**
  - Affine Transformation mit 3+ bekannten Punktpaaren
  - Inverse Transformation
  - RMSE-Berechnung
  - TPS mit synthetischen Daten
  - Verhalten bei < 3 Paaren (Fehler)
- **API-Tests für `app.py`:**
  - Upload kleiner Testbilder
  - Session-Abruf
  - Kalibrierungs-Endpunkt
  - Persistenz der Kalibrierung
- **Fail-safe-Tests:**
  - Session-ID nicht gefunden → 404
  - Korrupte Kalibrierungs-JSON → graceful ignore

---

## 9. Sicherheitsaspekte

- **Lokaler Betrieb:** Der Server bindet sich an `127.0.0.1:8001` und ist nicht aus dem Netzwerk erreichbar.
- **Keine Authentifizierung/Autorisierung:** Nicht für Multi-User- oder Internet-Betrieb geeignet.
- **Datei-Uploads:** Hochgeladene Bilder werden im lokalen `data/uploads/`-Verzeichnis gespeichert. Es findet keine Dateityp-Validierung über die Dateiendung hinaus statt.
- **MD5 für Kalibrierungsschlüssel:** In `app.py` wird MD5 verwendet, um aus den beiden Originaldateinamen einen stabilen Schlüssel zu erzeugen. Dies ist hier kein Sicherheitsmerkmal, sondern dient der einfachen Wiedererkennung derselben Bildpaare.
- **Externer CDN-Import:** OpenSeadragon wird aus dem öffentlichen jsDelivr-CDN geladen. Bei Offline-Nutzung muss diese Abhängigkeit lokal bereitgestellt werden.
- **Prozess-Terminierung:** Die Starter-Skripte beenden Prozesse auf Port 8001 mit `kill -9` bzw. `Stop-Process -Force`. Achte darauf, dass keine anderen wichtigen Dienste auf diesem Port lauschen.

---

## 10. Wichtige Dateien für Agenten

| Datei | Zweck |
|-------|-------|
| `README-Anleitung.md` | Deutsche Bedienungsanleitung, wird von `/hilfe` gerendert |
| `PanoSync_ROI.md` | Projekt-Kontext, Architektur-Entscheidungen, Abnahmekriterien |
| `requirements.txt` | Python-Abhängigkeiten |
| `(MICROSOFT)PanoSync starten.bat` | Windows-Startskript |
| `(APPLE)PanoSync starten.command` | macOS-Startskript |
| `backend/app.py` | FastAPI-Hauptanwendung |
| `backend/registration.py` | Transformations- und TPS-Mathematik |
| `backend/pyramid.py` | DZI-Tile-Generierung |
| `backend/session.py` | JSON-Session-Store |

---

## 11. Häufige Änderungsszenarien

- **API-Änderungen:** FastAPI-Endpunkte in `backend/app.py` anpassen; Frontend-Templates unter `frontend/templates/` bei Breaking Changes mitziehen.
- **Transformationslogik:** Änderungen an affiner Transformation oder TPS ausschließlich in `backend/registration.py`.
- **Bildverarbeitung:** Tile-Größe, Overlap, Qualität oder Format in `backend/pyramid.py`.
- **UI/UX:** Änderungen an den HTML-Templates; beachte, dass `calibrate.html` OpenSeadragon-Initialisierung und Sync-Logik enthält.
- **Neue Features mit Persistenz:** Session-Daten in `backend/session.py` speichern; langfristige Kalibrierungen unter `data/calibrations/`.

---

*Zuletzt aktualisiert auf Basis des Projektstands Pano-Synch_1.0.*
