"""Aufnahmefähigkeit der Kreise: Kreisreihen zu Kapazität und Engpass im Bau.

Quelle: BA, „Regionalreport über Beschäftigte (Quartalszahlen)“, eine Excel-Datei je Kreis und Quartal mit
fünf Stichtagen. Daraus: sozialversicherungspflichtig Beschäftigte am Arbeitsort insgesamt, Ausländer,
Baugewerbe (WZ 2008 Abschnitt F), Bauberufe und Handwerksberufe (Aggregate der BA), Berufshauptgruppen 31-34
der KldB 2010 und Anforderungsniveaus. Kreisliste mit NUTS-3-Code und Bevölkerung von Destatis.

Nur Standardbibliothek, damit es auch mit einem nackten Python unter Windows läuft.

    python -m monitor.aufnahme_kreise kreise <ordner>                 # Kreisliste (Destatis)
    python -m monitor.aufnahme_kreise ba <ordner> --stichtag 202603   # BA-Dateien laden und auswerten
                                                 [--ziel data/static]

Die Excel-Dateien bleiben im Ordner (Zwischenspeicher); ins Repo kommt nur die Tabelle
aufnahme_ba_kreise.csv im Langformat (ags, nuts3, stichtag, merkmal, wert).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from monitor.aufnahme import NUTS21_24

KREISE = ("https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/Gemeindeverzeichnis/Administrativ/"
          "04-kreise.xlsx?__blob=publicationFile")
BA = ("https://statistik.arbeitsagentur.de/Statistikdaten/Detail/{m}/iiia6/beschaeftigung-reg-bst-reg/"
      "bst-reg-{ags}-0-{m}-xlsx.xlsx?__blob=publicationFile")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
MONATE = {"Jan": 1, "Feb": 2, "Mrz": 3, "Apr": 4, "Mai": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9,
          "Okt": 10, "Nov": 11, "Dez": 12}

# Tabelle, Spalte des Schlüssels, Schlüssel -> Merkmal
MERKMALE = {
    "Tabelle 2.2": {("A", "Insgesamt"): "svb_insgesamt", ("B", "Ausländer"): "svb_auslaender"},
    "Tabelle 2.3": {("A", "F"): "svb_wz_f_baugewerbe"},
    "Tabelle 2.4": {("A", "Helfer"): "svb_helfer", ("A", "Fachkraft"): "svb_fachkraft",
                    ("A", "Bauberufe"): "svb_bauberufe", ("A", "Handwerksberufe"): "svb_handwerksberufe",
                    ("A", "31"): "svb_kldb31_bauplanung", ("A", "32"): "svb_kldb32_hoch_tiefbau",
                    ("A", "33"): "svb_kldb33_ausbau", ("A", "34"): "svb_kldb34_gebaeudetechnik"},
}


def _laden(url: str, datei: Path, versuche: int = 6) -> bool:
    """Lädt eine Datei, falls noch nicht vorhanden. False bei 404."""
    if datei.exists() and datei.stat().st_size > 0:
        return True
    for i in range(versuche):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor (Aufnahmefähigkeit)"})
            with urllib.request.urlopen(req, timeout=120) as r:
                datei.write_bytes(r.read())
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            if i == versuche - 1:
                raise
            if e.code == 429:  # die BA drosselt; Wartezeit aus Retry-After, sonst steigend
                time.sleep(int(e.headers.get("Retry-After") or 30 * (i + 1)))
                continue
        except (urllib.error.URLError, TimeoutError):
            if i == versuche - 1:
                raise
        time.sleep(3 * (i + 1))
    return False


# ---------------------------------------------------------------- xlsx ohne Zusatzpakete

def _spalte(ref: str) -> str:
    return re.match(r"[A-Z]+", ref).group(0)


def blaetter(pfad: Path, namen: set[str] | None = None) -> dict[str, list[dict[str, object]]]:
    """Liest Arbeitsblätter als Liste von Zeilen {Spaltenbuchstabe: Wert}; Zahlen als float."""
    with zipfile.ZipFile(pfad) as z:
        texte = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
                texte.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        ziel = {r.get("Id"): r.get("Target") for r in rels}
        aus = {}
        for s in wb.find("m:sheets", NS):
            name = s.get("name")
            if namen and name not in namen:
                continue
            pfad_blatt = ziel[s.get(f"{{{NS['r']}}}id")].lstrip("/")
            pfad_blatt = pfad_blatt if pfad_blatt.startswith("xl/") else "xl/" + pfad_blatt
            zeilen = []
            for row in ET.fromstring(z.read(pfad_blatt)).iter(f"{{{NS['m']}}}row"):
                zeile = {}
                for c in row.findall("m:c", NS):
                    t, v = c.get("t"), c.find("m:v", NS)
                    if t == "s" and v is not None:
                        wert = texte[int(v.text)]
                    elif t == "inlineStr":
                        wert = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
                    elif t == "str" and v is not None:
                        wert = v.text
                    elif v is not None:
                        try:
                            wert = float(v.text)
                        except ValueError:
                            wert = v.text
                    else:
                        continue
                    zeile[_spalte(c.get("r"))] = wert
                if zeile:
                    zeilen.append(zeile)
            aus[name] = zeilen
        return aus


# ---------------------------------------------------------------- Kreisliste

def kreise(ordner: Path) -> list[dict]:
    """Kreise mit Amtlichem Regionalschlüssel, NUTS 3 (Stand 2024), Fläche und Bevölkerung (Destatis)."""
    ordner.mkdir(parents=True, exist_ok=True)
    xlsx = ordner / "destatis_kreise.xlsx"
    _laden(KREISE, xlsx)
    blatt = next(iter(blaetter(xlsx, {"Kreisfreie Städte u. Landkreise"}).values()))
    aus = []
    for z in blatt:
        ags = str(z.get("A", "")).strip()
        if re.fullmatch(r"\d{5}", ags) and z.get("D"):
            aus.append({"ags": ags, "name": z.get("C", ""), "nuts3": NUTS21_24.get(z["D"], z["D"]),
                        "flaeche_km2": z.get("E", ""), "bevoelkerung": int(z["F"]) if z.get("F") else ""})
    with (ordner / "kreise_de.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(aus[0]))
        w.writeheader()
        w.writerows(aus)
    print(f"{len(aus)} Kreise")
    return aus


def _lies_kreise(ordner: Path) -> list[dict]:
    if not (ordner / "kreise_de.csv").exists():
        return kreise(ordner)
    return list(csv.DictReader((ordner / "kreise_de.csv").open(encoding="utf-8")))


# ---------------------------------------------------------------- BA-Regionalreport

def _stichtage(blatt: list[dict]) -> dict[str, str]:
    """Spalte -> Stichtag (JJJJ-MM) aus der Kopfzeile mit Einträgen wie „Mrz. 26“."""
    for z in blatt:
        treffer = {}
        for sp, w in z.items():
            m = re.fullmatch(r"([A-Z][a-z]{2})\.\s*(\d\d)", str(w).strip())
            if m and m.group(1) in MONATE:
                treffer[sp] = f"20{m.group(2)}-{MONATE[m.group(1)]:02d}"
        if len(treffer) >= 2:
            return treffer
    return {}


def _schluessel(w) -> str:
    if isinstance(w, float) and w.is_integer():
        return str(int(w))
    return str(w).strip()


def regionalreport(pfad: Path) -> list[tuple[str, str, float | None]]:
    """(stichtag, merkmal, wert) aus einem Regionalreport; anonymisierte Werte (*) als None."""
    aus = []
    for name, blatt in blaetter(pfad, set(MERKMALE)).items():
        spalten = _stichtage(blatt)
        for z in blatt:
            for (sp, schl), merkmal in MERKMALE[name].items():
                if _schluessel(z.get(sp, "")) == schl:
                    for s, tag in spalten.items():
                        w = z.get(s)
                        aus.append((tag, merkmal, w if isinstance(w, float) else None))
    return aus


def ba(ordner: Path, stichtag: str, ziel: Path) -> None:
    kr = _lies_kreise(ordner)
    cache = ordner / "ba_regionalreport"
    cache.mkdir(parents=True, exist_ok=True)
    zeilen, fehlt = [], []
    for i, k in enumerate(kr, 1):
        datei = cache / f"bst-reg-{k['ags']}-{stichtag}.xlsx"
        if not _laden(BA.format(m=stichtag, ags=k["ags"]), datei):
            fehlt.append(k["ags"])
            continue
        for tag, merkmal, wert in regionalreport(datei):
            zeilen.append((k["ags"], k["nuts3"], tag, merkmal, "" if wert is None else int(wert)))
        if i % 50 == 0:
            print(f"{i} von {len(kr)} Kreisen", flush=True)
        time.sleep(1.5)
    ziel.mkdir(parents=True, exist_ok=True)
    with (ziel / "aufnahme_ba_kreise.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ags", "nuts3", "stichtag", "merkmal", "wert"])
        w.writerows(sorted(set(zeilen)))
    print(f"{len(kr) - len(fehlt)} Kreise, {len(zeilen)} Werte; ohne Datei: {', '.join(fehlt) or 'keiner'}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.aufnahme_kreise")
    ap.add_argument("schritt", choices=["kreise", "ba"])
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--stichtag", default="202603", help="Berichtsmonat des Regionalreports, JJJJMM")
    ap.add_argument("--ziel", type=Path, default=None)
    a = ap.parse_args(argv)
    if a.schritt == "kreise":
        kreise(a.ordner)
    else:
        ba(a.ordner, a.stichtag, a.ziel or a.ordner)


if __name__ == "__main__":
    main(sys.argv[1:])
