"""Antworten auf die sieben Fragen: Satz, Zahl, Vergleich und kurzes Urteil, verständlich ohne Vorwissen."""
from __future__ import annotations

import pandas as pd

MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
QUARTER_WORDS = ["1.", "2.", "3.", "4."]


def num(v: float, d: int = 1, sign: bool = False) -> str:
    s = f"{abs(v):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if v < 0:
        return "−" + s
    return ("+" + s) if sign and v > 0 else s


def period(ts: pd.Timestamp, freq: str) -> str:
    if freq == "Q":
        return f"{QUARTER_WORDS[(ts.month - 1) // 3]} Quartal {ts.year}"
    return f"{MONTHS[ts.month - 1]} {ts.year}"


def prev_word(ts: pd.Timestamp, freq: str) -> str:
    return "im Vorquartal" if freq == "Q" else f"im {MONTHS[ts.month - 1]}"


def _s(data: dict[str, pd.Series], sid: str) -> pd.Series:
    s = data.get(sid)
    if s is None or s.empty:
        raise KeyError(sid)
    return s.dropna().sort_index()


def growth(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    v, p, t = s.iloc[-1], s.iloc[-2], s.index[-1]
    yoy = data.get(q.get("yoy"))
    avg = s[(s.index >= "2015-01-01") & (s.index < "2020-01-01")].mean()
    verb = "gewachsen" if v >= 0.05 else ("geschrumpft" if v <= -0.05 else "kaum verändert")
    head = (f"Im {period(t, 'Q')} ist die Wirtschaft um {num(abs(v))} % {verb}." if verb != "kaum verändert"
            else f"Im {period(t, 'Q')} hat sich die Wirtschaftsleistung kaum verändert ({num(v, sign=True)} %).")
    more = [f"Im Quartal davor: {num(p, sign=True)} %."]
    if yoy is not None and not yoy.dropna().empty:
        more.append(f"Gegenüber dem Vorjahr: {num(yoy.dropna().iloc[-1], sign=True)} %.")
    more.append(f"Zum Vergleich: In den Jahren 2015 bis 2019 wuchs sie im Schnitt um {num(avg)} % je Quartal.")
    verdict = ("schrumpft" if v <= -0.05 else "stagniert" if v < 0.1 else "wächst leicht" if v < 0.4 else "wächst" if v < 0.8 else "wächst kräftig")
    return {"value": round(float(v), 1), "unit": "%", "signed": True, "period": period(t, "Q"), "head": head, "more": more,
            "verdict": verdict, "spark": q["series"]}


def inflation(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    v, p, t = s.iloc[-1], s.iloc[-2], s.index[-1]
    head = f"Im {period(t, 'M')} waren die Preise um {num(v)} % höher als ein Jahr zuvor."
    if v < 0:
        head = f"Im {period(t, 'M')} waren die Preise um {num(abs(v))} % niedriger als ein Jahr zuvor."
    dirw = "gesunken" if v < p - 0.05 else ("gestiegen" if v > p + 0.05 else "gleich geblieben")
    more = [f"Im Vormonat lag die Rate bei {num(p)} %, sie ist also {dirw}."]
    idx = data.get(q.get("index"))
    if idx is not None and len(idx.dropna()) > 1 and idx.dropna().index[-1] == t:
        i = idx.dropna()
        more.append(f"Gegenüber dem Vormonat: {num((i.iloc[-1] / i.iloc[-2] - 1) * 100, sign=True)} %.")
    core = data.get(q.get("core"))
    if core is not None and not core.dropna().empty and core.dropna().index[-1] == t:
        more.append(f"Ohne Energie und Nahrungsmittel (Kernrate): {num(core.dropna().iloc[-1])} %.")
    parts = []
    for label, sid in (q.get("parts") or {}).items():
        ps = data.get(sid)
        if ps is not None and not ps.dropna().empty and ps.dropna().index[-1] == t:
            parts.append(f"{label} {num(ps.dropna().iloc[-1], sign=True)} %")
    if parts:
        more.append("Gegenüber dem Vorjahresmonat: " + ", ".join(parts) + ".")
    more.append("Die Europäische Zentralbank strebt 2 % an.")
    verdict = ("unter dem Ziel" if v < 1.5 else "nahe am Ziel" if v <= 2.5 else "über dem Ziel" if v <= 4 else "hoch")
    return {"value": round(float(v), 1), "unit": "%", "signed": False, "period": period(t, "M"), "head": head, "more": more,
            "verdict": verdict, "spark": q["series"], "ref": 2.0}


def unemployment(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    lvl = _s(data, q["level"])
    v, t = s.iloc[-1], s.index[-1]
    year_ago = s[s.index <= t - pd.DateOffset(months=12)]
    people = lvl.iloc[-1] / 1000
    head = f"Im {period(t, 'M')} waren rund {num(people, 2)} Millionen Menschen arbeitslos gemeldet; die Quote betrug {num(v)} %."
    more = []
    verdict = "stabil"
    if not year_ago.empty:
        d = v - year_ago.iloc[-1]
        more.append(f"Vor einem Jahr waren es {num(year_ago.iloc[-1])} %.")
        verdict = "steigt" if d >= 0.15 else ("sinkt" if d <= -0.15 else "stabil")
    more.append("Gezählt sind bei der Arbeitsagentur gemeldete Arbeitslose, saisonbereinigt.")
    return {"value": round(float(v), 1), "unit": "%", "signed": False, "period": period(t, "M"), "head": head, "more": more,
            "verdict": f"Arbeitslosigkeit {verdict}", "spark": q["series"]}


def _mom_3m(s: pd.Series) -> tuple[float, float]:
    mom = (s.iloc[-1] / s.iloc[-2] - 1) * 100
    three = (s.iloc[-3:].mean() / s.iloc[-6:-3].mean() - 1) * 100
    return mom, three


def index_mom(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    t = s.index[-1]
    mom, three = _mom_3m(s)
    what = {"industrie": ("die Industrie", "produziert"), "konsum": ("der Einzelhandel", "abgesetzt")}.get(q["id"], ("die Branche", "umgesetzt"))
    head = (f"Im {period(t, 'M')} hat {what[0]} {num(abs(mom))} % {'mehr' if mom >= 0 else 'weniger'} {what[1]} "
            f"als {prev_word(t - pd.DateOffset(months=1), 'M')}.")
    more = [f"Die letzten drei Monate zusammen: {num(three, sign=True)} % gegenüber den drei Monaten davor. "
            "Dieser Vergleich schwankt weniger als der einzelne Monat."]
    if q.get("orders") and q["orders"] in data:
        o = _s(data, q["orders"])
        om, o3 = _mom_3m(o)
        more.append(f"Aufträge im {period(o.index[-1], 'M')}: {num(om, sign=True)} % zum Vormonat, "
                    f"{num(o3, sign=True)} % im Dreimonatsvergleich.")
    if q.get("mood") and q["mood"] in data:
        m = _s(data, q["mood"])
        more.append(f"Das Verbrauchervertrauen lag im {period(m.index[-1], 'M')} bei {num(m.iloc[-1])} Punkten "
                    f"({'besser' if m.iloc[-1] > m.iloc[-2] else 'schlechter' if m.iloc[-1] < m.iloc[-2] else 'so'} als im Vormonat).")
    verdict = "steigt" if three >= 1 else ("sinkt" if three <= -1 else "stabil")
    return {"value": round(float(mom), 1), "unit": "%", "signed": True, "period": period(t, "M"), "head": head, "more": more,
            "verdict": verdict, "spark": q["series"], "label": "zum Vormonat"}


def level_mom(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    t = s.index[-1]
    mom, three = _mom_3m(s)
    head = (f"Im {period(t, 'M')} exportierte Deutschland Waren im Wert von {num(s.iloc[-1])} Mrd. €, "
            f"{num(abs(mom))} % {'mehr' if mom >= 0 else 'weniger'} als im Vormonat.")
    more = [f"Die letzten drei Monate zusammen: {num(three, sign=True)} % gegenüber den drei Monaten davor.",
            "Die Werte sind nominal, also nicht um Preisänderungen bereinigt."]
    verdict = "steigt" if three >= 1 else ("sinkt" if three <= -1 else "stabil")
    return {"value": round(float(s.iloc[-1]), 1), "unit": "Mrd. €", "signed": False, "period": period(t, "M"), "head": head,
            "more": more, "verdict": verdict, "spark": q["series"], "label": f"{num(mom, sign=True)} % zum Vormonat"}


def sentiment(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    v, p, t = s.iloc[-1], s.iloc[-2], s.index[-1]
    rel = "über" if v > 100.5 else ("unter" if v < 99.5 else "auf")
    head = f"Im {period(t, 'M')} lag der Wirtschaftsklimaindikator bei {num(v)} Punkten und damit {rel} dem langjährigen Durchschnitt von 100."
    more = [f"Im Vormonat: {num(p)} Punkte, die Stimmung hat sich also {'aufgehellt' if v > p + 0.2 else 'eingetrübt' if v < p - 0.2 else 'kaum verändert'}."]
    verdict = "überdurchschnittlich" if v >= 103 else ("leicht überdurchschnittlich" if v > 100.5 else "durchschnittlich" if v >= 99.5 else "unterdurchschnittlich" if v >= 90 else "deutlich unterdurchschnittlich")
    return {"value": round(float(v), 1), "unit": "Punkte", "signed": False, "period": period(t, "M"), "head": head, "more": more,
            "verdict": f"Klima {verdict}", "spark": q["series"], "ref": 100.0}


def insolvency(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    v, t = s.iloc[-1], s.index[-1]
    mon = MONTHS[t.month - 1]
    head = f"Im {period(t, 'M')} beantragten {num(v, 0)} Unternehmen ein Insolvenzverfahren."
    more = []
    ya = s.get(t - pd.DateOffset(years=1))
    if ya is not None and ya > 0:
        d = (v / ya - 1) * 100
        more.append(f"Das sind {num(abs(d))} % {'mehr' if d >= 0 else 'weniger'} als im {mon} {t.year - 1}.")
    base = s[(s.index.month == t.month) & (s.index.year >= 2016) & (s.index.year <= 2019)]
    verdict = "Insolvenzen"
    if len(base):
        norm = base.mean()
        d = (v / norm - 1) * 100
        more.append(f"Vor der Pandemie (2016 bis 2019) waren es in einem {mon} durchschnittlich {num(norm, 0)}; der aktuelle Wert liegt {num(abs(d), 0)} % {'darüber' if d >= 0 else 'darunter'}.")
        verdict = ("deutlich über Vorkrisenniveau" if d >= 20 else "über Vorkrisenniveau" if d >= 5
                   else "auf Vorkrisenniveau" if d > -5 else "unter Vorkrisenniveau")
    ytd = s[(s.index.year == t.year)]
    prev = s[(s.index.year == t.year - 1) & (s.index.month <= t.month)]
    if len(ytd) == t.month and len(prev) == t.month and prev.sum() > 0:
        d = (ytd.sum() / prev.sum() - 1) * 100
        more.append(f"Januar bis {mon} {t.year}: {num(ytd.sum(), 0)} Insolvenzen, {num(abs(d))} % {'mehr' if d >= 0 else 'weniger'} als ein Jahr zuvor.")
    emp, cl = data.get(q.get("employees")), data.get(q.get("claims"))
    if emp is not None and cl is not None and t in emp.index and t in cl.index:
        more.append(f"Betroffen waren rund {num(emp[t], 0)} Beschäftigte; die voraussichtlichen Forderungen der Gläubiger beliefen sich auf {num(cl[t])} Mrd. €.")
    more.append("Erfasst werden beantragte Verfahren nach Meldung der Amtsgerichte; die Daten erscheinen mit rund drei Monaten Verzögerung.")
    return {"value": round(float(v)), "unit": "Unternehmen", "signed": False, "period": period(t, "M"), "head": head, "more": more,
            "verdict": verdict, "spark": q["series"], "decimals": 0}


KINDS = {"growth": growth, "inflation": inflation, "unemployment": unemployment, "index_mom": index_mom,
         "level_mom": level_mom, "sentiment": sentiment, "insolvency": insolvency}


def answer(q: dict, data: dict) -> dict | None:
    try:
        return KINDS[q["kind"]](q, data)
    except (KeyError, IndexError):
        return None
