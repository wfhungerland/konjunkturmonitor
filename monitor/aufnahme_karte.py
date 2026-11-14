"""Aufnahmefähigkeit der Kreise: Karte der Baukapazität im Kreis und im Einzugsgebiet.

Zwei Karten mit gleicher Skala (Index Bund = 100, Beschäftigte im Baugewerbe je 1.000 Einwohner): links im Kreis
selbst, rechts im Einzugsgebiet (monitor.aufnahme_einzug). Kreisgrenzen: GISCO NUTS 2024, 1:3 Mio., ETRS89-LAEA.

    python -m monitor.aufnahme_karte [--cache <ordner>] [--ziel docs]

Schreibt aufnahme_karte.html (SVG mit Hover, heller und dunkler Modus) und für die Monitor-Seite
data/static/aufnahme_karte.json (vereinfachte Kreisgrenzen und Werte, Abbildungstyp „kreise“). Nur Standardbibliothek.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import urllib.request
from pathlib import Path

DATEN = Path(__file__).resolve().parent.parent / "data" / "static"
GISCO = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_03M_2024_3035_LEVL_{e}.geojson"

# Divergierend um den Bundeswert: Rot = weniger, Blau = mehr, Grau = nahe 100 (95 bis unter 105)
KLASSEN = [(0, 60, "unter 60"), (60, 80, "60 bis unter 80"), (80, 95, "80 bis unter 95"),
           (95, 105, "95 bis unter 105"), (105, 120, "105 bis unter 120"), (120, 140, "120 bis unter 140"),
           (140, 10_000, "140 und mehr")]
HELL = ["#a8302f", "#e34948", "#f3aba7", "#e4e2dc", "#9ec5f4", "#3987e5", "#1c5cab"]
DUNKEL = ["#f28b86", "#e66767", "#7d3634", "#45443f", "#2b5c95", "#3987e5", "#9ec5f4"]


def _geo(cache: Path, ebene: int) -> dict:
    datei = cache / f"nuts_rg_03m_2024_3035_l{ebene}.geojson"
    if not datei.exists():
        cache.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(GISCO.format(e=ebene), headers={"User-Agent": "konjunkturmonitor"})
        with urllib.request.urlopen(req, timeout=120) as r:
            datei.write_bytes(r.read())
    return json.loads(datei.read_text(encoding="utf-8"))


def _ringe(geom: dict):
    if geom["type"] == "Polygon":
        yield from geom["coordinates"]
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            yield from poly


def _pfad(geom: dict, abb) -> str:
    teile = []
    for ring in _ringe(geom):
        punkte, letzter = [], None
        for x, y in ring:
            p = abb(x, y)
            if p != letzter:
                punkte.append(p)
                letzter = p
        if len(punkte) >= 3:
            teile.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in punkte) + "Z")
    return "".join(teile)


def _vereinfachen(punkte: list, toleranz: float) -> list:
    """Douglas-Peucker ohne Rekursion; behält Anfang und Ende."""
    if len(punkte) < 4:
        return punkte
    behalten = [False] * len(punkte)
    behalten[0] = behalten[-1] = True
    stapel = [(0, len(punkte) - 1)]
    while stapel:
        a, b = stapel.pop()
        (x1, y1), (x2, y2) = punkte[a], punkte[b]
        dx, dy = x2 - x1, y2 - y1
        n2 = dx * dx + dy * dy
        best, idx = -1.0, None
        for i in range(a + 1, b):
            px, py = punkte[i]
            if n2 == 0:
                d = (px - x1) ** 2 + (py - y1) ** 2
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / n2))
                d = (px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2
            if d > best:
                best, idx = d, i
        if idx is not None and best > toleranz * toleranz:
            behalten[idx] = True
            stapel += [(a, idx), (idx, b)]
    return [p for p, k in zip(punkte, behalten) if k]


def monitor_json(cache: Path, ziel: Path, breite: int = 1000, toleranz: float = 0.6) -> None:
    """Kreisgrenzen (vereinfacht, ganzzahlig auf 1.000 Einheiten Breite) und Werte für die Monitor-Seite."""
    werte = {r["nuts3"]: r for r in csv.DictReader((DATEN / "aufnahme_einzug.csv").open(encoding="utf-8"))}
    bund = sum(float(r["svb_wz_f_baugewerbe_kreis"]) for r in werte.values()) * 1000 / \
        sum(float(r["bevoelkerung"]) for r in werte.values())
    kreise = [f for f in _geo(cache, 3)["features"] if f["properties"]["CNTR_CODE"] == "DE"]
    xs = [x for f in kreise for ring in _ringe(f["geometry"]) for x, _ in ring]
    ys = [y for f in kreise for ring in _ringe(f["geometry"]) for _, y in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    m = breite / (x1 - x0)

    def pfad(geom) -> str:
        teile = []
        for ring in _ringe(geom):
            pk = _vereinfachen([((x - x0) * m, (y1 - y) * m) for x, y in ring], toleranz)
            pk = [(round(a), round(b)) for a, b in pk]
            pk = [p for i, p in enumerate(pk) if i == 0 or p != pk[i - 1]]
            if len(pk) >= 4:
                teile.append("M" + "L".join(f"{a},{b}" for a, b in pk) + "Z")
        return "".join(teile)

    aus = []
    for f in sorted(kreise, key=lambda f: f["properties"]["NUTS_ID"]):
        r = werte.get(f["properties"]["NUTS_ID"])
        if not r:
            continue
        aus.append({"id": r["nuts3"], "name": r["name"], "d": pfad(f["geometry"]),
                    "kreis": round(100 * float(r["je_1000_kreis"]) / bund, 1), "einzug": float(r["index_einzug_bund_100"]),
                    "je_kreis": float(r["je_1000_kreis"]), "je_einzug": float(r["je_1000_einzug"]),
                    "geschaetzt": r.get("kreiswert_geschaetzt") == "1"})
    daten = {"breite": breite, "hoehe": round((y1 - y0) * m), "bund": round(bund, 1), "stichtag": "2026-03",
             "halbwertszeit": 28, "unit": "Index, Bund = 100", "unit_en": "Index, Germany = 100", "kreise": aus}
    ziel.write_text(json.dumps(daten, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(aus)} Kreise, {ziel.stat().st_size / 1e6:.2f} MB")


def _klasse(wert: float) -> int:
    return next(i for i, (lo, hi, _) in enumerate(KLASSEN) if lo <= wert < hi)


def zeichnen(cache: Path, ziel: Path) -> None:
    werte = {r["nuts3"]: r for r in csv.DictReader((DATEN / "aufnahme_einzug.csv").open(encoding="utf-8"))}
    bund = sum(float(r["svb_wz_f_baugewerbe_kreis"]) for r in werte.values()) * 1000 / \
        sum(float(r["bevoelkerung"]) for r in werte.values())
    kreise = [f for f in _geo(cache, 3)["features"] if f["properties"]["CNTR_CODE"] == "DE"]
    laender = _geo(cache, 0)["features"]

    xs = [x for f in kreise for ring in _ringe(f["geometry"]) for x, _ in ring]
    ys = [y for f in kreise for ring in _ringe(f["geometry"]) for _, y in ring]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    breite = 420.0
    m = breite / (x1 - x0)
    hoehe = (y1 - y0) * m

    def abb(x, y):
        return (round((x - x0) * m, 1), round((y1 - y) * m, 1))

    def karte(spalte: str, titel: str, kennung: str) -> str:
        rand = 8
        nachbarn = "".join(
            f'<path class="nachbar" d="{_pfad(f["geometry"], abb)}"/>' for f in laender
            if f["properties"]["CNTR_CODE"] != "DE")
        flaechen = []
        for f in kreise:
            k = f["properties"]["NUTS_ID"]
            r = werte.get(k)
            if not r:
                continue
            if spalte == "kreis":
                index = 100 * float(r["je_1000_kreis"]) / bund
                je = float(r["je_1000_kreis"])
            else:
                index = float(r["index_einzug_bund_100"])
                je = float(r["je_1000_einzug"])
            hinweis = " (Kreiswert geschätzt)" if r.get("kreiswert_geschaetzt") == "1" else ""
            text = f"{r['name']}: Index {index:.0f}, {je:.1f} je 1.000 Einwohner{hinweis}"
            flaechen.append(f'<path class="k{_klasse(index)}" d="{_pfad(f["geometry"], abb)}" '
                            f'data-t="{html.escape(text)}"><title>{html.escape(text)}</title></path>')
        return (f'<figure><figcaption>{titel}</figcaption>'
                f'<svg id="{kennung}" viewBox="{-rand} {-rand} {breite + 2 * rand:.0f} {hoehe + 2 * rand:.0f}" '
                f'role="img" aria-label="{html.escape(titel)}">'
                f'<clipPath id="c{kennung}"><rect x="{-rand}" y="{-rand}" width="{breite + 2 * rand:.0f}" '
                f'height="{hoehe + 2 * rand:.0f}"/></clipPath><g clip-path="url(#c{kennung})">{nachbarn}</g>'
                f'<g class="kreise">{"".join(flaechen)}</g></svg></figure>')

    legende = "".join(f'<span><i class="k{i}"></i>{t}</span>' for i, (*_, t) in enumerate(KLASSEN))
    css_klassen = "\n".join(f"  .k{i} {{ fill: var(--k{i}); }}" for i in range(len(KLASSEN)))
    tokens_hell = " ".join(f"--k{i}: {c};" for i, c in enumerate(HELL))
    tokens_dunkel = " ".join(f"--k{i}: {c};" for i, c in enumerate(DUNKEL))
    seite = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Baukapazität der Kreise</title>
<style>
  :root {{ --flaeche: #fcfcfb; --seite: #f9f9f7; --tinte: #0b0b0b; --tinte2: #52514e; --leise: #898781;
          --grenze: #fcfcfb; --nachbar: #ecebe6; {tokens_hell} }}
  @media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --flaeche: #1a1a19; --seite: #0d0d0d;
          --tinte: #f0efec; --tinte2: #c3c2b7; --grenze: #1a1a19; --nachbar: #2c2c2a; {tokens_dunkel} }} }}
  :root[data-theme="dark"] {{ --flaeche: #1a1a19; --seite: #0d0d0d; --tinte: #f0efec; --tinte2: #c3c2b7;
          --grenze: #1a1a19; --nachbar: #2c2c2a; {tokens_dunkel} }}
  body {{ margin: 0; background: var(--seite); color: var(--tinte); font: 14px/1.45 system-ui, sans-serif; }}
  main {{ max-width: 980px; margin: 0 auto; padding: 24px 16px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  p {{ color: var(--tinte2); margin: 0 0 12px; max-width: 70ch; }}
  .karten {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;
            background: var(--flaeche); padding: 16px; border-radius: 8px; }}
  figure {{ margin: 0; }}
  figcaption {{ font-weight: 600; margin-bottom: 6px; }}
  svg {{ width: 100%; height: auto; display: block; }}
  .nachbar {{ fill: var(--nachbar); stroke: var(--grenze); stroke-width: 0.6; }}
  .kreise path {{ stroke: var(--grenze); stroke-width: 0.5; cursor: default; }}
  .kreise path:hover, .kreise path.an {{ stroke: var(--tinte); stroke-width: 1.5; paint-order: stroke; }}
{css_klassen}
  .legende {{ display: flex; flex-wrap: wrap; gap: 6px 14px; margin: 12px 0 4px; color: var(--tinte2); }}
  .legende i {{ display: inline-block; width: 14px; height: 10px; border-radius: 2px; margin-right: 6px;
               vertical-align: -1px; }}
  .legende i.k0 {{ background: var(--k0); }} .legende i.k1 {{ background: var(--k1); }}
  .legende i.k2 {{ background: var(--k2); }} .legende i.k3 {{ background: var(--k3); }}
  .legende i.k4 {{ background: var(--k4); }} .legende i.k5 {{ background: var(--k5); }}
  .legende i.k6 {{ background: var(--k6); }}
  #info {{ min-height: 1.5em; color: var(--tinte); font-variant-numeric: tabular-nums; }}
  .quelle {{ font-size: 12px; color: var(--leise); margin-top: 12px; }}
</style>
</head>
<body>
<main>
<h1>Baukapazität der Kreise: im Kreis und im Einzugsgebiet</h1>
<p>Sozialversicherungspflichtig Beschäftigte im Baugewerbe (WZ F) je 1.000 Einwohner, Index Bund = 100
({bund:.1f} je 1.000). Rechts verteilt auf die Kreise, die sie nach Fahrzeit erreichen
(Halbwertszeit 28 Minuten, aus den TED-Bauzuschlägen geschätzt).</p>
<div class="legende" aria-label="Legende">{legende}</div>
<div id="info" aria-live="polite">Kreis berühren oder antippen für Werte.</div>
<div class="karten">
{karte("kreis", "Im Kreis", "a")}
{karte("einzug", "Im Einzugsgebiet", "b")}
</div>
<p class="quelle">Quellen: BA, Regionalreport über Beschäftigte, Arbeitsort, Stichtag 31.03.2026; Destatis,
Bevölkerung 31.12.2024; TED-Bauzuschläge 2025-2026; Fahrzeiten OSRM/OpenStreetMap; Grenzen © EuroGeographics
(GISCO). Gesperrte BA-Werte in 13 Kreisen aus den Bauberufen geschätzt. Methode: docs/aufnahme.md.</p>
</main>
<script>
  const info = document.getElementById("info");
  document.querySelectorAll(".kreise path").forEach(p => {{
    const zeige = () => {{ info.textContent = p.dataset.t; }};
    p.addEventListener("mouseenter", zeige);
    p.addEventListener("click", zeige);
  }});
</script>
</body>
</html>
"""
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / "aufnahme_karte.html").write_text(seite, encoding="utf-8")
    print(f"{len(kreise)} Kreise gezeichnet")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m monitor.aufnahme_karte")
    ap.add_argument("--cache", type=Path, default=Path(".cache_gisco"))
    ap.add_argument("--ziel", type=Path, default=Path("docs"))
    a = ap.parse_args(argv)
    zeichnen(a.cache, a.ziel)
    monitor_json(a.cache, DATEN / "aufnahme_karte.json")


if __name__ == "__main__":
    main(sys.argv[1:])
