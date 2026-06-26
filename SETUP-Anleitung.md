# PanoSync — Update & Bereinigung (Setup-Anleitung)

Diese Anleitung richtet sich an alle, die PanoSync **bereits installiert** haben und auf
die neue Version aktualisieren möchten. Sie dauert wenige Minuten und braucht keine
Vorkenntnisse.

## Worum geht es?

Ältere PanoSync-Versionen haben ihre Bilddaten (viele kleine „Tiles") **direkt im
Programmordner** abgelegt. Wer PanoSync in einem **OneDrive-Ordner** gespeichert hat, bei
dem wurden diese Tausenden Einzeldateien in die Cloud hochgeladen und nie gelöscht — die
Cloud lief damit über.

Die neue Version behebt das:

- Sie speichert alle Bilddaten ab sofort in einem **lokalen Ordner außerhalb von OneDrive**
  (`%LOCALAPPDATA%\PanoSync` unter Windows / `~/Library/Caches/PanoSync` am Mac). Da spiegelt
  OneDrive nichts mehr in die Cloud.
- Sie **räumt die alten Bilddaten beim ersten Start automatisch weg** — gespeicherte
  Kalibrierungen bleiben dabei erhalten.

---

## Teil 1 — Update installieren

1. **Neues PanoSync herunterladen** (ZIP-Datei über den Link, den du von Lucas bekommen hast).
2. ZIP **entpacken** und den Inhalt **über deinen bestehenden PanoSync-Ordner kopieren**
   (vorhandene Dateien überschreiben/zusammenführen).

   > ⚠️ **Wichtig:** Bitte wirklich **über den alten Ordner** entpacken, nicht in einen neuen.
   > Nur so findet das Programm die alten Bilddaten und kann sie aufräumen.

3. PanoSync wie gewohnt starten:
   - **Windows:** Doppelklick auf **`(MICROSOFT)PanoSync starten.bat`**
   - **Mac:** Doppelklick auf **`(APPLE)PanoSync starten.command`**

Beim ersten Start erscheint im schwarzen Fenster kurz eine Zeile wie
„*Migration: alter Daten-Ordner … entfernt*". Das ist gewollt — die alten Tiles werden
gelöscht. Fertig.

> 💡 **Empfehlung:** Lege den PanoSync-Ordner am besten **außerhalb von OneDrive** ab
> (z. B. direkt unter `C:\PanoSync`). Nötig ist das nach dem Update nicht mehr, es ist aber
> sauberer.

---

## Teil 2 — Mehrere alte Kopien aufräumen (wichtig, wenn zutreffend)

**Hast du PanoSync mehrmals heruntergeladen** (z. B. mehrere Ordner in *Downloads*, auf dem
*Desktop*, „PanoSync (1)", „PanoSync (2)" …)? Dann hat **jede Kopie ihre eigenen alten
Bilddaten** in der Cloud. Der Auto-Start in Teil 1 räumt nur die *eine* Kopie auf, die du
gerade startest — die anderen bleiben.

Dafür gibt es ein eigenes Aufräum-Tool, das **alle** Kopien auf einmal findet und bereinigt:

1. **Windows:** Doppelklick auf **`(MICROSOFT)PanoSync bereinigen.bat`**
   **Mac:** Doppelklick auf **`(APPLE)PanoSync bereinigen.command`**
2. Das Tool durchsucht deinen OneDrive und **zeigt dir zuerst an**, welche alten Datenordner
   es gefunden hat und wie viele Dateien das sind. Es löscht **nichts** ohne deine Bestätigung.
3. Mit **`j`** + Enter bestätigen. Das Tool sichert deine Kalibrierungen und löscht dann die
   alten Daten.

Das kannst du gefahrlos ausführen — es löscht ausschließlich PanoSync-Bilddaten, keine
anderen Dateien, und deine gespeicherten Kalibrierungen bleiben erhalten.

---

## Danach: OneDrive synchronisieren lassen

Nach Teil 1 bzw. Teil 2 löscht dein Computer die alten Tiles lokal. **Lass OneDrive jetzt
einmal in Ruhe fertig synchronisieren** — dadurch verschwinden die Dateien auch aus der
Cloud. Wenn der Speicher sofort frei werden soll, leere zusätzlich den
**OneDrive-Papierkorb** (online unter „Papierkorb").

---

## Kurze Fragen & Antworten

**Verliere ich meine gesetzten Punktpaare / Kalibrierungen?**
Nein. Die werden vor dem Aufräumen automatisch in den neuen Datenordner gesichert. Lädst du
dieselben Bilddateien wieder hoch, sind die Punktpaare wieder da.

**Muss ich etwas an meinen Bildern ändern?**
Nein. Es ändert sich nur, *wo* PanoSync seine Zwischendaten ablegt.

**Das schwarze Fenster zeigt einen Fehler / Python fehlt.**
Starte einmal PanoSync über das normale Start-Skript — das installiert Python automatisch.
Danach funktioniert auch das Bereinigungs-Tool.

**Ich bin unsicher, ob ich mehrere Kopien habe.**
Führe einfach Teil 2 aus. Findet das Tool nichts, meldet es „nichts zu tun" — es kann nichts
kaputtmachen.
