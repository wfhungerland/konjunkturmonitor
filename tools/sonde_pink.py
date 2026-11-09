"""Einmalige Sonde: Weltbank Pink Sheet (Link, Lizenz, Aufbau). Schreibt nichts."""
import io, re, urllib.request
import pandas as pd

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor-sonde"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

page = get("https://www.worldbank.org/en/research/commodity-markets").decode("utf-8", "replace")
links = sorted(set(re.findall(r'https://thedocs\.worldbank\.org/[^"\s]+\.xlsx', page)))
print("xlsx-Links:", links)
for m in re.finditer(r"(?i)(licen[cs]e|creative commons|cc[ -]by|terms of use)[^<]{0,160}", page):
    print("Lizenztext:", m.group(0))
url = next(l for l in links if "Monthly" in l and "Historical" in l)
x = pd.ExcelFile(io.BytesIO(get(url)))
print("Blätter:", x.sheet_names)
for sh in x.sheet_names:
    df = pd.read_excel(x, sh, header=None, nrows=8)
    print(f"\n## {sh} {df.shape}")
    print(df.fillna("").astype(str).iloc[:8, :12].to_csv(sep="|", index=False))
d = pd.read_excel(x, "Monthly Prices", header=None)
print("Letzte Zeilen:", d.iloc[-3:, :6].to_csv(sep="|", index=False))
desc = next((s for s in x.sheet_names if "escr" in s or "ndex" in s), None)
if desc:
    t = pd.read_excel(x, desc, header=None).fillna("").astype(str)
    for _, r in t.iterrows():
        s = " ".join(r.tolist())
        if re.search(r"(?i)licen|creative|copyright|terms", s):
            print("Beschreibung:", s[:300])
