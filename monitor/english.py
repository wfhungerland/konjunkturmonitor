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
    "% ggü. Vormonat, Beiträge in Pp": "% on the previous month, contributions in pp",
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
    ("Weltbank", "World Bank"), ("gemeinfrei", "public domain"),
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
        # Beschriftungen deutsch -> englisch: Reihennamen, Namenslisten (Länder, Branchen …) und feste Beschriftungen
        self.labels = {}
        cat = root / "series.yaml"
        if cat.exists():
            c = yaml.safe_load(cat.read_text(encoding="utf-8")) or {}
            for s in c.get("series") or []:
                lab, en = s.get("label"), self.get("series", s.get("id"), "label")
                if lab and en and "{" not in lab:
                    self.labels.setdefault(lab, en)
            self.names_de = c.get("names") or {}
            for kind, vals in self.names_de.items():
                for code, de in (vals or {}).items():
                    en = ((self.d.get("names") or {}).get(kind) or {}).get(code)
                    if en:
                        self.labels.setdefault(str(de), str(en))
        self.labels.update(self.d.get("labels") or {})

    def get(self, sect: str, key: str, field: str, default=None):
        v = ((self.d.get(sect) or {}).get(key) or {})
        v = v.get(field) if isinstance(v, dict) else None
        return v if v not in (None, "") else default

    def lab(self, text):
        """Beschriftung übersetzen: exakt, „26 Elektronik und Optik“ als Branchennummer mit Name, sonst unverändert."""
        if not isinstance(text, str):
            return text
        if text in self.labels:
            return self.labels[text]
        m = re.match(r"^(\d{2}) (.+)$", text)
        if m and m.group(2) in self.labels:
            return f"{m.group(1)} {self.labels[m.group(2)]}"
        return text

    def note(self, text):
        """Automatische Hinweise (Wetter, Rhein, Ausreißer) nach Mustern übersetzen; Handhinweise über labels; sonst None."""
        if text in self.labels:
            return self.labels[text]
        de_num = lambda s: s.replace(".", "").replace(",", ".")
        m = re.match(r"^(\w+ \d{4}) (ungewöhnlich mild|ungewöhnlich kalt): ([\d,]+) °C (über|unter) dem Mittel 1991–2020 \(Deutscher Wetterdienst\)$", text)
        if m:
            return f"{de_period_to_en(m.group(1))} unusually {'mild' if 'mild' in m.group(2) else 'cold'}: {de_num(m.group(3))} °C {'above' if m.group(4) == 'über' else 'below'} the 1991–2020 average (German Weather Service)"
        m = re.match(r"^(\w+ \d{4}) sehr nass: Niederschlag ([\d.,]+) % des Mittels 1991–2020 \(Deutscher Wetterdienst\)$", text)
        if m:
            return f"{de_period_to_en(m.group(1))} very wet: precipitation {de_num(m.group(2))}% of the 1991–2020 average (German Weather Service)"
        m = re.match(r"^(\w+ \d{4}): an (\d+) Tagen Niedrigwasser am Rhein \(Pegel Kaub unter 78 cm\)$", text)
        if m:
            return f"{de_period_to_en(m.group(1))}: low water on the Rhine on {m.group(2)} days (Kaub gauge below 78 cm)"
        return None

    def label(self, sid, de):
        """Englischer Reihenname; bei ausgeklappten Reihen (de_insolv_land_09) aus der Vorlage mit Platzhaltern."""
        v = self.get("series", sid, "label")
        if v or not sid:
            return v or self.lab(de)
        ser = self.d.get("series") or {}
        base = max((k for k in ser if sid.startswith(k + "_")), key=len, default=None)
        tpl = self.get("series", base, "label") if base else None
        if not tpl:
            return self.lab(de)
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
        return self.lab(de) if bad else out

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


PROJ_EN = {"Herbstprojektion": "autumn projection", "Frühjahrsprojektion": "spring projection", "Jahresprojektion": "annual projection"}


