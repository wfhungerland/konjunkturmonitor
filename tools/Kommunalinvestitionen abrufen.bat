@echo off
rem Zieht die Kommunalfinanzen je Kreis aus der Regionaldatenbank nach C:\Daten\Regionalstatistik.
rem Braucht Python 3 und ein kostenloses Konto bei www.regionalstatistik.de (Benutzername und Passwort werden abgefragt).
setlocal
set ZIEL=C:\Daten\Regionalstatistik
set QUELLE=https://api.github.com/repos/wfhungerland/konjunkturmonitor/contents/monitor
set PYTHONUTF8=1

if not exist "%ZIEL%\monitor" mkdir "%ZIEL%\monitor"
cd /d "%ZIEL%"
echo Lade Skript ...
curl -s -f -H "Accept: application/vnd.github.raw" -o monitor\kommunal_invest.py "%QUELLE%/kommunal_invest.py?ref=claude/sweet-hypatia-at9ep0" || goto fehler

set PY=py -3
%PY% --version >nul 2>&1 || set PY=python
%PY% --version >nul 2>&1 || (echo Python nicht gefunden. Bitte von python.org installieren. & goto ende)

%PY% -m monitor.kommunal_invest abruf "%ZIEL%" || goto fehler
echo.
echo Fertig. Die CSV-Dateien liegen in %ZIEL%.
explorer "%ZIEL%"
goto ende

:fehler
echo.
echo Abbruch. Einfach noch einmal doppelklicken; fertige Tabellen werden übersprungen.

:ende
pause
