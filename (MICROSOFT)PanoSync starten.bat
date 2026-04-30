@echo off
cd /d "%~dp0"

echo Starte PanoSync...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 goto trypy

echo Installiere/pruefe Abhaengigkeiten...
python -m pip install -r requirements.txt

echo Beende alten Server falls vorhanden...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

echo Server laeuft. Browser oeffnet sich gleich...
echo Dieses Fenster offen lassen. Zum Beenden: Fenster schliessen.
echo.
start /b powershell -NoProfile -Command "Start-Sleep 2; Start-Process 'http://localhost:8001'"
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
pause
exit

:trypy
py --version >nul 2>&1
if %errorlevel% neq 0 goto install_python

echo Installiere/pruefe Abhaengigkeiten...
py -m pip install -r requirements.txt

echo Beende alten Server falls vorhanden...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul

echo Server laeuft. Browser oeffnet sich gleich...
echo Dieses Fenster offen lassen. Zum Beenden: Fenster schliessen.
echo.
start /b powershell -NoProfile -Command "Start-Sleep 2; Start-Process 'http://localhost:8001'"
py -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
pause
exit

:install_python
echo.
echo FEHLER: Python wurde nicht gefunden. Starte automatische Installation...
curl -# -L -o python_installer.exe "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
start /wait python_installer.exe /passive InstallAllUsers=0 PrependPath=1 Include_test=0
del python_installer.exe

set "LOCAL_PYTHON=%LocalAppData%\Programs\Python\Python311\python.exe"
if exist "%LOCAL_PYTHON%" (
    echo Python erfolgreich installiert!
    
    echo Installiere/pruefe Abhaengigkeiten...
    "%LOCAL_PYTHON%" -m pip install -r requirements.txt
    
    echo Beende alten Server falls vorhanden...
    powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
    timeout /t 2 /nobreak >nul
    
    echo Server laeuft. Browser oeffnet sich gleich...
    echo Dieses Fenster offen lassen. Zum Beenden: Fenster schliessen.
    echo.
    start /b powershell -NoProfile -Command "Start-Sleep 2; Start-Process 'http://localhost:8001'"
    "%LOCAL_PYTHON%" -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
    pause
    exit
) else (
    echo.
    echo FEHLER: Python konnte nach der automatischen Installation nicht gefunden werden.
    echo Bitte lade dir Python manuell herunter: https://www.python.org/downloads/
    echo Bei der Installation "Add Python to PATH" aktivieren.
    pause
    exit
)
