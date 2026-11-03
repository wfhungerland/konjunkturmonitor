import re, requests
H = {"User-Agent": "konjunkturmonitor-probe", "Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"}
B = "https://api.statistiken.bundesbank.de/rest"
# 1) Dataflows der Bundesbank
r = requests.get(f"{B}/metadata/dataflow/BBK", headers={"User-Agent": "x"}, timeout=60)
flows = re.findall(r'<structure:Dataflow[^>]*id="([^"]+)".*?<common:Name xml:lang="de">([^<]+)</common:Name>', r.text, re.S)
print("FLOWS", r.status_code, len(flows))
for fid, name in flows:
    if re.search(r"konjunktur|aktivit|produktion|auftr|umsatz|einzelhandel|außenhandel|aussenhandel|insolven|saison", name, re.I):
        print("  FLOW", fid, "|", name)
# 2) Titel in Kandidaten-Flows
pat = re.compile(r"Wöchentlich|Aktivitätsindex|Auftragseingang|Produktion|Umsatz|Einzelhandel|Ausfuhr|Einfuhr|Außenhandel|Insolvenz", re.I)
for flow in ["BBDE1", "BBDY1", "BBDL1", "BBDP1", "BBXP1", "BBKRT"]:
    if flow == "BBKRT": continue
    try:
        x = requests.get(f"{B}/data/{flow}?detail=nodata", headers=H, timeout=180)
        n = 0
        for blk in re.findall(r"<generic:Series>(.*?)</generic:Series>", x.text, re.S):
            key = ".".join(re.findall(r'<generic:Value id="[^"]+" value="([^"]*)"', blk.split("</generic:SeriesKey>")[0]))
            t = (re.search(r'id="BBK_TITLE" value="([^"]*)"', blk) or [None, ""])[1]
            if pat.search(t) and key.startswith(("M.", "W.", "D.", "Q.")) and (".Y." in key or key.startswith(("W.", "D."))):
                n += 1
                if n <= 60: print(flow, key, "|", t[:150])
        print("FLOW", flow, x.status_code, "Treffer", n, flush=True)
    except Exception as e:
        print("ERR", flow, e)
# 3) ifo-Zeitreihen
for ym in ["202610", "202609", "202611"]:
    for u in [f"https://www.ifo.de/sites/default/files/secure/timeseries/gsk-d-{ym}.xlsx"]:
        try:
            x = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=60); print("IFO", u, x.status_code, len(x.content), x.headers.get("content-type"))
        except Exception as e: print("IFO ERR", u, e)
x = requests.get("https://www.ifo.de/umfragen/zeitreihen", headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
print("IFO page", x.status_code, [l for l in re.findall(r'href="([^"]+)"', x.text) if re.search(r"xlsx|zeitreihe|gsk", l, re.I)][:25])
# 4) Eurostat
E = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
for q in ["ei_bsco_m?geo=DE&indic=BS-CSMCI&s_adj=SA&unit=BAL", "ei_bssi_m_r2?geo=DE&indic=BS-ESI-I&s_adj=SA", "ei_bsin_m_r2?geo=DE&indic=BS-ICI&s_adj=SA&unit=BAL",
          "sts_trtu_m?geo=DE&indic_bt=VOL_SLS&nace_r2=G47&s_adj=SCA&unit=I21", "sts_inpr_m?geo=DE&indic_bt=PRD&nace_r2=F&s_adj=SCA&unit=I21"]:
    x = requests.get(E + q + "&format=JSON&lastTimePeriod=2", timeout=60)
    try:
        j = x.json(); print("EUROSTAT", q.split("?")[0], x.status_code, list(j.get("value", {}).values())[-2:], list(j["dimension"]["time"]["category"]["index"])[-2:])
    except Exception as e: print("EUROSTAT", q, x.status_code, x.text[:200])
