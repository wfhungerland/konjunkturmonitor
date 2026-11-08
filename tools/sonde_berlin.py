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

for sel in ["45212-*"]:
    txt = post("catalogue/tables", selection=sel, area="all", pagelength="200", language="de")
    for code, content in re.findall(r'"Code"\s*:\s*"([^"]+)"\s*,\s*"Content"\s*:\s*"([^"]+)"', txt):
        print(f"{code}\t{content[:150]}")


def walk(o, depth=0):
    if isinstance(o, dict):
        if o.get("Type") == "Merkmal":
            print("  " * depth + f"- {o.get('Code')}: {o.get('Content')} ({o.get('Values')})")
        for v in o.values():
            walk(v, depth + 1)
    elif isinstance(o, list):
        for v in o:
            walk(v, depth)


import json
for name in ["45412-0025", "45213-0014", "31111-0120", "61111-0021", "13111-0005", "45212-0011", "45212-0012", "45212-0014", "45212-0015"]:
    try:
        j = json.loads(post("metadata/table", name=name, area="all", language="de"))
        print(f"\n## {name}: {(j.get('Object') or {}).get('Content')} {(j.get('Object') or {}).get('Time')}")
        walk(j.get("Object"))
    except Exception as e:
        print(f"\n## {name}: Fehler {e}")
for var in ["BAUTK1", "GEBAT1", "BAU004", "BAU005", "BAU002", "PREIS1", "WERT01"]:
    try:
        txt = post("catalogue/values2variable", name=var, area="all", pagelength="60", language="de")
        vals = re.findall(r'"Code"\s*:\s*"([^"]+)"\s*,\s*"Content"\s*:\s*"([^"]+)"', txt)
        print(f"\n## Werte {var}:", vals[:40])
    except Exception as e:
        print(f"\n## Werte {var}: Fehler {e}")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor-sonde"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


page = get("https://www.statistik-berlin-brandenburg.de/m-i-2-m").decode("utf-8", "replace")
be = sorted(set(re.findall(r'https://download\.statistik-berlin-brandenburg\.de/[^"]+_BE\.xlsx', page)))[-1]
for url in [be, "https://www.statistikportal.de/sites/default/files/2026-09/vgrdl_hjr_bs2026_0.xlsx",
            "https://www.statistikportal.de/sites/default/files/2026-03/vgrdl_r1b1_bs2025.xlsx"]:
    try:
        x = pd.ExcelFile(io.BytesIO(get(url)))
        print(f"\n## {url}\nBlätter: {x.sheet_names}")
        for sh in x.sheet_names[:12]:
            df = x.parse(sh, header=None, nrows=60)
            if df.empty:
                continue
            txt = df.fillna("").astype(str)
            hit = txt.apply(lambda r: r.str.contains("Berlin|Nahrung|Energie|Kraftstoff|Gaststätt|Verbraucherpreisindex|Deutschland|Halbjahr", regex=True)).any(axis=1)
            print(f"\n### Blatt {sh}: {df.shape}")
            for i in list(range(min(6, len(df)))) + list(txt[hit].index[:25]):
                print(i, " | ".join(v[:28] for v in txt.iloc[i].tolist()[:12]))
    except Exception as e:
        print(f"\n## {url}: Fehler {e}")
