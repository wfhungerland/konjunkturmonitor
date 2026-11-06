import os, re, io, json, urllib.request, urllib.parse
def get(u, data=None, headers=None, n=None):
    try:
        req = urllib.request.Request(u, data=data, headers=dict({"User-Agent": "Konjunkturmonitor/1.0"}, **(headers or {})))
        b = urllib.request.urlopen(req, timeout=120).read()
        return b.decode("utf-8", "replace")
    except Exception as e:
        return f"FEHLER {e}"
def show(t, s, n=700): print("=====", t); print(s[:n])
BB = "https://api.statistiken.bundesbank.de/rest"
# 1 Bundesbank: Datenflüsse mit Tarif/Echtzeit
df = get(BB + "/metadata/dataflow/BBK", headers={"Accept": "application/xml"})
names = re.findall(r'id="(\w+)"[^>]*>.*?<com:Name xml:lang="de">([^<]+)', df, re.S)
show("Dataflows Tarif/Echtzeit/Arbeit", "\n".join(f"{i}: {n}" for i, n in names if re.search(r"Tarif|Echtzeit|Arbeitsk|Löhn|Lohn|Verdienst", n)), 2000)
# 2 Tariflohn: Kandidaten
for flow in ("BBDL1", "BBDP1", "BBDE1", "BBEE1"):
    s = get(f"{BB}/data/{flow}?lastNObservations=1&detail=serieskeysonly", headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"})
    keys = [l.split(",")[0:12] for l in s.splitlines()[1:]]
    hits = [l for l in s.splitlines() if re.search(r"DN1|TV|CA010", l)]
    show(f"{flow}: {len(keys)} Reihen, Treffer DN1/CA010", "\n".join(hits[:15]) or s[:300], 2500)
# 3 Echtzeit BIP vierteljährlich
s = get(f"{BB}/data/BBKRT/Q.DE.?lastNObservations=1&lastNVintages=1&detail=serieskeysonly", headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"})
show("BBKRT Q Reihen mit AG1/BIP", "\n".join([l for l in s.splitlines() if "AG1" in l or "B1G" in l][:20]) or s[:600], 2500)
s = get(f"{BB}/data/BBKRT/Q.DE.Y.A.AG1.CA010.A.I?lastNVintages=3&lastNObservations=4", headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"})
show("BBKRT Versuch Q.DE.Y.A.AG1.CA010.A.I", s, 1500)
# 4 GENESIS 13211-0007
u, p = os.environ.get("GENESIS_USER", ""), os.environ.get("GENESIS_PASSWORD", "")
for tab in ("13211-0007", "13211-0005"):
    s = get("https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile", data=urllib.parse.urlencode({"name": tab, "area": "all", "compress": "false", "format": "ffcsv", "language": "en", "startyear": "2024"}).encode(),
            headers={"username": u, "password": p, "Content-Type": "application/x-www-form-urlencoded"})
    lines = s.splitlines()
    show(f"GENESIS {tab}: {len(lines)} Zeilen", "\n".join(lines[:4]), 1800)
# 5 Eurostat: Preiserwartungen Verbraucher, Lohnstückkosten
ES = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
s = get(f"{ES}/ei_bsco_m?geo=DE&format=JSON&lang=en&sinceTimePeriod=2026-01")
try:
    j = json.loads(s); show("ei_bsco_m indic", json.dumps(j["dimension"]["indic"]["category"]["label"], ensure_ascii=False), 2500)
except Exception as e: show("ei_bsco_m", s, 400)
s = get(f"{ES}/namq_10_lp_ulc?geo=DE&format=JSON&lang=en&sinceTimePeriod=2025-Q1")
try:
    j = json.loads(s); d = j["dimension"]; show("namq_10_lp_ulc", json.dumps({k: d[k]["category"]["label"] for k in ("unit", "na_item", "s_adj")}, ensure_ascii=False), 2500)
except Exception as e: show("namq_10_lp_ulc", s, 400)
# 6 EZB SPF
s = get("https://data-api.ecb.europa.eu/service/data/SPF/Q.U2.HICP..?format=csvdata&lastNObservations=1&detail=serieskeysonly")
show("SPF HICP Reihen", "\n".join(s.splitlines()[:40]), 3000)
