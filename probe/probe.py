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


gen_vars("62361-0010", None, startyear="2023")
gen_vars("62361-0001", None, startyear="2025")
hdr("GSCPI")
r = S.get("https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx", timeout=60)
x = pd.ExcelFile(io.BytesIO(r.content))
print(x.sheet_names)
for sh in x.sheet_names[:3]:
    d = pd.read_excel(x, sh, header=None)
    print("---", sh, d.shape); print(d.head(8).to_string()); print(d.tail(3).to_string())
