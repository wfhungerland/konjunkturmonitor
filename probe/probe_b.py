"""Temporäre Probe für Paket B: SMARD, Gas, GENESIS-Tabellen Bau und Häuserpreise, EZB-Zinsen und Kredite. Gibt keine Zugangsdaten aus."""
import json
import os
import urllib.parse
import urllib.request


def get(url, data=None, headers=None, n=600):
    try:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None,
                                     headers={"User-Agent": "Konjunkturmonitor/1.0", **(headers or {})})
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"FEHLER {e}"


print("== SMARD Index Verbrauch 410 monat:", get("https://www.smard.de/app/chart_data/410/DE/index_month.json")[:300])
print("== SMARD Index Preis 4169 monat:", get("https://www.smard.de/app/chart_data/4169/DE-LU/index_month.json")[:300])
idx = get("https://www.smard.de/app/chart_data/410/DE/index_month.json")
try:
    ts = json.loads(idx)["timestamps"]
    print("erste/letzte", ts[:2], ts[-2:])
    print(get(f"https://www.smard.de/app/chart_data/410/DE/410_DE_month_{ts[-1]}.json")[:400])
except Exception as e:
    print("SMARD", e)

print("== THE Verbrauch:", get("https://datenservice-api.tradinghub.eu/api/evoq/GetAggregierteVerbrauchsdatenTabelle?DatumStart=10-01-2026&DatumEnde=10-05-2026&GasXType_Id=all")[:600])
print("== AGSI ohne Schlüssel:", get("https://agsi.gie.eu/api?country=DE&size=2")[:300])

for k in ("MIR/M.DE.B.A2I.AM.R.A.2240.EUR.N", "MIR/M.DE.B.A2B.A.R.A.2250.EUR.N", "BSI/M.DE.N.A.A20.A.I.U2.2240.Z01.A", "BSI/M.DE.Y.U.A20.A.I.U2.2240.Z01.A", "BSI/M.DE.N.A.A22.A.I.U2.2250.Z01.A"):
    f, _, key = k.partition("/")
    t = get(f"https://data-api.ecb.europa.eu/service/data/{f}/{key}?lastNObservations=2&format=csvdata&detail=full")
    lines = t.splitlines()
    print("==", k, "|", (lines[1][:250] if len(lines) > 1 else t[:200]))

user, pw = os.environ.get("GENESIS_USER", ""), os.environ.get("GENESIS_PASSWORD", "")
for sel in ("31111*", "61262*", "61261*"):
    t = get("https://genesis.destatis.de/genesisWS/rest/2020/catalogue/tables", data={"selection": sel, "area": "all", "pagelength": "50", "language": "de"},
            headers={"username": user, "password": pw, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        for it in json.loads(t).get("List") or []:
            print(sel, it.get("Code"), "|", it.get("Content", "").replace("\n", " "), "|", it.get("Time"))
    except Exception:
        print(sel, t[:200])

for name, start in (("31111-0002", "2025"), ("61262-0001", "2024")):
    t = get("https://genesis.destatis.de/genesisWS/rest/2020/data/tablefile",
            data={"name": name, "area": "all", "compress": "false", "format": "ffcsv", "startyear": start, "language": "de"},
            headers={"username": user, "password": pw, "Content-Type": "application/x-www-form-urlencoded"})
    lines = t.splitlines()
    print("==", name, len(lines), "Zeilen")
    print("\n".join(lines[:4]))
    vals = sorted({";".join(l.split(";")[5:17:4]) for l in lines[1:]})
    print("Merkmale:", vals[:25])

print("== Destatis Terminvorschau:", get("https://www.destatis.de/DE/Presse/Termine/_inhalt.html")[:200].replace("\n", " "))
print("== Eurostat Kalender:", get("https://ec.europa.eu/eurostat/api/dissemination/catalogue/rss/de/statistics-update.rss")[:200].replace("\n", " "))
