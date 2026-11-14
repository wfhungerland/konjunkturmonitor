from monitor.build import chart_sentences


def test_rank_among_countries():
    s = lambda i, lab, v: {"id": i, "label": lab, "x": ["2026-01-01"], "y": [v]}
    c = {"type": "line", "freq": "A", "unit": "%", "decimals": 1, "no_yoy": True, "emphasis": "de", "rank": True,
         "series": [s("de", "Deutschland", 30.1), s("fr", "Frankreich", 36.1), s("pl", "Polen", 19.0)]}
    assert chart_sentences(c)[-1] == "Unter den drei verglichenen Ländern liegt nur Frankreich höher (36,1 %), am niedrigsten liegt Polen (19,0 %)."


def test_tpl_thousands_from_millions_and_direction():
    x = ["2024-01-01", "2025-01-01"]
    c = {"type": "line", "freq": "A", "unit": "Mio. Personen", "decimals": 2, "series": [{"id": "m", "unit": "Mio. Personen", "x": x, "y": [0.452, 0.242]}],
         "tpl": ["{tsd[m]} {abzu[m]}, nach {tsd0[m]}."]}
    assert chart_sentences(c) == ["242.000 zu, nach 452.000."]
