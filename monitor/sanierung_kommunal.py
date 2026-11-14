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
Schreibt sanierung_kommunal.csv im Langformat (ags, jahr, ebene, wert; Ebenen gemeinden, kreise, alle, einwohner)
und sanierung_kommunal_luecke.csv: je Kreis die Summe der jährlichen Abstände der Sachinvestitionen je Einwohner zum
Schnitt der Flächenländer (Euro je Einwohner, nominal; positiv heißt weniger investiert) sowie den mittleren Index
(Schnitt = 100) für 1995 bis 2014 und 2018 bis 2025. Braucht openpyxl für die BBSR-Datei.
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


def bevoelkerung_bbsr(xlsx: Path) -> dict[tuple[str, int], float]:
    """Bevölkerung je Kreis (Stand des Jahres) am 31.12. aus den BBSR-Blättern, in Personen."""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    aus = {}
    for blatt in wb.sheetnames:
        try:
            von = int(blatt.split("-")[0])
        except ValueError:
            continue
        for r in list(wb[blatt].iter_rows(values_only=True))[1:]:
            if r and len(r) > 6 and r[0] is not None and str(r[0]).strip().isdigit() and isinstance(r[6], (int, float)):
                k = f"{int(r[0]) // 1000:05d}"
                aus[(k, von)] = aus.get((k, von), 0.0) + float(r[6]) * 1000 * float(r[3] if r[3] is not None else 1)
    return aus


def lies_71717(datei: Path) -> list[tuple[str, int, str, float]]:
    """Rechnungsergebnisse 2018 ff.: Kreisebene (alle Gemeinden, Gemeindeverbände und der Kreis zusammen)."""
    aus = []
    for r in csv.DictReader(datei.open(encoding="utf-8-sig"), delimiter=";"):
        if r["1_variable_code"] != "FKREISE":
            continue
        kreis = r["1_variable_attribute_code"].lstrip("F")[:5]
        try:
            v = float(r["value"])
        except ValueError:
            continue
        if r["value_variable_code"] == "FINBEV":
            aus.append((kreis, int(r["time"]), "einwohner", v))
        elif r["value_variable_code"] == "AINVD78" and r["2_variable_attribute_label"] == "Sachinvestitionen":
            aus.append((kreis, int(r["time"]), "alle", v))
    return aus


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
    for datei in sorted(ordner.glob("71717-Z-05_20[0-9][0-9].csv")):
        for kreis, jahr, eb, wert in lies_71717(datei):
            for k, a in auf_zielstand(kreis, min(jahr, ZIELSTAND), schluessel):
                werte[(k, jahr, eb)] += wert * a
    # Einwohner 1995 bis 2014 aus den BBSR-Blättern (Rechnungsergebnisse ab 2018 bringen sie selbst mit)
    for (kreis, jahr), ew in bevoelkerung_bbsr(xlsx).items():
        if 1995 <= jahr <= 2014:
            for k, a in auf_zielstand(kreis, jahr, schluessel):
                werte[(k, jahr, "einwohner")] += ew * a
    ziel.mkdir(parents=True, exist_ok=True)
    with (ziel / "sanierung_kommunal.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ags", "jahr", "ebene", "wert"])
        for (k, j, eb), v in sorted(werte.items()):
            w.writerow([k, j, eb, round(v)])

    # Investitionslücke: je Jahr Sachinvestitionen je Einwohner gegen den Schnitt der Flächenländer; Summe der
    # Abstände in Euro je Einwohner (nominal). Vergleich statt Niveau, weil 1995-2014 nur Gemeinden und Kreise,
    # ab 2018 auch Ämter, Verbandsgemeinden und Samtgemeinden erfasst sind.
    jahre = sorted({j for _, j, eb in werte if eb != "einwohner"})
    # nur Kreise und kreisfreie Städte; höhere Kommunalverbände (etwa 05200, 07390) und Stadtstaaten fallen weg
    liste = Path(__file__).resolve().parent.parent / "data" / "static" / "aufnahme_kreise_de.csv"
    gueltig = {r["ags"] for r in csv.DictReader(liste.open(encoding="utf-8"))} if liste.exists() else None
    kreise = sorted({k for k, _, eb in werte if eb != "einwohner" and (gueltig is None or k in gueltig)})
    inv = lambda k, j: (werte.get((k, j, "gemeinden"), 0) + werte.get((k, j, "kreise"), 0) + werte.get((k, j, "alle"), 0))
    luecke, index = defaultdict(float), defaultdict(list)
    for j in jahre:
        ew = {k: werte.get((k, j, "einwohner"), 0) for k in kreise}
        gesamt = sum(inv(k, j) for k in kreise if ew[k] > 0) / sum(v for v in ew.values() if v > 0)
        for k in kreise:
            if ew[k] > 0:
                pk = inv(k, j) / ew[k]
                luecke[k] += gesamt - pk
                index[(k, "frueh" if j <= 2014 else "spaet")].append(100 * pk / gesamt)
    with (ziel / "sanierung_kommunal_luecke.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ags", "investitionsluecke_eur_je_einwohner", "index_1995_2014", "index_2018_2025", "jahre"])
        for k in kreise:
            fr, sp = index[(k, "frueh")], index[(k, "spaet")]
            w.writerow([k, round(luecke[k]), round(sum(fr) / len(fr), 1) if fr else "", round(sum(sp) / len(sp), 1) if sp else "",
                        len(fr) + len(sp)])
    print(f"{len(kreise)} Kreise (Stand 2024), Jahre {jahre[0]} bis {jahre[-1]} ({len(jahre)} Jahre)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.sanierung_kommunal")
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--ziel", type=Path, default=None)
    a = ap.parse_args(argv)
    auswerten(a.ordner, a.ziel or a.ordner)


if __name__ == "__main__":
    main(sys.argv[1:])
