"""Downloads je Abbildung: Excel (Daten und Diagramm), PowerPoint-Folie (bearbeitbares Diagramm), CSV.

Die Folie nutzt den leeren Standard-Folienmaster von PowerPoint (Office-Design, 16:9, 33,867 × 19,05 cm),
Layout „Nur Titel“: Titel im Titelplatzhalter, darunter Untertitel, Einheit, Diagramm, Quellenzeile und Fußzeile.
So lässt sich die Folie in jede eigene Vorlage übernehmen.
Diagramme nach dem Grafikstandard: Werteachse rechts, feine graue Gitterlinien, Legende oben links,
keine Überschrift im Diagramm, Arial Narrow, Hausfarben.
"""
from __future__ import annotations

import copy
from datetime import datetime
import re
from pathlib import Path

import pandas as pd

from konjunkturwolf.downloads import stata_name

PALETTE = ["#002060", "#0070C0", "#00B0F0", "#51154A", "#7030A0", "#D86DCD", "#47D359"]
FONT = "Arial Narrow"
GRID = "#BFBFBF"
MUTED = "#576164"
BAR_PALETTE = ["#0070C0", "#D86DCD", "#00B0F0", "#51154A", "#47D359", "#7030A0", "#002060"]  # kontrastreich für gestapelte Balken
CONTENT_LICENSE = "Abbildung und Erläuterung: CC BY 4.0, Wolf-Fabian Hungerland, Konjunkturmonitor (https://creativecommons.org/licenses/by/4.0/deed.de)"
# Abbildungen mit Daten unter ShareAlike-Lizenz (Global Macro Database) übernehmen deren Lizenz
NCSA_LICENSE = "Abbildung, Erläuterung und Daten: CC BY-NC-SA 4.0, Wolf-Fabian Hungerland, Konjunkturmonitor, nach der Global Macro Database (https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de)"

# Geometrie auf dem Standard-Folienmaster 16:9 (EMU); Titel steht im Titelplatzhalter des Layouts „Nur Titel“
SLIDE_W, SLIDE_H = 12192000, 6858000
LEFT, WIDTH = 609600, 10972800
OVERTITLE = (LEFT, 120000, WIDTH, 220000)
SUB = (LEFT, 1440000, WIDTH, 300000)
UNIT = (LEFT, 1760000, WIDTH, 260000)
CHART = (LEFT, 2030000, WIDTH, 3880000)
SOURCE = (LEFT, 5960000, WIDTH, 300000)
FOOT_L = (LEFT, 6356350, 5800000, 365125)
FOOT_R = (6500000, 6356350, 4000000, 365125)
NUMBER = (10600000, 6356350, 982400, 365125)


# ---------------------------------------------------------------------------
# Tabelle je Abbildung
# ---------------------------------------------------------------------------
def _ma3(y: list) -> list:
    s = pd.Series(y, dtype=float)
    return s.rolling(3).mean().round(4).tolist()


