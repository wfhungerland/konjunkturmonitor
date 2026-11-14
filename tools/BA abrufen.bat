@echo off
rem Zieht die BA-Regionalreports aller 400 Kreise und schreibt aufnahme_ba_kreise.csv nach C:\Daten\BA.
rem Doppelklick genügt. Braucht nur ein installiertes Python 3 (python.org).
setlocal
set ZIEL=C:\Daten\BA
set QUELLE=https://raw.githubusercontent.com/wfhungerland/konjunkturmonitor/claude/sweet-hypatia-at9ep0/monitor
set PYTHONUTF8=1

if not exist "%ZIEL%\monitor" mkdir "%ZIEL%\monitor"
cd /d "%ZIEL%"

echo Lade Skripte ...
curl -s -f -H "Cache-Control: no-cache" -o monitor\aufnahme.py %QUELLE%/aufnahme.py?frisch=%RANDOM%%RANDOM% || goto fehler
curl -s -f -H "Cache-Control: no-cache" -o monitor\aufnahme_kreise.py %QUELLE%/aufnahme_kreise.py?frisch=%RANDOM%%RANDOM% || goto fehler

set PY=py -3
%PY% --version >nul 2>&1 || set PY=python
%PY% --version >nul 2>&1 || (echo Python nicht gefunden. Bitte von python.org installieren. & goto ende)

echo Kreisliste ...
%PY% -m monitor.aufnahme_kreise kreise "%ZIEL%" || goto fehler
echo BA-Dateien, dauert mindestens zehn Minuten. Fenster offen lassen.
%PY% -m monitor.aufnahme_kreise ba "%ZIEL%" --stichtag 202603 --ziel "%ZIEL%" || goto fehler

echo.
echo Fertig: %ZIEL%\aufnahme_ba_kreise.csv
explorer "%ZIEL%"
goto ende

:fehler
echo.
echo Abbruch. Einfach noch einmal doppelklicken; schon geladene Dateien bleiben erhalten.

:ende
pause
