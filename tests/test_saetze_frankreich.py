from monitor.build import chart_sentences
from monitor.ausschreiben import spell


def test_combine_ends_names_highest_and_lowest():
    s = lambda lab, v: {"id": lab, "label": lab, "x": ["2026-10-01"], "y": [v]}
    c = {"type": "line", "freq": "M", "unit": "Basispunkte", "decimals": 0, "series": [s("Frankreich", 147), s("Niederlande", 12), s("Italien", 126)],
         "combine": {"ends": "war der Aufschlag", "pre": "für ", "names": {"Niederlande": "für die Niederlande"}, "lead": "x"}}
    assert chart_sentences(c) == ["Im Oktober 2026 war der Aufschlag für Frankreich am höchsten (147 Basispunkte), für die Niederlande am niedrigsten (12)."]


def test_tpl_uses_all_series_despite_emphasis():
    s = lambda i, v: {"id": i, "x": ["2026-10-01"], "y": [v]}
    c = {"type": "line", "freq": "M", "unit": "%", "decimals": 2, "emphasis": "fr", "series": [s("fr", 4.89), s("it", 4.68)],
         "tpl": ["{n[fr]} und {n[it]}; {mw[fr-it]}."]}
    assert chart_sentences(c) == ["4,89 und 4,68; mehr."]


def test_points_in_dative_after_bei():
    assert spell("lag bei 0,10 Punkte, 0,09 Punkte höher") == "lag bei 0,10\xa0Punkten, 0,09\xa0Punkte höher"