def chart_table(c: dict) -> tuple[pd.DataFrame, dict]:
    """Breite Tabelle und Beschreibung, wie die Abbildung zu zeichnen ist.

    plan: kind (line, stacked, threshold, hbar, scatter, columns, tiles), lines/bars (Spaltennamen),
    thin (nur dünn zu zeichnende Spalten), emphasis, dashed.
    """
    typ = c.get("type", "line")
    if typ in ("line", "threshold", "stacked", "dumbbell") and c.get("series"):
        cols, thin, bars, lines = {}, [], [], []
        for s in c["series"]:
            x = pd.to_datetime(s["x"])
            if c.get("ma3") and s.get("style") != "bar":
                cols[s["label"] + " (Monatswert)"] = pd.Series(s["y"], index=x)
                cols[s["label"]] = pd.Series(_ma3(s["y"]), index=x)
                thin.append(s["label"] + " (Monatswert)")
                lines.append(s["label"])
            elif s.get("req"):  # Projektion: gemeldete und nötige Quartale in getrennten Spalten
                k, need = len(s["y"]) - s["req"], s["label"] + " (nötig für die Projektion)"
                cols[s["label"]] = pd.Series(s["y"][:k] + [None] * s["req"], index=x)
                cols[need] = pd.Series([None] * k + s["y"][k:], index=x)
                bars += [s["label"], need]
            else:
                cols[s["label"]] = pd.Series(s["y"], index=x)
                (bars if s.get("style") == "bar" else lines).append(s["label"])
        df = pd.DataFrame(cols).sort_index()
        dashed = []
        for key, label in (("ref", "Referenz"), ("threshold", "Schwelle")):
            if c.get(key) is not None:
                name = f"{label} ({str(c[key]).replace('.', ',')})"
                df[name] = c[key]
                lines.append(name)
                dashed.append(name)
        for r in c.get("refs") or []:  # Referenzwerte mit eigener Beschriftung, etwa Maastricht-Grenzen
            df[r["label"]] = r["y"]
            if r.get("x0"):  # Referenz erst ab diesem Datum, etwa ein Jahresziel
                df.loc[df.index < pd.Timestamp(r["x0"]), r["label"]] = None
            lines.append(r["label"])
            dashed.append(r["label"])
        df.index.name = "Datum"
        emph = next((s["label"] for s in c["series"] if s["id"] == c.get("emphasis")), None)
        kind = "stacked" if bars and typ == "stacked" else ("columns" if bars and not lines else "line")
        if bars and lines and typ != "stacked":
            kind = "stacked"
        return df.reset_index(), {"kind": kind, "bars": bars, "lines": lines + thin, "thin": thin, "emphasis": emph, "dashed": dashed}
    if typ == "latest" and c.get("bars"):
        df = pd.DataFrame({"Bereich": [b["label"] for b in c["bars"]],
                           c.get("bar_name", "Letztes Quartal"): [b["value"] for b in c["bars"]],
                           "Quartal davor": [b["prev"] for b in c["bars"]]})
        if df["Quartal davor"].isna().all():
            df = df.drop(columns="Quartal davor")
        return df.iloc[::-1].reset_index(drop=True), {"kind": "hbar"}
    if typ == "seasonal":
        x = pd.to_datetime(c["x"])
        df = pd.DataFrame({"Monatswert": c["y"], "Gleitendes Zwölfmonatsmittel": c["ma12"],
                           "Vorkrisenniveau (Mittel desselben Monats 2016 bis 2019)": c["norm"]}, index=x)
        df.index.name = "Datum"
        return df.reset_index(), {"kind": "line", "lines": list(df.columns[0:]), "thin": ["Monatswert"],
                                  "emphasis": "Gleitendes Zwölfmonatsmittel", "dashed": ["Vorkrisenniveau (Mittel desselben Monats 2016 bis 2019)"]}
    if typ == "clock" and c.get("clock"):
        k = c["clock"]
        df = pd.DataFrame({"Monat": k["t"], "Lage (Auftragsbestand)": k["x"], "Erwartungen (Produktion)": k["y"]})
        return df, {"kind": "scatter"}
    if typ == "forecast" and c.get("forecasts"):
        latest = [f for f in c["forecasts"] if f.get("latest")]
        years = sorted({y for f in latest for y in f["values"]})
        df = pd.DataFrame({"Herausgeber": [f"{f['by']} ({f['round']})" for f in latest],
                           **{str(y): [f["values"].get(y) for f in latest] for y in years}})
        return df, {"kind": "columns_cat"}
    if typ == "calendar" and c.get("calendar"):
        ev = c["calendar"]["events"]
        df = pd.DataFrame({"Datum (geschätzt)": [e["date"] for e in ev], "Veröffentlichung": [e["name"] for e in ev], "Quelle": [e["source"] for e in ev]})
        return df, {"kind": "list"}
    if typ == "enso_comm" and c.get("enso"):
        E = c["enso"]
        rows = [{"Rohstoff": r["label"], f"nach El Niño, % ggü. Vorjahr ({E['lag']} Monate später)": r["nino"], "nach neutralen Monaten, %": r["neutral"],
                 "Monate El Niño": r["n_nino"], "Monate neutral": r["n_neutral"], "t-Wert": r["t"], "deutlich (|t| > 1,96)": "ja" if r["sig"] else "nein"} for r in E["rows"]]
        return pd.DataFrame(rows), {"kind": "list"}
    if typ == "event" and c.get("event"):
        rows = [{"Größe": p["title"], "Ereignis": l["label"] + (" (laufend)" if l["current"] else ""), "Beginn": l["start"], "Monat": x, "Index (Monat 0 = 100)": y}
                for p in c["event"]["panels"] for l in p["lines"] for x, y in zip(l["x"], l["y"])]
        return pd.DataFrame(rows), {"kind": "list"}
    if typ == "heatbars" and c.get("heat"):
        h = c["heat"]
        df = pd.DataFrame({"Branche": [r["label"] for r in h["rows"]],
                           "Dreimonatsvergleich, %": [r["m3"] for r in h["rows"]],
                           "Niveau gegenüber 2019, %": [r["level"] for r in h["rows"]]})
        return df.iloc[::-1].reset_index(drop=True), {"kind": "table"}
    if typ == "heat" and c.get("heat"):
        h = c["heat"]
        df = pd.DataFrame({"Branche": [r["label"] for r in h["rows"]],
                           **{pd.to_datetime(d).strftime("%m/%Y"): [r["values"].get(d) for r in h["rows"]] for d in h["cols"]},
                           "Dreimonatsvergleich, %": [r["m3"] for r in h["rows"]],
                           "Niveau gegenüber 2019, %": [r["level"] for r in h["rows"]]})
        return df.iloc[::-1].reset_index(drop=True), {"kind": "table"}
    if typ == "tiles" and c.get("tiles") and c["tiles"].get("measure") == "diff":
        rows = c["tiles"]["rows"]
        df = pd.DataFrame({"Land": [r["name"] for r in rows], "Kürzel": [r["abbr"] for r in rows],
                           f"Wert {c['tiles']['span']}, %": [r["level"] for r in rows],
                           "Veränderung gegenüber Vorjahr, Pp": [r["change"] for r in rows]})
        return df, {"kind": "tiles"}
    if typ == "tiles" and c.get("tiles"):
        rows = c["tiles"]["rows"]
        df = pd.DataFrame({"Land": [r["name"] for r in rows], "Kürzel": [r["abbr"] for r in rows],
                           f"Summe {c['tiles']['span']}": [r["sum"] for r in rows],
                           "Veränderung gegenüber Vorjahreszeitraum, %": [r["change"] for r in rows]})
        if c.get("tiles6"):
            m6 = {r["abbr"]: r["change"] for r in c["tiles6"]["rows"]}
            df[f"Veränderung, letzte 6 Monate ({c['tiles6']['span']}), %"] = df["Kürzel"].map(m6)
        return df, {"kind": "tiles"}
    return pd.DataFrame(), {"kind": "none"}