def _special_en(c: dict) -> list[str] | None:
    """Sätze für Sonderabbildungen (Karte, Wärmetabelle, Uhr, Saison, Balken, Prognosen, Beiträge, Ereignisse); None für Linien."""
    typ, d = c.get("type"), int(c.get("decimals", 1))
    sg = lambda v, k=1: num(v, k, True)
    if c.get("pot_names"):  # momentum: GDP growth against the range of potential growth estimates
        bar = next(x for x in c["series"] if x.get("style") == "bar")
        lo, hi = (next(x for x in c["series"] if x.get("style") == st) for st in ("band_lo", "band_hi"))
        band = {d[:4]: (a, b) for d, a, b in zip(lo["x"], lo["y"], hi["y"])}
        y, g = bar["x"][-1][:4], bar["y"][-1]
        who = ", ".join(n.split("(")[-1].rstrip(")").replace("IWF", "IMF") for n in c["pot_names"])
        who = " and ".join(who.rsplit(", ", 1))
        out = []
        if y in band:
            a, b = band[y]
            cmp = "slower than" if g < a else "faster than" if g > b else "about as fast as"
            out.append(f"In {y}, GDP grew by {num(g)}%, {cmp} potential output as estimated by {who} ({num(a)} to {num(b)}%).")
        y1 = str(int(y) + 1)
        if y1 in band:
            a, b = band[y1]
            gv = (c.get("gov_values") or {}).get(y1)
            rnd = c.get("gov_round") or ""
            rnd = " ".join(rnd.split()[1:]) + " " + PROJ_EN.get(rnd.split()[0], "") if rnd else ""
            out.append(f"For {y1}, they put potential growth at {num(a)} to {num(b)}%" + (f"; the Federal Government's {rnd} expects GDP growth of {num(gv)}%." if gv is not None else "."))
        return out
    if c.get("diff"):  # breadth: number of industries growing
        parts = []
        for label, k in c["diff"].items():
            what = {"Produktion": "output", "Auftragseingang": "orders"}.get(label, label)
            ago = f", a year earlier in {k['up_ago']}" if k.get("up_ago") is not None else ""
            parts.append(f"{what} rose in {k['up']} of {k['n']} industries{ago}")
        t = pd.Timestamp(max(k["period"] for k in c["diff"].values()))
        return [f"In the three months to {period(t, 'M')} on the three months before, " + "; ".join(parts) + "."]
    if c.get("proj"):  # projection of the Federal Government
        p = c["proj"]
        rnd = lambda r: " ".join(r.split()[1:]) + " " + PROJ_EN.get(r.split()[0], r.split()[0])  # „Herbstprojektion 2026“ -> „2026 autumn projection“
        ordn = {1: "first", 2: "second", 3: "third", 4: "fourth"}
        qs = lambda l: f"in the {ordn[l[0]]} quarter" if len(l) == 1 else "in each of the " + ", ".join(ordn[q] for q in l[:-1]) + f" and {ordn[l[-1]]} quarters"
        if p["rest"]:
            k = p["known"][-1] if p["known"] else None
            out = [f"To meet the Federal Government's {rnd(p['round'])} of {num(p['target'])}% for {p['year']}, GDP would have to be {num(p['need'])}% above "
                   f"the same quarter a year earlier {qs(p['rest'])}" + (f"; in the {ordn[k['q']]} quarter it was {num(k['v'])}%." if k else ".")]
            if p.get("need_qoq") is not None and p.get("last_qoq") is not None:
                out.append(f"Seasonally and calendar adjusted, that would mean growth of {num(p['need_qoq'])}% on the previous quarter in the {ordn[p['rest'][0]]} quarter; "
                           f"the latest figure was {num(p['last_qoq'])}%.")
        else:
            out = [f"Over the four quarters, GDP grew by about {num(p['done_rate'])}% in {p['year']}; the Federal Government's {rnd(p['round'])} expected {num(p['target'])}%."]
        if p.get("prev"):
            out.append(f"The {rnd(p['prev']['round'])} had expected {num(p['prev']['value'])}% for {p['year']}.")
        return out
    if typ == "tiles":
        w = c["tiles"]
        if w.get("measure") == "diff":
            hi, lo = max(w["rows"], key=lambda r: r["level"]), min(w["rows"], key=lambda r: r["level"])
            up = max(w["rows"], key=lambda r: r["change"])
            out = [f"In {w['span']} the {c.get('what') or 'rate'} was highest in {hi['name']} at {num(hi['level'])}% and lowest in {lo['name']} at {num(lo['level'])}%."]
            if up["change"] > 0:
                out.append(f"It rose most in {up['name']}: by {num(up['change'])} pp on the previous year.")
            return out
        big = sorted(w["rows"], key=lambda r: r.get("sum") or 0)[len(w["rows"]) // 2:] if all(r.get("sum") is not None for r in w["rows"]) else w["rows"]
        rows = sorted(big, key=lambda r: r["change"])
        span = de_period_to_en(w["span"]).replace(" bis ", " to ")
        cnt = lambda r: f" ({int(r['sum']):,} cases)" if r.get("sum") is not None else ""
        pre = f"{span}, among the {len(big)} states with the most cases: " if len(big) < len(w["rows"]) else f"{span}: "
        return [f"{pre}the strongest increase on the same period a year earlier was in {rows[-1]['name']} at {sg(rows[-1]['change'])}%{cnt(rows[-1])}.",
                f"The {'largest decrease' if rows[0]['change'] < 0 else 'smallest increase'} was in {rows[0]['name']} at {sg(rows[0]['change'])}%{cnt(rows[0])}."]
    if typ == "heat":
        rows, per = c["heat"]["rows"], period(pd.Timestamp(c["heat"]["cols"][-1]), "M")
        return [f"In the three months to {per}, “{rows[-1]['label']}” grew most: {sg(rows[-1]['m3'])}% on the three months before.",
                f"In the three months to {per}, “{rows[0]['label']}” was weakest: {sg(rows[0]['m3'])}% on the three months before."]
    if typ == "heatbars":
        lv = sorted([r for r in c["heat"]["rows"] if r.get("level") is not None], key=lambda r: r["level"])
        if not lv:
            return []
        per = period(pd.Timestamp(c["heat"]["cols"][-1]), "M")
        below = sum(1 for r in lv if r["level"] < 0)
        m3 = sorted([r for r in c["heat"]["rows"] if r.get("m3") is not None], key=lambda r: r["m3"])
        first = [f"In the three months to {per}, “{m3[-1]['label']}” grew most ({sg(m3[-1]['m3'])}% on the three months before), “{m3[0]['label']}” was weakest ({sg(m3[0]['m3'])}%)."] if m3 else []
        return first + [f"In {per}, {below} of {len(lv)} industries were below their 2019 average, the last full year before the pandemic.",
                f"Furthest above 2019 was “{lv[-1]['label']}” ({sg(lv[-1]['level'])}%), furthest below “{lv[0]['label']}” ({sg(lv[0]['level'])}%)."]
    if typ == "clock":
        k = c["clock"]
        x, y, t0 = k["x"][-1], k["y"][-1], pd.Timestamp(k["t"][-1])
        phase = "boom" if x >= 0 and y >= 0 else "downswing" if x >= 0 else "upswing" if y >= 0 else "recession"
        w = f"In {period(t0, 'M')}"
        return [f"{w}, industry was in the “{phase}” quadrant of the business cycle clock.",
                f"{w}, manufacturers rated their order books {'better' if x >= 0 else 'worse'} than the 2005–2019 average (balance {sg(x)} pp).",
                f"{w}, manufacturers expected {'stronger' if y >= 0 else 'weaker'} production over the next three months than the 2005–2019 average (balance {sg(y)} pp)."]
    if typ == "seasonal":
        i = max(k for k, v in enumerate(c["y"]) if v is not None)
        t0, lab = pd.Timestamp(c["x"][i]), c.get("label") or c.get("title", "")
        out = [f"In {period(t0, 'M')} the figure for “{lab}” was {num(c['y'][i], d)}."]
        if c["ma12"][i] is not None:
            out.append(f"In the twelve months to {period(t0, 'M')} it averaged {num(c['ma12'][i], d)} a month.")
        if c["norm"][i] is not None:
            out.append(f"Before the pandemic (2015 to 2019) it averaged {num(c['norm'][i], d)} in {MONTHS[t0.month - 1]}.")
        return out
    if typ == "latest":
        b = c.get("bars") or []
        if not b:
            return []
        if c.get("base"):
            bs = sorted(b, key=lambda x: x["value"])
            pc = lambda x: f" ({num(x['pct'], 1, True)}%)" if x.get("pct") is not None else ""
            out = [f"Since {period(pd.Timestamp(c['base']), c.get('freq', 'Q'))}, employment rose most in “{bs[-1]['label']}”: by {num(bs[-1]['value'], d)} {(c.get('unit') or '').split(',')[0]}{pc(bs[-1])}.".replace(" .", ".").replace("  (", " (")]
            if bs[0]["value"] < 0:
                out.append(f"It fell most in “{bs[0]['label']}”: by {num(abs(bs[0]['value']), d)} {(c.get('unit') or '').split(',')[0]}{pc(bs[0])}.".replace(" .", ".").replace("  (", " ("))
            return out
        w = when(b[0]["period"], c.get("freq", "Q"))
        cb = c.get("combine")
        if isinstance(cb, dict) and cb.get("lead_en"):
            items = [f"{x['label']} {sg(x['value'], d)}%" for x in b]
            return [f"{w}, {cb['lead_en']} " + (", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else items[0]) + "."]
        return [f"{w}, “{x['label']}” {'rose' if x['value'] > 0.05 else 'fell' if x['value'] < -0.05 else 'barely changed'}"
                + (f" by {num(abs(x['value']), d)}%" if abs(x["value"]) > 0.05 else "") + " on the previous period." for x in b]
    if typ == "forecast":
        fs = c.get("forecasts") or []
        what = {"gdp": "real GDP growth", "inflation": "inflation", "core": "core inflation"}.get(c.get("measure", "gdp"), "growth")
        years = sorted({int(k) for f in fs for k in f["values"] if int(k) >= pd.Timestamp.now().year})
        out = []
        for y in years:
            latest = {}
            for f in sorted(fs, key=lambda f: f["date"]):
                if y in f["values"] or str(y) in f["values"]:
                    latest[f["by"]] = f["values"].get(y, f["values"].get(str(y)))
            if len(latest) >= 2:
                v = sorted(latest.values())
                out.append(f"The latest forecasts of {len(v)} institutions for {what} in {y} range from {num(v[0])}% to {num(v[-1])}%.")
        return out
    if typ == "stacked":
        series = [s for s in c.get("series") or [] if s.get("y")]
        bars0 = [s for s in series if s.get("style") == "bar"]
        if not bars0:
            return []
        last = max(s["x"][-1] for s in bars0)
        bars = [s for s in bars0 if last in s["x"]]
        at = lambda s: s["y"][s["x"].index(last)]
        w = when(last, c.get("freq", "Q"))
        hi, lo = max(bars, key=at), min(bars, key=at)
        out = [f"{w}, “{hi['label']}” contributed most: {sg(at(hi), d)} pp."]
        if round(at(lo), d) < 0:
            out.append(f"{w}, “{lo['label']}” held it back most: {sg(at(lo), d)} pp.")
        return out
    if typ == "event" and c.get("kind") == "history":
        out = []
        for p in c["event"]["panels"]:
            cur = next((l for l in p["lines"] if l["current"]), None)
            if not cur or len(cur["y"]) < 2 or cur["y"][-1] is None:
                continue
            k, v, pk = len(cur["y"]) - 1, cur["y"][-1], cur["start"][:4]
            old = [l for l in p["lines"] if not l["current"] and len(l["y"]) > k and l["y"][k] is not None]
            cmp = "; at the same point " + ", ".join(f"{l['label']} {num(l['y'][k] - p['base'], 1, True)}{' pp' if p.get('unit') in ('pp', 'Pp') else '%'}" for l in old) if old else ""
            if p.get("mode") == "level":
                out.append(f"{k} {'year' if k == 1 else 'years'} after the {pk} inflation peak, the inflation rate was {num(v)}%{cmp.replace('+', '')}.")
            elif p.get("unit") in ("pp", "Pp"):
                out.append(f"Since the {pk} peak the unemployment rate has {'risen' if v > 0 else 'fallen'} by {num(abs(v))} pp ({k} {'year' if k == 1 else 'years'}){cmp}.")
            else:
                out.append(f"{k} {'year' if k == 1 else 'years'} after the {pk} peak, real GDP was {num(abs(v - 100))}% {'below' if v < 100 else 'above'} the peak{cmp}.")
        return out
    if typ == "event" and c.get("kind") == "downturn":
        out = []
        for p in c["event"]["panels"]:
            cur = next((l for l in p["lines"] if l["current"]), None)
            if not cur or len(cur["y"]) < 2:
                continue
            k, v, st = len(cur["y"]) - 1, cur["y"][-1], pd.Timestamp(cur["start"])
            step = "quarters" if p.get("step") in ("Quarter", "Quartal") else "months"
            if p.get("unit") in ("pp", "Pp"):
                out.append(f"Since the production peak in {period(st, 'M')} the unemployment rate has {'risen' if v > 0 else 'fallen'} by {num(abs(v))} pp ({k} {step}).")
            else:
                out.append(f"{k} {step} after the peak in {period(st, 'Q' if step == 'quarters' else 'M')}, {p['title'][:1].lower() + p['title'][1:]} was {num(abs(v - 100))}% {'below' if v < 100 else 'above'} the peak.")
        return out
    if typ == "event":
        return []
    return None


def chart_sentences_en(c: dict) -> list[str]:
    """Englische Fassung der automatischen Sätze: Sonderabbildungen eigens, Linien und Balken nach der Einheit."""
    typ, d = c.get("type"), int(c.get("decimals", 1))
    try:
        sp = _special_en(c)
    except (KeyError, IndexError, ValueError, TypeError, ZeroDivisionError):
        return []
    if sp is not None:
        return sp
    if typ == "enso_comm" and c.get("enso"):
        E = c["enso"]
        for r in E["rows"]:  # Rohstoffnamen englisch (die englische Fassung ist eine eigene Kopie)
            r["label"] = (c.get("items_en") or {}).get(r["id"], r["label"])
        und = lambda xs: ", ".join(xs[:-1]) + " and " + xs[-1] if len(xs) > 1 else xs[0]
        up = [r["label"] for r in reversed(E["rows"]) if r["sig"] and r["nino"] > r["neutral"]]
        dn = [r["label"] for r in E["rows"] if r["sig"] and r["nino"] < r["neutral"]]
        span = f"From {E['from'][:4]} to {E['to'][:4]}"
        out = [f"{span}, prices of {und(up)} rose clearly more {E['lag']} months after El Niño months than after neutral months." if up else
               f"{span}, no commodity rose clearly more {E['lag']} months after El Niño months than after neutral months."]
        if dn:
            out.append(f"For {und(dn)} the rise after El Niño was clearly weaker.")
        top = E["rows"][-1]
        if top["nino"] > top["neutral"]:
            out.append(f"The largest lead after El Niño is for {top['label']}: {num(top['nino'], 1, True)}% on a year earlier after El Niño, {num(top['neutral'], 1, True)}% after neutral months.")
        return out
    halves = [s for s in (c.get("series") or []) if isinstance(s, dict) and s.get("style") == "half" and s.get("y")]
    if halves:  # erstes Halbjahr eines Jahres, etwa BIP Berlin: eigener Satz
        y0 = halves[0]
        out = [f"In the first half of {y0['x'][-1][:4]}, real GDP growth in {y0.get('label', 'Berlin').split(',')[0]} was {num(y0['y'][-1], d)}% on a year earlier, according to a first estimate."]
        out += [f"In {h.get('label', 'Germany').split(',')[0]} it was {num(h['y'][-1], d)}% over the same period." for h in halves[1:]]
        return out
    if typ not in ("line", "dumbbell", None) or not isinstance(c.get("series"), list):
        return []
    try:
        series = [s for s in c["series"] if s.get("y")]
        norm = next((s for s in series if s.get("style") == "norm"), None)
        series = [s for s in series if s.get("style") != "norm"]
        if c.get("emphasis"):
            series = [s for s in series if s["id"] == c["emphasis"]] or series
        freq = c.get("freq", "M")
        if c.get("combine") and not isinstance(c.get("combine"), dict) and (c.get("unit_de") or "").startswith("Index"):  # gleich gebaute Reihen in einem Satz
            last = max(s["x"][-1] for s in series)
            parts = [(re.sub(r"^\d+\s+", "", s.get("label", "")), (s["y"][-1] / s["y"][-13] - 1) * 100)
                     for s in series if s["x"][-1] == last and len(s["y"]) > 12 and s["y"][-13]]
            if parts:
                below = sum(1 for _, p in parts if round(p, 1) < 0)
                words = {0: "none", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
                return [f"{when(last, freq)}, output was below its level of a year earlier in {words.get(below, below)} of {words.get(len(parts), len(parts))} industries: "
                        + "; ".join(f"{lab} {num(p, 1, True)}%" for lab, p in parts) + "."]
        series = series[:6]
        last = max(s["x"][-1] for s in series)
        w = when(last, freq)
        if c.get("mad_band"):  # Korrekturen des BIP-Wachstums
            rv = next((s for s in c["series"] if s.get("style") == "bar"), None)
            hv = {s["id"]: s for s in c["series"] if s.get("style") == "hover"}
            if rv and rv["y"]:
                pts = [(x, v) for x, v in zip(rv["x"], rv["y"]) if v is not None]
                m = sum(abs(v) for _, v in pts) / len(pts)
                xb, vb = max(pts, key=lambda p: abs(p[1]))
                out = [f"From {period(pd.Timestamp(pts[0][0]), freq)} to {period(pd.Timestamp(pts[-1][0]), freq)}, quarterly GDP growth was revised by {num(m, 2)} pp on average, most in {period(pd.Timestamp(xb), freq)} ({num(vb, 1, True)} pp)."]
                f0, l0 = hv.get("gdp_rt_first"), hv.get("gdp_rt_latest")
                if f0 and l0 and f0["x"][-1] == l0["x"][-1]:
                    out.append(f"For {period(pd.Timestamp(f0['x'][-1]), freq)}, the first release was {num(f0['y'][-1], 1)}% and the current figure is {num(l0['y'][-1], 1)}%; recent quarters have usually seen little revision so far.")
                return out
        cb = c.get("combine")
        if isinstance(cb, dict) and cb.get("lead_en"):  # gleich gebaute Reihen in einem Satz
            su0 = (c.get("unit_de") or "").split(",")[0]
            sym = "%" if su0.startswith("%") else " pp" if su0.startswith(("Pp", "Saldo")) else "" if su0.startswith("Index") else " " + (c.get("unit") or "").split(",")[0]
            last_c = min(s["x"][-1] for s in series) if cb.get("common") else last
            at = lambda s: s["y"][s["x"].index(last_c)] if last_c in s["x"] else None
            items = [f"{cb.get('pre_en', '')}{s.get('label', '')} {num(at(s), d, cb.get('sign', True))}{sym}" for s in series if at(s) is not None]
            if items:
                return [f"{when(last_c, freq) if cb.get('common') else w}, {cb['lead_en']} " + (", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else items[0]) + "."]
        mig = {"de_netmig_de": "Germans", "de_netmig_eu": "people from other EU countries", "de_netmig_neu": "people from outside the EU"}
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
            if s.get("id") in mig:  # Wanderung: wer kam, wer ging
                out.append(f"{w}, net {num(abs(v), d)} thousand {mig[s['id']]} {'moved to Germany' if v >= 0 else 'left Germany'}.")
                continue
            if s.get("id") in ("gdp_rt_first", "gdp_rt_latest"):
                out.append(f"{w}, {subj} was {num(v, d)}% on the previous quarter.")
                continue
            if s.get("id") == "gdp_rt_rev":
                out.append(f"{w}, GDP growth is unchanged since the first release." if round(v, d) == 0 else f"{w}, GDP growth has been revised {'up' if v > 0 else 'down'} by {num(abs(v), d)} pp since the first release.")
                continue
            if su.startswith("Index") and not su.startswith("Index 0") and c.get("sent_ma3") and len(s["y"]) >= 15 and None not in s["y"][-15:]:
                ch = (sum(s["y"][-3:]) / sum(s["y"][-15:-12]) - 1) * 100
                out.append(f"In the three months to {period(pd.Timestamp(last), f)}, {subj} was {num(abs(ch), 1)}% {'above' if ch > 0 else 'below'} the same period a year earlier.")
                continue
            if s.get("id") == "de_hdd":
                out.append(f"{w}, heating demand was {num(v, d)} degree days.")
                continue
            if su.startswith(("% ggü", "Pp ggü")):
                ref = ("on the previous month" if "Vormonat" in su else "on the previous quarter" if "Vorquartal" in su else "on a year earlier" if "Vorjahr" in su
                       else "on the previous week" if "Vorwoche" in su else "")
                pu = "%" if su.startswith("%") else " pp"
                if round(v, d) == 0:
                    sent = f"{w}, {subj} barely changed ({ref})"
                else:
                    sent = f"{w}, {subj} {'rose' if v > 0 else 'fell'} by {num(abs(v), d)}{pu} {ref}"
                if len(s["y"]) > 1 and s["y"][-2] is not None and not c.get("no_yoy"):
                    sent += f", after {num(s['y'][-2], d, True)}{pu} {prev_lbl.get(f, 'before')}"
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
        if c.get("long_mean") and out and series:
            su0 = (c.get("unit_de") or "").split(",")[0]
            u0 = "%" if su0.startswith("%") and not su0.startswith(("% des", "% der")) else " " + (c.get("unit") or "").split(",")[0]
            parts = [(s.get("label", ""), [v for v in s["y"] if v is not None]) for s in series if s.get("y")]
            parts = [(lab, v) for lab, v in parts if v]
            if parts:
                many = len(parts) > 1
                out.append(f"For comparison, average {series[0]['x'][0][:4]} to {series[0]['x'][-1][:4]} excluding war years: "
                           + "; ".join(f"{lab + ' ' if many else ''}{num(sum(v) / len(v), d)}{u0}" for lab, v in parts) + ".")
        if c.get("type") == "threshold" and c.get("threshold") is not None and out and series and series[0]["y"][-1] is not None:
            out.append("This is a recession signal." if series[0]["y"][-1] >= float(c["threshold"]) else "This is not a recession signal.")
        if norm and out and norm["x"][-1] == last and series and series[0]["y"][-1] is not None and norm["y"][-1]:
            a0, a1 = c.get("norm") or ("", "")
            out.append(f"That is {num(series[0]['y'][-1] / norm['y'][-1] * 100, 0)}% of the {a0}–{a1} average for the same month ({num(norm['y'][-1], d)}).")
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
        for c in [x for c0 in t["charts"] for x in [c0] + ([c0["variant"]] if isinstance(c0.get("variant"), dict) else [])]:
            cid = c.get("chart")
            if c.get("type") == "heatbars" and cid not in (tr.d.get("charts") or {}):  # aus der Wärmetabelle abgeleitet
                w = BARS["Auftragseingang" if "order" in cid else "Produktion"]
                c["title"] = f"{w[0]} by industry: three-month change and level vs 2019"
                c["ask"] = f"Which industries have gained in {w[1]}, which are below 2019?"
                c["caption"] = (f"{w[0]} by industry as bars, switchable. Three-month comparison: last three months vs the three months before, seasonally adjusted. "
                                "Level vs 2019: latest month vs the 2019 average, the last full year before the pandemic and the 2022 energy price shock; "
                                "it shows which industries have regained their pre-crisis level. Orange: increase, blue: decrease.")
            if c.get("kind") in ("downturn", "history") and isinstance(c.get("event"), dict):
                PT = {"Inflationsrate": "Inflation rate", "in %; waagerecht: Jahre seit dem Inflationshoch": "in %; horizontal: years since the inflation peak",
                      "Spanne der übrigen Schübe": "Range of the other surges", "Reales BIP": "Real GDP", "Jahr des Hochs = 100; waagerecht: Jahre seit dem Hoch": "peak year = 100; horizontal: years since the peak",
                      "Veränderung seit dem Jahr des Hochs in Pp; waagerecht: Jahre": "change since the peak year in pp; horizontal: years", "Jahr": "Year",
                      "Spanne der übrigen Abschwünge": "Range of the other downturns",
                      "Industrieproduktion": "Industrial production", "Arbeitslosenquote": "Unemployment rate", "Wirtschaftsleistung (BIP)": "Economic output (GDP)",
                      "Hoch = 100; waagerecht: Monate seit dem Hoch": "peak = 100; horizontal: months since the peak",
                      "Veränderung seit dem Hoch der Produktion in Pp; waagerecht: Monate": "change since the production peak in pp; horizontal: months",
                      "Quartal des Hochs = 100; waagerecht: Quartale": "quarter of the peak = 100; horizontal: quarters", "Monat": "Month", "Quartal": "Quarter"}
                for pn in c["event"]["panels"]:
                    for f in ("title", "sub", "step", "band_label"):
                        pn[f] = PT.get(pn.get(f), pn.get(f))
                    pn["unit"] = "pp" if pn.get("unit") == "Pp" else pn.get("unit")
                    for ln in pn["lines"]:
                        ln["label"] = ln["label"].replace("Finanzkrise ab", "Financial crisis from").replace("Corona ab", "COVID from").replace("Energiekrise ab", "Energy crisis from").replace("Finanzkrise ", "Financial crisis ").replace("Weltwirtschaftskrise ", "Great Depression ").replace("Korea-Boom ", "Korean War boom ").replace("Zweite Ölkrise ", "Second oil crisis ").replace("Ölkrise ", "Oil crisis ").replace("Wiedervereinigung ", "Reunification ").replace("Corona ", "COVID ").replace("laufend, seit ", "ongoing, since ").replace("seit ", "since ")
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
            for r in c.get("refs") or []:
                r["label"] = tr.lab(r.get("label"))
            for s in c.get("series") or [] if isinstance(c.get("series"), list) else []:
                if isinstance(s, dict):
                    s["unit_de"] = s.get("unit")
                    if s.get("label") and s.get("id"):
                        de_lab = s["label"]
                        s["label"] = {"band_lo": "Range of estimates, lower bound", "band_hi": "Range of estimates, upper bound"}.get(s.get("style")) or tr.label(s["id"], s["label"])
                        lab_map[de_lab] = s["label"]
                    if s.get("unit"):
                        s["unit"] = tr.get("series", s.get("id"), "unit", tr.s(s["unit"]))
            if c.get("diff"):
                for s_ in c["series"]:
                    s_["label"] = s_["label"].replace("Produktion", "Output").replace("Auftragseingang", "Orders").replace("Branchen", "industries")
                c["refs"] = [{"y": 50, "label": "Half of industries"}]
                c["adjustment"] = "seasonally and calendar adjusted (Bundesbank)"
                c["sources"] = ["Deutsche Bundesbank (output and orders of the Federal Statistical Office)", "own calculation"]
            if c.get("proj"):  # Projektion: Bezeichnungen der Runde übersetzen
                pj, rnd = c["proj"], lambda r: PROJ_EN.get(r.split()[0], r.split()[0]).capitalize() + " " + " ".join(r.split()[1:])
                c["refs"] = [{"y": pj["target"], "x0": f"{pj['year']}-01-01", "label": f"{rnd(pj['round'])}: {num(pj['target'])}%"}]
                c["adjustment"] = "price adjusted, not seasonally or calendar adjusted (like the annual rate of the projection)"
                for s_ in c["series"]:
                    s_["label"] = "GDP on the same quarter a year earlier"
                c["sources"] = ["Eurostat (GDP of the Federal Statistical Office)", f"Federal Government ({rnd(pj['round'])})", "own calculation"]
            c["outliers"] = [dict(o, label=tr.lab(lab_map.get(o.get("label"), o.get("label")))) for o in c.get("outliers") or []]
            c["notes"] = [dict(n, text=en) for n in c.get("notes") or [] if (en := tr.note(n.get("text", "")))]
            if isinstance(c.get("heat"), dict):
                for r in c["heat"].get("rows") or []:
                    r["label"] = tr.lab(r.get("label"))
            for b in c.get("bars") or []:
                b["label"] = tr.lab(lab_map.get(b.get("label"), b.get("label")))
            if c.get("type") == "seasonal" and c.get("label"):
                c["label"] = tr.label(c.get("series") if isinstance(c.get("series"), str) else None, c["label"])
            if isinstance(c.get("alt"), dict):
                for s in c["alt"].get("series") or []:
                    s["label"] = tr.lab(s.get("label"))
                c["alt"]["label"], c["alt"]["base"] = "on previous month", "on a year earlier"
                c["alt"]["unit"] = tr.s(c["alt"].get("unit"))
            for w in (c.get("tiles"), c.get("tiles6")):
                for r in (w or {}).get("rows") or []:
                    r["name"] = tr.lab(r.get("name"))
            for f in c.get("forecasts") or []:
                f["by"], f["round"] = tr.src(f.get("by")), tr.src(f.get("round"))
            if isinstance(c.get("calendar"), dict):
                for e in c["calendar"].get("events") or []:
                    e["name"], e["source"] = tr.lab(e.get("name")), tr.lab(e.get("source"))
                for l in c["calendar"].get("links") or []:
                    l["name"] = tr.lab(l.get("name"))
            from .satzpruefung import BAD
            texts = [x.replace("in Euro area", "in the euro area").replace("in European Union", "in the European Union")
                     for x in chart_sentences_en(c) if not BAD.search(x)]  # Platzhalter oder Rechenreste: Satz entfällt
            c["texts"], c["text"] = texts, " ".join(texts)
            if isinstance(c.get("files"), dict):
                c["files"] = {k: _rel(v) for k, v in c["files"].items()}
            nu = c.get("next_update")
            if isinstance(nu, dict) and nu.get("period"):
                nu["period"] = de_period_to_en(nu["period"])
    for t in p["topics"]:  # zwei Abbildungen in einer Karte: Sätze und Erläuterung der zweiten Ansicht anhängen
        for c in t["charts"]:
            o = c.get("variant")
            if isinstance(o, dict):
                c["texts"] = list(c.get("texts") or []) + list(o.get("texts") or [])
                c["text"] = " ".join(c["texts"])
                tg = c.get("toggle") or {}
                tg["base"], tg["label"] = tg.get("base_en", tg.get("base")), tg.get("label_en", tg.get("label"))
                if o.get("caption"):
                    c["caption"] = f"{c.get('caption', '')} View “{tg['label']}”: {o['caption']}".strip()
    for t in p["topics"]:  # beschriftete Bezugslinien
        for c in t["charts"]:
            if c.get("ref_labels_en"):
                c["ref_labels"] = c["ref_labels_en"]
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
