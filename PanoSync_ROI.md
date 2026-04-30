# PanoSync — Projektdarstellung nach STAR
*OnsiteAI · ArchiDoxx · Interne Analyse-Unterstützung*

---

## Situation

Ein Laborbetrieb analysiert Luftpartikel unter dem Mikroskop anhand zweier Panorama-Scans derselben Probe: einmal im Original (grau, ungefärbt) und einmal mit BWB-Kontrast (blau, gefärbt). Beide Scans entstehen in unterschiedlichen Auflösungen und mit unterschiedlichem Seitenverhältnis — Panorama A misst **38.232 × 2.560 px**, Panorama B **31.752 × 4.096 px**.

Die Herausforderung: Partikel müssen manuell zwischen beiden Scans verglichen werden. Bislang geschah das durch paralleles Scrollen in zwei separaten Bildbetrachtungsprogrammen — zeitaufwendig, fehleranfällig und ohne räumliche Zuordnung.

Erschwerend: Beide Panoramen sind aus einzelnen Streifen zusammengesetzt (Stitching), was zu lokalen Versatzfehlern führt, die sich mit globalen Transformationen nicht vollständig korrigieren lassen.

---

## Task

Gesucht war ein browserbasiertes Werkzeug, das:
- beide Gigapixel-Panoramen flüssig darstellbar macht (kein Download, kein Spezial-Viewer)
- einen Klick in Panorama A automatisch zur korrekten Position in Panorama B springt (und umgekehrt)
- lokale Stitching-Versätze kompensiert, nicht nur eine globale Verschiebung
- Kalibrierungsdaten persistent speichert, sodass dieselben Scans am nächsten Tag ohne Neueinrichtung nutzbar sind
- von nicht-technischen Mitarbeitenden per Doppelklick startbar ist

---

## Action

**Architektur-Entscheidung:** FastAPI (Backend) + OpenSeadragon (Tile-Viewer) + PIL (DZI-Tile-Generierung) — ohne Machine Learning, ohne OpenCV. Bewusst schlanke Abhängigkeiten für maximale Portabilität.

**Kernlösungen im Detail:**

- **Tile-Pyramide (DZI):** Beide Panoramen werden beim Upload in Deep-Zoom-Tiles zerlegt. OpenSeadragon rendert nur den sichtbaren Ausschnitt — auch 130-MB-Bilder laufen ohne Ruckeln.

- **Affine Transformation (6 Parameter):** Aus manuell gesetzten Referenzpunkt-Paaren wird per Least-Squares-Fitting eine globale Transformation berechnet. Liefert den RMSE-Fehler als Qualitätsindikator.

- **Thin-Plate Spline (TPS):** Da die affine Transformation Stitching-Artefakte nicht modellieren kann, wird zusätzlich eine nicht-parametrische TPS-Interpolation berechnet. Sie trifft jeden Referenzpunkt exakt und interpoliert glatt dazwischen — lokale Versätze werden damit korrekt kompensiert.

- **Virtuelle Gitteranker:** Um TPS-Extrapolationsdrift an den Bildrändern zu verhindern, werden automatisch ~130 virtuelle Ankerpunkte aus der kalibrierten affinen Transformation erzeugt (Raster ca. 1.500 px × 600 px über die gesamte Panoramafläche). Für den Benutzer unsichtbar, aber entscheidend für Randgenauigkeit.

- **Persistenz (AC4):** Kalibrierungen werden unter einem MD5-Schlüssel aus den Originaldateinamen gespeichert. Beim nächsten Upload derselben Scans wird die Kalibrierung automatisch wiederhergestellt — inklusive Toast-Benachrichtigung.

- **Launcher:** Plattformspezifische Starter (`PanoSync starten.bat` für Windows, `.command` für macOS) installieren Abhängigkeiten automatisch, räumen Port-Konflikte auf und öffnen den Browser — kein Terminal-Know-how erforderlich.

---

## Result

- **Alle 4 Abnahmekriterien (AC1–AC4) erfüllt** — von Upload bis persistenter Kalibrierung.
- **80–90 % der Scan-Streifen** werden mit dem Spitzenwerk der Positionsgenauigkeit von **~95 %** synchronisiert — ausreichend für die visuelle Partikel-Zuordnung.
- **Höchste Präzision** (nahezu pixelgenau) in Bereichen, in denen Referenzpaare gesetzt wurden — der Benutzer steuert Aufwand und Genauigkeit selbst.
- Startzeit per Doppelklick: **unter 30 Sekunden** (nach erster Paketinstallation).
- Tile-Generierung für 134-MB-Panoramen: **unter 5 Minuten**, danach flüssige Navigation im Browser ohne Wartezeit.
- **Keine externen Dienste, keine Cloud** — läuft vollständig lokal, datenschutzkonform.

---

*Werkzeuge: Python · FastAPI · OpenSeadragon · PIL · NumPy · TPS (Thin-Plate Spline) · DZI*
*Plattformen: Windows 11 · macOS*
