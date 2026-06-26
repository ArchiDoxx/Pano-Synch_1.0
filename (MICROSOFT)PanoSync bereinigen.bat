@echo off
cd /d "%~dp0"

echo PanoSync-Bereinigung
echo Dieses Tool sucht alte PanoSync-Datenordner in OneDrive und raeumt sie auf.
echo.

python --version >nul 2>&1
if %errorlevel% equ 0 (
    python bereinigen.py
    goto ende
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    py bereinigen.py
    goto ende
)

echo FEHLER: Python wurde nicht gefunden.
echo Bitte zuerst PanoSync einmal ueber das Start-Skript ausfuehren
echo (das installiert Python) oder Python manuell installieren:
echo https://www.python.org/downloads/

:ende
echo.
pause
