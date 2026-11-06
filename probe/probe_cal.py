"""Temporäre Probe: Aufbau der Veröffentlichungskalender (Destatis, BA, Eurostat)."""
import re
import urllib.request


def get(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 Konjunkturmonitor/1.0"})
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        return f"FEHLER {e}"


t = get("https://www.destatis.de/DE/Presse/Termine/_inhalt.html")
print("== Destatis Länge", len(t))
for m in re.finditer(r"(ics|ical|rss|Terminvorschau|Woche|Monat)[^\"<]{0,80}", t, re.I):
    pass
links = sorted(set(re.findall(r'href="([^"]*(?:ics|ical|rss|termin|Termin)[^"]*)"', t)))
print("Links:", links[:40])
i = t.find("Termin")
body = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", "", t, flags=re.S))
for kw in ("2026", "November"):
    for m in list(re.finditer(kw, body))[:8]:
        print("…", body[max(0, m.start() - 200): m.start() + 300])
        print("----")
b = get("https://statistik.arbeitsagentur.de/DE/Navigation/Service/Veroeffentlichungskalender/Veroeffentlichungskalender-Nav.html")
bb = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", "", b, flags=re.S))
print("== BA Länge", len(b))
for m in list(re.finditer(r"\d{2}\.\d{2}\.2026", bb))[:10]:
    print("…", bb[max(0, m.start() - 150): m.start() + 200])
    print("----")
e = get("https://ec.europa.eu/eurostat/api/dissemination/catalogue/rss/en/release-calendar.rss")
print("== Eurostat RSS", e[:800])
