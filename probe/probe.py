"""Einmalige Erkundung: Reallohnindex (GENESIS) und GSCPI (NY Fed) (wird wieder entfernt)."""
import io, os, re, subprocess, sys
import pandas as pd, requests
from konjunkturwolf.fetchers import GENESIS_BASE, genesis_text

S = requests.Session()
AUTH = {"username": os.environ["GENESIS_USER"], "password": os.environ["GENESIS_PASSWORD"],
        "Content-Type": "application/x-www-form-urlencoded"}

def hdr(t): print("\n" + "=" * 20, t, flush=True)

for name, start in [("62361-0010", "2023"), ("62361-0001", "2025")]:
    hdr(f"GENESIS {name}")
    r = S.post(f"{GENESIS_BASE}/data/tablefile", timeout=300, headers=AUTH,
               data={"name": name, "area": "all", "compress": "false", "format": "ffcsv", "language": "en", "startyear": start})
    t = genesis_text(r.content).lstrip("﻿")
    lines = t.splitlines()
    i = next((k for k, l in enumerate(lines[:60]) if l.count(";") >= 3 and "time" in l.lower()), None)
    df = pd.read_csv(io.StringIO("\n".join(lines[i:])), sep=";", dtype=str, keep_default_na=False)
    print(list(df.columns))
    keep = [c for c in df.columns if "variable" in c or c in ("value_unit",)]
    print(df[keep].drop_duplicates().head(40).to_string())
    print(df.tail(6).to_string())

hdr("GSCPI")
r = S.get("https://www.newyorkfed.org/medialibrary/research/interactives/gscpi/downloads/gscpi_data.xlsx", timeout=60)
print(r.status_code, r.headers.get("content-type"), r.content[:8])
for eng in ("openpyxl", "xlrd"):
    try:
        if eng == "xlrd":
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xlrd"], check=False)
        x = pd.ExcelFile(io.BytesIO(r.content), engine=eng)
        print("engine", eng, x.sheet_names)
        for sh in x.sheet_names[:3]:
            d = pd.read_excel(x, sh, header=None)
            print("---", sh, d.shape); print(d.head(8).to_string()); print(d.tail(3).to_string())
        break
    except Exception as e:
        print("engine", eng, "Fehler", e)
