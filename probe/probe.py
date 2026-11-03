"""Einmalige Erkundung: Rohdaten prüfen (wird nach Auswertung wieder entfernt)."""
import io, os, sys
import pandas as pd, requests
from konjunkturwolf.fetchers import GENESIS_BASE, genesis_text

def genesis(name, startyear="2015"):
    r = requests.post(f"{GENESIS_BASE}/data/tablefile", timeout=120,
        data={"name": name, "area": "all", "compress": "false", "format": "ffcsv", "language": "en", "startyear": startyear},
        headers={"username": os.environ["GENESIS_USER"], "password": os.environ["GENESIS_PASSWORD"],
                 "Content-Type": "application/x-www-form-urlencoded"})
    t = genesis_text(r.content).lstrip("﻿")
    lines = t.splitlines()
    i = next((k for k, l in enumerate(lines[:60]) if l.count(";") >= 3 and "time" in l.lower()), None)
    if i is None:
        print(name, "KEIN KOPF", t[:400]); return None
    return pd.read_csv(io.StringIO("\n".join(lines[i:])), sep=";", dtype=str, keep_default_na=False)

def show(name, startyear="2015"):
    print("=" * 30, name)
    df = genesis(name, startyear)
    if df is None: return
    print("Spalten:", list(df.columns))
    for c in df.columns:
        u = df[c].unique()
        if 1 < len(u) <= 40 and c.lower() not in ("value",):
            print(f"  {c}: {list(u)[:40]}")
    print(df.head(3).to_string())
    return df

for n in ["52411-0010", "52411-0110"]:
    df = show(n)
    if df is not None:
        keep = [c for c in df.columns if df[c].nunique() > 1 and "value" not in c.lower()]
        d = df[df.duplicated(keep, keep=False)] if keep else df
        print("Duplikate über", keep, len(d)); print(d.head(8).to_string())
for n in ["61111-0002", "61111-0004", "61111-0006"]:
    try:
        show(n, "2024")
    except Exception as e:
        print(n, "Fehler", e)

print("=" * 30, "Bundesbank VPI-Reihen")
for q in ["M.DE.N.VPI.C..VGJ.LV", "M.DE.Y.VPI..VGJ.LV", "M.DE.N.VPI...."]:
    r = requests.get(f"https://api.statistiken.bundesbank.de/rest/data/BBDP1/{q}",
                     params={"format": "sdmx_csv", "lastNObservations": 1}, timeout=120)
    print(q, r.status_code)
    if r.ok:
        d = pd.read_csv(io.StringIO(r.text), sep=None, engine="python", dtype=str)
        cols = [c for c in d.columns if c.upper() in ("KEY", "BBK_ID", "TITLE", "TITLE_DE", "OBS_VALUE", "TIME_PERIOD")] or list(d.columns)
        print(list(d.columns)); print(d[cols].to_string()[:6000])
r = requests.get("https://api.statistiken.bundesbank.de/rest/metadata/codelist/BBK/CL_BBK_PREIS_ERHEBUNGSBEREICH", timeout=60)
print("codelist", r.status_code, r.text[:200])
