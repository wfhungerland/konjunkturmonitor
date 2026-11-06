"""Temporäre Probe 2: Terminsuche Destatis, BA-Termine."""
import re
import urllib.request


def get(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Konjunkturmonitor/1.0", "Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.geturl() + " || " + r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"FEHLER {e}"


def show(name, u, pat=r"\d{1,2}\.\s?\d{1,2}\.\s?2026|\d{1,2}\. (November|Dezember|Januar) 202[67]", n=12, w=260):
    t = get(u)
    b = re.sub(r"\s+", " ", re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S))
    print("==", name, len(t), t[:150])
    for m in list(re.finditer(pat, b))[:n]:
        print("…", re.sub(r"<[^>]+>", " | ", b[max(0, m.start() - w): m.start() + w]))
        print("----")


show("Destatis Terminsuche", "https://www.destatis.de/SiteGlobals/Forms/Suche/Termine/DE/Terminsuche_Formular.html?nn=250582")
show("Destatis Terminsuche Seite 2", "https://www.destatis.de/SiteGlobals/Forms/Suche/Termine/DE/Terminsuche_Formular.html?gtp=250592_list%253D2&nn=250582", n=4)
show("BA Statistik", "https://statistik.arbeitsagentur.de/DE/Navigation/Service/Veroeffentlichungskalender/Veroeffentlichungskalender-Nav.html", n=6)
show("BA Presse", "https://www.arbeitsagentur.de/presse/termine", n=6)
show("Eurostat Kalender", "https://ec.europa.eu/eurostat/news/release-calendar", n=4)
