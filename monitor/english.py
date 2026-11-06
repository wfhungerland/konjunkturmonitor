"""Englische Fassung der Seite (site/en/).

Aus der fertigen deutschen Nutzlast entsteht eine englische: Titel, Fragen, Erläuterungen und Reihennamen kommen aus
data/static/en.yaml (fehlt ein Eintrag, bleibt der deutsche Text). Die Antworten und die automatischen Sätze werden
mit englischen Vorlagen neu erzeugt; für Abbildungsarten ohne englische Vorlage entfallen die Sätze.
Die Abbildungen selbst (Achsen, Legenden, Hinweise in der Grafik) folgen in einem späteren Schritt.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

import pandas as pd
import yaml

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MON3 = [m[:3] for m in MONTHS]


def num(v: float, d: int = 1, sign: bool = False) -> str:
    v = round(float(v), d)
    v = 0.0 if v == 0 else v
    s = f"{abs(v):,.{d}f}"
    return ("-" + s) if v < 0 else ("+" + s) if sign and v > 0 else s


def period(ts: pd.Timestamp, freq: str) -> str:
    if freq == "Q":
        return f"Q{(ts.month - 1) // 3 + 1} {ts.year}"
    if freq == "A":
        return str(ts.year)
    if freq in ("D", "B"):
        return f"{ts.day} {MONTHS[ts.month - 1]} {ts.year}"
    return f"{MONTHS[ts.month - 1]} {ts.year}"


def when(x: str, freq: str) -> str:
    t = pd.Timestamp(x)
    if freq == "A":
        return f"In {t.year}"
    if freq == "D":
        return f"In the week to {t.day} {MONTHS[t.month - 1]} {t.year}"
    if freq == "B":
        return f"On {t.day} {MONTHS[t.month - 1]} {t.year}"
    return f"In {period(t, freq)}"


def de_period_to_en(s: str) -> str:
    """„3. Quartal 2026“ → „Q3 2026“, „Oktober 2026“ → „October 2026“, „4. November 2026“ → „4 November 2026“."""
    from .answers import MONTHS as DE
    if not isinstance(s, str):
        return s
    s = re.sub(r"^(das|den|der) ", "", s)
    s = re.sub(r"(\d)\. Quartal (\d{4})", r"Q\1 \2", s)
    s = re.sub(r"(\d{1,2})\. (" + "|".join(DE) + r") (\d{4})", lambda m: f"{m.group(1)} {MONTHS[DE.index(m.group(2))]} {m.group(3)}", s)
    for i, m in enumerate(DE):
        s = re.sub(rf"\b{m}\b", MONTHS[i], s)
    return s.replace("Woche bis ", "week to ")


LICENCES = {
    "Datenlizenz Deutschland – Namensnennung – Version 2.0 (Statistisches Bundesamt)": "Data licence Germany – attribution – version 2.0 (Federal Statistical Office)",
    "Wiederverwendung mit Quellenangabe (Deutsche Bundesbank)": "Reuse with attribution (Deutsche Bundesbank)",
    "Wiederverwendung mit Quellenangabe (EZB)": "Reuse with attribution (ECB)",
    "Nutzungsbedingungen der Originalquelle laut FRED, mit Quellenangabe": "Terms of use of the original source as stated by FRED, with attribution",
    "Statistik der Bundesagentur für Arbeit, mit Quellenangabe": "Statistics of the Federal Employment Agency, with attribution",
    "Statistisches Bundesamt (GENESIS)": "Federal Statistical Office (GENESIS)",
    "eigene Berechnung": "own calculation",
    "Pkt.": "pts", "Anträge": "filings", "% ggü. Vorjahr": "% on a year earlier", "% ggü. Vorjahresmonat": "% on a year earlier",
    "% ggü. Vorjahresmonat, Beiträge in Pp": "% on a year earlier, contributions in pp",
    "% gegenüber Vorjahresmonat, Beiträge in Prozentpunkten": "% on a year earlier, contributions in pp",
    "Veränderung ggü. denselben 12 Monaten ein Jahr zuvor, %": "change on the same 12 months a year earlier, %", "Pp": "pp", "Punkte": "points", "Vorquartal": "previous quarter", "Vormonat": "previous month", "Vorjahr": "year earlier",
}
# Wortweise Übersetzung für Quellen- und Lizenzangaben (nach den exakten Treffern)
WORDS = [
    ("Eigene Zusammenstellung nach dem üblichen Veröffentlichungsrhythmus der Quellen", "Own compilation based on the sources’ usual release patterns"),
    ("WSV-Pegeldaten, bereitgestellt durch die Bundesanstalt für Gewässerkunde (R-Paket hyd1d)", "WSV gauge data provided by the Federal Institute of Hydrology (R package hyd1d)"),
    ("geprüfte Pegeldaten über BfG (bis Vorjahr)", "validated gauge data via BfG (to end of previous year)"),
    ("geprüfte Pegeldaten über BfG", "validated gauge data via BfG"),
    ("Datenlizenz Deutschland – Zero – Version 2.0", "Data licence Germany – Zero – version 2.0"),
    ("Datenlizenz Deutschland – Namensnennung – Version 2.0", "Data licence Germany – attribution – version 2.0"),
    ("Nutzungsbedingungen der Vereinten Nationen", "terms of use of the United Nations"),
    ("Unternehmensumfrage Industrie", "industry business survey"),
    ("Wiederverwendung mit Quellenangabe", "reuse with attribution"),
    ("Quellenangabe erforderlich", "attribution required"), ("Quellenangabe", "attribution"),
    ("Eigene Berechnung aus", "Own calculation from"), ("eigene Berechnung", "own calculation"), ("Eigene Berechnung", "Own calculation"),
    ("Europäische Kommission", "European Commission"), ("EU-Kommission", "European Commission"),
    ("des Statistischen Bundesamts", "of the Federal Statistical Office"), ("Statistisches Bundesamt", "Federal Statistical Office"),
    ("Bundesagentur für Arbeit", "Federal Employment Agency"), ("Bundesnetzagentur", "Federal Network Agency"),
    ("Deutscher Wetterdienst", "German Weather Service"), ("Sachverständigenrat", "German Council of Economic Experts"),
    ("Frühjahrsprognose", "spring forecast"), ("Herbstprognose", "autumn forecast"), ("Herbstprojektion", "autumn projection"),
    ("Frühjahrsprojektion", "spring projection"), ("Konjunkturprognose", "economic forecast"), ("Gemeinschaftsdiagnose", "Joint Economic Forecast"),
    ("Bundesregierung", "Federal Government"), ("Gemeinfrei", "Public domain"), ("IWF", "IMF"), ("EZB", "ECB"),
    ("VPI", "CPI"), ("Erzeugerpreise", "producer prices"), ("Nutzungsbedingungen", "terms of use"), ("-Daten", " data"),
    ("Ländergrenzen: © GeoBasis-DE / BKG (VG2500)", "State borders: © GeoBasis-DE / BKG (VG2500)"),
    ("(über ", "(via "), (" über ", " via "), (" und ", " and "), (" laut ", " as stated by "), (" mit ", " with "),
]
BARS = {"Auftragseingang": ("New orders", "orders"), "Produktion": ("Production", "production")}


class Tr:
    def __init__(self, root: Path):
        p = root / "data" / "static" / "en.yaml"
        self.d = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
        self.strings = dict(LICENCES, **(self.d.get("strings") or {}))

    def get(self, sect: str, key: str, field: str, default=None):
        v = ((self.d.get(sect) or {}).get(key) or {})
        v = v.get(field) if isinstance(v, dict) else None
        return v if v not in (None, "") else default

    def label(self, sid, de):
        """Englischer Reihenname; bei ausgeklappten Reihen (de_insolv_land_09) aus der Vorlage mit Platzhaltern."""
        v = self.get("series", sid, "label")
        if v or not sid:
            return v or de
        ser = self.d.get("series") or {}
        base = max((k for k in ser if sid.startswith(k + "_")), key=len, default=None)
        tpl = self.get("series", base, "label") if base else None
        if not tpl:
            return de
        code, names, bad = sid[len(base) + 1:], self.d.get("names") or {}, []

        def rep(m):
            kind = m.group(1)
            if kind == "wz":
                return code.upper()
            for k, val in (names.get(kind.replace("_name", "")) or {}).items():
                if str(k).lower() == code:
                    return str(val)
            bad.append(kind)
            return m.group(0)
        out = re.sub(r"\{(\w+)\}", rep, tpl)
        return de if bad else out

    def s(self, text):
        """Kurzer fester Text (Einheit, Bereinigung): exakte Übersetzung, sonst unverändert."""
        if not isinstance(text, str):
            return text
        return self.strings.get(text, text)

    def src(self, text):
        """Quellen- oder Lizenzangabe: exakt, sonst Wort für Wort."""
        if not isinstance(text, str) or text in self.strings:
            return self.s(text)
        for de, en in WORDS:
            text = text.replace(de, en)
        return text


# --------------------------------------------------------------------------- Antworten auf die Startfragen

def _s(data, sid):
    s = data.get(sid)
    if s is None or s.dropna().empty:
        raise KeyError(sid)
    return s.dropna().sort_index()


def _mom_3m(s):
    return (s.iloc[-1] / s.iloc[-2] - 1) * 100, (s.iloc[-3:].mean() / s.iloc[-6:-3].mean() - 1) * 100


def answer_en(q: dict, data: dict, tr: Tr) -> dict | None:
    k = q.get("kind")
    try:
        s = _s(data, q["series"])
        v, p, t = s.iloc[-1], s.iloc[-2], s.index[-1]
        if k == "growth":
            yoy = data.get(q.get("yoy"))
            avg = s[(s.index >= "2015-01-01") & (s.index < "2020-01-01")].mean()
            head = (f"In {period(t, 'Q')} the economy {'grew' if v > 0 else 'shrank'} by {num(abs(v))}%." if abs(v) >= 0.05
                    else f"In {period(t, 'Q')} economic output barely changed ({num(v, sign=True)}%).")
            more = [f"In the previous quarter output changed by {num(p, sign=True)}%."]
            if yoy is not None and not yoy.dropna().empty:
                y = yoy.dropna().iloc[-1]
                more.append(f"In {period(t, 'Q')} output was {num(abs(y))}% {'above' if y >= 0 else 'below'} its level a year earlier.")
            more.append(f"From 2015 to 2019 the economy grew by {num(avg)}% a quarter on average.")
            verdict = "shrinking" if v <= -0.05 else "stagnating" if v < 0.1 else "growing slightly" if v < 0.4 else "growing" if v < 0.8 else "growing strongly"
            return {"head": head, "more": more, "verdict": verdict, "period": period(t, "Q")}
        if k == "inflation":
            head = f"In {period(t, 'M')} prices were {num(abs(v))}% {'higher' if v >= 0 else 'lower'} than a year earlier."
            more = [f"In the previous month the rate was {num(p)}%, so it has {'fallen' if v < p - 0.05 else 'risen' if v > p + 0.05 else 'held steady'}."]
            idx = data.get(q.get("index"))
            if idx is not None and len(idx.dropna()) > 1 and idx.dropna().index[-1] == t:
                i = idx.dropna()
                more.append(f"In {period(t, 'M')} consumer prices changed by {num((i.iloc[-1] / i.iloc[-2] - 1) * 100, sign=True)}% on the previous month.")
            core = data.get(q.get("core"))
            if core is not None and not core.dropna().empty and core.dropna().index[-1] == t:
                more.append(f"Excluding energy and food, inflation (the core rate) was {num(core.dropna().iloc[-1])}% in {period(t, 'M')}.")
            more.append("The European Central Bank aims for 2%.")
            verdict = "below target" if v < 1.5 else "close to target" if v <= 2.5 else "above target" if v <= 4 else "high"
            return {"head": head, "more": more, "verdict": verdict, "period": period(t, "M")}
        if k == "unemployment":
            lvl = _s(data, q["level"])
            ya = s[s.index <= t - pd.DateOffset(months=12)]
            head = f"In {period(t, 'M')} about {num(lvl.iloc[-1] / 1000, 2)} million people were registered as unemployed; the rate was {num(v)}%."
            more, verdict = [], "stable"
            if not ya.empty:
                d = v - ya.iloc[-1]
                more.append(f"A year earlier it was {num(ya.iloc[-1])}%.")
                verdict = "rising" if d >= 0.15 else "falling" if d <= -0.15 else "stable"
            more.append("The figures count people registered as unemployed with the Federal Employment Agency, seasonally adjusted.")
            return {"head": head, "more": more, "verdict": f"unemployment {verdict}", "period": period(t, "M")}
        if k == "index_mom":
            mom, three = _mom_3m(s)
            who, did = {"industrie": ("industry", "produced"), "konsum": ("retailers", "sold")}.get(q["id"], ("the sector", "turned over"))
            head = f"In {period(t, 'M')} {who} {did} {num(abs(mom))}% {'more' if mom >= 0 else 'less'} than in {MONTHS[(t - pd.DateOffset(months=1)).month - 1]}."
            more = [f"In the three months to {period(t, 'M')} {who} {did} {num(abs(three))}% {'more' if three >= 0 else 'less'} than in the three months before; "
                    "this comparison is less volatile than a single month."]
            if q.get("orders") and q["orders"] in data:
                o = _s(data, q["orders"])
                om, o3 = _mom_3m(o)
                more.append(f"New orders changed by {num(om, sign=True)}% on the previous month in {period(o.index[-1], 'M')} and by {num(o3, sign=True)}% on a three-month basis.")
            if q.get("mood") and q["mood"] in data:
                m = _s(data, q["mood"])
                more.append(f"Consumer confidence stood at a balance of {num(m.iloc[-1], sign=True)} pp in {period(m.index[-1], 'M')} "
                            f"({'better than' if m.iloc[-1] > m.iloc[-2] else 'worse than' if m.iloc[-1] < m.iloc[-2] else 'the same as'} in the previous month).")
            verdict = "rising" if three >= 1 else "falling" if three <= -1 else "stable"
            return {"head": head, "more": more, "verdict": verdict, "period": period(t, "M"), "label": "on previous month"}
        if k == "level_mom":
            mom, three = _mom_3m(s)
            head = f"In {period(t, 'M')} Germany exported goods worth €{num(s.iloc[-1])} billion, {num(abs(mom))}% {'more' if mom >= 0 else 'less'} than in the previous month."
            more = [f"In the three months to {period(t, 'M')} Germany exported {num(abs(three))}% {'more' if three >= 0 else 'less'} than in the three months before.",
                    "The values are nominal, i.e. not adjusted for price changes."]
            verdict = "rising" if three >= 1 else "falling" if three <= -1 else "stable"
            return {"head": head, "more": more, "verdict": verdict, "period": period(t, "M"), "label": f"{num(mom, sign=True)}% on previous month", "unit": "€ bn"}
        if k == "sentiment":
            rel = "above" if v > 100.5 else "below" if v < 99.5 else "at"
            head = f"In {period(t, 'M')} the economic sentiment indicator stood at {num(v)} points, {rel} its long-term average of 100."
            more = [f"In the previous month it stood at {num(p)} points, so sentiment has {'improved' if v > p + 0.2 else 'deteriorated' if v < p - 0.2 else 'barely changed'}."]
            verdict = "above average" if v >= 103 else "slightly above average" if v > 100.5 else "average" if v >= 99.5 else "below average" if v >= 90 else "well below average"
            return {"head": head, "more": more, "verdict": f"sentiment {verdict}", "period": period(t, "M"), "unit": "points"}
        if k == "insolvency":
            mon = MONTHS[t.month - 1]
            head = f"In {period(t, 'M')} {num(v, 0)} companies filed for insolvency."
            more, verdict = [], "insolvencies"
            ya = s.get(t - pd.DateOffset(years=1))
            if ya is not None and ya > 0:
                d = (v / ya - 1) * 100
                more.append(f"That is {num(abs(d))}% {'more' if d >= 0 else 'fewer'} than in {mon} {t.year - 1}.")
            base = s[(s.index.month == t.month) & (s.index.year >= 2015) & (s.index.year <= 2019)]
            if len(base):
                d = (v / base.mean() - 1) * 100
                more.append(f"Before the pandemic (2015 to 2019) the average for {mon} was {num(base.mean(), 0)}; the latest figure is {num(abs(d), 0)}% {'higher' if d >= 0 else 'lower'}.")
                verdict = ("well above pre-crisis level" if d >= 20 else "above pre-crisis level" if d >= 5 else "at pre-crisis level" if d > -5 else "below pre-crisis level")
            more.append("The figures cover filed proceedings reported by local courts; they are published with a delay of about three months.")
            return {"head": head, "more": more, "verdict": verdict, "period": period(t, "M"), "unit": "companies"}
        if k == "level":
            unit, d = tr.s(q.get("unit", "")), int(q.get("decimals", 1))
            name = tr.get("questions", q["id"], "name", None) or q.get("name", "")
            rate = "%" in unit
            ch = (lambda a, b: f"{num(a - b, 2 if d >= 2 else 1, sign=True)} pp") if rate else (lambda a, b: f"{num((a / b - 1) * 100, sign=True)}%")
            head = f"In {period(t, 'M')} {name} stood at {num(v, d)} {unit}.".replace(" % ", "% ").replace(" %.", "%.")
            more = [f"Compared with the previous month, {name} changed by {ch(v, p)}."]
            ya = s[s.index <= t - pd.DateOffset(months=12)]
            if not ya.empty:
                more.append(f"Compared with a year earlier, {name} changed by {ch(v, ya.iloc[-1])}.")
            dy = (v - ya.iloc[-1]) if not ya.empty else 0
            return {"head": head, "more": more, "verdict": "rising" if dy > 0 else "falling" if dy < 0 else "stable", "period": period(t, "M"), "unit": unit}
    except (KeyError, IndexError, ZeroDivisionError):
        return None
    return None


def overview_en(ans: dict) -> str:
    out = []
    g, i, a = ans.get("wachstum"), ans.get("preise"), ans.get("arbeit")
    if g:
        out.append(g["head"])
    if i:
        out.append(f"Inflation was {num(i['value'])}% in {i['period']}.")
    if a:
        out.append(f"The unemployment rate was {num(a['value'])}%" + (f" in {a['period']}." if not i or a["period"] != i["period"] else "."))
    return " ".join(out)


# --------------------------------------------------------------------------- Sätze zu den Abbildungen

def _subject(label: str) -> str:
    if not label:
        return "the value"
    first = label.split()[0]
    keep = first[:2].isupper() or first in ("Germany", "German", "Euro", "Brent", "Kaub", "EU", "US") or "(" in first
    return label if keep else "the " + label[:1].lower() + label[1:]


def chart_sentences_en(c: dict) -> list[str]:
    """Englische Fassung der Standardsätze für Linien- und Balkenabbildungen; übrige Arten vorerst ohne Sätze."""
    typ, d = c.get("type"), int(c.get("decimals", 1))
    if typ not in ("line", None) or not isinstance(c.get("series"), list):
        return []
    try:
        series = [s for s in c["series"] if s.get("y")]
        if c.get("emphasis"):
            series = [s for s in series if s["id"] == c["emphasis"]] or series
        series = series[:6]
        freq = c.get("freq", "M")
        last = max(s["x"][-1] for s in series)
        w = when(last, freq)
        prev_lbl = {"M": "in the previous month", "Q": "in the previous quarter", "A": "in the previous year", "D": "in the previous week", "B": "on the previous day"}
        out = []
        for s in series:
            if s["x"][-1] != last:
                continue
            v, f = s["y"][-1], s.get("freq", freq)
            su = ((s.get("unit_de") if c.get("own_scale") else c.get("unit_de")) or "").split(",")[0]
            lag = {"M": 12, "Q": 4, "A": 1, "D": 52}.get(f, 12)
            yago = s["y"][-1 - lag] if len(s["y"]) > lag else None
            if f == "B":
                ago = (pd.Timestamp(last) - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
                k = max((i for i, x in enumerate(s["x"]) if x <= ago), default=None)
                yago = s["y"][k] if k is not None else None
            unit_en = (s.get("unit") if c.get("own_scale") else c.get("unit")) or ""
            uu = "%" if su.startswith("%") and not su.startswith(("% des", "% der")) else "pp" if su.startswith(("Pp", "Saldo")) else "" if su.startswith("Index") else unit_en.split(",")[0]
            vv = (f"{num(v, d, su.startswith('Saldo'))}{uu}" if uu == "%" else f"{num(v, d, su.startswith('Saldo'))} {uu}".strip()) if not su.startswith("Index 0") else f"{num(v, d)} out of 100 points"
            subj = _subject(s.get("label", ""))
            if su.startswith(("% ggü", "Pp ggü")):
                ref = ("on the previous month" if "Vormonat" in su else "on the previous quarter" if "Vorquartal" in su else "on a year earlier" if "Vorjahr" in su
                       else "on the previous week" if "Vorwoche" in su else "")
                pu = "%" if su.startswith("%") else " pp"
                if round(v, d) == 0:
                    sent = f"{w}, {subj} barely changed ({ref})"
                else:
                    sent = f"{w}, {subj} {'rose' if v > 0 else 'fell'} by {num(abs(v), d)}{pu} {ref}"
                if len(s["y"]) > 1 and s["y"][-2] is not None and not c.get("no_yoy"):
                    sent += f", after {num(s['y'][-2], d)}{pu} {prev_lbl.get(f, 'before')}"
                out.append(sent.replace(" ()", "") + ".")
                continue
            if su.startswith("Index") and not su.startswith("Index 0"):
                if not yago:
                    continue
                ch = (v / yago - 1) * 100
                out.append(f"{w}, {subj} was " + ("at its level of a year earlier." if round(ch, 1) == 0 else f"{num(abs(ch), 1)}% {'above' if ch > 0 else 'below'} its level of a year earlier."))
                continue
            sent = f"{w}, {subj} stood at {vv}"
            if not (c.get("no_yoy") or yago is None):
                diff = v - yago
                level_like = su.startswith(("%", "Pp", "Saldo", "Punkte", "Index 0", "°C", "cm")) or " je " in su
                neg = any(q is not None and q < 0 for x in c["series"] for q in x["y"])
                if level_like or neg:
                    du = "pp" if su.startswith(("%", "Pp", "Saldo")) else ("point" if round(abs(diff), d) == 1 else "points") if su.startswith(("Punkte", "Index 0")) else uu
                    sent += ", the same as a year earlier" if round(diff, d) == 0 else f", {num(abs(diff), d)} {du} {'higher' if diff > 0 else 'lower'} than a year earlier"
                elif yago:
                    pc = (v / yago - 1) * 100
                    sent += ", the same as a year earlier" if round(pc, 1) == 0 else f", {num(abs(pc), 1)}% {'more' if pc > 0 else 'less'} than a year earlier"
            out.append(sent + ".")
        return [x.replace(" .", ".") for x in out]
    except (KeyError, IndexError, ValueError, TypeError, ZeroDivisionError):
        return []


# --------------------------------------------------------------------------- Nutzlast übersetzen

def _rel(path):
    return path if not isinstance(path, str) or path.startswith(("http", "../", "#")) else "../" + path


def english_payload(payload: dict, data: dict, root: Path) -> dict:
    tr = Tr(root)
    p = copy.deepcopy(payload)
    p["lang"] = "en"
    S = p["site"]
    S["claim"] = "How is the German economy doing? Key indicators with a short assessment, updated every working day from official and freely available data."
    S["license"] = "Text and own charts: CC BY 4.0 (attribution: Wolf-Fabian Hungerland, Konjunkturmonitor). The data are subject to the licences of their sources."
    S["url"] = S.get("url", "") + "en/"
    ans = {}
    for t in p["topics"]:
        t["title"] = tr.get("topics", t["id"], "title", t["title"])
        if t.get("ask"):
            t["ask"] = tr.get("topics", t["id"], "ask", t["ask"])
        q = t.get("question")
        if q:
            q["ask"] = tr.get("questions", q["id"], "ask", q["ask"])
            q["explain"] = tr.get("questions", q["id"], "explain", q.get("explain"))
            a = answer_en(q, data, tr)
            if a:
                q["answer"].update({k: v for k, v in a.items() if k in ("head", "more", "verdict", "period", "label", "unit")})
                ans[q["id"]] = dict(q["answer"])
            else:
                q["answer"].update(head="", more=[])
        for c in t["charts"]:
            cid = c.get("chart")
            if c.get("type") == "heatbars" and cid not in (tr.d.get("charts") or {}):  # aus der Wärmetabelle abgeleitet
                w = BARS["Auftragseingang" if "order" in cid else "Produktion"]
                c["title"] = f"{w[0]} by industry: three-month change and level vs 2019"
                c["ask"] = f"Which industries have gained in {w[1]}, which are below 2019?"
                c["caption"] = (f"{w[0]} by industry as bars, switchable. Three-month comparison: last three months vs the three months before, seasonally adjusted. "
                                "Level vs 2019: latest month vs the 2019 average, the last full year before the pandemic and the 2022 energy price shock; "
                                "it shows which industries have regained their pre-crisis level. Orange: increase, blue: decrease.")
            if c.get("kind") == "downturn" and isinstance(c.get("event"), dict):
                PT = {"Industrieproduktion": "Industrial production", "Arbeitslosenquote": "Unemployment rate", "Wirtschaftsleistung (BIP)": "Economic output (GDP)",
                      "Hoch = 100; waagerecht: Monate seit dem Hoch": "peak = 100; horizontal: months since the peak",
                      "Veränderung seit dem Hoch der Produktion in Pp; waagerecht: Monate": "change since the production peak in pp; horizontal: months",
                      "Quartal des Hochs = 100; waagerecht: Quartale": "quarter of the peak = 100; horizontal: quarters", "Monat": "Month", "Quartal": "Quarter"}
                for pn in c["event"]["panels"]:
                    for f in ("title", "sub", "step"):
                        pn[f] = PT.get(pn.get(f), pn.get(f))
                    pn["unit"] = "pp" if pn.get("unit") == "Pp" else pn.get("unit")
                    for ln in pn["lines"]:
                        ln["label"] = ln["label"].replace("Finanzkrise ab", "Financial crisis from").replace("Corona ab", "COVID from").replace("Energiekrise ab", "Energy crisis from").replace("seit ", "since ")
            c["sources"] = [tr.src(x) for x in c.get("sources") or []]
            c["licenses"] = [tr.src(x) for x in c.get("licenses") or []]
            for f in ("title", "ask", "caption", "what"):
                if c.get(f):
                    c[f] = tr.get("charts", cid, f, c[f])
            c["unit_de"] = c.get("unit")
            lab_map = {}
            if c.get("unit"):
                c["unit"] = tr.get("charts", cid, "unit", tr.s(c["unit"]))
            if c.get("adjustment"):
                c["adjustment"] = tr.s(c["adjustment"])
            for s in c.get("series") or [] if isinstance(c.get("series"), list) else []:
                if isinstance(s, dict):
                    s["unit_de"] = s.get("unit")
                    if s.get("label") and s.get("id"):
                        de_lab = s["label"]
                        s["label"] = tr.label(s["id"], s["label"])
                        lab_map[de_lab] = s["label"]
                    if s.get("unit"):
                        s["unit"] = tr.get("series", s.get("id"), "unit", tr.s(s["unit"]))
            c["outliers"] = [dict(o, label=lab_map.get(o.get("label"), o.get("label"))) for o in c.get("outliers") or []]
            texts = chart_sentences_en(c)
            c["texts"], c["text"] = texts, " ".join(texts)
            c["notes"] = []  # automatische Hinweise vorerst nur deutsch
            if isinstance(c.get("files"), dict):
                c["files"] = {k: _rel(v) for k, v in c["files"].items()}
            nu = c.get("next_update")
            if isinstance(nu, dict) and nu.get("period"):
                nu["period"] = de_period_to_en(nu["period"])
    for q in p.get("questions") or []:
        q["ask"] = tr.get("questions", q["id"], "ask", q["ask"])
        if q["id"] in ans:
            q["answer"] = ans[q["id"]]
    p["overview"] = overview_en(ans)
    for r in p.get("start") or []:
        r["label"] = tr.label(r.get("series"), r["label"])
        r["unit"] = tr.s(r.get("unit"))
        r["group"] = tr.get("topics", r.get("topic"), "title", r.get("group"))
        r["period"] = de_period_to_en(r.get("period"))
        for k in ("prev_label", "change_unit"):
            r[k] = tr.s(r.get(k))
    p["geo_source"] = Tr.src(tr, p.get("geo_source"))
    titles = {c.get("no"): c.get("title") for t in p["topics"] for c in t["charts"]}
    p["week"] = [dict(w, title=titles.get(w.get("no"), w.get("title"))) for w in p.get("week") or []]
    p["news"] = [dict(n, label=tr.label(n.get("series"), n.get("label")), period=de_period_to_en(n.get("period"))) for n in p.get("news") or []]
    for k in ("archive_file",):
        p[k] = _rel(p.get(k))
    if isinstance(p.get("all_series"), dict):
        p["all_series"] = {k: _rel(v) for k, v in p["all_series"].items()}
    return p
