"""Einmalige Erkundung: Reihen-Codes für Paket 1 und 3 der Überarbeitung (wird wieder entfernt)."""
import io, os, re, json
import pandas as pd, requests
from konjunkturwolf.fetchers import GENESIS_BASE, genesis_text

S = requests.Session()
BBK = "https://api.statistiken.bundesbank.de/rest"
AUTH = {"username": os.environ.get("GENESIS_USER", ""), "password": os.environ.get("GENESIS_PASSWORD", ""),
        "Content-Type": "application/x-www-form-urlencoded"}

def hdr(t): print("\n" + "=" * 20, t, flush=True)

def bbk_titles(flow, key, pat, limit=80):
    hdr(f"BBK {flow}/{key} ~ {pat}")
    try:
        r = S.get(f"{BBK}/data/{flow}/{key}", params={"format": "sdmx_csv", "lastNObservations": 1, "lang": "de"}, timeout=300)
        print("status", r.status_code, len(r.text))
        if not r.ok: return
        d = pd.read_csv(io.StringIO(r.text), sep=None, engine="python", dtype=str)
        d.columns = [c.lstrip("﻿") for c in d.columns]
        d = d[d["BBK_TITLE"].str.contains(pat, case=False, regex=True, na=False)]
        for _, x in d.head(limit).iterrows():
            print(x["BBK_ID"], "|", x["TIME_PERIOD"], x["OBS_VALUE"], "|", str(x["BBK_TITLE"])[:170])
        print("Treffer:", len(d))
    except Exception as e:
        print("Fehler", e)

def euro(ds, last=1, **params):
    hdr(f"Eurostat {ds} {params}")
    try:
        r = S.get(f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}",
                  params={"format": "JSON", "lang": "en", "lastTimePeriod": last, **params}, timeout=120)
        j = r.json()
        if "error" in j: print("Fehler", j["error"]); return
        for dim in j["id"]:
            cats = j["dimension"][dim]["category"]["label"]
            print(f"  {dim} ({len(cats)}):", "; ".join(f"{k}={v}" for k, v in list(cats.items())[:60])[:1500])
        print("  Werte:", list(j.get("value", {}).values())[:12])
    except Exception as e:
        print("Fehler", e)

def gen_tables(sel):
    hdr(f"GENESIS Tabellen {sel}")
    r = S.post(f"{GENESIS_BASE}/catalogue/tables", data={"selection": sel, "area": "all", "pagelength": "60", "language": "de"}, headers=AUTH, timeout=120)
    try:
        for t in r.json().get("List") or []:
            print(t.get("Code"), "|", " ".join(str(t.get("Content")).split())[:160], "|", t.get("Time"))
    except Exception as e:
        print("Fehler", r.status_code, r.text[:300])

def fred(sid):
    try:
        r = S.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=60)
        print("FRED", sid, r.status_code, r.text[:40].replace("\n", " | "), "...", r.text[-90:].replace("\n", " | "))
    except Exception as e:
        print("FRED", sid, "Fehler", e)

def url(u):
    try:
        r = S.get(u, timeout=60)
        print("URL", u, r.status_code, r.headers.get("content-type"), len(r.content))
    except Exception as e:
        print("URL", u, "Fehler", e)


# Paket 1: Dienstleistungen insgesamt im VPI, BIP-Vorjahresrate kalenderbereinigt
bbk_titles("BBDP1", "M.DE.N.VPI.C..I20.A", "Dienstl|Waren|Miete", 40)
for adj in ["CA", "NSA", "SCA"]:
    euro("namq_10_gdp", last=2, geo="DE", na_item="B1GQ", unit="CLV_PCH_SM", s_adj=adj)
# Paket 3: Einkommen, Staat, Arbeit, Aufträge, Dienstleistungen, Zuwanderung, Welt, Maut
euro("nasq_10_ki", geo="DE")
euro("gov_10a_main", geo="DE", sector="S13", unit="PC_GDP")
euro("gov_10q_ggnfa", geo="DE", sector="S13", unit="PC_GDP", s_adj="SCA")
euro("sts_setu_m", geo="DE")
euro("migr_imm1ctz", geo="DE", age="TOTAL", sex="T", agedef="COMPLET")
euro("ei_lmhr_m", geo="DE")
bbk_titles("BBDL1", "M.DE.....", "Unterbesch|Kurzarb|Leih|sozialversicherungspflichtig|Arbeitnehmer|Lohn|Verdienst", 80)
bbk_titles("BBDE1", "M.DE.Y.AEA1.....", ".", 80)
bbk_titles("BBDE1", "M.DE.....", "Dienstleist|Maut", 40)
for sel in ["42191*", "62361*", "62321*", "13231*", "81000*", "12711*"]:
    gen_tables(sel)
for sid in ["GSCPI", "WUIDEU", "EUEPUINDXM", "GEPUCURRENT", "GDPC1", "CHNGDPNQDSMEI", "CLVMNACSCAB1GQEA19", "DEUEPUINDXM"]:
    fred(sid)
url("https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx")
url("https://www.cpb.nl/sites/default/files/omnidownload/CPB-World-Trade-Monitor-August-2026.xlsx")
url("https://api.db.nomics.world/v22/series/AMECO/ZVGDF/DEU.1.0.0.0.ZVGDF?observations=1")