def header_lines(c: dict) -> tuple[str, str]:
    typ = c.get("type")
    if typ in ("clock", "forecast"):
        sub = ""
    elif typ == "tiles":
        sub = ("Jahr " if c.get("tiles", {}).get("measure") == "diff" else "Summe ") + c["tiles"]["span"] if c.get("tiles") else ""
    else:
        freq = {"Q": "Vierteljährlich", "A": "Jährlich", "D": "Wöchentlich", "B": "Täglich (Arbeitstage)"}.get(c.get("freq"), "Monatlich")
        sub = " · ".join(x for x in (freq, c.get("adjustment")) if x)
    unit = {"clock": "Saldo in Prozentpunkten, Abstand zum Mittel 2005 bis 2019", "forecast": "% gegenüber Vorjahr, BIP real",
            "tiles": "Veränderung gegenüber demselben Zeitraum ein Jahr zuvor, %"}.get(typ, ("Saldo in Prozentpunkten (Anteil positiver minus Anteil negativer Antworten)" + c["unit"][5:]) if (c.get("unit") or "").startswith("Saldo") else c.get("unit") or "")
    if typ == "tiles" and c.get("tiles", {}).get("measure") == "diff":
        unit = f"Quote {c['tiles']['span']} in %; Veränderung gegenüber dem Vorjahr in Prozentpunkten"
    return sub, unit


def source_line(c: dict) -> str:
    src = "Quelle: " + ", ".join(c.get("sources") or [])
    if c.get("licenses"):
        src += ". Lizenz: " + "; ".join(c["licenses"])
    if c.get("type") == "tiles" and GEO:
        src += ". Ländergrenzen: © GeoBasis-DE / BKG (VG2500), dl-de/by-2-0"
    return src


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def write_xlsx(c: dict, df: pd.DataFrame, plan: dict, path: Path, stand: str, cite: str) -> None:
    title = f"Abb. {c['no']} {c.get('title', '')}"
    sub, unit = header_lines(c)
    with pd.ExcelWriter(path, engine="xlsxwriter", datetime_format="yyyy-mm-dd") as xw:
        wb = xw.book
        bold = wb.add_format({"bold": True, "font_name": FONT, "font_size": 12})
        norm = wb.add_format({"font_name": FONT, "font_color": MUTED})
        wrap = wb.add_format({"font_name": FONT, "text_wrap": True, "valign": "top"})
        sn = c.get("_sheet", "Daten")
        sheet = wb.add_worksheet("Grafik")
        sheet.hide_gridlines(2)
        sheet.write(0, 0, c.get("_stem", title), bold)
        sheet.write(1, 0, " · ".join(x for x in (sub, unit) if x), norm)
        sheet.write(24, 0, c.get("caption", ""), norm)
        sheet.write(25, 0, source_line(c), norm)
        df.to_excel(xw, sheet_name=sn, index=False, startrow=3)
        ws = xw.sheets[sn]
        ws.write(0, 0, c.get("_stem", title), bold)
        ws.write(1, 0, source_line(c), norm)
        ws.set_column(0, 0, 16)
        ws.set_column(1, max(1, len(df.columns) - 1), 18)
        chart = _xlsx_chart(wb, df, plan, c)
        if chart is not None:
            sheet.insert_chart(3, 0, chart)
        info = wb.add_worksheet("Quelle")
        info.set_column(0, 0, 22)
        info.set_column(1, 1, 110)
        for r, (k, v) in enumerate([("Datei", c.get("_stem", "")), ("Abbildung", title), ("Zeitraum und Bereinigung", sub), ("Einheit", unit),
                                    ("Erläuterung", c.get("caption", "")), ("Quelle", source_line(c)),
                                    ("Datenstand", c.get("datenstand", "")), ("Abrufdatum", stand), ("Zitiervorschlag", cite), ("Code-Stand", c.get("_code", "")), ("Lizenz", NCSA_LICENSE if c.get("content_license") == "CC BY-NC-SA 4.0" else CONTENT_LICENSE)]):
            info.write(r, 0, k, wb.add_format({"bold": True, "font_name": FONT}))
            info.write(r, 1, v, wrap)
        sheet.activate()


