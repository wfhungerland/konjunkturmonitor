"""Erster Bildschirm „Lage auf einen Blick“: sieben Kernzahlen, Lage-Satz, Warnlampen und Ausblick.

Leser sind Ministerin, Kanzler, Konzernlenker: Wo steht die Wirtschaft, wohin läuft sie, wo liegt das Risiko.
Alle Werte kommen aus den Reihen des Monitors. Lage-Satz und Warnlampen sind Wertung nach festen Regeln; die Seite
zeigt sie nur mit eingeschaltetem Kommentar. Texte deutsch und englisch, die Seite wählt nach DATA.lang.
"""
from __future__ import annotations

import pandas as pd

M_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
M_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NB = " "


def _num(v: float, d: int, lang: str, sign: bool = False) -> str:
    s = f"{abs(v):,.{d}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".") if lang == "de" else s
    if round(v, d) < 0:
        return "−" + s
    return ("+" + s) if sign and round(v, d) > 0 else s


def _per(ts: pd.Timestamp, freq: str, lang: str) -> str:
    if freq == "Q":
        q = (ts.month - 1) // 3 + 1
        return f"{q}. Quartal {ts.year}" if lang == "de" else f"Q{q} {ts.year}"
    return f"{(M_DE if lang == 'de' else M_EN)[ts.month - 1]} {ts.year}"


def _tri(a: float, b: float, d: int = 1) -> str:
    return "flat" if round(a, d) == round(b, d) else ("up" if a > b else "down")


def _s(data: dict, k: str) -> pd.Series | None:
    s = data.get(k)
    return s.dropna() if s is not None and len(s.dropna()) else None


def _gas_eur(data: dict) -> pd.Series | None:
    """Erdgas Europa in Euro je MWh: US-Dollar je MMBtu durch US-Dollar je Euro (Monatsmittel) und 0,293071 MWh je MMBtu."""
    g, fx = _s(data, "w_gas_eu"), _s(data, "fx_usd")
    if g is None or fx is None:
        return None
    fx = fx.groupby(fx.index.to_period("M")).mean()
    fx.index = fx.index.to_timestamp()
    return (g / fx.reindex(g.index) / 0.293071).dropna()


def _three(s: pd.Series) -> float | None:
    """Veränderung der letzten drei Monate gegenüber den drei Monaten davor, in %."""
    if len(s) < 6:
        return None
    return (s.iloc[-3:].mean() / s.iloc[-6:-3].mean() - 1) * 100


