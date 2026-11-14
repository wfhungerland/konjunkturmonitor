@echo off
rem Holt frühere Ausgaben der BASt-Brückenstatistik aus dem Internet Archive nach C:\Daten\BASt.
rem Doppelklick genügt. Braucht nur ein installiertes Python 3 (python.org).
setlocal
set ZIEL=C:\Daten\BASt
set QUELLE=https://raw.githubusercontent.com/wfhungerland/konjunkturmonitor/claude/sweet-hypatia-at9ep0/monitor
set PYTHONUTF8=1

if not exist "%ZIEL%\monitor" mkdir "%ZIEL%\monitor"
cd /d "%ZIEL%"
echo Lade Skript ...
curl -s -f -o monitor\bruecken_archiv.py %QUELLE%/bruecken_archiv.py || goto fehler

set PY=py -3
%PY% --version >nul 2>&1 || set PY=python
%PY% --version >nul 2>&1 || (echo Python nicht gefunden. Bitte von python.org installieren. & goto ende)

%PY% -m monitor.bruecken_archiv "%ZIEL%" || goto fehler
echo.
echo Fertig: %ZIEL%\brueckenstatistik_staende.csv.gz
explorer "%ZIEL%"
goto ende

:fehler
echo.
echo Abbruch. Einfach noch einmal doppelklicken.

:ende
pause
