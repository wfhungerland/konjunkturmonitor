"""Einmalige Prüfung: Welche GENESIS-Tabellen führen Betriebe der Branchen 25.40 (Waffen und Munition) und
30.40 (militärische Kampffahrzeuge), und sind die Werte frei oder gesperrt?

Läuft nur im Prüflauf eines Pull Requests mit den Secrets GENESIS_USER/GENESIS_PASSWORD und schreibt den
Aufbau der Tabellen ins Protokoll. Zugangsdaten werden nie ausgegeben.
"""
from __future__ import annotations

import io
import os
import sys
import urllib.parse
import urllib.request
import zipfile

BASE = "https://genesis.destatis.de/genesisWS/rest/2020"
TABLES = ["42111-0003", "42111-0004", "42111-0005", "42111-0006"]
CODES = ("25-40", "2540", "25.40", "30-40", "3040", "30.40")


def post(path: str, fields: dict) -> bytes:
    req = urllib.request.Request(f"{BASE}/{path}", data=urllib.parse.urlencode(fields).encode(),
                                 headers={"username": os.environ.get("GENESIS_USER", ""), "password": os.environ.get("GENESIS_PASSWORD", ""),
                                          "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def text(raw: bytes) -> str:
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            raw = z.read(z.namelist()[0])
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def main() -> int:
    if not os.environ.get("GENESIS_USER"):
        print("GENESIS-Zugang fehlt; Prüfung übersprungen.")
        return 0
    try:
        cat = text(post("catalogue/tables", {"selection": "42111*", "pagelength": "50", "language": "de"}))
        print("== Katalog 42111*:\n" + cat[:4000])
    except Exception as e:  # Katalog ist nur Zusatz
        print("Katalog nicht abrufbar:", type(e).__name__, str(e)[:200])
    # Werte der Branche 25.40 (Waffen und Munition): Betriebe (0003, 0004) und fachliche Betriebsteile (0023, 0024)
    for t in ("42111-0003", "42111-0023", "42111-0024"):
        fields = {"name": t, "area": "all", "compress": "false", "format": "ffcsv", "language": "de", "startyear": "2019",
                  "classifyingvariable1": "WZ08X4", "classifyingkey1": "WZ08-2540"}
        try:
            body = text(post("data/tablefile", fields))
        except Exception as e:
            print(f"== {t}: Fehler {type(e).__name__}: {str(e)[:300]}")
            continue
        lines = [l.split(";") for l in body.splitlines()]
        head = lines[0]
        rows = [c for c in lines[1:] if "WZ08-2540" in c]
        print(f"== {t} WZ08-2540: {len(rows)} Zeilen; Kopf: {head[5:]}")
        keep = [c for c in rows if c[-2] in ("UMS002", "ERW012", "UMSN3")]
        for c in keep[-80:]:
            when = c[4] + ("-" + c[7] if c[5] == "MONAT" else "")
            print("   ", when, c[-2], c[-4], c[-3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
