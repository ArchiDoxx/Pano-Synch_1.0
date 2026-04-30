# OnsiteAI — PanoSync

**PanoSync** ist ein internes Analyse-Werkzeug von OnsiteAI zum synchronisierten Vergleich zweier Mikroskopie-Panoramen. Es erkennt automatisch Partikel auf beiden Scans und erlaubt präzise Navigation zwischen Original- und Kontrastaufnahme.

## Inhaltsverzeichnis
- [Voraussetzungen](#voraussetzungen)
- [Programm starten](#programm-starten)
- [⚠️ Wichtiger Hinweis zur Bildzuweisung](#️-wichtiger-hinweis-zur-bildzuweisung)
- [Wichtig während der Nutzung](#wichtig-während-der-nutzung)
- [Erste Schritte](#erste-schritte)
- [Kalibrierung](#kalibrierung)
- [Sync-Navigation](#sync-navigation)
- [Häufig gestellte Fragen (FAQ)](#häufig-gestellte-fragen-faq)
- [Bedienungsanleitung (Was macht welcher Button?)](#bedienungsanleitung-was-macht-welcher-button)
- [Fehlerbehebung](#fehlerbehebung)

---

## Voraussetzungen

- **Python 3.10 oder neuer** muss installiert sein.
FALL DER AUTOINSTALLER NICHT ALLES ERFOLGREICH INSTALLIER ODER FEHLER ANZEIGT:
  → Download: https://www.python.org/downloads/
  → Bei der Installation unbedingt **„Add Python to PATH"** aktivieren.
- Eine aktive Internetverbindung wird beim ersten Start benötigt (für die automatische Paketinstallation).

---

## Programm starten

### Windows
Doppelklick auf **`PanoSync starten.bat`** oder das pendante der "Command-Datei" bei MacOS

Das Programm installiert beim ersten Start automatisch alle notwendigen Komponenten. Anschließend öffnet sich der Browser automatisch.

### macOS
1. **Erstes Mal auf einem neuen Mac:** Rechtsklick auf **`PanoSync starten.command`** → „Öffnen" → „Öffnen" bestätigen.
2. **Ab dem zweiten Mal:** normaler Doppelklick funktioniert.

> Das einmalige Rechtsklick-Öffnen ist eine Apple-Sicherheitsmaßnahme (Gatekeeper) und lässt sich nicht umgehen.

---

## ⚠️ Wichtiger Hinweis zur Bildzuweisung

**PanoSync ist fest darauf ausgelegt, dass „Panorama B“ immer das Blau-Weiß-Blau (BWB) Bild sein muss.**
Da das System speziell für den Abgleich dieser Aufnahmen konzipiert wurde, ist es für die korrekte Verarbeitung und Synchronisierung zwingend erforderlich, dass die gefärbten BWB-Bilder konsequent in den Upload-Slot für Panorama B geladen werden. Bitte achten Sie darauf, diese Reihenfolge (*Pano A = unbefärbtes Original, Pano B = BWB-Kontrastbild*) in jedem Durchlauf exakt einzuhalten!

---

## Wichtig während der Nutzung

Das schwarze Terminal-Fenster muss **geöffnet bleiben**, solange PanoSync läuft — es ist der Server im Hintergrund. es ist das eigentliche Programm, das Browserfenster ist nur die sichbare Benutzeroberfläche (GUI)
Zum Beenden einfach das Terminal-Fenster schließen (GUI schließt NICHT automatisch, verliert aber seine funktion).

---

## Erste Schritte

1. **Start** → Browser öffnet sich automatisch mit der Upload-Seite.
2. **Panorama A** hochladen (Original, ungefärbt, grau).
3. **Panorama B** hochladen (BWB-Kontrast, gefärbt, blau).
4. **„Verarbeitung starten"** klicken — die Tile-Generierung dauert je nach Bildgröße einige Minuten.
5. Nach Abschluss öffnet sich automatisch der **Kalibrierungsbereich**.

---

## Kalibrierung

Um beide Panoramen zu synchronisieren, müssen mindestens **3 Referenzpunkt-Paare** gesetzt werden:

1. Klick auf **„Kalibrierung"** (oben rechts) um den Kalibrierungsmodus zu aktivieren.
2. Auf ein markantes Partikel in **Panorama A** klicken — ein blauer Chip erscheint.
3. Auf dasselbe Partikel in **Panorama B** klicken — das Paar ist gespeichert.
4. Mindestens 2 weitere Paare setzen, idealerweise über die gesamte Breite verteilt.
5. **„Neu berechnen"** klicken → RMSE-Wert und „TPS aktiv" erscheinen im Badge.
6. **„Speichern"** klicken → Kalibrierung wird gespeichert und beim nächsten Upload derselben Dateien automatisch wiederhergestellt.

**Tipp für hohe Genauigkeit:** Je mehr Referenzpaare, desto genauer die Synchronisation — besonders in Bereichen, in denen viele Partikel analysiert werden sollen.

---

## Sync-Navigation

- **„Sync-Modus"** aktivieren → Klick auf eine Position in Panorama A springt automatisch zur entsprechenden Position in Panorama B (und umgekehrt).
- **„Zoom-Sync"** aktivieren → beide Panoramen zoomen gemeinsam.
- **Escape** bricht einen halbfertigen Klick im Kalibrierungsmodus ab.
- **„Alle löschen"** entfernt alle gesetzten Referenzpaare.

---

## Häufig gestellte Fragen (FAQ)

**Wie werden Sessions und Bilder gespeichert?**
Über den Button *"Speichern"* in der oberen Leiste werden die gesetzten Punktpaare dauerhaft gesichert und mit den Dateinamen der hochgeladenen Bilder verknüpft. 

**Wie kann ich gespeicherte Bilder und Kalibrierungen wieder nutzen?**
Wenn Sie exakt dieselben Bilddateien (mit exakt demselben Dateinamen) auf der Startseite erneut hochladen, erkennt PanoSync diese und stellt alle zuvor gespeicherten Kalibrierungspunkte automatisch wieder her.

**Was bedeuten die Werte (z.B. 12px) unten in den Punktpaar-Chips?**
Das sind die *Residuums-Werte* (Abweichung in Pixeln). Ein kleiner Wert (grün) bedeutet, dass dieses Punktpaar sehr gut in die berechnete Synchronisation passt. Ein großer Wert (orange/rot) bedeutet, dass diese Punkte mathematisch abweichen (z.B. weil ein Punkt ungenau geklickt wurde). Klickt man auf das "✕" im Chip, kann man fehlerhafte Punkte löschen.

**Was ist "TPS" in der oberen Leiste und was macht es?**
TPS steht für *Thin Plate Spline*. Das ist eine fortgeschrittene Methode, die das Bild nicht nur starr übereinanderlegt, sondern es wie eine elastische Folie lokal minimal "verbiegt". So werden lokale Linsenverzerrungen oder Stitching-Fehler ausgeglichen.

**Sollte ich lieber mehr oder weniger Punkte für die Kalibrierung setzen?**
**Definitiv mehr!** TPS braucht mindestens 3 Punkte, um zu starten. Erst mit mehreren Punkten (z.B. 5-15 Stück) entfaltet TPS seine volle Stärke, da es die Bilder tief im Inneren lokal perfekt anpassen kann.

**Tipp für höchste Präzision:**
Um die besten Präzisionsergebnisse zu erzielen, müssen die Punkte über das gesamte Bild verteilt werden – **sowohl auf der X- als auch auf der Y-Achse**. Wenn Sie die Punkte als ein zweidimensionales Netz im gesamten zu analysierenden Bereich verteilen, kann PanoSync lokale Verzerrungen überall optimal ausgleichen. Setzen Sie die Punkte niemals nur auf einer flachen, horizontalen oder vertikalen Linie!

**Was bedeutet der "RMSE"-Wert oben in der Leiste?**
Dies ist der mittlere Fehler über alle Punkte (Root Mean Square Error). Ein niedrigerer Wert zeigt an, dass die Synchronisation insgesamt sehr nah an den gesetzten Punkten passgenau ist. 
*Wchtig:* **Mehr Punkte bei einem insgesamt etwas höheren RMSE-Wert sind fast immer besser, als sehr wenig Punkte mit einem niedrigen RMSE-Wert.**
Da das Bild riesig ist, bedeutet eine Kalibrierung mit nur wenigen Punkten: Sie ist zwar genau an diesen drei Klicks perfekt, aber weit abseits dieser Punkte sinkt die Präzision drastisch. Ein etwas höherer Fehlerwert bei deutlich mehr (und räumlich tiefer in die X/Y-Richtungen verteilten) Punkten bedeutet, dass die lokale Präzision im gesamten Bild absolut konstant und zuverlässig ist. **Merke: Mehr synchrone Punkte > als extrem niedrige Fehlerwerte.**

---

## Bedienungsanleitung (Was macht welcher Button?)

### Upload-Seite
- **Bilder-Boxen (Panorama A / B):** Klick öffnet ein Fenster zur Dateiauswahl von Ihrem Computer.
- **Verarbeitung starten:** Startet den Upload und generiert im Hintergrund hochauflösende Bildkacheln für ein flüssiges Zoomen in der Ansicht.

### Kalibrierungs-Seite (Obere Leiste)
- **Neu berechnen:** Wendet neu gesetzte oder gelöschte Punkte an und aktualisiert sofort die Synchronisations-Mathematik (und den RMSE-Wert).
- **Zoom-Sync (AN/AUS):** Wenn AN, sind die Vergrößerungsstufen gekoppelt. Zoomt man in einem Bild rein, zoomt das andere exakt im selben Maßstab mit.
- **Modus (Sync-Modus / Kalibrierung):** Wechselt das Verhalten beim Klick ins Bild.
  - *Kalibrierung:* Klick setzt einen neuen Referenzpunkt.
  - *Sync-Modus:* Klick wandert im anderen Bild exakt an dieselbe geografische Stelle.
- **Speichern:** Sichert die aktuellen Punktpaare permanent für zukünftige Uploads derselben Dateien.
- **Hilfe:** (Wird demnächst eingefügt) Ein Button, der direkt zu dieser Lese-Anleitung führt, um Fragen ohne Umwege zu beantworten.

### Kalibrierungs-Seite (Bildbetrachter & Werkzeuge)
- **− / + Buttons und %-Eingabe:** Heraus- oder Hineinzoomen. Man kann auch direkt eine Prozentzahl eingeben und Enter drücken.
- **Reset:** Setzt den Zoom für dieses Bild wieder auf die Gesamtansicht zurück.
- **Chip mit Nummer unten (Klick):** Lässt beide Bilder genau zu diesem Punktpaar springen, um es zu überprüfen.
- **✕ im Chip:** Löscht dieses spezifische Punktpaar.
- **✕ Alle löschen:** Leert sofort das gesamte Board von allen gesetzten Punkten.

---

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| Browser öffnet sich nicht | Manuell aufrufen: `http://localhost:8001` |
| „Port bereits belegt" | Programm nochmals starten — der alte Server wird automatisch beendet |
| Seite lädt nicht | Terminal-Fenster geöffnet? Server muss laufen |
| Kalibrierung sehr ungenau | Mehr Referenzpaare setzen, gleichmäßig über die Bildbreite verteilt |
| Altes Gerät, langsamer Start | Tile-Generierung bei großen Bildern kann 2–5 Minuten dauern — bitte warten |

---

*OnsiteAI´s PanoSync— Interne Analyse-Unterstützung by ArchiDoxx