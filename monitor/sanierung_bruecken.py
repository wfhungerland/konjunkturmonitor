"""Sanierungsbedarf der Kreise, Baustein Brücken der Bundesfernstraßen (BASt-Brückenstatistik).

Die BASt veröffentlicht jedes Teilbauwerk mit Baujahr, Fläche, Traglastindex und Zustandsnote (1,0 sehr gut bis
4,0 ungenügend), aber ohne Lage. Die Lage steckt in der Bauwerksnummer: Ihre ersten vier Ziffern sind das Blatt
der Topographischen Karte 1:25.000 (TK25), Zeile und Spalte eines Rasters von 6 Bogenminuten Breite und
10 Bogenminuten Länge mit dem Ursprung 55°54' Nord, 5°50' Ost. Der Blattmittelpunkt (rund 11 mal 11 km) wird dem
Kreis zugeordnet, in dem er liegt (GISCO, NUTS 2024); Brücken nahe einer Kreisgrenze können so im Nachbarkreis
landen.

Kennzahlen je Kreis: Brückenfläche, Anteil der Fläche mit Note ab 3,0 (nicht ausreichend oder ungenügend) und ab
2,5, mittleres Baujahr, Fläche mit Traglastindex IV oder V. Fortschreibung: Wie schnell die Note mit dem Alter
steigt, ist im Querschnitt aller Brücken je Baustoff geschätzt (mittlere Note je Altersjahr, geglättet). Jede
Brücke wird mit dieser Alterungskurve fortgeschrieben, ausgehend von ihrer heutigen Note und ohne Erneuerung.
Ergebnis: Fläche mit Note ab 3,0 im Jahr 2030 und 2035, wenn nichts erneuert wird. Der Querschnitt unterschätzt die
Alterung stark (im Mittel steigt die Note nur um rund 0,01 je Jahr, weil schlechte alte Brücken schon ersetzt
sind); die Fortschreibung ist eine Untergrenze, bis eine zweite Ausgabe der Statistik je Brücke vorliegt.
Robuster ist die Altersgröße: Anteil der Fläche, die heute und 2035 mindestens 60 Jahre alt ist, und der Anteil
Spannbeton vor 1980 (anfällig für Spannungsrisskorrosion, ein Kriterium des Bundes für Ersatzneubauten).

    python -m monitor.sanierung_bruecken <ordner> [--ziel data/static]

Lädt die CSV der BASt und die Kreisgrenzen in den Ordner, schreibt sanierung_bruecken.csv (je Kreis).
Nur Standardbibliothek.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

BAST = "https://www.bast.de/DE/Publikationen/Statistik/Bruecken/Brueckenstatistik-csv.csv?__blob=publicationFile&v=2"
GISCO = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_03M_2024_4326_LEVL_3.geojson"
STAND = 2026          # Stichtag der Statistik: 1. März 2026
SCHLECHT = 3.0        # Note ab 3,0: nicht ausreichend (3,0 bis 3,4) oder ungenügend (3,5 bis 4,0)


def _laden(url: str, datei: Path) -> Path:
    if not datei.exists():
        datei.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor (Sanierungsbedarf)"})
        with urllib.request.urlopen(req, timeout=300) as r:
            datei.write_bytes(r.read())
    return datei


def tk25_mitte(bwnr: str) -> tuple[float, float] | None:
    """Mittelpunkt (Breite, Länge) des TK25-Blatts aus den ersten vier Ziffern der Bauwerksnummer."""
    try:
        zeile, spalte = int(bwnr[:2]), int(bwnr[2:4])
    except ValueError:
        return None
    if not (1 <= zeile <= 90 and 1 <= spalte <= 70):
        return None
    return 55.9 - (zeile - 1) * 0.1 - 0.05, 5 + 50 / 60 + (spalte - 1) / 6 + 1 / 12


def _in_ring(lon: float, lat: float, ring: list) -> bool:
    drin = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            drin = not drin
    return drin


class Kreise:
    """Punkt-in-Fläche für die deutschen NUTS-3-Regionen mit Rahmen als Vorfilter."""

    def __init__(self, geojson: Path):
        self.flaechen = []
        for f in json.loads(geojson.read_text(encoding="utf-8"))["features"]:
            if f["properties"]["CNTR_CODE"] != "DE":
                continue
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            xs = [x for p in polys for x, _ in p[0]]
            ys = [y for p in polys for _, y in p[0]]
            self.flaechen.append((f["properties"]["NUTS_ID"], (min(xs), min(ys), max(xs), max(ys)), polys))

    def finde(self, lat: float, lon: float) -> str | None:
        for kid, (x0, y0, x1, y1), polys in self.flaechen:
            if x0 <= lon <= x1 and y0 <= lat <= y1:
                for p in polys:
                    if _in_ring(lon, lat, p[0]) and not any(_in_ring(lon, lat, loch) for loch in p[1:]):
                        return kid
        return None


def alterungskurven(brucken: list[dict]) -> dict[str, list[float]]:
    """Mittlere Note je Altersjahr (0 bis 120) und Baustoff, gleitend über ±5 Jahre geglättet und monoton gemacht."""
    summe, zahl = defaultdict(lambda: [0.0] * 121), defaultdict(lambda: [0] * 121)
    for b in brucken:
        a = min(120, max(0, STAND - b["baujahr"]))
        for k in (b["baustoff"], "alle"):
            summe[k][a] += b["note"] * b["flaeche"]
            zahl[k][a] += b["flaeche"]
    kurven = {}
    for k in summe:
        glatt = []
        for a in range(121):
            s = sum(summe[k][j] for j in range(max(0, a - 5), min(120, a + 5) + 1))
            n = sum(zahl[k][j] for j in range(max(0, a - 5), min(120, a + 5) + 1))
            glatt.append(s / n if n else None)
        # Lücken füllen und Monotonie erzwingen (die Note sinkt mit dem Alter nicht)
        letzte = next(v for v in glatt if v is not None)
        for a in range(121):
            letzte = max(letzte, glatt[a]) if glatt[a] is not None else letzte
            glatt[a] = letzte
        kurven[k] = glatt
    return kurven


def fortschreiben(b: dict, kurven: dict, jahre: int) -> float:
    kurve = kurven.get(b["baustoff"]) or kurven["alle"]
    a = min(120, max(0, STAND - b["baujahr"]))
    a2 = min(120, a + jahre)
    return min(4.0, b["note"] + (kurve[a2] - kurve[a]))


def auswerten(ordner: Path, ziel: Path) -> None:
    csv_datei = _laden(BAST, ordner / "brueckenstatistik.csv")
    kreise = Kreise(_laden(GISCO, ordner / "nuts3_rg_03m_2024_4326.geojson"))
    brucken, ohne = [], 0
    for r in csv.DictReader(csv_datei.open(encoding="utf-8")):
        lage = tk25_mitte(r["bwnr"].strip())
        kreis = kreise.finde(*lage) if lage else None
        try:
            b = {"kreis": kreis, "baujahr": int(r["baujahr"]), "flaeche": float(r["flaeche"] or 0),
                 "note": float(r["zustandsnote"]), "traglast": r["trag_l_idx"].strip(),
                 "baustoff": r["baustoffklasse"].strip(), "planung": "Erneuerung/Ersatzneubau" in r["stadium_text"]}
        except ValueError:
            continue
        if not kreis:
            ohne += 1
        brucken.append(b)
    kurven = alterungskurven(brucken)
    je = defaultdict(lambda: defaultdict(float))
    for b in brucken:
        if not b["kreis"]:
            continue
        k, f = je[b["kreis"]], b["flaeche"]
        k["anzahl"] += 1
        k["flaeche"] += f
        k["baujahr_f"] += b["baujahr"] * f
        k["ab30"] += f * (b["note"] >= SCHLECHT)
        k["ab25"] += f * (b["note"] >= 2.5)
        k["traglast_iv_v"] += f * (b["traglast"] in ("IV", "V"))
        k["ersatz_geplant"] += f * b["planung"]
        k["ab30_2030"] += f * (fortschreiben(b, kurven, 2030 - STAND) >= SCHLECHT)
        k["ab30_2035"] += f * (fortschreiben(b, kurven, 2035 - STAND) >= SCHLECHT)
        k["alt60_heute"] += f * (STAND - b["baujahr"] >= 60)
        k["alt60_2035"] += f * (2035 - b["baujahr"] >= 60)
        k["spann_vor1980"] += f * (b["baustoff"] == "Spannbeton" and b["baujahr"] < 1980)
    ziel.mkdir(parents=True, exist_ok=True)
    spalten = ["nuts3", "bauwerke", "flaeche_m2", "mittleres_baujahr", "anteil_note_ab_3_0", "anteil_note_ab_2_5",
               "anteil_traglast_iv_v", "anteil_ersatz_geplant", "flaeche_note_ab_3_0_m2", "flaeche_note_ab_3_0_2030_m2",
               "flaeche_note_ab_3_0_2035_m2", "anteil_60_jahre_heute", "anteil_60_jahre_2035", "anteil_spannbeton_vor_1980"]
    with (ziel / "sanierung_bruecken.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(spalten)
        for kid in sorted(je):
            k = je[kid]
            fl = k["flaeche"] or 1
            w.writerow([kid, int(k["anzahl"]), round(k["flaeche"]), round(k["baujahr_f"] / fl), round(k["ab30"] / fl, 3),
                        round(k["ab25"] / fl, 3), round(k["traglast_iv_v"] / fl, 3), round(k["ersatz_geplant"] / fl, 3),
                        round(k["ab30"]), round(k["ab30_2030"]), round(k["ab30_2035"]), round(k["alt60_heute"] / fl, 3),
                        round(k["alt60_2035"] / fl, 3), round(k["spann_vor1980"] / fl, 3)])
    gesamt = sum(b["flaeche"] for b in brucken)
    heute = sum(b["flaeche"] for b in brucken if b["note"] >= SCHLECHT)
    p30 = sum(b["flaeche"] for b in brucken if fortschreiben(b, kurven, 2030 - STAND) >= SCHLECHT)
    p35 = sum(b["flaeche"] for b in brucken if fortschreiben(b, kurven, 2035 - STAND) >= SCHLECHT)
    print(f"{len(brucken)} Teilbauwerke, ohne Kreis {ohne}; Fläche mit Note ab 3,0: heute {100 * heute / gesamt:.1f} %, "
          f"2030 {100 * p30 / gesamt:.1f} %, 2035 {100 * p35 / gesamt:.1f} % (ohne Erneuerung); "
          f"{len(je)} Kreise mit Brücken; Stand {dt.date.today():%d.%m.%Y}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.sanierung_bruecken")
    ap.add_argument("ordner", type=Path)
    ap.add_argument("--ziel", type=Path, default=None)
    a = ap.parse_args(argv)
    auswerten(a.ordner, a.ziel or a.ordner)


if __name__ == "__main__":
    main(sys.argv[1:])
