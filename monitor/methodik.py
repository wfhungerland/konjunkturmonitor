"""Methodenblätter: je Abbildung eine eigenständige Seite mit Daten, Quellen, Rechenschritten und Methode (site/methodik/).

Jedes Blatt ist für sich verständlich und passt gedruckt auf eine A4-Seite. Es entsteht bei jedem Bau aus denselben
Angaben wie die Abbildung: Katalog (series.yaml), Seitenaufbau (monitor.yaml), Abrufprotokoll (run_status.json) und
von Hand gepflegten Methodentexten (data/static/methodik.yaml).
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import yaml

FREQ = {"M": "monatlich", "Q": "vierteljährlich", "A": "jährlich", "D": "wöchentlich", "B": "täglich (Arbeitstage)"}
SOURCE_NAMES = {"bundesbank": "Deutsche Bundesbank", "eurostat": "Eurostat", "genesis": "Statistisches Bundesamt (GENESIS-Online)",
                "fred": "FRED (Federal Reserve Bank of St. Louis)", "ecb": "Europäische Zentralbank", "static": "Datei im Repository",
                "gmd": "Global Macro Database", "derived": "eigene Berechnung"}

# Darstellung je Abbildungsart, in Alltagssprache
FORM = {
    "line": "Liniendiagramm über die Zeit. Jeder Wert steht in der Mitte seines Zeitraums (Monat, Quartal oder Jahr); fehlende Zeiträume bleiben Lücken.",
    "stacked": "Gestapelte Balken für die Beiträge einzelner Bestandteile, dazu eine Linie für die Gesamtgröße. Positive Beiträge stehen über, negative unter der Nulllinie; zusammen ergeben sie bis auf Rundung die Linie.",
    "threshold": "Liniendiagramm mit einer Schwelle (rot gestrichelt). Überschreitet die Linie die Schwelle, gilt das als Warnsignal.",
    "latest": "Waagerechte Balken, je Bereich einer, nach der Größe geordnet.",
    "forecast": "Punktreihe je Zieljahr: jeder Punkt ist die jüngste Prognose eines Herausgebers; das graue Feld reicht vom niedrigsten bis zum höchsten Wert.",
    "event": "Ereignisstudie: Verläufe ab einem Ausgangszeitpunkt übereinandergelegt, damit sich Episoden direkt vergleichen lassen.",
    "clock": "Konjunkturuhr: ein Punkt je Monat in einem Feld aus zwei Achsen; die Spur zeigt den Weg der letzten Monate.",
    "heat": "Wärmetabelle: Zeilen sind Branchen, Spalten Monate; die Farbe zeigt die Veränderung (orange Zunahme, blau Abnahme).",
    "heatbars": "Balken je Branche, umschaltbar zwischen zwei Vergleichen.",
    "tiles": "Karte der Länder; die Farbe zeigt die Veränderung, die Liste daneben ordnet die Länder.",
    "seasonal": "Monatswerte (dünn), gleitendes Zwölfmonatsmittel (dick) und das übliche Niveau desselben Monats vor Corona (gestrichelt).",
    "calendar": "Kalender der nächsten Veröffentlichungen mit Verweis auf die betroffenen Abbildungen.",
    "dumbbell": "Hantelgrafik: je Land ein hohler Punkt für das erste und ein voller Punkt für das jüngste Jahr, verbunden durch eine Linie.",
}

DERIVE = {
    "yoy_pct": "Veränderung gegenüber dem Vorjahr in Prozent: (Wert ÷ Wert desselben Zeitraums ein Jahr zuvor − 1) × 100.",
    "diff": "Differenz zweier Reihen: {a} minus {b}.",
    "sum": "Summe zweier Reihen: {a} plus {b}.",
    "sahm": "Rezessionssignal nach Michaillat und Saez: Dreimonatsmittel der Arbeitslosenquote (einschließlich Kurzarbeit in Vollzeitäquivalenten) minus ihr Tief der letzten zwölf Monate, und Hoch der Quote offener Stellen minus ihr Dreimonatsmittel; das Signal ist der kleinere der beiden Werte.",
    "acr": "Handelsgewinne nach Arkolakis, Costinot und Rodríguez-Clare: 1 − λ^(1/θ), λ = Inlandsanteil der Ausgaben.",
}


def _fmt_params(spec) -> str:
    p = {k: v for k, v in (spec.params or {}).items() if k not in ("source_name", "query", "aggregate", "scale")}
    if spec.source == "genesis":
        f = p.get("filters") or {}
        return f"Tabelle {spec.key}" + (f", Merkmal {p.get('value_variable')}" if p.get("value_variable") else "") + (", " + ", ".join(f"{k} = {v}" for k, v in f.items()) if f else "")
    if spec.source in ("eurostat", "ecb", "bundesbank", "fred"):
        return f"Datensatz {spec.key}" + (" (" + ", ".join(f"{k} = {v}" for k, v in p.items()) + ")" if p else "")
    if spec.source == "gmd":
        return f"Variable {spec.key}, Land {p.get('country', '')}"
    if spec.source == "static":
        return f"Datei data/static/{spec.key}.csv"
    if spec.source == "derived":
        return "abgeleitet"
    return spec.key


def chart_series_ids(c: dict, meta: dict, status_ids) -> list[str]:
    """Reihen, auf denen eine Abbildung beruht (dieselbe Logik wie die Statusprüfung)."""
    ids = []
    if isinstance(c.get("series"), list):
        ids += [s.get("id") for s in c["series"] if isinstance(s, dict) and s.get("id") in meta]
    elif isinstance(c.get("series"), str):
        ids.append(c["series"])
    ids += [s.id for s in meta.values() if s.chart_id == c.get("chart") and s.id not in ids]
    if c.get("type") == "tiles":
        ids += sorted(k for k in status_ids if k.startswith(c.get("prefix", "@")) and k not in ids)[:3]
    if c.get("type") == "event":
        from .build import HIST_PANELS
        hist = [x for p in (c.get("panels") or HIST_PANELS) for x in (p["hist"], p["cur"])]
        ids += [k for k in ({"downturn": ["de_ip", "de_alq_sa", "de_gdp_index"], "history": hist}
                            .get(c.get("kind"), ["enso_roni", "de_vpi", "de_vpi_food", "de_agri"])) if k not in ids]
    for k in ("x", "y", "total", "fx"):
        if isinstance(c.get(k), str) and c[k] in meta and c[k] not in ids:
            ids.append(c[k])
    out, seen = [], set()
    for i in ids:  # abgeleitete Reihen: Ausgangsreihen mitnehmen
        stack = [i]
        while stack:
            k = stack.pop(0)
            if k in seen or k not in meta:
                continue
            seen.add(k)
            out.append(k)
            d = meta[k].derive or {}
            stack += [v for v in [d.get("from"), d.get("minus"), d.get("plus")] + list((d.get("with") or {}).values()) if v]
    return out


def _steps(c: dict, meta: dict, ids: list[str]) -> list[str]:
    st = []
    for k in ids:
        d = meta[k].derive or {}
        if d.get("op") in DERIVE:
            a = meta.get(d.get("from")) or meta[k]
            b = meta.get(d.get("minus") or d.get("plus") or "")
            st.append(f"<b>{escape(meta[k].label or meta[k].title)}</b>: " + escape(DERIVE[d["op"]].format(a=a.title, b=b.title if b else "")))
    if c.get("transform") == "yoy":
        st.append("Die Niveaus werden in Veränderungsraten gegenüber dem Vorjahr umgerechnet: (Wert ÷ Wert ein Jahr zuvor − 1) × 100.")
    if c.get("transform") == "sum12":
        st.append("Monatswerte werden zur Summe der jeweils letzten zwölf Monate zusammengefasst; das gleicht saisonale Schwankungen aus.")
    if c.get("scale") and float(c["scale"]) != 1:
        st.append(f"Umrechnung der Einheit mit dem Faktor {str(c['scale']).replace('.', ',')} (Anzeige in {escape(c.get('unit', ''))}).")
    if c.get("fx"):
        f = c.get("fx_factor")
        st.append("Umrechnung von US-Dollar in Euro: Wert ÷ Monatsmittel des EZB-Referenzkurses (US-Dollar je Euro)" + (f" ÷ {str(f).replace('.', ',')} (MWh je MMBtu)" if f else "") + ".")
    if c.get("transform") == "cagr10":
        st.append("Durchschnittliches jährliches Wachstum über zehn Jahre: ((Wert ÷ Wert zehn Jahre zuvor) hoch 1/10 − 1) × 100.")
    if c.get("blank_years"):
        st.append("Ausgelassene Jahre (Lücke statt Werte): " + ", ".join(f"{a} bis {b}" for a, b in c["blank_years"]) + ".")
    if c.get("crises"):
        st.append("Graue Bänder: Jahre mit Bankenkrise nach der Datierung der Global Macro Database.")
    if c.get("long_mean"):
        st.append("Vergleichswert im Satz: einfacher Durchschnitt aller gezeigten Jahre.")
    if c.get("ma3"):
        st.append("Gleitender Dreimonatsdurchschnitt (dicke Linie): Mittel aus dem Monat und den beiden Monaten davor. Die dünne Linie zeigt die Monatswerte.")
    if c.get("norm"):
        st.append(f"Vergleichsmarke je Monat: Mittel desselben Kalendermonats der Jahre {c['norm'][0]} bis {c['norm'][1]}.")
    if c.get("ref_mean"):
        st.append(f"Graue Referenzlinie: Mittel der Jahre {c['ref_mean'][0]} bis {c['ref_mean'][1]}.")
    if c.get("mad_band"):
        st.append("Graues Band: mittlere absolute Korrektur, also der Durchschnitt der Korrekturen ohne Vorzeichen über den gezeigten Zeitraum.")
    if c.get("type") == "latest" and c.get("base"):
        st.append("Veränderung seit dem Stichtag: jüngster Wert minus Wert am Stichtag; in Klammern dieselbe Veränderung in Prozent des Stands am Stichtag.")
    if c.get("type") == "latest" and not c.get("base"):
        st.append("Veränderung gegenüber der Vorperiode in Prozent; die Raute zeigt die Veränderung der Periode davor.")
    if c.get("type") == "tiles":
        st.append("Je Land die Summe der jüngsten zwölf (umschaltbar: sechs) Monate gegenüber derselben Summe ein Jahr zuvor, in Prozent." if (c.get("tiles") or {}).get("measure") != "diff"
                  else "Je Land der Jahresdurchschnitt der Quote; die Farbe zeigt die Veränderung gegenüber dem Vorjahr in Prozentpunkten.")
    if c.get("type") == "heat":
        st.append("Je Branche und Monat die Veränderung gegenüber dem Vorjahresmonat in Prozent. Rechte Spalten: Dreimonatsvergleich (letzte drei Monate gegenüber den drei Monaten davor) und Niveau gegenüber dem Durchschnitt 2019.")
    if c.get("type") == "heatbars":
        st.append("Dreimonatsvergleich: Mittel der letzten drei Monate gegenüber dem Mittel der drei Monate davor, in Prozent. Niveau gegenüber 2019: jüngster Monat gegenüber dem Durchschnitt des Jahres 2019, in Prozent.")
    if c.get("type") == "seasonal":
        st.append("Gleitendes Zwölfmonatsmittel: Mittel des Monats und der elf Monate davor. Übliches Niveau: Mittel desselben Kalendermonats 2015 bis 2019.")
    if c.get("type") == "clock":
        st.append("Beide Salden als Abstand zu ihrem Mittel 2005 bis 2019. Waagerecht die Beurteilung der Aufträge, senkrecht die Produktionserwartungen der nächsten drei Monate.")
    if c.get("type") == "forecast":
        st.append("Je Herausgeber gilt die jüngste veröffentlichte Prognose. Prognosen, die älter als vier Monate sind, erscheinen heller.")
    if c.get("type") == "event" and c.get("kind") == "history" and any(p.get("mode") == "level" for p in c.get("panels") or []):
        st.append("Ausgangsjahr jeder Episode ist das Jahr des Inflationshochs; gezeigt ist die Jahresrate selbst in den folgenden Jahren.")
    elif c.get("type") == "event" and c.get("kind") in ("downturn", "history"):
        st.append("Index: Wert ÷ Wert im Ausgangszeitpunkt (Hoch) × 100. Arbeitslosenquote: Wert minus Wert im Ausgangszeitpunkt, in Prozentpunkten.")
    if c.get("type") == "stacked":
        st.append("Wachstumsbeiträge in Prozentpunkten: Veränderung eines Bestandteils, gewichtet mit seinem Anteil an der Gesamtgröße der Vorperiode. Gruppen (etwa Konsum) sind die Summe ihrer Bestandteile.")
    if c.get("refs"):
        st.append("Referenzwerte (grau gestrichelt): " + "; ".join(escape(str(r.get("label", ""))) for r in c["refs"]) + ".")
    if c.get("ref") not in (None, 0):
        st.append(f"Blau gestrichelt: Zielwert {str(c['ref']).replace('.', ',')}.")
    if c.get("threshold") is not None:
        st.append(f"Rot gestrichelt: Schwelle {str(c['threshold']).replace('.', ',')}.")
    st.append("Gerundet wird erst für die Anzeige; Berechnungen nutzen die ungerundeten Werte der Quelle.")
    return st


def _page(c: dict, topic: dict, meta: dict, status: dict, texts: dict, payload: dict, lic_of=lambda s: s.license, corr: list | None = None) -> str:
    corr = corr or []
    ids = chart_series_ids(c, meta, status.keys())
    stand = payload.get("stand", "")
    stand_de = f"{stand[8:10]}.{stand[5:7]}.{stand[:4]}" if len(stand) >= 10 else stand
    title = c.get("title", "")
    no = c.get("no")
    lic = c.get("content_license") or "CC BY 4.0"
    lic_url = "https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de" if "NC-SA" in lic else "https://creativecommons.org/licenses/by/4.0/deed.de"
    rows, notes, got = [], [], []
    more = max(0, len(ids) - 8)  # gleich gebaute Reihen (Länder, Branchen): die ersten acht zeigen
    for k in ids[:8]:
        s, r = meta[k], status.get(k, {})
        src = (s.params or {}).get("source_name") or SOURCE_NAMES.get(s.source, s.source)
        api = r.get("api_url") or s.link
        ken = escape(_fmt_params(s))
        ken = f'<a href="{escape(api, True)}">{ken}</a>' if api else ken
        sub = "" if not s.title or s.title.startswith(s.label or "@") else f"<br><span class=small>{escape(s.title)}</span>"
        got.append(str(r.get("retrieved_at", ""))[:10])
        rows.append(
            f"<tr><td><b>{escape(s.label or s.title)}</b>{sub}</td><td>{escape(src)}<br><span class=small>{ken}</span></td>"
            f"<td>{escape(s.unit)}<br><span class=small>{FREQ.get(s.frequency, s.frequency)}, {escape(s.adjustment)}</span></td>"
            f"<td class=small>{escape(str(r.get('first', ''))[:7])} bis {escape(str(r.get('last', ''))[:7])}</td>"
            f"<td class=small>{escape(lic_of(s) or '')}</td></tr>")
        if s.note and s.note not in notes:
            notes.append(s.note)
    if more:
        rows.append(f"<tr><td colspan=5 class=small>und {more} weitere Reihen gleicher Bauart aus derselben Quelle</td></tr>")
    if c.get("type") == "forecast":
        rows += [f"<tr><td colspan=5>{escape(x)}</td></tr>" for x in c.get("sources") or []]
    t = texts.get(c.get("chart"), {}) if isinstance(texts.get(c.get("chart")), dict) else {}
    method = t.get("methode") or ""
    limits = list(t.get("grenzen") or [])
    if c.get("warn"):
        limits.insert(0, c["warn"])
    for n in c.get("notes") or []:
        limits.append(f"{n.get('date', '')[:7]}: {n.get('text', '')}")
    limits.append("Amtliche Daten werden nachträglich überarbeitet; die Abbildung zeigt immer den jüngsten Datenstand der Quelle.")
    form = FORM.get(c.get("type") or "line", FORM["line"])
    if c.get("multiples"):
        form = "Kleine Einzeldiagramme (Small Multiples), je Reihe eines; die übrigen Reihen stehen grau dahinter. Die Skala ist gemeinsam oder je Feld umschaltbar."
    years = c.get("years")
    window = f"Zeitfenster: rund {years} Jahre." if years and c.get("type") in (None, "line", "stacked", "threshold") else ""
    files = c.get("files") or {}
    dl = " · ".join(f'<a href="../{escape(v, True)}">{k.upper()}</a>' for k, v in files.items() if isinstance(v, str))
    cite = f"{payload['site'].get('author', '')} ({stand[:4]}): Konjunkturmonitor, Abb. {no} {title}. Stand {stand_de}. {payload['site'].get('url', '')}"
    steps = "".join(f"<li>{x}</li>" for x in _steps(c, meta, ids))
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Methodenblatt Abb. {no}: {escape(title)} · Konjunkturmonitor</title>
<style>
@font-face {{ font-family: "Source Sans 3"; font-weight: 400; src: url("../fonts/source-sans-3-latin-400-normal.woff2") format("woff2"); }}
@font-face {{ font-family: "Source Sans 3"; font-weight: 700; src: url("../fonts/source-sans-3-latin-700-normal.woff2") format("woff2"); }}
@font-face {{ font-family: "Source Sans 3"; font-style: italic; font-weight: 400; src: url("../fonts/source-sans-3-latin-400-italic.woff2") format("woff2"); }}
body {{ font-family: "Source Sans 3", "Segoe UI", Arial, sans-serif; color: #000; background: #fff; max-width: 820px; margin: 24px auto; padding: 0 16px; font-size: 15px; line-height: 1.45; }}
h1 {{ font-size: 22px; margin: 4px 0 2px; }} h2 {{ font-size: 16px; margin: 18px 0 4px; border-bottom: 1px solid #ccc; padding-bottom: 2px; }}
.top {{ font-size: 13px; }} .small {{ font-size: 12.5px; }} a {{ color: #000; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13.5px; }} td, th {{ vertical-align: top; text-align: left; padding: 4px 6px; border-bottom: 1px solid #e2e2e2; }}
th {{ font-weight: 700; border-bottom: 1px solid #999; }} tr.note td {{ border-bottom: 1px solid #e2e2e2; padding-top: 0; font-style: italic; }}
ol, ul {{ margin: 4px 0; padding-left: 20px; }} li {{ margin: 2px 0; }} .ask {{ font-size: 17px; font-weight: 700; }}
@media print {{ @page {{ size: A4; margin: 10mm 12mm; }} body {{ margin: 0; max-width: none; font-size: 8.6pt; line-height: 1.28; }} h1 {{ font-size: 13.5pt; margin: 2pt 0; }} h2 {{ font-size: 10pt; margin: 6pt 0 2pt; }}
  p {{ margin: 2pt 0; }} table {{ font-size: 7.2pt; }} td, th {{ padding: 1pt 3pt; }} .small {{ font-size: 7pt; }} .ask {{ font-size: 10pt; }} a {{ text-decoration: none; }} .noprint {{ display: none; }} li {{ margin: 0; }} }}
</style></head><body>
<p class="top">Konjunkturmonitor · Methodenblatt · Stand {stand_de} · Abschnitt {escape(topic.get('title', ''))} <span class="noprint">· <a href="../index.html#abb-{no}">zur Abbildung</a> · <a href="index.html">alle Methodenblätter</a></span></p>
<h1>Abb. {no}: {escape(title)}</h1>
<p class="ask">{escape(c.get('ask') or (topic.get('question') or {}).get('ask', ''))}</p>
<h2>Kurz gesagt</h2>
<p>{escape(c.get('text', ''))}</p>
<p class="small">Die Sätze entstehen bei jedem Datenabruf automatisch aus den jüngsten Werten.</p>
<h2>Was die Abbildung zeigt</h2>
<p>{escape(c.get('caption', ''))}</p>
<p class="small">Darstellung: {escape(form)} {escape(window)} Einheit: {escape(str(c.get('unit', '')))}. {('Häufigkeit: ' + FREQ.get(c.get('freq'), '') + '.') if c.get('freq') in FREQ else ''}</p>
<h2>Daten und Quellen</h2>
<table><tr><th>Reihe</th><th>Quelle und Kennung</th><th>Einheit</th><th>Zeitraum</th><th>Lizenz</th></tr>{''.join(rows)}</table>
<p class="small">{('Abgerufen am ' + max(g for g in got if g) + '. ') if any(got) else ''}{('Angaben der Quelle: ' + ' '.join(escape(n) for n in notes)) if notes else ''}</p>
<h2>Rechenschritte</h2>
<ol>{steps}</ol>
{f'<h2>Methode</h2><p>{escape(method)}</p>' if method else ''}
<h2>Grenzen und Hinweise</h2>
<ul>{''.join(f'<li>{escape(x)}</li>' for x in limits)}</ul>
{('<h2>Änderungen</h2><ul>' + ''.join(f"<li>{r['date'][8:10]}.{r['date'][5:7]}.{r['date'][:4]}, {escape(r['art'])}: {escape(r['text'])}</li>" for r in corr) + '</ul><p class="small noprint"><a href="../korrekturen.html">Alle Korrekturen und Änderungen</a></p>') if corr else ''}
<h2>Zitieren und weiterverwenden</h2>
<p class="small">Zitiervorschlag: {escape(cite)}<br>Lizenz der Abbildung: <a href="{lic_url}">{escape(lic)}</a>; die Daten unterliegen den oben genannten Lizenzen der Quellen.<br>Berechnet mit dem Code-Stand {escape(c.get('_code', ''))}. Frühere Datenstände: <a href="{escape(payload['site'].get('repo', ''), True)}/releases">wöchentliche Archive</a>.{('<br>Downloads: ' + dl) if dl else ''}</p>
</body></html>
"""


