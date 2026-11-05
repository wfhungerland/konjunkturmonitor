"""Temporäre Probe 2 für Paket B: Merkmalscodes der GENESIS-Tabellen 31111-0020 und 61262-0002, EZB-Schlüssel. Gibt keine Zugangsdaten aus."""
import io
import os
import urllib.parse
import urllib.request
import zipfile

import pandas as pd


def get(url, data=None, headers=None):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None,
                                 headers={"User-Agent": "Konjunkturmonitor/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


user, pw = os.environ.get("GENESIS_USER", ""), os.environ.get("GENESIS_PASSWORD", "")
for name, start in (("31111-0020", "2026"), ("61262-0002", "2025")):
    try:
        raw = get("https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile",
                  data={"name": name, "area": "all", "compress": "false", "format": "ffcsv", "startyear": start, "language": "de"},
                  headers={"username": user, "password": pw, "Content-Type": "application/x-www-form-urlencoded"})
        if raw[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(raw)); raw = z.read(z.namelist()[0])
        df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig")), sep=";", dtype=str)
        print("==", name, len(df), "Zeilen; Spalten:", list(df.columns))
        for i in range(1, 5):
            if f"{i}_variable_code" in df:
                g = df.groupby([f"{i}_variable_code", f"{i}_variable_attribute_code", f"{i}_variable_attribute_label"]).size()
                print(g.to_string()[:2500])
        if "value_variable_code" in df:
            print(df.groupby(["value_variable_code", "value_variable_label", "value_unit"]).size().to_string())
        print(df.head(3).to_string()[:1500])
    except Exception as e:
        print(name, "Fehler", e)

for k in ("MIR/M.DE.B.A2C.AM.R.A.2250.EUR.N", "BSI/M.DE.N.A.A22.A.I.U2.2250.Z01.A", "BSI/M.DE.N.A.A20.A.I.U2.2240.Z01.A"):
    f, _, key = k.partition("/")
    try:
        t = get(f"https://data-api.ecb.europa.eu/service/data/{f}/{key}?lastNObservations=1&format=csvdata&detail=full").decode()
        print("==", k, "|", t.splitlines()[1][:300])
    except Exception as e:
        print("==", k, "Fehler", e)
