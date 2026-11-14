from monitor.build import chart_sentences

M = [f"2026-{m:02d}-01" for m in range(1, 10)]


def test_tpl_saldo_word_follows_sign():
    s = lambda i, v: {"id": i, "x": M, "y": [v] * 9}
    c = {"type": "line", "freq": "M", "unit": "Mrd. €", "decimals": 0, "series": [s("bal", -3.0)], "tpl": ["Dann lag {sw[bal]} bei {v[bal]}."]}
    assert chart_sentences(c)[0].startswith("Dann lag das Defizit bei")


def test_long_mean_one_sentence_with_unit_at_end():
    x = [f"{y}-01-01" for y in (2020, 2021)]
    c = {"type": "line", "freq": "A", "unit": "% des BIP", "decimals": 1, "long_mean": True,
         "series": [{"id": "a", "label": "A", "x": x, "y": [20.0, 21.0]}, {"id": "b", "label": "B", "x": x, "y": [1.0, 2.0]}]}
    assert chart_sentences(c)[-1] == "Im Mittel der Jahre 2020 bis 2021 ohne Kriegsjahre waren es 20,5 % und 1,5 % des BIP."
