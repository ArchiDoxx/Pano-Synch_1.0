#!/bin/bash
chmod +x "$0"
cd "$(dirname "$0")"

echo "PanoSync-Bereinigung"
echo "Dieses Tool sucht alte PanoSync-Datenordner und räumt sie auf."
echo ""

if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo "FEHLER: Python wurde nicht gefunden."
    echo "Bitte zuerst PanoSync einmal über das Start-Skript ausführen"
    echo "oder Python installieren: https://www.python.org/downloads/"
    read -p "Beliebige Taste drücken zum Beenden..."
    exit 1
fi

$PY bereinigen.py

echo ""
read -p "Beliebige Taste drücken zum Beenden..."
