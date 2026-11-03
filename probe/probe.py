"""Einmalige Erkundung: Reihen-Codes für die Lücken aus der Konjunkturmappe (wird wieder entfernt)."""
import io, os, re, json
import pandas as pd, requests
from konjunkturwolf.fetchers import GENESIS_BASE, genesis_text

S = requests.Session()
BBK = "https://api.statistiken.bundesbank.de/rest"
AUTH = {"username": os.environ["GENESIS_USER"], "password": os.environ["GENESIS_PASSWORD"],
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

def bbk_flows(pat):
    hdr(f"BBK Dataflows ~ {pat}")
    r = S.get(f"{BBK}/metadata/dataflow/BBK", headers={"Accept": "application/vnd.sdmx.structure+json;version=1.0"}, timeout=120)
    print("status", r.status_code)
    try:
        flows = r.json()["data"]["dataflows"]
        for f in flows:
            name = f.get("name") or (f.get("names") or {}).get("de", "")
            if re.search(pat, json.dumps(f, ensure_ascii=False), re.I):
                print(f["id"], "|", str(name)[:150])
    except Exception as e:
        print("Fehler", e, r.text[:500])

def euro(ds, **params):
    hdr(f"Eurostat {ds} {params}")
    try:
        r = S.get(f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}",
                  params={"format": "JSON", "lang": "en", "lastTimePeriod": 1, **params}, timeout=120)
        j = r.json()
        if "error" in j: print("Fehler", j["error"]); return
        for dim in j["id"]:
            cats = j["dimension"][dim]["category"]["label"]
            print(f"  {dim} ({len(cats)}):", "; ".join(f"{k}={v}" for k, v in list(cats.items())[:40])[:900])
        print("  Werte:", list(j.get("value", {}).values())[:10])
    except Exception as e:
        print("Fehler", e)

def gen_vars(name, pat=None, startyear="2025"):
    hdr(f"GENESIS {name} ~ {pat}")
    try:
        r = S.post(f"{GENESIS_BASE}/data/tablefile", timeout=300, headers=AUTH,
                   data={"name": name, "area": "all", "compress": "false", "format": "ffcsv", "language": "de", "startyear": startyear})
        t = genesis_text(r.content).lstrip("﻿")
        lines = t.splitlines()
        i = next((k for k, l in enumerate(lines[:60]) if l.count(";") >= 3 and re.search(r"(^|;)\"?(time|zeit)\"?(;|$)", l.lower())), None)
        if i is None: print("kein Kopf", t[:300]); return
        df = pd.read_csv(io.StringIO("\n".join(lines[i:])), sep=";", dtype=str, keep_default_na=False)
        print("Spalten:", [c for c in df.columns if "label" not in c])
        for c in df.columns:
            if c.endswith("attribute_code") or c in ("value_variable_code", "value_unit"):
                lab = c.replace("code", "label")
                pairs = df[[c, lab]].drop_duplicates() if lab in df.columns else df[[c]].drop_duplicates()
                if len(pairs) > 1 and not pairs[c].str.startswith("MONAT").all():
                    if pat and lab in pairs:
                        pairs = pairs[pairs[lab].str.contains(pat, case=False, na=False) | (len(pairs) < 25)]
                    print(f"  {c}:", " ; ".join("=".join(map(str, x)) for x in pairs.head(60).values.tolist())[:2500])
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


for k in ["M.DE.Y.GUA1.....", "M.DE.Y.KAA1.....", "M.DE.Y.UAA1.....", "M.DE.Y.UAB1.....", "M.DE.Y.UAB5....."]:
    bbk_titles("BBDE1", k, ".", 60)
bbk_titles("BBDE1", "M.DE.Y.....", "Umsatz", 80)
bbk_titles("BBDP1", "M.DE.N.HVPI.C.A00000..", ".", 10)
euro("bop_c6_m", geo="DE", partner="WRL_REST", bop_item="CA", stk_flow="BAL", currency="MIO_EUR")
hdr("namq_10_gdp units")
r = S.get("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/namq_10_gdp",
          params={"format": "JSON", "lang": "en", "lastTimePeriod": 1, "geo": "DE", "na_item": "B1GQ", "s_adj": "SCA"}, timeout=120)
print(list(r.json()["dimension"]["unit"]["category"]["label"].keys()))
gen_vars("45212-0005", None, startyear="2026")
for sid in ["MCOILBRENTEU", "PNGASEUUSDM"]:
    r = S.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=60); print(sid, r.status_code, r.text[-120:].replace("\n", " | "))
