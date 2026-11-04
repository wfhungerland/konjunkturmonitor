set -x
cp -r probe/kd /tmp/KONJUNKTURDATEN && cd /tmp/KONJUNKTURDATEN
python laufen.py; wc -l PEGEL_TAGESWERTE.csv WETTER_MONAT.csv
python laufen.py; wc -l PEGEL_TAGESWERTE.csv WETTER_MONAT.csv
echo "--- PEGEL letzte 5"; tail -5 PEGEL_TAGESWERTE.csv
echo "--- PEGEL Kopf"; head -3 PEGEL_TAGESWERTE.csv
echo "--- WETTER letzte 5"; tail -5 WETTER_MONAT.csv
echo "--- WETTER Kopf und 2010"; head -3 WETTER_MONAT.csv; grep "^2010;1;" WETTER_MONAT.csv
echo "--- Doppelte Pegel+Datum"; cut -d';' -f1,2 PEGEL_TAGESWERTE.csv | sort | uniq -d | wc -l
echo "--- LAUFPROTOKOLL"; cat LAUFPROTOKOLL.txt; ls -la
