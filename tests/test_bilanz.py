"""Erfolgsbilanz: Treffer, Vorlauf und Signale ohne Rezession."""
import pandas as pd

from monitor.bilanz import episodes, evaluate


def test_bilanz():
    idx = pd.date_range("2000-01-01", "2012-12-01", freq="MS")
    flag = pd.Series(False, index=idx)
    flag["2007-06-01":"2008-03-01"] = True  # Vorwarnung vor der Rezession 2008
    flag["2003-01-01":"2003-02-01"] = True  # Signal ohne Rezession
    recs = [{"peak": "2001-02-01", "trough": "2003-06-01"}, {"peak": "2008-01-01", "trough": "2009-04-01"}]
    b = evaluate(flag, recs, 12)
    assert b["n"] == 1  # 2001 liegt vor dem Beginn der Prüfung
    assert b["rows"][0]["signal"] == "2007-06" and b["rows"][0]["lead"] == 7
    assert b["false"] == ["2003-01"]
    assert len(episodes(flag)) == 2
