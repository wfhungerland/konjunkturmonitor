"""Einmalige Erkundung: VPI-Gliederungen (wird nach Auswertung wieder entfernt)."""
import io, os
import pandas as pd, requests
from konjunkturwolf.fetchers import GENESIS_BASE

r = requests.get("https://api.statistiken.bundesbank.de/rest/data/BBDP1/M.DE.N.VPI....",
                 params={"format": "sdmx_csv", "lastNObservations": 1, "lang": "de"}, timeout=120)
d = pd.read_csv(io.StringIO(r.text), sep=None, engine="python", dtype=str)
d.columns = [c.lstrip("﻿") for c in d.columns]
for _, x in d.iterrows():
    print(x["BBK_ID"], "|", x["TIME_PERIOD"], x["OBS_VALUE"], "|", x.get("BBK_TITLE"), "|", x.get("BBK_UNIT"))

auth = {"username": os.environ["GENESIS_USER"], "password": os.environ["GENESIS_PASSWORD"],
        "Content-Type": "application/x-www-form-urlencoded"}
for sel in ["61111*"]:
    r = requests.post(f"{GENESIS_BASE}/catalogue/tables", data={"selection": sel, "area": "all", "pagelength": "100", "language": "de"},
                      headers=auth, timeout=120)
    try:
        for t in r.json().get("List") or []:
            print(t.get("Code"), "|", t.get("Content"), "|", t.get("Time"))
    except Exception as e:
        print("Fehler", r.status_code, r.text[:300])
