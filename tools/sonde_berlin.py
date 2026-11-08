"""Einmalige Sonde: welche Tabellen und Seiten für einen Berlin-Abschnitt taugen (nur Ausgabe, schreibt nichts)."""
import os, re, sys, urllib.request, urllib.parse

B = "https://genesis.destatis.de/genesisWS/rest/2020"
H = {"username": os.environ.get("GENESIS_USER", ""), "password": os.environ.get("GENESIS_PASSWORD", ""),
     "Content-Type": "application/x-www-form-urlencoded"}


def post(path, **data):
    req = urllib.request.Request(f"{B}/{path}", data=urllib.parse.urlencode(data).encode(), headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


if not H["username"]:
    sys.exit("keine GENESIS-Zugangsdaten")
import io
import pandas as pd

for name in ["61111-0011", "61111-0021", "45412-0025", "45213-0014", "45212-0014", "31111-0120", "13111-0005"]:
    try:
        txt = post("data/tablefile", name=name, area="all", compress="false", format="ffcsv", language="en", startyear="2025")
        lines = txt.splitlines()
        h = next(i for i, l in enumerate(lines[:60]) if l.count(";") >= 3 and ("time" in l.lower()))
        df = pd.read_csv(io.StringIO("\n".join(lines[h:])), sep=";", dtype=str, keep_default_na=False)
        print(f"\n## Daten {name}: {df.shape}\nSpalten: {list(df.columns)}")
        for c in df.columns:
            if c.endswith("attribute_code") or c.endswith("variable_code") or c in ("time", "value_unit", "value_variable_code", "time_code"):
                u = sorted(df[c].unique())
                print(f"  {c}: {len(u)} -> {u[:40]}")
        print(df.head(3).to_csv(sep="|", index=False))
    except Exception as e:
        print(f"\n## Daten {name}: Fehler {type(e).__name__} {str(e)[:300]}")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor-sonde"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


page = get("https://www.statistik-berlin-brandenburg.de/m-i-2-m").decode("utf-8", "replace")
be = sorted(set(re.findall(r'https://download\.statistik-berlin-brandenburg\.de/[^"]+_BE\.xlsx', page)))[-1]
x = pd.ExcelFile(io.BytesIO(get(be)))
for sh in ["3", "5", "6", "7", "8"]:
    df = pd.read_excel(x, sh, header=None).astype(object)
    print(f"\n## AfS Blatt {sh}: {df.shape}")
    for i, row in df.iterrows():
        vals = ["" if pd.isna(v) else str(v).replace("\n", " ")[:22] for v in row.tolist()[:14]]
        if any(vals):
            print(i, "|".join(vals))
