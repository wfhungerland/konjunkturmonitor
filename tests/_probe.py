import os, re, io, zipfile, json, urllib.request, urllib.parse
def get(u, data=None, headers=None, raw=False):
    try:
        req = urllib.request.Request(u, data=data, headers=dict({"User-Agent": "Konjunkturmonitor/1.0"}, **(headers or {})))
        b = urllib.request.urlopen(req, timeout=180).read()
        return b if raw else b.decode("utf-8", "replace")
    except Exception as e:
        return (f"FEHLER {e}").encode() if raw else f"FEHLER {e}"
def show(t, s, n=1500): print("=====", t); print(s[:n] if isinstance(s, str) else s)
BB = "https://api.statistiken.bundesbank.de/rest"
CSV = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}
# Bundesbank: Liste der Datenflüsse roh
s = get(BB + "/metadata/dataflow/BBK", headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"})
ids = re.findall(r'<str:Dataflow[^>]*id="(\w+)"', s); nm = re.findall(r'<com:Name xml:lang="de">([^<]+)', s)
show("Dataflows", f"{len(ids)} " + " | ".join(f"{a}:{b}" for a, b in zip(ids, nm) if re.search(r"Tarif|Verdien|Lohn|Löhn|Arbeitsk", b)) + " ... alle ids: " + ",".join(ids), 3000)
for key in ("BBDL1/M.DE.N.TV.DN1.CA010.I", "BBDL1/M.DE..TV....", "BBDE1/M.DE.N.TV.DN1.CA010.I"):
    show("BB " + key, get(f"{BB}/data/{key}?lastNObservations=2", headers=CSV), 800)
# Echtzeit BIP: Anzahl Datenstände
s = get(f"{BB}/data/BBKRT/Q.DE.Y.A.AG1.CA010.A.I?startPeriod=2024-Q1", headers=CSV)
vint = sorted({".".join(l.split(";")[9:12]) for l in s.splitlines()[1:] if l})
show("BBKRT Datenstände", f"{len(vint)} {vint[:3]} ... {vint[-3:]}", 600)
s = get(f"{BB}/data/BBKRT/Q.DE.Y.A.AG1.CA010.A.I?startPeriod=2010-Q1&startVintage=2010-01-01&endVintage=2010-12-31", headers=CSV)
show("BBKRT 2010 Datenstände", f"{len(s.splitlines())} Zeilen " + s.splitlines()[1][:200] if len(s.splitlines()) > 1 else s, 600)
# GENESIS 13211-0007 entpackt
u, p = os.environ.get("GENESIS_USER", ""), os.environ.get("GENESIS_PASSWORD", "")
b = get("https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile", raw=True, data=urllib.parse.urlencode({"name": "13211-0007", "area": "all", "compress": "false", "format": "ffcsv", "language": "en", "startyear": "2025"}).encode(),
        headers={"username": u, "password": p, "Content-Type": "application/x-www-form-urlencoded"})
if b[:2] == b"PK":
    z = zipfile.ZipFile(io.BytesIO(b)); txt = z.read(z.namelist()[0]).decode("utf-8-sig", "replace").splitlines()
    show("GENESIS 13211-0007", "\n".join(txt[:6]) + f"\n... {len(txt)} Zeilen; Merkmale: " + str(sorted({tuple(l.split(";")[k] for k in (7, 9)) for l in txt[1:]})[:30]), 3500)
else: show("GENESIS 13211-0007", b[:500])
s = get("https://genesis.destatis.de/genesisWS/rest/2020/find/find", data=urllib.parse.urlencode({"term": "Tarifindex", "category": "tables", "language": "de"}).encode(),
        headers={"username": u, "password": p, "Content-Type": "application/x-www-form-urlencoded"})
show("GENESIS Suche Tarifindex", re.sub(r"\s+", " ", s), 2500)
# EZB SPF
E = "https://data-api.ecb.europa.eu/service/data/SPF"
for key in ("Q.U2.HICP.POINT.LT.Q.AVG", "Q.U2.HICP.POINT.P24M.Q.AVG", "Q.U2.HICP.POINT.Y2.Q.AVG", "Q.U2.HICP.POINT..Q.AVG"):
    s = get(f"{E}/{key}?format=csvdata&lastNObservations=2")
    show("SPF " + key, s if s.startswith("FEHLER") else "\n".join(s.splitlines()[:4])[:900], 900)
