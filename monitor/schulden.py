"""Sätze zur Schuldenstruktur des Staates: Ebene, Instrument, Gläubiger, Restlaufzeit und Zins.

Die automatischen Sätze für Linien und gestapelte Balken passen hier nicht (sie sprechen von „Beiträgen“). Diese
Funktionen bilden aus den Reihen einer Abbildung je ein bis zwei Sätze, deutsch und englisch.
"""
from __future__ import annotations

CHARTS = {"gov_debt_level", "gov_debt_instr", "gov_debt_holder", "gov_debt_mat", "gov_debt_cost"}


def _last(c: dict, sid: str):
    for s in c.get("series") or []:
        if s.get("id") == sid:
            pts = [(x, y) for x, y in zip(s.get("x") or [], s.get("y") or []) if y is not None]
            return pts
    return []


def _when(x: str, freq: str, lang: str) -> str:
    from .answers import MONTHS
    from .english import MONTHS as MONTHS_EN
    y, m = x[:4], int(x[5:7])
    if freq == "Q":
        q = (m - 1) // 3 + 1
        return f"im {q}. Quartal {y}" if lang == "de" else f"in Q{q} {y}"
    if freq == "M":
        return f"im {MONTHS[m - 1]} {y}" if lang == "de" else f"in {MONTHS_EN[m - 1]} {y}"
    return f"Ende {y}" if lang == "de" else f"at the end of {y}"


