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
    # Feingliederung ausdrücklich anfordern: Betriebe (0003) und fachliche Betriebsteile (0023), Jahre
    for t in ("42111-0003", "42111-0023"):
        for var in ("WZ08X4",):
            fields = {"name": t, "area": "all", "compress": "false", "format": "ffcsv", "language": "de", "startyear": "2019",
                      "classifyingvariable1": var}
            try:
                body = text(post("data/tablefile", fields))
            except Exception as e:
                print(f"== {t} {var}: Fehler {type(e).__name__}: {str(e)[:300]}")
                continue
            lines = body.splitlines()
            codes = {}
            for l in lines[1:]:
                c = l.split(";")
                if len(c) > 16 and (c[15].startswith("WZ08-25") or c[15].startswith("WZ08-30")):
                    codes.setdefault(c[15], (c[16], set()))[1].add(c[-4][:12])
            print(f"== {t} {var}: Codes der Branchen 25 und 30:")
            for k, (lab, vals) in sorted(codes.items()):
                print(f"    {k} {lab[:60]} | Beispielwerte: {sorted(vals)[:4]}")
            hits = [l for l in lines if "WZ08-25-4" in l or "WZ08-30-4" in l]
            print(f"== {t} {var}: {len(lines)} Zeilen, davon {len(hits)} mit 25.4/30.4")
            if not hits:
                print("   ", body[:400].replace(chr(10), " | "))
            for l in hits:
                cols = l.split(";")
                print("   ", ";".join(cols[4:5] + cols[-8:]))
            if hits:
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
