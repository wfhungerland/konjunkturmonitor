from monitor.build import chart_sentences

M = [f"2026-{m:02d}-01" for m in range(1, 12)]


def test_last_change_skips_partial_month_average():
    y = [2.0] * 5 + [2.1167, 2.25, 2.25, 2.375, 2.5, 2.5]
    c = {"type": "line", "freq": "M", "unit": "% p. a.", "decimals": 2, "no_yoy": True, "last_change": "dfr",
         "series": [{"id": "dfr", "label": "Einlagesatz", "x": M, "y": y}]}
    assert chart_sentences(c)[-1].endswith("; zuletzt hat die EZB ihn im September 2026 von 2,25 auf 2,50 % angehoben.")


def test_combine_sort_singular_mom_and_year_ago():
    x = [f"{y}-{m:02d}-01" for y in (2025, 2026) for m in range(1, 13)][:22]
    s = lambda lab, a, b: {"id": lab, "label": lab, "x": x, "y": [a] * 21 + [b]}
    c = {"type": "line", "freq": "M", "unit": "Pp", "decimals": 2, "series": [s("Italien", 0.9, 1.26), s("Frankreich", 0.96, 1.47)],
         "combine": {"sort": True, "sing": True, "yago": True, "lead": "lag der Abstand", "pre": "für ", "mid": " bei", "sign": False, "mom": {"Frankreich": "für Frankreich"}}}
    assert chart_sentences(c) == ["Im Oktober 2026 lag der Abstand für Frankreich bei 1,47 Pp und für Italien bei 1,26 Pp.",
                                  "Ggü. dem Vormonat stieg er am stärksten für Frankreich (+0,51 Pp).", "Ein Jahr zuvor waren es 0,96 Pp und 0,90 Pp."]