def _xlsx_chart(wb, df: pd.DataFrame, plan: dict, c: dict):
    sn = c.get("_sheet", "Daten")
    n = len(df)
    if not n or plan["kind"] in ("none", "tiles", "table", "list"):
        return None
    axis_font = {"name": FONT, "size": 9}
    dec = "General"
    col = {name: j for j, name in enumerate(df.columns)}

    def ref(j):
        return [sn, 4, j, 3 + n, j]

    cats = [sn, 4, 0, 3 + n, 0]
    kind = plan["kind"]
    if kind == "scatter":
        ch = wb.add_chart({"type": "scatter", "subtype": "straight_with_markers"})
        ch.add_series({"name": "Verlauf", "categories": ref(1), "values": ref(2), "line": {"color": PALETTE[0], "width": 1.5},
                       "marker": {"type": "circle", "size": 4, "fill": {"color": PALETTE[0]}, "border": {"color": PALETTE[0]}}})
    elif kind in ("hbar", "columns_cat"):
        ch = wb.add_chart({"type": "bar" if kind == "hbar" else "column"})
        for i, name in enumerate(df.columns[1:]):
            ch.add_series({"name": [sn, 3, i + 1], "categories": cats, "values": ref(i + 1),
                           "fill": {"color": PALETTE[i % len(PALETTE)]}, "gap": 60})
    else:
        ch = wb.add_chart({"type": "column", "subtype": "stacked"}) if kind in ("stacked", "columns") else wb.add_chart({"type": "line"})
        for i, name in enumerate(plan.get("bars", []) if kind in ("stacked", "columns") else []):
            ch.add_series({"name": [sn, 3, col[name]], "categories": cats, "values": ref(col[name]),
                           "fill": {"color": BAR_PALETTE[i % len(BAR_PALETTE)]}, "gap": 40})
        target = ch
        if kind == "stacked" and plan.get("lines"):
            target = wb.add_chart({"type": "line"})
        for i, name in enumerate(n_ for n_ in plan.get("lines", []) if n_ not in plan.get("thin", [])):
            color = "#000000" if kind == "stacked" else PALETTE[i % len(PALETTE)]
            width = 2.25 if (plan.get("emphasis") in (None, name)) else 1.25
            line = {"color": "#C00000" if name in plan.get("dashed", []) and name.startswith("Schwelle") else color, "width": width}
            if name in plan.get("dashed", []):
                line.update(dash_type="dash", width=1.25, color=PALETTE[1] if name.startswith("Referenz") else line["color"])
            target.add_series({"name": [sn, 3, col[name]], "categories": cats, "values": ref(col[name]),
                               "line": line, "marker": {"type": "none"}})
        for i, name in enumerate(plan.get("thin", [])):
            target.add_series({"name": [sn, 3, col[name]], "categories": cats, "values": ref(col[name]),
                               "line": {"color": PALETTE[i % len(PALETTE)], "width": 0.75, "transparency": 50}, "marker": {"type": "none"}})
        if target is not ch:
            ch.combine(target)
        ch.show_blanks_as("gap")
    x_opts = {"num_font": {**axis_font, "rotation": 0}, "line": {"none": True}, "major_tick_mark": "none", "label_position": "low"}
    if kind in ("line", "stacked", "columns"):
        x_opts.update(date_axis=True, num_format="yyyy", major_unit=1, major_unit_type="years")
    if kind not in ("hbar",):
        x_opts["crossing"] = "max"
    ch.set_x_axis(x_opts)
    ch.set_y_axis({"num_font": axis_font, "line": {"none": True}, "major_tick_mark": "none", "num_format": dec,
                   "major_gridlines": {"visible": True, "line": {"color": GRID, "width": 0.25}}})
    ch.set_legend({"position": "top", "font": axis_font, "delete_series": list(range(len(df.columns) - 1 - len(plan.get("thin", [])), len(df.columns) - 1)) if plan.get("thin") else []})
    ch.set_chartarea({"border": {"none": True}})
    ch.set_plotarea({"border": {"none": True}})
    ch.set_size({"width": 760, "height": 420})
    return ch


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------
def _rgb(hexcolor: str):
    from pptx.dml.color import RGBColor

    return RGBColor.from_string(hexcolor.lstrip("#").upper())


def _text(slide, box, text, size, color="#000000", bold=False, align=None, font=None, italic=False):
    from pptx.util import Pt

    tb = slide.shapes.add_textbox(*box)
    tf = tb.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.word_wrap = True
    p = tf.paragraphs[0]
    if align is not None:
        p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
    if font:
        r.font.name = font
    r.font.color.rgb = _rgb(color)
    return tb


def _frame(slide, stand: str, number: int, lic: str = "CC BY 4.0"):
    """Fußzeile in den Positionen der Fußzeilenplatzhalter des Standardmasters; kein Rahmen, kein Hintergrund."""
    from pptx.enum.text import PP_ALIGN

    _text(slide, FOOT_L, f"Konjunkturmonitor · {lic}, Wolf-Fabian Hungerland", 10, MUTED)
    _text(slide, FOOT_R, f"Letzte Aktualisierung: {stand}", 10, MUTED, align=PP_ALIGN.RIGHT)
    _text(slide, NUMBER, str(number), 10, MUTED, align=PP_ALIGN.RIGHT)


def _style_chart(chart, c: dict, plan: dict):
    from pptx.enum.chart import XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK
    from pptx.util import Pt

    chart.font.name, chart.font.size = FONT, Pt(12)
    chart.has_title = False
    chart.has_legend = plan["kind"] not in ("scatter",) and len(chart.plots[0].series) + sum(len(p.series) for p in chart.plots[1:]) > 1
    if chart.has_legend:
        chart.legend.position = XL_LEGEND_POSITION.TOP
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(12)
    va = chart.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = _rgb(GRID)
    va.major_gridlines.format.line.width = Pt(0.25)
    va.format.line.fill.background()
    va.major_tick_mark = XL_TICK_MARK.NONE
    va.tick_labels.number_format = "General"  # keine überflüssigen Nachkommastellen
    va.tick_labels.number_format_is_linked = False
    if plan["kind"] != "hbar":
        from pptx.enum.chart import XL_AXIS_CROSSES
        va.crosses = XL_AXIS_CROSSES.MAXIMUM  # Werteachse rechts (wie XlsxWriter: crosses=max am valAx)
        ns = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
        for ax in chart._chartSpace.iter(ns + "valAx"):
            pos = ax.find(ns + "axPos")
            if pos is not None:
                pos.set("val", "r")
    try:
        ca = chart.category_axis
        ca.format.line.fill.background()
        ca.major_tick_mark = XL_TICK_MARK.NONE
        ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    except Exception:
        pass
    plot = chart.plots[0]
    el = chart._chartSpace.chart
    disp = el.find("{http://schemas.openxmlformats.org/drawingml/2006/chart}dispBlanksAs")
    if disp is not None:
        disp.set("val", "gap")


