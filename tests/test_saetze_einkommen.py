from monitor.build import chart_sentences

Q = [f"{y}-{m:02d}-01" for y in range(2019, 2027) for m in (1, 4, 7, 10)][:30]  # bis 2. Quartal 2026


def test_tpl_streak_and_comparison():
    s = lambda i, ys: {"id": i, "x": Q, "y": ys}
    c = {"type": "line", "freq": "Q", "unit": "% ggü. Vorjahresquartal", "decimals": 1,
         "series": [s("real", [-1.0] * 27 + [0.5, 1.0, 1.5]), s("cpi", [2.0] * 30)],
         "tpl": ["{when} {up_pl[real]} die Reallöhne um {abs[real]} %, {cmp[real-cpi]} die Preise; sie {trend_pl[real]} seit {streak[real]}."]}
    assert chart_sentences(c) == ["Im 2. Quartal 2026 stiegen die Reallöhne um 1,5 %, 0,5 Pp langsamer als die Preise; sie steigen seit drei Quartalen."]


def test_ref_year_mean():
    c = {"type": "line", "freq": "Q", "unit": "% des verfügbaren Einkommens", "decimals": 1, "ref_year": 2019,
         "series": [{"id": "de_saving", "label": "Sparquote", "x": Q, "y": [17.0, 18.0, 18.0, 17.0] + [19.0] * 26}]}
    assert chart_sentences(c)[-1] == "Im Mittel des Jahres 2019 waren es 17,5 %."
