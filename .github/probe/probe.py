import io, os, re, zipfile, requests
B = "https://genesis.destatis.de/genesisWS/rest/2020"
H = {"username": os.environ["GENESIS_USER"], "password": os.environ["GENESIS_PASSWORD"], "Content-Type": "application/x-www-form-urlencoded"}
for sel in ["52411*", "52311*"]:
    r = requests.post(f"{B}/catalogue/tables", data={"selection": sel, "area": "all", "pagelength": "100", "language": "de"}, headers=H, timeout=60)
    print("CAT", sel, r.status_code)
    try:
        for t in r.json().get("List", []) or []: print("  ", t.get("Code"), "|", t.get("Content", "")[:150].replace("\n", " "))
    except Exception: print(r.text[:400])
def head(code, start="2024"):
    r = requests.post(f"{B}/data/tablefile", data={"name": code, "area": "all", "compress": "false", "format": "ffcsv", "language": "de", "startyear": start}, headers=H, timeout=120)
    raw = r.content
    if raw[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(raw)); raw = z.read(z.namelist()[0])
    txt = raw.decode("utf-8", "replace")
    lines = [l for l in txt.splitlines() if l.strip()]
    print("TABLE", code, r.status_code, len(lines))
    for l in lines[:6]: print("   ", l[:400])
for code in ["52411-0001", "52411-0010", "52411-0012", "52411-0014", "52411-0020", "52311-0001", "52311-0010", "52311-0011"]:
    try: head(code)
    except Exception as e: print("ERR", code, e)