def _date_axis_years(chart, freq: str):
    """Kategorienachse als Datumsachse mit Jahresbeschriftung."""
    from lxml import etree

    ns = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
    for ax in chart._chartSpace.iter(ns + "dateAx"):
        for tag, val in (("baseTimeUnit", "months"), ("majorUnit", "1"), ("majorTimeUnit", "years")):
            e = ax.find(ns + tag)
            if e is None:
                e = etree.SubElement(ax, ns + tag)
            e.set("val", val)
        nf = ax.find(ns + "numFmt")
        if nf is not None:
            nf.set("formatCode", "yyyy")
            nf.set("sourceLinked", "0")


def _line_overlay(chart, names: list[str]):
    """Linien-Reihen eines gestapelten Säulendiagramms in ein überlagertes Liniendiagramm verschieben."""
    from lxml import etree

    ns = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
    plot_area = chart._chartSpace.find(f"{ns}chart/{ns}plotArea")
    bar = plot_area.find(ns + "barChart")
    sers = [s for s in bar.findall(ns + "ser") if s.find(f"{ns}tx//{ns}v") is not None and s.find(f"{ns}tx//{ns}v").text in names]
    if not sers:
        return
    line = etree.SubElement(plot_area, ns + "lineChart")
    etree.SubElement(line, ns + "grouping").set("val", "standard")
    etree.SubElement(line, ns + "varyColors").set("val", "0")
    for s in sers:
        bar.remove(s)
        for tag in ("invertIfNegative",):
            e = s.find(ns + tag)
            if e is not None:
                s.remove(e)
        mk = etree.SubElement(s, ns + "marker")
        etree.SubElement(mk, ns + "symbol").set("val", "none")
        # Reihenfolge: marker muss vor cat/val stehen
        cat = s.find(ns + "cat")
        if cat is not None:
            s.remove(mk)
            cat.addprevious(mk)
        line.append(s)
    etree.SubElement(line, ns + "marker").set("val", "1")
    for ax_id in bar.findall(ns + "axId"):
        line.append(copy.deepcopy(ax_id))
    # Linie hinter die Achsen-Definitionen, aber nach dem Säulendiagramm
    plot_area.remove(line)
    bar.addnext(line)


def _color_series(chart, plan: dict):
    from pptx.util import Pt

    bars, thin = plan.get("bars", []), plan.get("thin", [])
    bi = li = ti = 0
    for plot in chart.plots:
        for s in plot.series:
            name = s.name
            if name in bars:
                s.format.fill.solid()
                s.format.fill.fore_color.rgb = _rgb(BAR_PALETTE[bi % len(BAR_PALETTE)])
                bi += 1
                continue
            ln = s.format.line
            if name in thin:
                ln.color.rgb = _rgb(PALETTE[ti % len(PALETTE)])
                ln.width = Pt(0.75)
                ti += 1
                continue
            if name in plan.get("dashed", []):
                ln.color.rgb = _rgb("#C00000" if name.startswith("Schwelle") else PALETTE[1])
                ln.dash_style = 4  # MSO_LINE.DASH
                ln.width = Pt(1.25)
                continue
            color = "#000000" if plan["kind"] == "stacked" else PALETTE[li % len(PALETTE)]
            ln.color.rgb = _rgb(color)
            ln.width = Pt(2.25 if plan.get("emphasis") in (None, name) else 1.25)
            li += 1
            try:
                s.smooth = False
                s.marker.style = None
                from pptx.enum.chart import XL_MARKER_STYLE
                s.marker.style = XL_MARKER_STYLE.NONE
            except Exception:
                pass


def _hide_legend_entries(chart, names: list[str]):
    from lxml import etree

    if not names or not chart.has_legend:
        return
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
    legend = chart._chartSpace.find(f"{ns}chart/{ns}legend")
    idx = 0
    for plot in chart.plots:
        for s in plot.series:
            if s.name in names:
                le = etree.Element(ns + "legendEntry")
                etree.SubElement(le, ns + "idx").set("val", str(s.index))
                etree.SubElement(le, ns + "delete").set("val", "1")
                legend.find(ns + "legendPos").addnext(le)
            idx += 1


