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
    more = [f"Im Vormonat lag die Rate bei {num(p)} %, sie ist also {dirw}.",
            "Die Europäische Zentralbank strebt 2 % an."]
    verdict = ("unter dem Ziel" if v < 1.5 else "nahe am Ziel" if v <= 2.5 else "über dem Ziel" if v <= 4 else "hoch")
    return {"value": round(float(v), 1), "unit": "%", "signed": False, "period": period(t, "M"), "head": head, "more": more,
            "verdict": verdict, "spark": q["series"], "ref": 2.0}


def unemployment(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    lvl = _s(data, q["level"])
    v, t = s.iloc[-1], s.index[-1]
    year_ago = s[s.index <= t - pd.DateOffset(months=12)]
    people = lvl.iloc[-1] / 1000
    head = f"Im {period(t, 'M')} waren rund {num(people, 2)} Millionen Menschen arbeitslos gemeldet, {num(v)} % aller Erwerbspersonen."
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
    what = {"industrie": ("die Industrie", "hergestellt"), "konsum": ("der Einzelhandel", "verkauft")}.get(q["id"], ("die Branche", "umgesetzt"))
    head = (f"Im {period(t, 'M')} hat {what[0]} {num(abs(mom))} % {'mehr' if mom >= 0 else 'weniger'} {what[1]} "
            f"als {prev_word(t - pd.DateOffset(months=1), 'M')}.")
    more = [f"Die letzten drei Monate zusammen: {num(three, sign=True)} % gegenüber den drei Monaten davor. "
            "Dieser Vergleich ist ruhiger als der einzelne Monat."]
    if q.get("orders") and q["orders"] in data:
        o = _s(data, q["orders"])
        om, o3 = _mom_3m(o)
        more.append(f"Aufträge im {period(o.index[-1], 'M')}: {num(om, sign=True)} % zum Vormonat, "
                    f"{num(o3, sign=True)} % im Dreimonatsvergleich.")
    if q.get("mood") and q["mood"] in data:
        m = _s(data, q["mood"])
        more.append(f"Das Verbrauchervertrauen lag im {period(m.index[-1], 'M')} bei {num(m.iloc[-1])} Punkten "
                    f"({'besser' if m.iloc[-1] > m.iloc[-2] else 'schlechter' if m.iloc[-1] < m.iloc[-2] else 'so'} als im Vormonat).")
    verdict = "zieht an" if three >= 1 else ("schwächelt" if three <= -1 else "seitwärts")
    return {"value": round(float(mom), 1), "unit": "%", "signed": True, "period": period(t, "M"), "head": head, "more": more,
            "verdict": verdict, "spark": q["series"], "label": "zum Vormonat"}


def level_mom(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    t = s.index[-1]
    mom, three = _mom_3m(s)
    head = (f"Im {period(t, 'M')} hat Deutschland Waren für {num(s.iloc[-1])} Mrd. € ins Ausland verkauft, "
            f"{num(abs(mom))} % {'mehr' if mom >= 0 else 'weniger'} als im Vormonat.")
    more = [f"Die letzten drei Monate zusammen: {num(three, sign=True)} % gegenüber den drei Monaten davor.",
            "Die Werte sind nominal, also nicht um Preisänderungen bereinigt."]
    verdict = "zieht an" if three >= 1 else ("schwächelt" if three <= -1 else "seitwärts")
    return {"value": round(float(s.iloc[-1]), 1), "unit": "Mrd. €", "signed": False, "period": period(t, "M"), "head": head,
            "more": more, "verdict": verdict, "spark": q["series"], "label": f"{num(mom, sign=True)} % zum Vormonat"}


def sentiment(q: dict, data: dict) -> dict:
    s = _s(data, q["series"])
    v, p, t = s.iloc[-1], s.iloc[-2], s.index[-1]
    rel = "über" if v > 100.5 else ("unter" if v < 99.5 else "auf")
    head = f"Im {period(t, 'M')} lag die Stimmung in der Wirtschaft bei {num(v)} Punkten, {rel} dem langjährigen Durchschnitt von 100."
    more = [f"Im Vormonat: {num(p)} Punkte, die Stimmung hat sich also {'aufgehellt' if v > p + 0.2 else 'eingetrübt' if v < p - 0.2 else 'kaum verändert'}."]
    verdict = "gut" if v >= 103 else ("eher gut" if v > 100.5 else "durchschnittlich" if v >= 99.5 else "gedämpft" if v >= 90 else "schlecht")
    return {"value": round(float(v), 1), "unit": "Punkte", "signed": False, "period": period(t, "M"), "head": head, "more": more,
            "verdict": f"Stimmung {verdict}", "spark": q["series"], "ref": 100.0}


KINDS = {"growth": growth, "inflation": inflation, "unemployment": unemployment, "index_mom": index_mom,
         "level_mom": level_mom, "sentiment": sentiment}


def answer(q: dict, data: dict) -> dict | None:
    try:
        return KINDS[q["kind"]](q, data)
    except (KeyError, IndexError):
        return None
