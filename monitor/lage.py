"""Erster Bildschirm „Lage auf einen Blick“: links Raten im Steigungsbild (2019, vor einem Jahr, heute), rechts
Verläufe seit 2019 mit dem Durchschnitt 2015–19; dazu Lage-Satz, Warnlampen und Ausblick.

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


def _yoy(s: pd.Series | None, lag: int = 12) -> pd.Series | None:
    return None if s is None else ((s / s.shift(lag) - 1) * 100).dropna()


def _oil_eur(data: dict) -> pd.Series | None:
    """Rohöl Brent in Euro je Barrel: US-Dollar je Barrel durch US-Dollar je Euro (Monatsmittel)."""
    b, fx = _s(data, "w_brent"), _s(data, "fx_usd")
    if b is None or fx is None:
        return None
    fx = fx.groupby(fx.index.to_period("M")).mean()
    fx.index = fx.index.to_timestamp()
    return (b / fx.reindex(b.index)).dropna()


# Raten links (Steigungsbild): Schlüssel, Name deutsch, Name englisch, Reihe, Veränderungsrate?, Kapitel
def _rates(data: dict) -> list:
    od = _s(data, "de_orders")
    return [
        ("alq", "Arbeitslosenquote", "Unemployment rate", _s(data, "de_alq_sa"), False, "arbeit"),
        ("bund", "Rendite 10-jähriger Bundesanleihen", "10-year Bund yield", _s(data, "de_bund10"), False, "zinsen"),
        ("cpi", "Inflation", "Inflation", _s(data, "de_cpi_yoy"), False, "preise"),
        ("dfr", "Einlagesatz der EZB", "ECB deposit rate", _s(data, "ecb_dfr"), False, "geldpolitik"),
        ("tarif", "Tariflöhne, ggü. Vorjahr", "Negotiated wages, year on year", _s(data, "de_tarif_yoy"), True, "einkommen"),
        ("gdp", "Wirtschaftsleistung, ggü. Vorjahr", "GDP, year on year", _s(data, "de_gdp_yoy"), True, "wachstum"),
        ("ret", "Einzelhandel real, ggü. Vorjahr", "Retail sales, real, year on year", _yoy(_s(data, "de_retail")), True, "konsum"),
        ("exp", "Exporte, ggü. Vorjahr", "Exports, year on year", _yoy(_s(data, "de_exports")), True, "export"),
        ("ip", "Industrieproduktion, ggü. Vorjahr", "Industrial production, year on year", _yoy(_s(data, "de_ip")), True, "industrie"),
        ("bau", "Bauzinsen, neue Wohnungsbaukredite", "Mortgage rates, new housing loans", _s(data, "de_rate_house"), False, "zinsen"),
        ("frb", "Rendite 10-jähriger Staatsanleihen Frankreichs", "10-year French government bond yield", _s(data, "lt_fr"), False, "zinsen"),
        ("ord", "Auftragseingang Industrie, ggü. Vorjahr", "Industrial orders, year on year", _yoy(od.rolling(3).mean().dropna() if od is not None else None), True, "industrie"),
    ]


def _line(s: pd.Series, name: str = "", col: int = 0) -> dict:
    """Monatswerte seit 2019 und Durchschnitt 2015–19 für ein Feld rechts."""
    t = s[s.index >= "2019-01-01"]
    m = s[(s.index.year >= 2015) & (s.index.year <= 2019)]
    return {"name": name, "col": col, "x": [d.strftime("%Y-%m") for d in t.index], "y": [round(float(v), 3) for v in t.values],
            "mean": round(float(m.mean()), 3) if len(m) else None,
            "lo": round(float(m.min()), 3) if len(m) else None, "hi": round(float(m.max()), 3) if len(m) else None}


def _panels(data: dict, de: bool) -> list:
    out = []
    def add(title, unit, topic, lines, d=0, cur=""):
        lines = [l for l in lines if l[0] is not None and len(l[0])]
        if lines:
            out.append({"title": title, "unit": unit, "topic": topic, "d": d, "cur": cur, "lines": [_line(*l) for l in lines]})
    em = _s(data, "de_emp_m")
    add("Erwerbstätige" if de else "People in work", "Millionen Personen" if de else "million people", "arbeit", [(em / 1000 if em is not None else None,)], 1)
    add("Arbeitslose, offene Stellen" if de else "Unemployed, vacancies", "Tausend" if de else "thousands", "arbeit",
        [(_s(data, "de_alo_sa"), "Arbeitslose" if de else "unemployed", 0), (_s(data, "de_vac_sa"), "offene Stellen" if de else "vacancies", 1)])
    ins = _s(data, "de_insolv")
    add("Insolvenzen" if de else "Insolvencies", "Anträge je Monat, Mittel 12 Monate" if de else "filings a month, 12-month average", "insolvenzen",
        [(ins.rolling(12).mean().dropna() if ins is not None else None,)])
    add("Strom" if de else "Electricity", "€ je Megawattstunde, Großhandel" if de else "€ per megawatt hour, wholesale", "energie", [(_s(data, "de_power_price"),)], 0, "€")
    add("Erdgas" if de else "Natural gas", "€ je Megawattstunde" if de else "€ per megawatt hour", "energie", [(_gas_eur(data),)], 0, "€")
    add("Rohöl" if de else "Crude oil", "€ je Barrel" if de else "€ per barrel", "energie", [(_oil_eur(data),)], 0, "€")
    return out


def build(data: dict, forecasts: list[dict], lang: str = "de") -> dict:
    de = lang == "de"
    n = lambda v, d=1, sign=False: _num(v, d, lang, sign)
    pc = lambda v, d=1, sign=False: f"{n(v, d, sign)}{NB}%" if de else f"{n(v, d, sign)}%"
    facts = {}
    slope = []
    for key, lde, len_, ser, chg, topic in _rates(data):
        if ser is None or len(ser) < 13:
            continue
        t = ser.index[-1]
        y19 = ser[ser.index.year == 2019]
        ago = ser[ser.index <= t - pd.DateOffset(years=1)]
        if not len(y19) or not len(ago):
            continue
        a, b, c = float(y19.mean()), float(ago.iloc[-1]), float(ser.iloc[-1])
        slope.append({"key": key, "label": lde if de else len_, "topic": topic, "v": [round(a, 3), round(b, 3), round(c, 3)], "txt": n(c, 1, chg), "txts": [n(a, 1, chg), n(b, 1, chg)]})

    q = _s(data, "de_gdp_qoq")
    if q is not None and len(q) > 1:
        v = float(q.iloc[-1])
        facts["gdp"] = (v, float(q[(q.index.year >= 2015) & (q.index.year <= 2019)].mean()), q.index[-1])
    c = _s(data, "de_cpi_yoy")
    if c is not None and len(c) > 1:
        facts["cpi"] = (float(c.iloc[-1]), float(c.iloc[-2]))
    ip = _s(data, "de_ip")
    if ip is not None and _three(ip) is not None:
        facts["ip3"] = _three(ip)
    ins = _s(data, "de_insolv")
    if ins is not None and len(ins) > 12:
        t = ins.index[-1]
        v = float(ins.iloc[-1])
        ago = ins.get(t - pd.DateOffset(years=1))
        pre = ins[(ins.index.month == t.month) & (ins.index.year >= 2015) & (ins.index.year <= 2019)]
        facts["ins"] = ((v / float(ago) - 1) * 100 if ago else None, (v / float(pre.mean()) - 1) * 100 if len(pre) else None)
    gas, br = _gas_eur(data), _s(data, "w_brent")
    gyoy = byoy = None
    if gas is not None and len(gas) > 12:
        ago = gas.get(gas.index[-1] - pd.DateOffset(years=1))
        gyoy = (float(gas.iloc[-1]) / float(ago) - 1) * 100 if ago else None
    if br is not None and len(br) > 12:
        b0 = br.get(br.index[-1] - pd.DateOffset(years=1))
        byoy = (float(br.iloc[-1]) / float(b0) - 1) * 100 if b0 else None
    facts["energy"] = (gyoy, byoy)

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
    return {"slope": slope, "panels": _panels(data, de), "say": " ".join(say), "say2": " ".join(say2), "warn": warn, "outlook": out}
