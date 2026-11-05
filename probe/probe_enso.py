"""Temporäre Probe: El-Niño-Index der NOAA und GENESIS-Tabellen zu Preisen im früheren Bundesgebiet. Gibt keine Zugangsdaten aus."""
import os
import urllib.parse
import urllib.request


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None,
                                 headers={"User-Agent": "Konjunkturmonitor/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


for name, url in [("ONI", "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"),
                  ("RONI", "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt")]:
    try:
        t = get(url).splitlines()
        print(f"== {name}: {len(t)} Zeilen; Kopf: {t[0]}")
        for z in t:
            f = z.split()
            if len(f) >= 3 and f[1].isdigit() and (1981 <= int(f[1]) <= 1984 or 1996 <= int(f[1]) <= 1999 or 2014 <= int(f[1]) <= 2017 or 2022 <= int(f[1])):
                print(z)
    except Exception as e:
        print(name, "Fehler", e)

user, pw = os.environ.get("GENESIS_USER", ""), os.environ.get("GENESIS_PASSWORD", "")
base = "https://genesis.destatis.de/genesisWS/rest/2020"
for sel in ("61111*", "61211*"):
    try:
        t = get(f"{base}/catalogue/tables", data={"selection": sel, "area": "all", "pagelength": "100", "language": "de"},
                headers={"username": user, "password": pw, "Content-Type": "application/x-www-form-urlencoded"})
        import json
        j = json.loads(t)
        print("==", sel, j.get("Status", {}).get("Content"))
        for it in (j.get("List") or []):
            print(it.get("Code"), "|", it.get("Content"), "|", it.get("Time"))
    except Exception as e:
        print(sel, "Fehler", e)