def saetze(c: dict, lang: str = "de") -> list[str]:
    from .answers import num as num_de
    from .english import num as num_en
    de = lang == "de"
    num = num_de if de else num_en
    pc = (lambda v, d=1: f"{num(v, d)} %") if de else (lambda v, d=1: f"{num(v, d)}%")
    ch = c.get("chart")
    try:
        if ch == "gov_debt_level":
            parts = [("de_debt_s1311", "des Bundes", "the federal government"), ("de_debt_s1312", "der Länder", "the Länder"),
                     ("de_debt_s1313", "der Gemeinden", "municipalities"), ("de_debt_s1314", "der Sozialversicherung", "social security")]
            vals = [(_last(c, i)[-1], a, b) for i, a, b in parts if _last(c, i)]
            x = vals[0][0][0]
            w = _when(x, "Q", lang)
            tot = sum(v[0][1] for v in vals)
            if de:
                lst = [f"{a} bei {pc(v[1])}" if k == 0 else f"{a} bei {pc(v[1])}" for k, (v, a, _) in enumerate(vals)]
                s1 = f"{w[0].upper() + w[1:]} lagen die Schulden {lst[0]} des Bruttoinlandsprodukts, die {', die '.join(lst[1:-1])} und die {lst[-1]}."
                s2 = f"Der Bund trägt damit rund {num(vals[0][0][1] / tot * 100, 0)} % der Schulden aller Ebenen."
            else:
                lst = [f"that of {b} at {pc(v[1])}" for v, _, b in vals]
                s1 = f"{w[0].upper() + w[1:]}, the debt of the federal government stood at {pc(vals[0][0][1])} of GDP, {', '.join(lst[1:-1])} and {lst[-1]}."
                s2 = f"The federal government thus accounts for about {num(vals[0][0][1] / tot * 100, 0)}% of the debt of all levels."
            return [s1, s2]
        if ch == "gov_debt_instr":
            parts = [("de_debt_gd_f3", "Wertpapiere", "securities"), ("de_debt_gd_f4", "Kredite", "loans"), ("de_debt_gd_f2", "Bargeld und Einlagen", "currency and deposits")]
            vals = [(_last(c, i)[-1], a, b) for i, a, b in parts if _last(c, i)]
            tot = sum(v[0][1] for v in vals)
            y = vals[0][0][0][:4]
            sh = [num(v[0][1] / tot * 100, 0) for v in vals]
            if de:
                return [f"Ende {y} bestanden die Staatsschulden zu {sh[0]} % aus Wertpapieren, zu {sh[1]} % aus Krediten und zu {sh[2]} % aus Bargeld und Einlagen."]
            return [f"At the end of {y}, {sh[0]}% of government debt was securities, {sh[1]}% loans and {sh[2]}% currency and deposits."]
        if ch == "gov_debt_holder":
            ids = [("de_debt_h_s2", "das Ausland", "the rest of the world"), ("de_debt_h_s121", "die Bundesbank", "the Bundesbank"),
                   ("de_debt_h_s122_s123", "Banken im Inland", "domestic banks"), ("de_debt_h_s124_s129", "Versicherer, Fonds und andere", "insurers, funds and others"),
                   ("de_debt_h_s11_s14_s15", "Unternehmen und Haushalte", "firms and households")]
            ser = {i: dict(_last(c, i)) for i, _, _ in ids}
            y = max(ser["de_debt_h_s2"])
            tot = sum(ser[i].get(y, 0) for i, _, _ in ids)
            sh = {i: ser[i].get(y, 0) / tot * 100 for i, _, _ in ids}
            share_bb = {x: ser["de_debt_h_s121"].get(x, 0) / sum(ser[i].get(x, 0) for i, _, _ in ids) * 100 for x in ser["de_debt_h_s121"]}
            top = max(share_bb, key=share_bb.get)
            yy = y[:4]
            if de:
                s1 = (f"Ende {yy} hielt das Ausland {num(sh['de_debt_h_s2'], 0)} % der Staatsschulden, die Bundesbank {num(sh['de_debt_h_s121'], 0)} % "
                      f"und Banken im Inland {num(sh['de_debt_h_s122_s123'], 0)} %.")
                s2 = f"Der Anteil der Bundesbank war {top[:4]} mit {num(share_bb[top], 0)} % am höchsten." if top != y else ""
            else:
                s1 = (f"At the end of {yy}, the rest of the world held {num(sh['de_debt_h_s2'], 0)}% of government debt, the Bundesbank {num(sh['de_debt_h_s121'], 0)}% "
                      f"and domestic banks {num(sh['de_debt_h_s122_s123'], 0)}%.")
                s2 = f"The Bundesbank's share peaked at {num(share_bb[top], 0)}% in {top[:4]}." if top != y else ""
            return [x for x in (s1, s2) if x]
        if ch == "gov_debt_mat":
            de_pts = _last(c, "rmd_de")
            x, v = de_pts[-1]
            first = de_pts[0]
            oth = [(n_de, n_en, _last(c, i)) for i, n_de, n_en in (("rmd_fr", "Frankreich", "France"), ("rmd_it", "Italien", "Italy"), ("rmd_es", "Spanien", "Spain"))]
            oth = [(a, b, p[-1][1]) for a, b, p in oth if p and p[-1][0] == x]
            diff = v - first[1]
            if de:
                s1 = f"Ende {x[:4]} liefen die Staatsschulden im Durchschnitt noch {num(v, 1)} Jahre, {num(abs(diff), 1)} Jahre {'länger' if diff >= 0 else 'kürzer'} als {first[0][:4]}."
                s2 = ("Zum Vergleich: " + ", ".join(f"{a} {num(w, 1)}" for a, _, w in oth) + " Jahre.") if oth else ""
            else:
                s1 = f"At the end of {x[:4]}, government debt had an average of {num(v, 1)} years left to run, {num(abs(diff), 1)} years {'longer' if diff >= 0 else 'shorter'} than in {first[0][:4]}."
                s2 = ("For comparison: " + ", ".join(f"{b} {num(w, 1)}" for _, b, w in oth) + " years.") if oth else ""
            return [x for x in (s1, s2) if x]
        if ch == "gov_debt_cost":
            imp = _last(c, "de_gov_implicit")
            y10 = _last(c, "de_bund10")
            (xi, vi) = imp[-1]
            low = min(imp, key=lambda p: p[1])
            xm, vm = y10[-1]
            if de:
                s1 = f"{xi[:4]} zahlte der Staat im Durchschnitt {pc(vi)} Zinsen auf seine Schulden" + (f", nach {pc(low[1])} im Tiefpunkt {low[0][:4]}." if low[0] != xi else ".")
                s2 = f"Neue zehnjährige Bundesanleihen rentierten {_when(xm, 'M', 'de')} mit {pc(vm)}."
            else:
                s1 = f"In {xi[:4]} the government paid an average of {pc(vi)} interest on its debt" + (f", up from {pc(low[1])} at the low in {low[0][:4]}." if low[0] != xi else ".")
                s2 = f"New ten-year Bunds yielded {pc(vm)} {_when(xm, 'M', 'en')}."
            return [s1, s2]
    except (KeyError, IndexError, ValueError, ZeroDivisionError):
        return []
    return []
