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


UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) konjunkturmonitor"}
def page(u, pat=None, n=1500):
    try:
        rr = S.get(u, timeout=60, headers=UA)
        links = re.findall(r'href="([^"]+)"', rr.text)
        print(u, rr.status_code, len(rr.text))
        hits = [l for l in links if pat and re.search(pat, l, re.I)]
        print("  Links:", hits[:25])
        return rr
    except Exception as e:
        print(u, "Fehler", e)
hdr("WAI")
for u in ["https://www.bundesbank.de/de/statistiken/konjunktur-und-preise/woechentlicher-aktivitaetsindex",
          "https://www.bundesbank.de/de/statistiken/konjunktur-und-preise/wai",
          "https://www.bundesbank.de/en/statistics/economic-activity-and-prices/weekly-activity-index"]:
    page(u, r"xlsx|csv|\.xls|wai|aktivit")
hdr("Kalender")
for u in ["https://www.destatis.de/DE/Presse/Termine/Wochenvorschau/_inhalt.html",
          "https://www.destatis.de/SiteGlobals/Functions/RSSFeed/DE/RSSNewsfeed/Termine.xml",
          "https://www.destatis.de/DE/Service/Termine/_inhalt.html",
          "https://www.bundesbank.de/de/statistiken/statistischer-veroeffentlichungskalender",
          "https://statistik.arbeitsagentur.de/DE/Navigation/Footer/Top-Produkte/Veroeffentlichungskalender-Nav.html"]:
    rr = page(u, r"ics|ical|termin|kalender|rss|xml")
    if rr is not None and rr.ok:
        txt = re.sub(r"<[^>]+>", " ", rr.text); txt = re.sub(r"\s+", " ", txt)
        m = re.search(r"\d{1,2}\.\d{1,2}\.20\d\d", txt)
        print("  Text:", txt[max(0, (m.start() if m else 0) - 200):(m.start() if m else 0) + 1500])
r = S.get("https://ec.europa.eu/eurostat/o/calendars/eventsJson", params={"start": "2026-11-01", "end": "2026-12-31", "theme": 0, "category": 0}, timeout=60)
print("Eurostat Kalender", r.status_code, r.text[:1500])
hdr("AMECO")
r = S.get("https://api.db.nomics.world/v22/series/AMECO/OVGDP", params={"dimensions": json.dumps({"geo": ["deu"]}), "observations": 1, "limit": 20}, timeout=60)
j = r.json()
for s in j.get("series", {}).get("docs", []):
    print(s.get("series_code"), "|", s.get("series_name"), "|", list(zip(s.get("period", [])[-25:], s.get("value", [])[-25:])))
r = S.get("https://api.db.nomics.world/v22/series/AMECO/OVGD", params={"dimensions": json.dumps({"geo": ["deu"]}), "observations": 1, "limit": 20}, timeout=60)
for s in r.json().get("series", {}).get("docs", []):
    print(s.get("series_code"), "|", s.get("series_name"), "|", list(zip(s.get("period", [])[-12:], s.get("value", [])[-12:])))
hdr("OECD CIT")
r = S.get("https://sdmx.oecd.org/public/rest/dataflow/OECD.CTP.TPS/DSD_TAX_CIT@DF_CIT/latest", params={"references": "all"}, timeout=60)
print(r.status_code); dims = re.findall(r'<structure:Dimension id="([^"]+)"[^>]*position="(\d+)"', r.text); print(dims)
for key in ["DEU+FRA+ITA+USA+GBR+JPN+ESP+NLD.........", "DEU+FRA+ITA+USA+GBR+JPN+ESP+NLD........"]:
    rr = S.get(f"https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_TAX_CIT@DF_CIT,/{key}", params={"startPeriod": "2000", "format": "csvfile"}, timeout=60)
    print(key, rr.status_code, len(rr.text))
    if rr.ok:
        d = pd.read_csv(io.StringIO(rr.text), dtype=str)
        print(list(d.columns))
        for c in d.columns:
            if d[c].nunique() < 15: print("  ", c, d[c].unique()[:15])
        cols = [c for c in d.columns if c in ("REF_AREA", "TIME_PERIOD", "OBS_VALUE") or "MEASURE" in c or "TAX" in c]
        print(d[cols][d["TIME_PERIOD"].isin(["2000", "2010", "2025", "2026"])].head(80).to_string())
        break
