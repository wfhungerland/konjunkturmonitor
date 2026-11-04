"""Pegelstände: Tagesmittel und Tagesminimum des Wasserstands W für fünf Pegel an Rhein und Elbe.

Quelle: PEGELONLINE, Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV), REST-API v2, ohne Anmeldung.
Holt die 15-Minuten-Werte der letzten 31 Tage, rechnet sie zu Tageswerten zusammen und schreibt sie in
PEGEL_TAGESWERTE.csv im selben Ordner wie dieses Skript. Zeilen werden über Pegel und Datum dedupliziert:
Ein neuer Lauf überschreibt bestehende Zeilen, verdoppelt sie nie. Das Skript kann beliebig oft laufen.

Nur vollständige Tage werden geschrieben: der laufende Tag fehlt noch, und der älteste Tag im 31-Tage-Fenster
nur dann, wenn mindestens 90 der 96 Viertelstundenwerte vorliegen.
Nur Python-Standardbibliothek, keine Zusatzpakete nötig.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
DATEI = ORDNER / "PEGEL_TAGESWERTE.csv"
API = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
# Pegelnamen so, wie PEGELONLINE sie führt (geprüft am 4.11.2026); Magdeburg ist der Pegel Strombrücke
PEGEL = ["KAUB", "KÖLN", "DUISBURG-RUHRORT", "MAGDEBURG-STROMBRÜCKE", "DRESDEN"]
SPALTEN = ["Pegel", "Datum", "Mittel_cm", "Minimum_cm", "Abrufdatum"]
MIN_WERTE_JE_TAG = 90  # von 96 Viertelstunden


def hole(pegel: str) -> list[dict]:
    name = urllib.parse.quote(pegel)
    url = f"{API}/stations/{name}/W/measurements.json?start=P31D"
    req = urllib.request.Request(url, headers={"User-Agent": "Konjunkturdaten/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def tageswerte(messungen: list[dict]) -> dict[str, tuple[float, float, int]]:
    """Datum (Ortszeit laut Zeitstempel) -> (Mittel, Minimum, Anzahl Werte)."""
    tage = defaultdict(list)
    for m in messungen:
        if m.get("value") is None:
            continue
        tage[m["timestamp"][:10]].append(float(m["value"]))
    return {d: (sum(v) / len(v), min(v), len(v)) for d, v in tage.items()}


def zahl(x: float, stellen: int) -> str:
    return f"{x:.{stellen}f}".replace(".", ",")


def lies() -> dict[tuple[str, str], dict]:
    if not DATEI.exists():
        return {}
    with open(DATEI, encoding="utf-8-sig", newline="") as f:
        return {(z["Pegel"], z["Datum"]): z for z in csv.DictReader(f, delimiter=";")}


def schreibe(zeilen: dict[tuple[str, str], dict]) -> None:
    """Erst in eine Hilfsdatei schreiben, dann austauschen: Die CSV ist nie halb geschrieben."""
    fd, tmp = tempfile.mkstemp(dir=ORDNER, prefix=".pegel_", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN, delimiter=";")
        w.writeheader()
        for k in sorted(zeilen):
            w.writerow(zeilen[k])
    os.replace(tmp, DATEI)


def lauf() -> dict:
    heute = datetime.now().strftime("%Y-%m-%d")
    abruf = datetime.now().strftime("%Y-%m-%d %H:%M")
    zeilen = lies()
    vorher = len(zeilen)
    fehler, aktualisiert = [], 0
    for p in PEGEL:
        try:
            tw = tageswerte(hole(p))
        except Exception as e:  # ein gestörter Pegel hält die übrigen nicht auf
            fehler.append(f"{p}: {e}")
            continue
        aeltester = min(tw) if tw else None
        for datum, (mittel, minimum, n) in tw.items():
            if datum >= heute:
                continue  # laufender Tag ist noch unvollständig
            if datum == aeltester and n < MIN_WERTE_JE_TAG:
                continue  # Rand des 31-Tage-Fensters: nur Teil des Tages
            if (p, datum) in zeilen:
                aktualisiert += 1
            zeilen[(p, datum)] = {"Pegel": p, "Datum": datum, "Mittel_cm": zahl(mittel, 1),
                                  "Minimum_cm": zahl(minimum, 0), "Abrufdatum": abruf}
    schreibe(zeilen)
    return {"neu": len(zeilen) - vorher, "aktualisiert": aktualisiert, "gesamt": len(zeilen), "fehler": fehler}


if __name__ == "__main__":
    e = lauf()
    print(f"Pegel: {e['neu']} neue Zeilen, {e['aktualisiert']} aktualisiert, {e['gesamt']} insgesamt"
          + (f"; Fehler: {'; '.join(e['fehler'])}" if e["fehler"] else ""))
    sys.exit(1 if e["fehler"] else 0)
