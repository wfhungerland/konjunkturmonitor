import re, requests
H = {"User-Agent": "konjunkturmonitor-probe", "Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"}
B = "https://api.statistiken.bundesbank.de/rest"
r = requests.get(f"{B}/metadata/dataflow/BBK", headers={"User-Agent": "x"}, timeout=60)
for fid, name in re.findall(r'<structure:Dataflow[^>]*id="([^"]+)".*?<common:Name xml:lang="de">([^<]+)</common:Name>', r.text, re.S):
    print("FLOW", fid, "|", name)
def scan(flow, pat, must=None, limit=80):
    x = requests.get(f"{B}/data/{flow}?detail=nodata", headers=H, timeout=240)
    n = 0
    for blk in re.findall(r"<generic:Series>(.*?)</generic:Series>", x.text, re.S):
        key = ".".join(re.findall(r'<generic:Value id="[^"]+" value="([^"]*)"', blk.split("</generic:SeriesKey>")[0]))
        t = (re.search(r'id="BBK_TITLE" value="([^"]*)"', blk) or [None, ""])[1]
        if re.search(pat, t, re.I) and (must is None or re.search(must, key)):
            n += 1
            if n <= limit: print(flow, key, "|", t[:170])
    print("SCAN", flow, x.status_code, n, flush=True)
scan("BBDE1", r"^(Produktion|Umsatz|Auftragseingang (Inland|Ausland)).*(Industrie|Produzierendes Gewerbe|Bauhauptgewerbe|Insgesamt /)", r"^M\.DE\.Y\..*\.(I21|I15)\.A$", 60)
scan("BBDE1", r"Einzelhandel|Gastgewerbe", r"^M\.DE\.Y", 20)
scan("BBDA1", r".", r"^M\.DE\.Y", 40)
for f in ["BBWAI", "BBEE1", "BBXE1", "BBDP2"]:
    try: scan(f, r"Aktivit|Wöchentlich", None, 10)
    except Exception as e: print("ERR", f, e)
