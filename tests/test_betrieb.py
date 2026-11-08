"""Betrieb: Wächter (Werktage) und Prüfung auf auffällige Sprünge."""
from datetime import date

import pandas as pd

from monitor.alert import jumps
from monitor.waechter import workdays_between


def test_workdays_between():
    assert workdays_between(date(2026, 11, 6), date(2026, 11, 9)) == 1  # Freitag bis Montag
    assert workdays_between(date(2026, 11, 2), date(2026, 11, 9)) == 5
    assert workdays_between(date(2026, 11, 9), date(2026, 11, 9)) == 0


def test_jumps(tmp_path):
    idx = pd.date_range("2020-01-01", periods=48, freq="MS")
    import numpy as np
    calm = list(100 + np.random.default_rng(1).normal(0, 1, 48).cumsum())
    jump = calm[:-1] + [calm[-2] + 50]  # Einheitenwechsel im jüngsten Monat
    rows = [("calm", d, v) for d, v in zip(idx, calm)] + [("jump", d, v) for d, v in zip(idx, jump)]
    p = tmp_path / "obs.csv"
    pd.DataFrame(rows, columns=["series_id", "date", "value"]).to_csv(p, index=False)
    found = jumps(p)
    assert len(found) == 1 and "`jump`" in found[0]