def add_slide(prs, c: dict, df: pd.DataFrame, plan: dict, stand: str, number: int) -> None:
    from pptx.chart.data import CategoryChartData, XyChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.enum.text import PP_ALIGN

    from pptx.util import Pt

    slide = prs.slides.add_slide(prs.slide_layouts[5])  # Standardmaster, Layout „Nur Titel“
    _frame(slide, stand, number, c.get("content_license") or "CC BY 4.0")
    sub, unit = header_lines(c)
    _text(slide, OVERTITLE, f"Abb. {c['no']} · {c.get('topic_title', '')}", 12, MUTED)
    title = slide.shapes.title
    title.text = c.get("title", "")
    for p in title.text_frame.paragraphs:  # Schrift aus dem Master, nur kleiner, damit lange Titel passen
        for r in p.runs:
            r.font.size = Pt(28)
    if sub:
        _text(slide, SUB, sub, 14, MUTED)
    _text(slide, UNIT, unit, 12, "#000000", align=PP_ALIGN.RIGHT)
    _text(slide, SOURCE, source_line(c), 10, MUTED)
    if c.get("caption"):
        slide.notes_slide.notes_text_frame.text = (c.get("_stem", "") + "\n\n" + c["caption"]).strip()
    kind = plan["kind"]
    if df.empty or kind == "none":
        return
    if kind == "tiles":
        _tiles(slide, c)
        return
    if kind == "table":
        _table(slide, df)
        return
    if kind == "list":
        return
    if kind == "scatter":
        data = XyChartData()
        s = data.add_series("Verlauf")
        for x, y in zip(df.iloc[:, 1], df.iloc[:, 2]):
            s.add_data_point(x, y)
        gf = slide.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES, *CHART, data)
        chart = gf.chart
        _style_chart(chart, c, plan)
        ser = chart.plots[0].series[0]
        ser.format.line.color.rgb = _rgb(PALETTE[0])
        return
    data = CategoryChartData()
    first = df.columns[0]
    is_date = first == "Datum"
    data.categories = list(pd.to_datetime(df[first]).dt.date) if is_date else list(df[first])
    if kind in ("hbar", "columns_cat"):
        cols = list(df.columns[1:])
    else:
        cols = [*plan.get("bars", []), *[n for n in plan.get("lines", []) if n not in plan.get("thin", [])], *plan.get("thin", [])]
    for name in cols:
        data.add_series(name, [None if pd.isna(v) else float(v) for v in df[name]])
    ctype = {"hbar": XL_CHART_TYPE.BAR_CLUSTERED, "columns_cat": XL_CHART_TYPE.COLUMN_CLUSTERED,
             "stacked": XL_CHART_TYPE.COLUMN_STACKED, "columns": XL_CHART_TYPE.COLUMN_STACKED}.get(kind, XL_CHART_TYPE.LINE)
    gf = slide.shapes.add_chart(ctype, *CHART, data)
    chart = gf.chart
    if kind == "stacked":
        _line_overlay(chart, [n for n in cols if n not in plan.get("bars", [])])
    _style_chart(chart, c, plan)
    if kind in ("hbar", "columns_cat"):
        for i, s in enumerate(chart.plots[0].series):
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = _rgb(PALETTE[i % len(PALETTE)])
        chart.plots[0].gap_width = 60
    else:
        if kind in ("stacked", "columns"):
            chart.plots[0].gap_width = 40
            chart.plots[0].overlap = 100
        _color_series(chart, plan)
        if is_date:
            _date_axis_years(chart, c.get("freq", "M"))
        _hide_legend_entries(chart, plan.get("thin", []))


TILE_POS = {"SH": (0, 2), "HB": (1, 1), "HH": (1, 2), "MV": (1, 3), "NW": (2, 0), "NI": (2, 1), "ST": (2, 2), "BE": (2, 3),
            "BB": (2, 4), "RP": (3, 0), "HE": (3, 1), "TH": (3, 2), "SN": (3, 3), "SL": (4, 0), "BW": (4, 1), "BY": (4, 2)}


def _tile_color(v: float, m: float) -> tuple[str, str]:
    k = min(1.0, abs(v) / m)
    base = (227, 108, 10) if v >= 0 else (0, 112, 192)
    rgb = [round(255 - (255 - x) * k * 0.85) for x in base]
    return "#%02X%02X%02X" % tuple(rgb), ("#FFFFFF" if k > 0.55 else "#000000")


GEO: list | None = None
LABEL_OFFSET = {"HB": (-0.85, 0.45), "HH": (0.63, 1.0), "BE": (1.05, 0.25), "SL": (-0.45, -0.35)}


def _pct0(v: float) -> str:
    r = round(v)
    return ("+" if r > 0 else "") + (f"{abs(r)}" if r >= 0 else f"−{abs(r)}") + " %"


