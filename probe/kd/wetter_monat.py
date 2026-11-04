"""Wetter: Monatsreihen für Deutschland vom Open-Data-Server des Deutschen Wetterdienstes (DWD).

Schreibt WETTER_MONAT.csv im selben Ordner bei jedem Lauf komplett neu.
Spalten: Jahr, Monat, Temperatur_C, Niederschlag_mm, Heizgradtage, Heiztage

Quellen (Dateinamen und Spaltenköpfe am Server geprüft am 4.11.2026):
- Temperatur: climate_environment/CDC/regional_averages_DE/monthly/air_temperature_mean/regional_averages_tm_MM.txt
- Niederschlag: climate_environment/CDC/regional_averages_DE/monthly/precipitation/regional_averages_rr_MM.txt
  Je Kalendermonat MM eine Datei, ab 1881, Trennzeichen Semikolon, Spalten Jahr;Monat;…;Deutschland;
  verwendet wird die Spalte „Deutschland“ (Gebietsmittel).
- Heizgradtage: climate_environment/CDC/derived_germany/techn/monthly/heating_degreedays/hdd_3807/
  historical/ und recent/, je Monat eine Datei gradtage_JJJJMM.csv, ab Januar 2010, je Station eine Zeile:
  ID; geogr. Breite; geogr. Laenge; Station; Monat; Anzahl Tage; Monatsgradtage; Anzahl Heiztage; Mittelwert …
  Gradtage nach VDI 3807, Raumtemperatur 20 °C, Heizgrenze 15 °C.
  Der DWD veröffentlicht dafür keinen Deutschlandwert. Heizgradtage und Heiztage sind hier das ungewichtete
  Mittel über alle Stationen mit gültigem Wert im jeweiligen Monat (Fehlwert -999.9 ausgeschlossen).
  Vor 2010 bleiben beide Spalten leer.
Nur Python-Standardbibliothek, keine Zusatzpakete nötig.
"""
from __future__ import annotations

import csv
import os
import re
import sys
import tempfile
import urllib.request
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
DATEI = ORDNER / "WETTER_MONAT.csv"
CDC = "https://opendata.dwd.de/climate_environment/CDC/"
REGIONAL = CDC + "regional_averages_DE/monthly/"
HDD = CDC + "derived_germany/techn/monthly/heating_degreedays/hdd_3807/"
SPALTEN = ["Jahr", "Monat", "Temperatur_C", "Niederschlag_mm", "Heizgradtage", "Heiztage"]


def text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Konjunkturdaten/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("latin-1")


def gebietsmittel(ordner: str, kuerzel: str) -> dict[tuple[int, int], float]:
    """(Jahr, Monat) -> Wert der Spalte Deutschland aus den zwölf Monatsdateien."""
    werte = {}
    for m in range(1, 13):
        zeilen = text(f"{REGIONAL}{ordner}/regional_averages_{kuerzel}_{m:02d}.txt").splitlines()
        kopf = next(i for i, z in enumerate(zeilen) if z.startswith("Jahr;"))
        spalten = [s.strip() for s in zeilen[kopf].split(";")]
        de = spalten.index("Deutschland")
        for z in zeilen[kopf + 1:]:
            f = [s.strip() for s in z.split(";")]
            if len(f) > de and f[0].isdigit() and f[de]:
                werte[(int(f[0]), int(f[1]))] = float(f[de])
    return werte


def heizgradtage() -> dict[tuple[int, int], tuple[float, float, int]]:
    """(Jahr, Monat) -> (mittlere Gradtage, mittlere Heiztage, Zahl der Stationen)."""
    out = {}
    for teil in ("historical/", "recent/"):
        dateien = sorted(set(re.findall(r'href="(gradtage_\d{6}\.csv)"', text(HDD + teil))))
        for d in dateien:
            gt, ht = [], []
            for z in text(HDD + teil + d).splitlines():
                if z.startswith("#") or not z.strip():
                    continue
                f = [s.strip() for s in z.split(";")]
                if len(f) < 8:
                    continue
                try:
                    g, h = float(f[6]), float(f[7])
                except ValueError:
                    continue
                if g >= 0 and h >= 0:
                    gt.append(g)
                    ht.append(h)
            if gt:
                jm = d[9:15]
                out[(int(jm[:4]), int(jm[4:]))] = (sum(gt) / len(gt), sum(ht) / len(ht), len(gt))
    return out


def zahl(x: float | None, stellen: int) -> str:
    return "" if x is None else f"{x:.{stellen}f}".replace(".", ",")


def lauf() -> dict:
    vorher = 0
    if DATEI.exists():
        with open(DATEI, encoding="utf-8-sig") as f:
            vorher = max(0, sum(1 for _ in f) - 1)
    tm = gebietsmittel("air_temperature_mean", "tm")
    rr = gebietsmittel("precipitation", "rr")
    hdd = heizgradtage()
    fd, tmp = tempfile.mkstemp(dir=ORDNER, prefix=".wetter_", suffix=".tmp")
    n = 0
    with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(SPALTEN)
        for jm in sorted(set(tm) | set(rr) | set(hdd)):
            g = hdd.get(jm)
            w.writerow([jm[0], jm[1], zahl(tm.get(jm), 2), zahl(rr.get(jm), 1),
                        zahl(g[0] if g else None, 1), zahl(g[1] if g else None, 1)])
            n += 1
    os.replace(tmp, DATEI)  # erst fertig schreiben, dann austauschen
    return {"neu": n - vorher, "gesamt": n, "fehler": []}


if __name__ == "__main__":
    e = lauf()
    print(f"Wetter: {e['neu']} neue Zeilen, {e['gesamt']} insgesamt")
    sys.exit(0)