def write_method_pages(payload: dict, meta: dict, root: Path, out: Path, lic_of=None) -> int:
    """Schreibt site/methodik/<abbildung>.html und eine Übersicht; gibt die Zahl der Blätter zurück."""
    st_path = root / "data" / "processed" / "run_status.json"
    status = {s["series_id"]: s for s in json.loads(st_path.read_text(encoding="utf-8")).get("series", [])} if st_path.exists() else {}
    tp = root / "data" / "static" / "methodik.yaml"
    texts = (yaml.safe_load(tp.read_text(encoding="utf-8")) or {}).get("charts", {}) if tp.exists() else {}
    from .korrekturen import for_chart, load as load_corr
    corr = load_corr(root)
    d = out / "methodik"
    d.mkdir(parents=True, exist_ok=True)
    items = []
    for topic in payload["topics"]:
        for c in topic["charts"]:
            if not c.get("chart"):
                continue
            (d / f"{c['chart']}.html").write_text(_page(c, topic, meta, status, texts, payload, lic_of or (lambda s: s.license), for_chart(corr, c["chart"])), encoding="utf-8")
            items.append(f'<li><a href="{escape(c["chart"])}.html">Abb. {c.get("no")}: {escape(c.get("title", ""))}</a></li>')
    (d / "index.html").write_text(f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Methodenblätter · Konjunkturmonitor</title><style>body {{ font-family: "Source Sans 3", Arial, sans-serif; max-width: 820px; margin: 24px auto; padding: 0 16px; line-height: 1.5; }} a {{ color: #000; }}</style></head>
<body><p><a href="../index.html">Konjunkturmonitor</a></p><h1>Methodenblätter</h1>
<p>Je Abbildung ein Blatt mit Daten, Quellen, Rechenschritten und Methode. Jedes Blatt ist für sich verständlich und lässt sich auf eine A4-Seite drucken.</p>
<ol>{''.join(items)}</ol></body></html>""", encoding="utf-8")
    return len(items)
