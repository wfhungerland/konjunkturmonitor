import pandas as pd

from monitor import lage


def _monthly(start, end, value=1.0):
    idx = pd.date_range(start, end, freq="MS")
    return pd.Series(value, index=idx, dtype=float)


def test_band_needs_full_reference_period():
    full = lage._line(_monthly("2015-01-01", "2026-10-01"))
    assert full["lo"] is not None and full["hi"] is not None and full["mean"] is not None
    short = lage._line(_monthly("2019-01-01", "2026-10-01"))
    assert short["lo"] is None and short["hi"] is None and short["mean"] is None


def test_oil_in_euro_covers_2015_to_2019():
    idx = pd.date_range("2015-01-01", "2026-10-01", freq="MS")
    brent = pd.Series(50.0, index=idx)
    brent["2016-01-01"] = 30.0
    fxd = pd.Series(1.0, index=pd.date_range("2015-01-01", "2026-10-31", freq="B"))
    oil = lage._oil_eur({"w_brent": brent, "fx_usd": fxd})
    line = lage._line(oil)
    assert line["lo"] == 30.0 and line["hi"] == 50.0
