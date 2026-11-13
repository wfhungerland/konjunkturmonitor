from monitor.build import chart_sentences

X = [f"{y}-{m:02d}-01" for y in (2025, 2026) for m in range(1, 13)][:22]  # bis Oktober 2026


def test_tpl_several_series_with_ratio():
    c = {"type": "line", "freq": "M", "unit": "Tsd.", "decimals": 0,
         "series": [{"id": "alo", "x": X, "y": [2000] * 21 + [2100]}, {"id": "vac", "x": X, "y": [500] * 21 + [600]}],
         "tpl": ["{when} waren {v[alo]} arbeitslos ({chg[alo]}); gemeldet waren {full[vac]} Stellen.", "Je Stelle {q[alo/vac]}, zuvor {q0[alo/vac]}."]}
    assert chart_sentences(c) == ["Im Oktober 2026 waren 2.100 Tsd. arbeitslos (+5,0 %); gemeldet waren 600.000 Stellen.", "Je Stelle 3,5, zuvor 4,0."]


def test_combine_where_puts_verb_first():
    s = lambda lab, v: {"id": lab, "label": lab, "x": X, "y": [0] * 21 + [v]}
    c = {"type": "line", "freq": "M", "unit": "% ggü. Vorjahresmonat", "decimals": 1,
         "series": [s("Insgesamt", -0.1), s("A", -1.6), s("B", 0.5), s("C", -2.1)],
         "combine": {"subj": "die Beschäftigung", "where": {"A": "in A", "B": "in B", "C": "in C"}, "lead": "x"}}
    assert chart_sentences(c) == ["Im Oktober 2026 sank die Beschäftigung um 0,1 % ggü. dem Vorjahresmonat, in A um 1,6 %, in C um 2,1 %; in B stieg sie um 0,5 %."]


def test_tiles_diff_counts_rising_states():
    rows = [{"name": "Berlin", "level": 10.3, "change": 0.6}, {"name": "Bayern", "level": 4.0, "change": -0.1}, {"name": "Saarland", "level": 7.4, "change": 0.4}]
    c = {"type": "tiles", "what": "Arbeitslosenquote", "tiles": {"rows": rows, "span": "2025", "last": "2025-01-01", "measure": "diff"}}
    assert chart_sentences(c)[1] == "In zwei von drei Ländern stieg sie ggü. dem Vorjahr, am stärksten in Berlin (+0,6 Pp)."
