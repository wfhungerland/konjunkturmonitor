import os, re, io, zipfile, urllib.request, urllib.parse
u, p = os.environ.get("GENESIS_USER", ""), os.environ.get("GENESIS_PASSWORD", "")
H = {"username": u, "password": p, "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Konjunkturmonitor/1.0"}
G = "https://genesis.destatis.de/genesisWS/rest/2020"
def post(path, **kw):
    try:
        return urllib.request.urlopen(urllib.request.Request(G + path, data=urllib.parse.urlencode(kw).encode(), headers=H), timeout=180).read()
    except Exception as e:
        return f"FEHLER {e}".encode()
for term in ("Arbeitslose Länder Monate", "Arbeitslosenquote Bundesländer Monate", "Arbeitslose Bundesländer Monate"):
    s = post("/find/find", term=term, category="tables", language="de").decode("utf-8", "replace")
    print("=====", term); print("\n".join(f"{c}: {t}" for c, t in re.findall(r'"Code":"([\d-]+)","Content":"([^"]+)"', s))[:2500])
for tab, yr in (("62231-0001", "2024"), ("13211-0002", "2025"), ("13211-0003", "2025"), ("13211-0009", "2025")):
    b = post("/data/tablefile", name=tab, area="all", compress="false", format="ffcsv", language="en", startyear=yr)
    if b[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(b)); txt = z.read(z.namelist()[0]).decode("utf-8-sig", "replace").splitlines()
        hdr = txt[0].split(";")
        print("=====", tab, len(txt), "Zeilen"); print(txt[0]); print("\n".join(txt[1:4]))
        cols = [i for i, h in enumerate(hdr) if h.endswith("_code") or h in ("time", "value_variable_code")]
        for i in cols:
            print(hdr[i], sorted({l.split(";")[i] for l in txt[1:] if len(l.split(";")) > i})[:25])
    else:
        print("=====", tab, b[:300])
