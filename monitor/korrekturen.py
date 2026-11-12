"""Seite mit Korrekturen und Änderungen an Daten und Methoden (site/korrekturen.html) aus data/static/korrekturen.yaml."""
from __future__ import annotations

from html import escape
from pathlib import Path

import yaml

ART = {"Korrektur": "Fehler behoben", "Quelle": "Datenquelle geändert", "Methode": "Rechnung oder Darstellung geändert"}


def load(root: Path) -> list[dict]:
    p = root / "data" / "static" / "korrekturen.yaml"
    rows = (yaml.safe_load(p.read_text(encoding="utf-8")) or []) if p.exists() else []
    return sorted((dict(r, date=str(r["date"]), charts=list(r.get("charts") or [])) for r in rows), key=lambda r: r["date"], reverse=True)


def for_chart(rows: list[dict], chart: str) -> list[dict]:
    return [r for r in rows if chart in r["charts"]]


def _de(d: str) -> str:
    return f"{d[8:10]}.{d[5:7]}.{d[:4]}"


def write_page(rows: list[dict], payload: dict, out: Path) -> None:
    titles = {c["chart"]: (c.get("code") or f"Abb. {c.get('no')}", c.get("title", "")) for t in payload["topics"] for c in t["charts"] if c.get("chart")}
    repo = payload["site"].get("repo", "")

    def figs(r):
        if not r["charts"]:
            return "ganze Seite"
        return ", ".join(f'<a href="methodik/{escape(k, True)}.html">{escape(titles[k][0])} {escape(titles[k][1])}</a>' if k in titles else escape(k) for k in r["charts"])

    body = "".join(
        f"<tr><td class=nw>{_de(r['date'])}</td><td>{escape(r['art'])}<br><span class=small>{escape(ART.get(r['art'], ''))}</span></td>"
        f"<td>{figs(r)}</td><td>{escape(r['text'])}"
        + (f' <span class=small>(<a href="{escape(repo, True)}/pull/{int(r["pr"])}">Änderung #{int(r["pr"])}</a>)</span>' if r.get("pr") and repo else "")
        + "</td></tr>" for r in rows)
    (out / "korrekturen.html").write_text(f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Korrekturen und Änderungen · Konjunkturmonitor</title>
<style>
  @font-face {{ font-family: "Source Sans 3"; font-weight: 400; font-display: swap; src: url("fonts/source-sans-3-latin-400-normal.woff2") format("woff2"); }}
  @font-face {{ font-family: "Source Sans 3"; font-weight: 700; font-display: swap; src: url("fonts/source-sans-3-latin-700-normal.woff2") format("woff2"); }}
  body {{ margin: 0; background: #f7f7f5; color: #000; font: 17px/1.55 "Source Sans 3", "Segoe UI", system-ui, Arial, sans-serif; }}
  main {{ max-width: 60em; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 26px; }} a {{ color: #000; }} .back, .small {{ font-size: 13.5px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 15px; }} td, th {{ text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid #ddd; }}
  th {{ border-bottom: 1px solid #999; }} .nw {{ white-space: nowrap; }}
  @media (max-width: 640px) {{ table, tr, td {{ display: block; }} th {{ display: none; }} tr {{ border-bottom: 1px solid #999; padding: 6px 0; }} td {{ border: 0; padding: 2px 0; }} }}
</style></head>
<body><main>
<p class="back"><a href="./">← Zum Konjunkturmonitor</a></p>
<h1>Korrekturen und Änderungen</h1>
<p>Hier steht jede Änderung, die Zahlen oder Aussagen des Konjunkturmonitors berührt: behobene Fehler, neue Datenquellen und geänderte Rechnungen, jüngste zuerst. Reine Gestaltung fehlt. Wer frühere Stände nachrechnen will, findet sie in den <a href="{escape(repo, True)}/releases">wöchentlichen Archiven</a>.</p>
<table><tr><th>Datum</th><th>Art</th><th>Abbildung</th><th>Was sich geändert hat</th></tr>{body}</table>
</main></body></html>
""", encoding="utf-8")