def build(data: dict, forecasts: list[dict], lang: str = "de") -> dict:
    de = lang == "de"
    n = lambda v, d=1, sign=False: _num(v, d, lang, sign)
    pc = lambda v, d=1, sign=False: f"{n(v, d, sign)}{NB}%" if de else f"{n(v, d, sign)}%"
    kp, facts = [], {}

    def tile(key, label, value, unit, tri, bad, lines, per, topic):
        kp.append({"key": key, "label": label, "value": value, "unit": unit, "tri": tri, "bad": bool(bad and tri == "up"), "lines": lines, "per": per, "topic": topic})

    q = _s(data, "de_gdp_qoq")
    if q is not None and len(q) > 1:
        v, p = float(q.iloc[-1]), float(q.iloc[-2])
        norm = float(q[(q.index.year >= 2015) & (q.index.year <= 2019)].mean())
        facts["gdp"] = (v, norm, q.index[-1])
        tile("wachstum", "Wachstum" if de else "Growth", n(v, 1, True), "%", _tri(v, p), False,
             [(f"Vorquartal {pc(p, 1, True)}" if de else f"previous quarter {pc(p, 1, True)}"), (f"normal: {pc(norm, 1, True)}" if de else f"normal: {pc(norm, 1, True)}")],
             (_per(q.index[-1], "Q", lang) + (", ggü. Vorquartal" if de else ", on previous quarter")), "wachstum")
    c = _s(data, "de_cpi_yoy")
    if c is not None and len(c) > 1:
        v, p = float(c.iloc[-1]), float(c.iloc[-2])
        facts["cpi"] = (v, p)
        tile("preise", "Inflation", n(v), "%", _tri(v, p), True,
             [(f"Vormonat {pc(p)}" if de else f"previous month {pc(p)}"), (f"Ziel: {pc(2.0)}" if de else f"target: {pc(2.0)}")], _per(c.index[-1], "M", lang), "preise")
    a = _s(data, "de_alq_sa")
    if a is not None and len(a) > 12:
        v, y = float(a.iloc[-1]), float(a.iloc[-13])
        tile("arbeit", "Arbeitslosigkeit" if de else "Unemployment", n(v), "%", _tri(v, y), True,
             [(f"vor einem Jahr {pc(y)}" if de else f"a year ago {pc(y)}"), ("gemeldete Arbeitslose" if de else "registered unemployed")], _per(a.index[-1], "M", lang), "arbeit")
    e = _s(data, "de_esi")
    if e is not None and len(e) > 1:
        v, p = float(e.iloc[-1]), float(e.iloc[-2])
        tile("stimmung", "Stimmung" if de else "Sentiment", n(v), "", _tri(v, p), False,
             [(f"Vormonat {n(p)}" if de else f"previous month {n(p)}"), ("normal: 100")], _per(e.index[-1], "M", lang) + (", EU-Kommission" if de else ", European Commission"), "stimmung")
    ip, od = _s(data, "de_ip"), _s(data, "de_orders")
    if ip is not None:
        v = _three(ip)
        o = _three(od) if od is not None else None
        if v is not None:
            facts["ip3"] = v
            tile("industrie", "Industrie" if de else "Industry", n(v, 1, True), "%", "flat" if round(v, 1) == 0 else ("up" if v > 0 else "down"), False,
                 [("Produktion, drei Monate" if de else "output, three months"), ((f"Aufträge {pc(o, 1, True)}" if de else f"orders {pc(o, 1, True)}") if o is not None else "")],
                 (f"bis {_per(ip.index[-1], 'M', lang)}" if de else f"to {_per(ip.index[-1], 'M', lang)}"), "industrie")
    ins = _s(data, "de_insolv")
    if ins is not None and len(ins) > 12:
        t = ins.index[-1]
        v = float(ins.iloc[-1])
        ago = ins.get(t - pd.DateOffset(years=1))
        pre = ins[(ins.index.month == t.month) & (ins.index.year >= 2015) & (ins.index.year <= 2019)]
        yoy = (v / float(ago) - 1) * 100 if ago else None
        vs = (v / float(pre.mean()) - 1) * 100 if len(pre) else None
        facts["ins"] = (yoy, vs)
        tile("insolvenzen", "Insolvenzen" if de else "Insolvencies", n(v, 0), "", "flat" if yoy is None or round(yoy, 1) == 0 else ("up" if yoy > 0 else "down"), True,
             [x for x in [(f"{pc(yoy, 1, True)} zum Vorjahr" if de else f"{pc(yoy, 1, True)} on a year ago") if yoy is not None else "",
                          (f"{pc(vs, 0, True)} ggü. 2015–19" if de else f"{pc(vs, 0, True)} vs 2015–19") if vs is not None else ""] if x],
             _per(t, "M", lang), "insolvenzen")
    gas, br = _gas_eur(data), _s(data, "w_brent")
    if gas is not None and len(gas) > 12:
        t = gas.index[-1]
        v, ago = float(gas.iloc[-1]), gas.get(t - pd.DateOffset(years=1))
        dif = v - float(ago) if ago is not None else None
        byoy = None
        if br is not None and len(br) > 12:
            b0, b1 = br.get(br.index[-1] - pd.DateOffset(years=1)), float(br.iloc[-1])
            byoy = (b1 / float(b0) - 1) * 100 if b0 else None
        facts["energy"] = (dif / float(ago) * 100 if ago else None, byoy)
        lines = [(f"Gas, {'+' if dif >= 0 else '−'}€{n(abs(dif), 0)} zum Vorjahr" if de else f"gas, {'+' if dif >= 0 else '−'}€{n(abs(dif), 0)} on a year ago") if dif is not None else ""]
        if br is not None:
            lines.append((f"Öl ${n(float(br.iloc[-1]), 0)}" + (f", {pc(byoy, 0, True)}" if byoy is not None else "")) if de else (f"oil ${n(float(br.iloc[-1]), 0)}" + (f", {pc(byoy, 0, True)}" if byoy is not None else "")))
        tile("energie", "Energie" if de else "Energy", f"€{n(v, 0)}", "/MWh", "flat" if dif is None or round(dif) == 0 else ("up" if dif > 0 else "down"), True,
             [x for x in lines if x], (f"Gas {_per(t, 'M', lang)}" if de else f"gas {_per(t, 'M', lang)}"), "energie")

    # Lage-Satz (Wertung nach festen Regeln)
    say, say2 = [], []
    if "gdp" in facts:
        v, norm, t = facts["gdp"]
        g = ("Die Wirtschaft schrumpft" if v < 0 else "Die Wirtschaft wächst kaum" if v < 0.25 else "Die Wirtschaft wächst") if de else \
            ("The economy is shrinking" if v < 0 else "The economy is barely growing" if v < 0.25 else "The economy is growing")
        if "ip3" in facts:
            g += (", die Industrie schrumpft" if facts["ip3"] < 0 else ", die Industrie legt zu") if de else (", industry is shrinking" if facts["ip3"] < 0 else ", industry is expanding")
        say.append(g + ".")
        say2.append((f"Im {_per(t, 'Q', lang)} wuchs die Wirtschaft um {pc(v)}; im Schnitt der Jahre 2015 bis 2019 waren es {pc(norm)} je Quartal." if v >= 0 else
                     f"Im {_per(t, 'Q', lang)} schrumpfte die Wirtschaft um {pc(abs(v))}; im Schnitt der Jahre 2015 bis 2019 wuchs sie um {pc(norm)} je Quartal.") if de else
                    (f"In {_per(t, 'Q', lang)} the economy grew by {pc(v)}; in 2015 to 2019 it grew by {pc(norm)} a quarter on average." if v >= 0 else
                     f"In {_per(t, 'Q', lang)} the economy shrank by {pc(abs(v))}; in 2015 to 2019 it grew by {pc(norm)} a quarter on average."))
    if "cpi" in facts:
        v, p = facts["cpi"]
        mv = "sinkt" if v < p else "steigt" if v > p else "verharrt"
        rel = "über dem Ziel" if v > 2.2 else "unter dem Ziel" if v < 1.8 else "nahe am Ziel"
        if de:
            say.append(f"Die Inflation {mv}, liegt mit {pc(v)} aber {rel}." if (mv == "sinkt" and v > 2.2) or (mv == "steigt" and v < 1.8) else f"Die Inflation {mv} und liegt mit {pc(v)} {rel}.")
        else:
            mv = {"sinkt": "is falling", "steigt": "is rising", "verharrt": "is unchanged"}[mv]
            rel = {"über dem Ziel": "above target", "unter dem Ziel": "below target", "nahe am Ziel": "close to target"}[rel]
            say.append(f"Inflation {mv} and, at {pc(v)}, is {rel}.")
    en = facts.get("energy")
    if en and en[0] is not None:
        up = en[0] > 5 or (en[1] or 0) > 10
        down = en[0] < -5 and (en[1] or 0) < -10
        if up or down:
            say.append(("Energie wird teurer." if up else "Energie wird billiger.") if de else ("Energy is getting more expensive." if up else "Energy is getting cheaper."))
        if en[1] is not None and abs(en[1]) >= 20:
            say2.append((f"Rohöl kostet {pc(abs(en[1]), 0)} {'mehr' if en[1] > 0 else 'weniger'} als vor einem Jahr." if de else
                         f"Crude oil costs {pc(abs(en[1]), 0)} {'more' if en[1] > 0 else 'less'} than a year ago."))

    # Warnlampen: rot, gelb, grün
    warn = []
    if en and en[0] is not None:
        g, b = en[0], en[1] or 0
        lvl = "r" if g > 25 or b > 25 else "y" if g > 0 or b > 0 else "g"
        txt = {"r": ("Öl und Gas deutlich teurer als vor einem Jahr; das belastet Kaufkraft und Industrie.", "Oil and gas markedly dearer than a year ago, weighing on purchasing power and industry."),
               "y": ("Öl oder Gas teurer als vor einem Jahr.", "Oil or gas dearer than a year ago."),
               "g": ("Öl und Gas günstiger als vor einem Jahr.", "Oil and gas cheaper than a year ago.")}[lvl]
        warn.append({"lvl": lvl, "label": "Energie" if de else "Energy", "text": txt[0 if de else 1], "topic": "energie"})
    if "ins" in facts and facts["ins"][1] is not None:
        yoy, vs = facts["ins"]
        lvl = "r" if vs > 25 else "y" if vs > 5 else "g"
        trend = ("" if yoy is None else ", mehr als vor einem Jahr" if yoy > 0 else ", weniger als vor einem Jahr") if de else ("" if yoy is None else ", more than a year ago" if yoy > 0 else ", fewer than a year ago")
        warn.append({"lvl": lvl, "label": "Insolvenzen" if de else "Insolvencies",
                     "text": (f"{pc(abs(vs), 0)} {'über' if vs >= 0 else 'unter'} dem Stand vor der Pandemie{trend}." if de else f"{pc(abs(vs), 0)} {'above' if vs >= 0 else 'below'} the pre-pandemic level{trend}."), "topic": "insolvenzen"})
    sahm = _s(data, "de_sahm")
    if sahm is not None:
        v = float(sahm.iloc[-1])
        lvl = "r" if v >= 0.25 else "y" if v >= 0.15 else "g"
        warn.append({"lvl": lvl, "label": "Rezession" if de else "Recession",
                     "text": ((f"Signal vom Arbeitsmarkt ({n(v, 2)} von {n(0.25, 2)})." if lvl == "r" else f"kein Signal vom Arbeitsmarkt ({n(v, 2)} von {n(0.25, 2)}).") if de else
                              (f"signal from the labour market ({n(v, 2)} of {n(0.25, 2)})." if lvl == "r" else f"no signal from the labour market ({n(v, 2)} of {n(0.25, 2)}).")), "topic": "rezession"})

    # Ausblick: jüngste Projektion der Bundesregierung
    out = None
    gov = sorted((f for f in forecasts if f.get("by") == "Bundesregierung" and f.get("values")), key=lambda f: f["date"])
    if gov and q is not None:
        g, y = gov[-1], int(q.index[-1].year)
        vals = [(yy, g["values"][yy]) for yy in (y, y + 1) if yy in g["values"]]
        if vals:
            rnd = g.get("round", "")
            out = {"who": (f"Bundesregierung, {rnd}" if de else f"Federal government, {rnd}"), "vals": [{"year": yy, "v": n(vv)} for yy, vv in vals]}
    return {"kpis": kp, "say": " ".join(say), "say2": " ".join(say2), "warn": warn, "outlook": out}
