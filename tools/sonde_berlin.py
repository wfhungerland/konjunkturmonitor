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
for sel in ["61111-*", "45412-*", "45213-*", "45211-*", "31111-*", "13111-*", "42111-*", "81000-*", "82111-*"]:
    try:
        txt = post("catalogue/tables", selection=sel, area="all", pagelength="200", language="de")
        rows = re.findall(r'"Code"\s*:\s*"([^"]+)"\s*,\s*"Content"\s*:\s*"([^"]+)"', txt)
        print(f"\n## {sel}: {len(rows)} Tabellen")
        for code, content in rows:
            if re.search(r"Bundesl|Länder|Land", content):
                print(f"{code}\t{content[:150]}")
    except Exception as e:
        print(f"\n## {sel}: Fehler {type(e).__name__}: {str(e)[:200]}")
for name in ["61111-0011", "61111-0012", "61111-0013"]:
    try:
        txt = post("metadata/table", name=name, area="all", language="de")
        print(f"\n## Metadaten {name}:", re.sub(r"\s+", " ", txt)[:1200])
    except Exception as e:
        print(f"\n## Metadaten {name}: Fehler {e}")
for url in ["https://www.statistik-berlin-brandenburg.de/m-i-2-m",
            "https://download.statistik-berlin-brandenburg.de/",
            "https://www.statistikportal.de/de/vgrdl/ergebnisse-laenderebene/bruttoinlandsprodukt-bruttowertschoepfung",
            "https://statistik.arbeitsagentur.de/SiteGlobals/Forms/Suche/Einzelheftsuche_Formular.html?topic_f=monat-heft&r_f=bl_Berlin"]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor-sonde"})
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", "replace")
        links = sorted(set(re.findall(r'href="([^"]+\.(?:xlsx|xls|csv)[^"]*)"', body)))[:25]
        print(f"\n## {url}: HTTP {r.status}, {len(body)} Zeichen, Dateilinks: {links}")
    except Exception as e:
        print(f"\n## {url}: Fehler {e}")
