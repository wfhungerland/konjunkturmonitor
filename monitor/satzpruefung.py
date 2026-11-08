"""Prüfung der automatischen Sätze, bevor sie auf die Seite gehen.

Jeder Satz muss vier Regeln bestehen. Fällt er durch, entfällt er, und der Bau vermerkt den Grund;
der Workflow meldet die Funde im Ticket „Automatische Sätze: Auffälligkeiten“.
1. Keine Platzhalter oder Rechenreste (nan, None, inf, geschweifte Klammern, doppelte Leerzeichen).
2. Kein Zeitraum nach dem jüngsten Wert der Abbildung (außer bei Prognosen und Projektionen).
3. Richtungswort und Vorzeichen passen zusammen („stieg um -0,3 %“ oder „-0,3 Pp höher“ fallen durch).
4. Bei Linien: ein Wert nach „lag … bei“ muss einem jüngsten Wert der gezeigten Reihen entsprechen.
"""
from __future__ import annotations

import re

MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
BAD = re.compile(r"\b(nan|NaN|None|inf)\b|[{}]|\s{2,}|\s[,.;:](?!\d)")
UP = r"(?:stieg|stiegen|wuchs|wuchsen|gestiegen|gewachsen|zugenommen|legte[n]? zu)"
DOWN = r"(?:sank|sanken|gesunken|abgenommen|schrumpfte[n]?|geschrumpft)"
NEG, POS = r"[-−]\d", r"\+\d"
FORWARD = {"forecast", "proj_gap", "potential"}  # nennen Ziel- und Prognosejahre


def _num(t: str) -> float:
    return float(t.replace(".", "").replace(",", ".").replace("−", "-"))


def _periods(text: str) -> list[str]:
    """Zeiträume im Satz als JJJJ-MM (Monatsanfang des Zeitraums)."""
    out = []
    for m in re.finditer(r"\b(\d)\. Quartal(?:s)? (\d{4})", text):
        out.append(f"{m.group(2)}-{(int(m.group(1)) - 1) * 3 + 1:02d}")
    for m in re.finditer(r"\b(" + "|".join(MONTHS) + r") (\d{4})", text):
        out.append(f"{m.group(2)}-{MONTHS.index(m.group(1)) + 1:02d}")
    for m in re.finditer(r"\bJahr (\d{4})\b", text):
        out.append(f"{m.group(1)}-01")
    return out


def _clauses(text: str) -> list[str]:
    return re.split(r"[;:]|, (?=nach |zuvor )", text)


def check(c: dict, text: str) -> str | None:
    """Grund, warum der Satz nicht erscheinen darf, sonst None."""
    if BAD.search(text):
        return "Platzhalter oder Rechenrest"
    last = (c.get("last_x") or "")[:7]
    if last and c.get("chart") not in FORWARD and not c.get("forecast_after_bars"):
        late = [p for p in _periods(text) if p > last]
        if late:
            return f"Zeitraum {late[0]} liegt nach dem jüngsten Wert ({last})"
    for cl in _clauses(text):
        if re.search(UP + r"[^.]*?\bum " + NEG, cl) or re.search(DOWN + r"[^.]*?\bum " + POS, cl):
            return "Richtungswort passt nicht zum Vorzeichen"
        if re.search(NEG + r"[\d,.]*\s*(?:%|Pp)? (?:höher|mehr)\b", cl) or re.search(POS + r"[\d,.]*\s*(?:%|Pp)? (?:niedriger|weniger)\b", cl):
            return "Richtungswort passt nicht zum Vorzeichen"
    if c.get("type") == "line" and isinstance(c.get("series"), list):
        lasts = set()
        for s in c["series"]:
            ys = [v for v in (s.get("y") or []) if v is not None]
            if ys:
                lasts |= {round(ys[-1], k) for k in range(4)}
                if c.get("ma3") and len(ys) >= 3:
                    lasts |= {round(sum(ys[-3:]) / 3, k) for k in range(3)}
        for m in re.finditer(r"\b(?:lag|lagen|betrug)\b[^.;]*?\bbei ([-−+]?\d[\d.]*(?:,\d+)?)", text):
            v = _num(m.group(1))
            if lasts and not any(abs(v - x) < 1e-9 for x in lasts):
                return f"Wert {m.group(1)} entspricht keinem jüngsten Wert der Abbildung"
    return None


def apply(topics: list[dict]) -> list[str]:
    """Durchgefallene Sätze entfernen; Rückgabe: Funde als Zeilen für das Ticket."""
    found = []
    for t in topics:
        for c in t["charts"]:
            keep = []
            for s in c.get("texts") or []:
                why = check(c, s)
                if why:
                    found.append(f"- Abb. {c.get('no')} `{c.get('chart')}`: {why}. Satz: „{s}“")
                else:
                    keep.append(s)
            if c.get("texts") is not None:
                c["texts"], c["text"] = keep, " ".join(keep)
    return found
