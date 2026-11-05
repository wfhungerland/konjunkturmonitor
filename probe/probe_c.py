"""Temporäre Probe: neue HVPI-Kennungen 2026 (Eurostat und EZB)."""
import urllib.request
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Konjunkturmonitor/1.0"}), timeout=90) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"FEHLER {e}"
for u in ["https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_minr?geo=FR&lastTimePeriod=2&format=JSON",
          "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr?geo=FR&lastTimePeriod=2&format=JSON",
          "https://data-api.ecb.europa.eu/service/data/ICP/M.FR.N..4.ANR?lastNObservations=1&format=csvdata",
          "https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=en"]:
    t = get(u)
    if "toc" in u:
        print("== TOC hicp:", "\n".join(l[:160] for l in t.splitlines() if "hicp" in l.lower() and ("anr" in l.lower() or "rate" in l.lower()))[:2500])
    elif "csvdata" in u:
        print("==", u, "\n", "\n".join(l[:120] for l in t.splitlines() if "000000" in l or "TOT" in l or "KEY" in l)[:1500])
    else:
        print("==", u, "\n", t[:1500])
