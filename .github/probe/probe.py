import io, os, re, zipfile, requests
B = "https://genesis.destatis.de/genesisWS/rest/2020"
H = {"username": os.environ["GENESIS_USER"], "password": os.environ["GENESIS_PASSWORD"], "Content-Type": "application/x-www-form-urlencoded"}
r = requests.post(f"{B}/catalogue/tables", data={"selection": "52411*", "area": "all", "pagelength": "100", "language": "de"}, headers=H, timeout=60)
for t in r.json().get("List", []) or []:
    if "Bundesl" in t.get("Content", "") or "Land" in t.get("Content", ""): print("CAT", t.get("Code"), "|", t.get("Content", "")[:150].replace("\n", " "))
import collections
def codes(code, start="2025"):
    r = requests.post(f"{B}/data/tablefile", data={"name": code, "area": "all", "compress": "false", "format": "ffcsv", "language": "de", "startyear": start}, headers=H, timeout=180)
    raw = r.content
    if raw[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(raw)); raw = z.read(z.namelist()[0])
    lines = [l.split(";") for l in raw.decode("utf-8", "replace").splitlines() if l.strip()]
    hdr = lines[0]; print("TABLE", code, r.status_code, len(lines), hdr[5:])
    seen = collections.defaultdict(set)
    for row in lines[1:]:
        d = dict(zip(hdr, row))
        for k in hdr:
            if k.endswith("_attribute_code") or k == "value_variable_code":
                seen[k].add((d.get(k), d.get(k.replace("_code", "_label")) if k != "value_variable_code" else d.get("value_variable_label")))
    for k, v in seen.items(): print("  ", k, sorted(v)[:25])
for code in ["52311-0110", "52311-0130"]:
    try: codes(code)
    except Exception as e: print("ERR", code, e)
