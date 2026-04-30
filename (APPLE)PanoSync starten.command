#!/bin/bash
chmod +x "$0"
cd "$(dirname "$0")"

echo "Starte PanoSync..."
echo ""

# Python prüfen
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo "FEHLER: Python wurde nicht gefunden."
    echo "Bitte Python installieren: https://www.python.org/downloads/"
    echo 'Bei der Installation "Add Python to PATH" aktivieren.'
    read -p "Beliebige Taste drücken zum Beenden..."
    exit 1
fi

echo "Installiere/prüfe Abhängigkeiten..."
$PY -m pip install -r requirements.txt --quiet

echo "Beende alten Server falls vorhanden..."
lsof -ti:8001 | xargs kill -9 2>/dev/null
sleep 2

echo "Server läuft. Browser öffnet sich gleich..."
echo "Dieses Fenster offen lassen. Zum Beenden: Fenster schließen."
echo ""

# Browser nach 2 Sekunden öffnen
(sleep 2 && open "http://127.0.0.1:8001") &

$PY -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