def _map(slide, c: dict) -> None:
    """Länderkarte als bearbeitbare Freiformen (BKG VG2500), Beschriftung je Land."""
    import math
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Pt

    rows = {r["abbr"]: r for r in c["tiles"]["rows"]}
    m = max([10.0, *[abs(r["change"]) for r in rows.values()]])
    k = math.cos(math.radians(51.2))
    w_units, h_units = (15.2 - 5.7) * k + 1.9, 55.2 - 47.2
    scale = min(CHART[2] / w_units, (CHART[3] - 150000) / h_units)
    ox = CHART[0] + (CHART[2] - w_units * scale) / 2 + 0.9 * scale
    oy = CHART[1]
    X = lambda lon: ox + (lon - 5.7) * k * scale
    Y = lambda lat: oy + (55.2 - lat) * scale
    for f in sorted(GEO, key=lambda g: g["abbr"] == "BE"):
        r = rows.get(f["abbr"])
        bg, _ = _tile_color(r["change"], m) if r else ("#EEEEEE", "#000000")
        for ring in f["rings"]:
            pts = [(int(X(lo)), int(Y(la))) for lo, la in ring]
            fb = slide.shapes.build_freeform(*pts[0])
            fb.add_line_segments(pts[1:], close=True)
            shp = fb.convert_to_shape()
            shp.fill.solid()
            shp.fill.fore_color.rgb = _rgb(bg)
            shp.line.color.rgb = _rgb("#FFFFFF")
            shp.line.width = Pt(0.5)
            shp.shadow.inherit = False
    for f in GEO:
        r = rows.get(f["abbr"])
        if not r:
            continue
        lx, ly = X(f["label"][0]), Y(f["label"][1])
        _, fg = _tile_color(r["change"], m)
        off = LABEL_OFFSET.get(f["abbr"])
        if off:
            tx, ty = lx + off[0] * scale, ly - off[1] * scale
            ln = slide.shapes.add_connector(1, int(lx), int(ly), int(tx), int(ty))
            ln.line.color.rgb = _rgb("#555555")
            ln.line.width = Pt(0.5)
            lx, ly, fg = tx, ty, "#000000"
        box = slide.shapes.add_textbox(int(lx - 300000), int(ly - 120000), 600000, 260000)
        tf = box.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for i, (txt, b) in enumerate(((r["abbr"], True), (_pct0(r["change"]), False))):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = txt
            run.font.size, run.font.bold, run.font.name = Pt(11), b, FONT
            run.font.color.rgb = _rgb(fg)


def _tiles(slide, c: dict):
    if GEO:
        return _map(slide, c)
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Pt

    rows = c["tiles"]["rows"]
    m = max([10.0, *[abs(r["change"]) for r in rows]])
    size, gap = 740000, 66000
    x0 = CHART[0] + (CHART[2] - 5 * size - 4 * gap) // 2
    y0 = CHART[1] + 40000
    for r in rows:
        pos = TILE_POS.get(r["abbr"])
        if not pos:
            continue
        bg, fg = _tile_color(r["change"], m)
        shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x0 + pos[1] * (size + gap), y0 + pos[0] * (size + gap), size, size)
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(bg)
        shp.line.fill.background()
        shp.shadow.inherit = False
        tf = shp.text_frame
        tf.margin_left = tf.margin_right = 0
        sign = "+" if r["change"] > 0 else ""
        for i, (txt, sz, b) in enumerate(((r["abbr"], 12, True), (f"{sign}{r['change']:.0f} %".replace(".", ","), 10, False))):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = PP_ALIGN.CENTER
            run = p.add_run()
            run.text = txt
            run.font.size, run.font.bold, run.font.name = Pt(sz), b, FONT
            run.font.color.rgb = _rgb(fg)


def _table(slide, df: pd.DataFrame) -> None:
    """Tabelle mit Farbskala (orange Zunahme, blau Abnahme) für Wärmetabellen."""
    from pptx.util import Pt

    rows, cols = len(df) + 1, len(df.columns)
    shape = slide.shapes.add_table(rows, cols, CHART[0], CHART[1], CHART[2], min(CHART[3], 145000 * rows))
    tbl = shape.table
    tbl.columns[0].width = 2500000
    for j in range(1, cols):
        tbl.columns[j].width = int((CHART[2] - 2500000) / (cols - 1))
    for j, name in enumerate(df.columns):
        cell = tbl.cell(0, j)
        cell.text = str(name).replace(", %", "")
    for i, row in enumerate(df.itertuples(index=False), start=1):
        for j, v in enumerate(row):
            cell = tbl.cell(i, j)
            if j == 0:
                cell.text = str(v)
            elif v is None or pd.isna(v):
                cell.text = ""
            else:
                cell.text = f"{v:.0f}".replace("-", "−") if j < cols - 2 else f"{v:+.1f}".replace(".", ",").replace("-", "−")
                if j < cols - 2:
                    bg, fg = _tile_color(max(-15, min(15, float(v))), 15)
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = _rgb(bg)
                    cell.text_frame.paragraphs[0].runs[0].font.color.rgb = _rgb(fg)
    for i in range(rows):
        for j in range(cols):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = 20000
            cell.margin_top = cell.margin_bottom = 0
            if i == 0 or j == 0 or not (1 <= j < cols - 2):
                cell.fill.solid()
                cell.fill.fore_color.rgb = _rgb("#FFFFFF")
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size, r.font.name = Pt(9), FONT
                    if i == 0 or not (1 <= j < cols - 2):
                        r.font.color.rgb = _rgb("#000000")


def new_presentation():
    from pptx import Presentation

    prs = Presentation()  # leerer Standardmaster (Office-Design), von 4:3 auf 16:9 verbreitert
    k = SLIDE_W / prs.slide_width
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H
    for part in [prs.slide_master, *prs.slide_layouts]:
        for off in part.element.xpath(".//p:spTree//a:xfrm/a:off"):
            off.set("x", str(round(int(off.get("x")) * k)))
        for ext in part.element.xpath(".//p:spTree//a:xfrm/a:ext"):
            ext.set("cx", str(round(int(ext.get("cx")) * k)))
    return prs


# ---------------------------------------------------------------------------
# Dateinamen (Regelwerk Dateinamen Konjunkturmonitor)
# ---------------------------------------------------------------------------
_TRANS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"})
_FILL = {"der", "die", "das", "des", "dem", "den", "und", "im", "in", "von", "vom", "zur", "zum", "fuer", "mit", "nach",
         "je", "auf", "aus", "ein", "eine", "einer", "an", "bei", "ohne", "gegenueber"}


