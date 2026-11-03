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


bbk_titles("BBDP1", "M.DE..EPG....", ".", 80)
bbk_titles("BBDP1", "M.DE..APE1....", ".", 80)
bbk_titles("BBDP1", "M.DE.....", "Großhandel|Erzeugerpreise landw|Baupreis|Tarif", 30)

# Karte
import json, sys
from shapely.geometry import shape, mapping

URLS = [
    "https://sgx.geodatenzentrum.de/wfs_vg2500?service=WFS&version=2.0.0&request=GetFeature&typeNames=vg2500:vg2500_lan&outputFormat=application/json&srsName=EPSG:4326",
    "https://sgx.geodatenzentrum.de/wfs_vg2500?service=WFS&version=1.1.0&request=GetFeature&typeName=vg2500:vg2500_lan&outputFormat=application/json&srsName=EPSG:4326",
]
gj = None
for u in URLS:
    r = requests.get(u, timeout=120)
    print(u, r.status_code, r.headers.get("content-type"), r.text[:200].replace("\n", " "))
    if r.ok and r.text.lstrip().startswith("{"):
        gj = r.json(); break
if gj is None:
    r = requests.get("https://sgx.geodatenzentrum.de/wfs_vg2500?service=WFS&request=GetCapabilities", timeout=60)
    print(r.text[:3000]); raise SystemExit(0)
print("Attribute:", gj["features"][0]["properties"])
by = {}
for f in gj["features"]:
    p = f["properties"]
    code = str(p.get("ars"))[:2]
    if code not in by or str(p.get("gf")) == "4":
        by[code] = f
print("gf je Land:", {k: v["properties"].get("gf") for k, v in by.items()})
out = []
def rnd(c):
    if isinstance(c[0], (float, int)):
        return [round(c[0], 3), round(c[1], 3)]
    return [rnd(x) for x in c]
for code, f in sorted(by.items()):
    g = shape(f["geometry"]).simplify(0.008, preserve_topology=True)
    m = mapping(g)
    out.append({"code": code, "name": f["properties"].get("gen"), "type": m["type"], "coordinates": rnd(m["coordinates"])})
s = json.dumps(out, separators=(",", ":"))
print("LEN", len(s), "N", len(out))
for i in range(0, len(s), 4000):
    print("GJ:" + s[i:i + 4000])
