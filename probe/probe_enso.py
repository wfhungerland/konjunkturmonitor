"""Temporäre Probe 2: Beginn der Reihen und Aufbau der GENESIS-Tabelle 61211-0003. Gibt keine Zugangsdaten aus."""
import os
import urllib.parse
import urllib.request


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None,
                                 headers={"User-Agent": "Konjunkturmonitor/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


t = get("https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt").decode().splitlines()
print("== RONI Kopf:", t[0])
for z in t:
    f = z.split()
    if len(f) >= 3 and f[1].isdigit() and 1981 <= int(f[1]) <= 1984:
        print(z)

for key in ("BBDP1/M.DE.N.EPL.L.L1A00000000.I20.A", "BBDP1/M.DE.N.VPI.C.C2C011.I20.A", "BBDP1/M.DE.N.VPI.C.A00000.I20.A"):
    flow, _, k = key.partition("/")
    try:
        d = get(f"https://api.statistiken.bundesbank.de/rest/data/{flow}/{k}?firstNObservations=2&format=csv", headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}).decode("utf-8", "replace")
        print("==", key, "\n", "\n".join(d.splitlines()[:4]))
    except Exception as e:
        print(key, "Fehler", e)

try:
    d = get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPALTT01DEM661N").decode()
    print("== FRED CPALTT01DEM661N", d.splitlines()[:3], d.splitlines()[-2:])
except Exception as e:
    print("FRED Fehler", e)

user, pw = os.environ.get("GENESIS_USER", ""), os.environ.get("GENESIS_PASSWORD", "")
try:
    raw = get("https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile",
              data={"name": "61211-0003", "area": "all", "compress": "false", "format": "ffcsv", "startyear": "1980", "endyear": "1983", "language": "de"},
              headers={"username": user, "password": pw, "Content-Type": "application/x-www-form-urlencoded"})
    if raw[:2] == b"PK":
        import io, zipfile
        raw = zipfile.ZipFile(io.BytesIO(raw)).read(zipfile.ZipFile(io.BytesIO(raw)).namelist()[0])
    lines = raw.decode("utf-8-sig", "replace").splitlines()
    print("== GENESIS 61211-0003:", len(lines), "Zeilen")
    print("\n".join(lines[:6]))
    print("…")
    print("\n".join(l for l in lines if "Insgesamt" in l or "insgesamt" in l)[:2500])
except Exception as e:
    print("GENESIS Fehler", e)
