"""Sanierungsbedarf der Kreise, Baustein Kommunalinvestitionen: Sachinvestitionen je Kreis auf heutigem Gebietsstand.

Quellen (Regionaldatenbank, mit Konto; Abruf: monitor.kommunal_invest):
  71517-02-03-4  Kassenstatistik 1995 bis 2014, Gemeinden je Kreis: Ausgaben für Sachinvestitionen (Vermögenshaushalt)
  71517-04-02-4  dasselbe für die Kreise (Kreishaushalte)
  71717-Z-05     Rechnungsergebnisse 2018 bis 2025, Gemeinden und Gemeindeverbände: Auszahlungen für
                 Investitionstätigkeit (wird je Kreis aus den ersten fünf Stellen des Schlüssels summiert)

Gebietsstand: Die Kassenstatistik nennt die Kreise des jeweiligen Jahres. Die Umsteigeschlüssel des BBSR
(ref-kreise-1990-2024.xlsx, bevölkerungsproportional, Stand jeweils 31.12.) führen jeden Kreis Jahr für Jahr
auf den Stand 31.12.2024. 2015 bis 2017 fehlen in der Regionaldatenbank. Die Stadtstaaten Berlin, Hamburg und
Bremen fehlen (keine Kommunalhaushalte), ebenso Ämter, Verbandsgemeinden und Zweckverbände: Die Summe liegt deshalb
unter den Sachinvestitionen aller Kommunen.

    python -m monitor.sanierung_kommunal <ordner> [--ziel data/static]

Erwartet im Ordner die entpackten flachen CSV-Dateien (Namen beginnen mit dem Tabellencode) und die BBSR-Datei.
Schreibt sanierung_kommunal.csv im Langformat (ags, jahr, ebene, merkmal, eur). Braucht openpyxl für die BBSR-Datei.
"""
from __future__ import annotations

import argparse
import csv
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

BBSR = ("https://www.bbsr.bund.de/BBSR/DE/forschung/raumbeobachtung/Raumabgrenzungen/umstiegsschluessel/"
        "ref-kreise-1990-2024.xlsx?__blob=publicationFile&v=3")
ZIELSTAND = 2024


def umsteiger(xlsx: Path) -> dict[int, dict[str, list[tuple[str, float]]]]:
    """Je Jahr: Kreis (5 Stellen) -> [(Kreis im Folgejahr, Anteil)], bevölkerungsproportional."""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    aus = {}
    for blatt in wb.sheetnames:
        try:
            von, bis = (int(x) for x in blatt.split("-"))
        except ValueError:
            continue
        m = defaultdict(list)
        for r in list(wb[blatt].iter_rows(values_only=True))[1:]:
            if not r or len(r) < 9 or r[0] is None or r[8] is None or not str(r[0]).strip().isdigit():
                continue
            alt, neu = f"{int(r[0]) // 1000:05d}", f"{int(r[8]) // 1000:05d}"
            m[alt].append((neu, float(r[3] if r[3] is not None else 1)))
        aus[von] = m
    return aus


def auf_zielstand(kreis: str, jahr: int, schluessel: dict) -> list[tuple[str, float]]:
    """Kreis eines Jahres (Stand 31.12.) auf den Stand 31.12.2024, als Anteile."""
    teile = [(kreis, 1.0)]
    for j in range(jahr, ZIELSTAND):
        m = schluessel.get(j, {})
        neu = defaultdict(float)
        for k, a in teile:
            for k2, a2 in m.get(k, [(k, 1.0)]):
                neu[k2] += a * a2
        teile = list(neu.items())
    return teile


def lies_71517(datei: Path, ebene: str) -> list[tuple[str, int, str, float]]:
    """Sachinvestitionen je Kreis und Jahr aus der flachen CSV der Kassenstatistik."""
    aus = []
    for r in csv.DictReader(datei.open(encoding="utf-8-sig"), delimiter=";"):
        if r["1_variable_code"] != "KREISE" or r["2_variable_attribute_code"] != "AUSNWA006":
            continue
        try:
            # Sonderschlüssel wie 03241001 (Region Hannover) oder 10041100 (Regionalverband Saarbrücken): Kreis = 5 Stellen
            aus.append((r["1_variable_attribute_code"][:5], int(r["time"]), ebene, float(r["value"])))
        except ValueError:
            continue  # gesperrt oder fehlend
    return aus


def auswerten(ordner: Path, ziel: Path) -> None:
    xlsx = ordner / "ref-kreise-1990-2024.xlsx"
    if not xlsx.exists():
        req = urllib.request.Request(BBSR, headers={"User-Agent": "konjunkturmonitor"})
        with urllib.request.urlopen(req, timeout=120) as r:
            xlsx.write_bytes(r.read())
    schluessel = umsteiger(xlsx)
    werte = defaultdict(float)
    for muster, ebene in (("71517-02-03-4*flat.csv", "gemeinden"), ("71517-04-02-4*flat.csv", "kreise")):
        for datei in ordner.rglob(muster):
            for kreis, jahr, eb, eur in lies_71517(datei, ebene):
                for k, a in auf_zielstand(kreis, jahr, schluessel):
                    werte[(k, jahr, eb)] += eur * a
    ziel.mkdir(parents=True, exist_ok=True)
    with (ziel / "sanierung_kommunal.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ags", "jahr", "ebene", "merkmal", "eur"])
        for (k, j, eb), v in sorted(werte.items()):
            w.writerow([k, j, eb, "sachinvestitionen", round(v)])
    kreise = {k for k, _, _ in werte}
    print(f"{len(kreise)} Kreise (Stand 2024), Jahre {min(j for _, j, _ in werte)} bis {max(j for _, j, _ in werte)}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.sanierung_kommunal")
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--ziel", type=Path, default=None)
    a = ap.parse_args(argv)
    auswerten(a.ordner, a.ziel or a.ordner)


if __name__ == "__main__":
    main(sys.argv[1:])
