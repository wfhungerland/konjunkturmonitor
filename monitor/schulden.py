"""Sätze zur Schuldenstruktur des Staates, zu Staatsausgaben je Einwohner und zu Vermögen der Haushalte.

Die automatischen Sätze für Linien und gestapelte Balken passen hier nicht (sie sprechen von „Beiträgen“). Diese
Funktionen bilden aus den Reihen einer Abbildung je ein bis zwei Sätze, deutsch und englisch.
"""
from __future__ import annotations

CHARTS = {"gov_debt_level", "gov_debt_instr", "gov_debt_holder", "gov_debt_mat", "gov_debt_cost", "stx_pk", "hh_wealth", "hh_balance", "hh_share", "hh_spend"}


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
    k = lambda v: f"€{num(round(v) * 1000, 0)}"  # Werte in Tausend Euro als volle Beträge, etwa €129.000
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
        if ch == "stx_pk":
            ids = [("stx_pk_sozial", "soziale Sicherung", "social protection"), ("stx_pk_gesundheit", "Gesundheit", "health"),
                   ("stx_pk_bildung", "Bildung", "education"), ("stx_pk_verwaltung", "Verwaltung und Zinsen", "administration and interest"),
                   ("stx_pk_uebrige", "übrige Aufgaben", "other functions")]
            vals = [(_last(c, i)[-1], a, b) for i, a, b in ids]
            y = vals[0][0][0][:4]
            tot = sum(v[0][1] for v in vals)
            eur = (lambda v: f"€{num(v, 0)}") if de else (lambda v: f"€{num(v, 0)}")
            if de:
                return [f"{y} gab der Staat je Einwohner {eur(tot)} aus, davon {eur(vals[0][0][1])} für soziale Sicherung, {eur(vals[1][0][1])} für Gesundheit und {eur(vals[2][0][1])} für Bildung.",
                        f"Von €100 Ausgaben flossen damit €{num(vals[0][0][1] / tot * 100, 0)} in die soziale Sicherung."]
            return [f"In {y} the government spent {eur(tot)} per inhabitant, of which {eur(vals[0][0][1])} on social protection, {eur(vals[1][0][1])} on health and {eur(vals[2][0][1])} on education.",
                    f"Of every €100 spent, €{num(vals[0][0][1] / tot * 100, 0)} thus went to social protection."]
        if ch == "hh_wealth":
            md, mn = _last(c, "hh_nw_median"), _last(c, "hh_nw_mean")
            x, v = md[-1]
            m = dict(mn).get(x)
            w = _when(x, "Q", lang)
            if de:
                x0, v0 = md[0]
                out = [f"{w[0].upper() + w[1:]} besaß der Haushalt in der Mitte netto rund {k(v)}, der Durchschnitt aller Haushalte {k(m)}."]
                if v:
                    out.append(f"Der Durchschnitt liegt beim {num(m / v, 1)}-Fachen der Mitte.")
                if x0 != x:
                    w0 = _when(x0, "Q", lang)
                    out.append(f"{w0[0].upper() + w0[1:]} besaß der Haushalt in der Mitte netto {k(v0)} (nominal, ohne Abzug der Preissteigerung).")
                return out
            return [f"{w[0].upper() + w[1:]}, the household in the middle had net wealth of about {k(v)}, the average across all households {k(m)}."]
        if ch == "hh_balance":
            ids = [("hh_q3_nun", "Immobilien", "property"), ("hh_q3_f2m", "Bargeld und Einlagen", "cash and deposits"), ("hh_q3_f62", "Lebensversicherungen und Renten", "life insurance and pensions")]
            nw = _last(c, "hh_q3_nwa")
            x, v = nw[-1]
            debt = sum(dict(_last(c, i)).get(x, 0) for i in ("hh_q3_f4b", "hh_q3_f4x"))
            parts = [(dict(_last(c, i)).get(x, 0), a, b) for i, a, b in ids]
            w = _when(x, "Q", lang)
            if de:
                return [f"{w[0].upper() + w[1:]} besaßen die Haushalte im mittleren Fünftel im Durchschnitt Immobilien für {k(parts[0][0])} und Einlagen von {k(parts[1][0])}; "
                        f"dem standen Kredite von {k(abs(debt))} gegenüber. Netto blieben {k(v)}."]
            return [f"{w[0].upper() + w[1:]}, a household in the middle fifth owned property worth {k(parts[0][0])} and deposits of {k(parts[1][0])}, "
                    f"against loans of {k(abs(debt))}. Net wealth was {k(v)}."]
        if ch == "hh_spend":
            ids = [("hh_cons_cp04", "Wohnen und Energie", "housing and energy"), ("hh_cons_cp07", "Verkehr", "transport"), ("hh_cons_cp01", "Nahrungsmittel", "food")]
            ser = [(dict(_last(c, i)), a, b) for i, a, b in ids]
            y = max(ser[0][0])
            y0 = min(ser[0][0])
            if de:
                return [f"{y[:4]} gaben die Haushalte {pc(ser[0][0][y])} ihres Konsums für Wohnen und Energie aus, {pc(ser[1][0][y])} für Verkehr und {pc(ser[2][0][y])} für Nahrungsmittel.",
                        f"{y0[:4]} waren es für Wohnen und Energie {pc(ser[0][0][y0])}, für Nahrungsmittel {pc(ser[2][0][y0])}."]
            return [f"In {y[:4]} households spent {pc(ser[0][0][y])} of their consumption on housing and energy, {pc(ser[1][0][y])} on transport and {pc(ser[2][0][y])} on food.",
                    f"In {y0[:4]} the shares were {pc(ser[0][0][y0])} for housing and energy and {pc(ser[2][0][y0])} for food."]
        if ch == "hh_share":
            t, b = _last(c, "hh_share_t10"), _last(c, "hh_share_b50")
            x, vt = t[-1]
            vb = dict(b).get(x)
            w = _when(x, "Q", lang)
            if de:
                out = [f"{w[0].upper() + w[1:]} besaßen die reichsten 10\u00a0% der Haushalte {pc(vt)} des gesamten Nettovermögens, die ärmere Hälfte {pc(vb)}."]
                x0, t0 = t[0]
                b0 = dict(b).get(x0)
                if x0 != x and b0 is not None:
                    w0 = _when(x0, "Q", lang)
                    out.append(f"{w0[0].upper() + w0[1:]} waren es {pc(t0)} und {pc(b0)}.")
                return out
            return [f"{w[0].upper() + w[1:]}, the richest 10% of households held {pc(vt)} of total net wealth, the poorer half {pc(vb)}."]
    except (KeyError, IndexError, ValueError, ZeroDivisionError, TypeError):
        return []
    return []