def short_titles(root: Path) -> dict:
    """Kurztitel je Abbildung aus abbildungen.txt (Abbildung;Kurztitel;erste Ausgabe;gestrichen ab)."""
    path = root / "abbildungen.txt"
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#"):
                f = line.split(";")
                if len(f) >= 2 and f[1].strip():
                    out[f[0].strip()] = f[1].strip()
    return out


def clean_title(title: str) -> str:
    """Höchstens vier Wörter, ohne Artikel und Füllwörter, nur Buchstaben, Ziffern, Leerzeichen und Bindestrich."""
    t = title.translate(_TRANS)
    words = [w for w in re.sub(r"[^A-Za-z0-9 -]", " ", t).split() if w.lower() not in _FILL]
    return " ".join(words[:4]) or "Abbildung"


def file_stem(c: dict, date: str, width: int, shorts: dict) -> str:
    kind = "Tab." if c.get("type") in ("heat", "calendar") else "Abb."
    title = clean_title(shorts.get(c["chart"]) or c.get("title", ""))
    return f"Konjunkturmonitor ({date}, {kind} {c['no']:0{width}d}) {title}"[:79]


# ---------------------------------------------------------------------------
# Alles zusammen
# ---------------------------------------------------------------------------
def write_dta(df: pd.DataFrame, path: Path, title: str) -> bool:
    """Stata-Datei (Version 118) mit Variablenlabels; False, wenn sich die Tabelle nicht abbilden lässt."""
    used: set[str] = set()
    names = {c: ("date" if c == "Datum" else stata_name(str(c), used)) for c in df.columns}
    st = df.rename(columns=names).copy()
    if "date" in st.columns:
        st["date"] = pd.to_datetime(st["date"], errors="coerce")
    for col in st.columns:
        if st[col].dtype == object:
            num = pd.to_numeric(st[col], errors="coerce")
            st[col] = num if num.notna().sum() == st[col].notna().sum() else st[col].astype(str)
    try:
        st.to_stata(path, write_index=False, version=118, variable_labels={names[c]: str(c)[:80] for c in df.columns},
                    data_label=title[:80], convert_dates={"date": "td"} if "date" in st.columns else None)
        return True
    except Exception:
        path.unlink(missing_ok=True)
        return False


def write_all(payload: dict, out: Path, root: Path | None = None) -> None:
    global GEO
    GEO = payload.get("geo")
    folder = out / "dl"
    folder.mkdir(parents=True, exist_ok=True)
    stand = datetime.fromisoformat(payload["generated_at"]).strftime("%d.%m.%Y")
    site = payload["site"]
    cite = f"{site['author']} ({stand[-4:]}): Konjunkturmonitor. Stand {stand}. {site['url']}"
    deck = new_presentation()
    number = 0
    date = payload["generated_at"][:10]
    shorts = short_titles(root or Path.cwd())
    total = sum(len(t["charts"]) for t in payload["topics"])
    width = 3 if total >= 100 else 2
    flat = []
    for t in payload["topics"]:
        for c in t["charts"]:
            flat.append((t, c, False))
            if isinstance(c.get("variant"), dict):  # zweite Ansicht einer Karte: eigene Dateien, gleiche Nummer
                c["variant"]["no"] = c.get("no")
                flat.append((t, c["variant"], True))
    for t, c, is_variant in flat:
            number += 0 if is_variant else 1
            c["topic_title"] = t.get("title", "")
            df, plan = chart_table(c)
            stem = file_stem(c, date, width, shorts)
            c["_stem"] = stem
            c["_sheet"] = stem.split(", ", 1)[1].split(")")[0]  # etwa „Abb. 04“
            xs = [x for s in (c.get("series") or []) if isinstance(s, dict) for x in s.get("x", [])]
            c["datenstand"] = max(xs) if xs else ""
            files = {}
            if not df.empty:
                csv = df.copy()
                if "Datum" in csv:
                    csv["Datum"] = pd.to_datetime(csv["Datum"]).dt.strftime("%Y-%m-%d")
                with open(folder / f"{stem}.csv", "w", encoding="utf-8-sig", newline="") as fh:
                    fh.write(stem + "\n")  # Regel 9: Stamm in der ersten Zeile
                    csv.to_csv(fh, sep=";", decimal=",", index=False)
                files["csv"] = f"dl/{stem}.csv"
                if write_dta(df, folder / f"{stem}.dta", stem):
                    files["dta"] = f"dl/{stem}.dta"
                write_xlsx(c, df, plan, folder / f"{stem}.xlsx", stand, cite)
                files["xlsx"] = f"dl/{stem}.xlsx"
            prs = new_presentation()
            add_slide(prs, c, df, plan, stand, 1)
            prs.save(folder / f"{stem}.pptx")
            files["pptx"] = f"dl/{stem}.pptx"
            add_slide(deck, c, df, plan, stand, number)
            files["png"] = f"{stem}.png"
            c["files"] = files
            for k in ("topic_title", "_sheet"):
                c.pop(k, None)
    deck.save(folder / f"Konjunkturmonitor ({date}) Alle Abbildungen.pptx")
    payload["deck"] = f"dl/Konjunkturmonitor ({date}) Alle Abbildungen.pptx"
