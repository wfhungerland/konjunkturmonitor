from monitor.build import chart_sentences

M = [f"{y}-{m:02d}-01" for y in (2025, 2026) for m in range(1, 13)][:22]  # bis Oktober 2026


def test_spread_names_strongest_and_weakest_area():
    s = lambda i, v: {"id": i, "label": i, "x": M, "y": [1.0] * 21 + [v]}
    c = {"type": "line", "freq": "M", "unit": "% ggü. Vorjahresmonat", "decimals": 1, "emphasis": "tot",
         "spread": {"a": "Energie", "b": "Nahrungsmittel"}, "series": [s("tot", 2.8), s("a", 12.2), s("b", -0.4)]}
    assert chart_sentences(c)[-1] == "Am stärksten stiegen die Preise für Energie (+12,2 %), für Nahrungsmittel sanken sie (-0,4 %)."


def test_combine_mom_names_largest_rise():
    s = lambda lab, a, b: {"id": lab, "label": lab, "x": M[-2:], "y": [a, b]}
    c = {"type": "line", "freq": "M", "unit": "Saldo", "decimals": 0, "series": [s("Industrie", 24, 29), s("Bau", 17, 17)],
         "combine": {"lead": "lauteten die Salden:", "mom": {"Industrie": "in der Industrie"}}}
    assert chart_sentences(c)[1] == "Ggü. dem Vormonat stiegen sie am stärksten in der Industrie (+5 Pp)."
