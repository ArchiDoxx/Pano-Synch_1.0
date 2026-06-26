# Changelog

## [1.5] - 2026-06-26
- Datenverzeichnis wird cloud-sicher außerhalb des Programmordners angelegt.
- Automatische Bereinigung veralteter Sessions/Tiles/Uploads beim Start.
- Migration bestehender Daten aus dem alten Programmverzeichnis.
- GitHub Actions Workflow für Claude PR Assistant hinzugefügt.
- Cleanup-Tool (`bereinigen.py`) zum manuellen Aufräumen.

## [1.0] - Initialversion
- Upload zweier Panoramen (A = Original, B = BWB-Kontrast).
- Automatische DZI-Tile-Pyramidengenerierung.
- Affine Transformation und Thin-Plate-Spline-Kalibrierung.
- Persistente Kalibrierung pro Bildpaar.
- Synchroner Vergleich im Browser.
