"""Seite des Konjunkturmonitors aus den Beobachtungen der Pipeline bauen."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .answers import answer, num, overview

ROOT = Path.cwd()

SOURCE_NAMES = {"bundesbank": "Deutsche Bundesbank", "eurostat": "Eurostat", "ecb": "EZB", "static": "BA-Statistik (aufbereitet)",
                "derived": "eigene Berechnung"}
SOURCE_LICENSES = {"bundesbank": "Wiederverwendung mit Quellenangabe (Deutsche Bundesbank)", "eurostat": "CC BY 4.0 (Eurostat)",
                   "ecb": "Wiederverwendung mit Quellenangabe (EZB)", "fred": "Nutzungsbedingungen der Originalquelle laut FRED, mit Quellenangabe", "static": "Statistik der Bundesagentur für Arbeit, mit Quellenangabe"}


_META: dict = {}


def _base(s):
    """Für abgeleitete Reihen die Ausgangsreihe (Quelle und Lizenz kommen von dort)."""
    seen = 0
    while s.source == "derived" and (s.derive or {}).get("from") in _META and seen < 5:
        s, seen = _META[s.derive["from"]], seen + 1
    return s


def _source_name(s) -> str:
    """Quellenname je Reihe; statische Reihen können ihn in params.source_name setzen."""
    b = _base(s)
    name = (b.params or {}).get("source_name") or SOURCE_NAMES.get(b.source, b.source)
    return f"{name} (eigene Berechnung)" if s.source == "derived" and b is not s else name


def _license(s) -> str:
    b = _base(s)
    return b.license or SOURCE_LICENSES.get(b.source, "")


def load_observations(root: Path = ROOT) -> tuple[dict[str, pd.Series], str]:
    obs = pd.read_csv(root / "data" / "processed" / "observations.csv", parse_dates=["date"])
    data = {sid: g.set_index("date")["value"].sort_index() for sid, g in obs.groupby("series_id")}
    stand = str(obs["retrieved_at"].max())[:10] if "retrieved_at" in obs else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return data, stand


def _series_meta(catalog_path: Path) -> tuple[dict, dict]:
    from konjunkturwolf.catalog import load_catalog

    cat = load_catalog(catalog_path)
    raw = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    return {s.id: s for s in cat.series}, raw.get("charts", {})


def _xy(s: pd.Series, years: int | None) -> dict:
    s = s.dropna()
    if years:
        s = s[s.index >= s.index[-1] - pd.DateOffset(years=years)]
    return {"x": [d.strftime("%Y-%m-%d") for d in s.index], "y": [round(float(v), 4) for v in s.values]}


def _clock(cfg: dict, data: dict) -> dict | None:
    """Konjunkturuhr: Lage und Erwartungen als Abstand zum Mittel 2005 bis 2019, die letzten Monate als Spur."""
    if cfg["x"] not in data or cfg["y"] not in data:
        return None
    x, y = data[cfg["x"]].dropna(), data[cfg["y"]].dropna()
    df = pd.concat({"x": x, "y": y}, axis=1).dropna()
    base = df[(df.index >= "2005-01-01") & (df.index < "2020-01-01")].mean()
    dev = (df - base).iloc[-int(cfg.get("months", 24)):]
    return {"x": [round(float(v), 2) for v in dev["x"]], "y": [round(float(v), 2) for v in dev["y"]],
            "t": [d.strftime("%Y-%m-%d") for d in dev.index]}


LAND_ABBR = {"01": "SH", "02": "HH", "03": "NI", "04": "HB", "05": "NW", "06": "HE", "07": "RP", "08": "BW", "09": "BY", "10": "SL",
             "11": "BE", "12": "BB", "13": "MV", "14": "SN", "15": "ST", "16": "TH"}


def _seasonal(s: pd.Series, years: int | None) -> dict:
    """Monatswerte, 12-Monats-Mittel und das übliche Niveau desselben Monats 2015 bis 2019."""
    s = s.dropna()
    ma12 = s.rolling(12).mean()
    base = s[(s.index >= NORM[0]) & (s.index < NORM[1])]
    norm_by_month = base.groupby(base.index.month).mean() if len(base) else pd.Series(dtype=float)
    norm = pd.Series([norm_by_month.get(d.month) for d in s.index], index=s.index, dtype=float)
    if years:
        cut = s.index[-1] - pd.DateOffset(years=years)
        s, ma12, norm = s[s.index >= cut], ma12[ma12.index >= cut], norm[norm.index >= cut]
    r = lambda v: None if pd.isna(v) else round(float(v), 4)
    return {"x": [d.strftime("%Y-%m-%d") for d in s.index], "y": [r(v) for v in s], "ma12": [r(v) for v in ma12], "norm": [r(v) for v in norm]}


def _tiles(prefix: str, data: dict, meta: dict, months: int = 12) -> dict | None:
    """Veränderung der letzten `months` Monate gegenüber demselben Zeitraum ein Jahr zuvor, je Land."""
    rows, last = [], None
    for code, abbr in LAND_ABBR.items():
        s = data.get(f"{prefix}{code}")
        if s is None or len(s.dropna()) < 24:
            continue
        s = s.dropna()
        a, b = s.iloc[-months:].sum(), s.iloc[-12 - months:-12].sum()
        if b <= 0:
            continue
        last = s.index[-1] if last is None else max(last, s.index[-1])
        rows.append({"code": code, "abbr": abbr, "name": meta[f"{prefix}{code}"].label, "change": round((a / b - 1) * 100, 1), "sum": int(a)})
    if not rows:
        return None
    from .answers import MONTHS
    lo = last - pd.DateOffset(months=months - 1)
    span = f"{MONTHS[lo.month - 1]} {lo.year} bis {MONTHS[last.month - 1]} {last.year}"
    return {"rows": rows, "span": span, "months": months}


def _forecasts(root: Path) -> list[dict]:
    """Prognosen je Herausgeber und Runde; die jüngste Runde je Herausgeber ist als latest markiert."""
    path = root / "data" / "static" / "prognosen.yaml"
    if not path.exists():
        return []
    rows = [dict(r, date=str(r["date"]), values={int(k): float(v) for k, v in r["values"].items()})
            for r in (yaml.safe_load(path.read_text(encoding="utf-8")) or [])]
    newest = {}
    for r in rows:
        if r["by"] not in newest or r["date"] > newest[r["by"]]:
            newest[r["by"]] = r["date"]
    return sorted((dict(r, latest=r["date"] == newest[r["by"]]) for r in rows), key=lambda r: r["date"])


def _contrib(cfg: dict, data: dict) -> dict | None:
    """Beiträge zur Inflationsrate aus Teilindizes (2020 = 100).

    Gewichte w_i aus der Laspeyres-Identität I_gesamt = Summe w_i * I_i über die Monate ab 2020 geschätzt
    (kleinste Quadrate); Beitrag_i = w_i * (I_i,t - I_i,t-12) / I_gesamt,t-12 * 100. Der Rest gleicht
    Rundung und nicht erfasste Teile aus, damit die Balken die veröffentlichte Rate ergeben.
    """
    total_id, parts = cfg["total"], cfg["parts"]
    ids = [sid for group in parts.values() for sid in (group if isinstance(group, list) else [group])]
    if total_id not in data or any(sid not in data for sid in ids):
        return None
    df = pd.concat({sid: data[sid] for sid in [total_id, *ids]}, axis=1).dropna()
    fit = df[df.index >= "2020-01-01"]
    if len(fit) < 24:
        return None
    w, *_ = np.linalg.lstsq(fit[ids].to_numpy(), fit[total_id].to_numpy(), rcond=None)
    weights = dict(zip(ids, w))
    years = cfg.get("years", 3)

    def contributions(lag: int, total_label: str) -> list[dict]:
        prev = df.shift(lag)
        rate = (df[total_id] / prev[total_id] - 1) * 100
        out, used = {}, pd.Series(0.0, index=df.index)
        for label, group in parts.items():
            group = group if isinstance(group, list) else [group]
            c = sum(weights[g] * (df[g] - prev[g]) for g in group) / prev[total_id] * 100
            out[label] = c
            used = used + c
        out["Rest"] = rate - used
        keep = rate.dropna().index
        keep = keep[keep >= keep[-1] - pd.DateOffset(years=years)]
        r = lambda s: [round(float(v), 3) for v in s.loc[keep]]
        x = [d.strftime("%Y-%m-%d") for d in keep]
        series = [dict(id=f"contrib_{lag}_{i}", label=k, unit="Pp", freq="M", style="bar", x=x, y=r(v)) for i, (k, v) in enumerate(out.items())]
        series.append(dict(id=f"contrib_{lag}_total", label=total_label, unit="%", freq="M", style="line", x=x, y=r(rate)))
        return series

    series = contributions(12, "Inflationsrate")
    series_mom = contributions(1, "Veränderung gegenüber dem Vormonat")
    fitted = fit[ids].to_numpy() @ w
    err = float(np.max(np.abs(fitted - fit[total_id].to_numpy())))
    return {"series": series, "series_mom": series_mom, "weights": {k: round(float(v), 4) for k, v in weights.items()}, "fit_max_abs": round(err, 3)}


def _geo(root: Path) -> list[dict] | None:
    """Ländergrenzen (BKG VG2500, vereinfacht) mit Beschriftungspunkt je Land (Schwerpunkt der größten Teilfläche)."""
    path = root / "data" / "static" / "vg2500_laender.json"
    if not path.exists():
        return None
    out = []
    for f in json.loads(path.read_text(encoding="utf-8")):
        polys = f["coordinates"] if f["type"] == "MultiPolygon" else [f["coordinates"]]

        def area_centroid(ring):
            a = cx = cy = 0.0
            for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
                cr = x0 * y1 - x1 * y0
                a += cr
                cx += (x0 + x1) * cr
                cy += (y0 + y1) * cr
            a /= 2
            return abs(a), (cx / (6 * a), cy / (6 * a)) if a else ring[0]

        best = max((area_centroid(p[0]) for p in polys), key=lambda r: r[0])
        out.append({"code": f["code"], "abbr": LAND_ABBR.get(f["code"], f["code"]), "rings": [r for p in polys for r in p],
                    "outer": len(polys), "label": [round(best[1][0], 3), round(best[1][1], 3)]})
    return out


def _band(s: pd.Series) -> dict | None:
    """Spanne (Minimum bis Maximum) einer Reihe in den Jahren 2015 bis 2019 als Vergleichsmaßstab."""
    b = s.dropna()
    b = b[(b.index >= NORM[0]) & (b.index < NORM[1])]
    if len(b) < 4:
        return None
    return {"lo": round(float(b.min()), 4), "hi": round(float(b.max()), 4), "mean": round(float(b.mean()), 4)}


NORM = ("2015-01-01", "2020-01-01")  # Vergleichszeitraum 2015 bis 2019: die fünf letzten vollen Jahre vor der Pandemie


def _tendency(d: float | None, decimals: int) -> str | None:
    """Richtung der jüngsten Veränderung: ▲ steigt, ▼ sinkt, ■ unverändert (in der angezeigten Genauigkeit)."""
    if d is None or pd.isna(d):
        return None
    if round(abs(d), decimals) == 0:
        return "flat"
    return "up" if d > 0 else "down"


def _start_rows(cfg: dict, data: dict, meta: dict | None = None, titles: dict | None = None) -> list[dict]:
    """Kennzahlentabelle: Wert, drei feste Vergleiche (Vorperiode, Vorjahr, Dreimonatsvergleich), Verlauf und Tendenz.

    kind rate: Wert ist eine Rate oder ein Saldo; Vergleiche als Differenz (Prozentpunkte oder Punkte).
    kind level: Wert ist ein Niveau (Index, Anzahl, Euro); Vergleiche als prozentuale Veränderung,
    mit change: diff als Differenz in change_unit. seasonal: true heißt nicht saisonbereinigt mit
    deutlichem Saisonmuster; dann entfallen Vorperioden- und Dreimonatsvergleich.
    """
    from .answers import period

    meta, titles = meta or {}, titles or {}
    rows = []
    for r in cfg.get("start_table") or []:
        s = data.get(r["series"])
        if s is None or len(s.dropna()) < 7:
            continue
        s = s.dropna()
        q = s.index.to_series().diff().dt.days.median() > 60
        lag_y = 4 if q else 12
        kind = r.get("kind", "rate")
        scale = float(r.get("scale", 1))
        cd = int(r.get("change_decimals", 1))
        if kind == "rate":
            diff = lambda a, b: a - b
            cunit = r.get("change_unit") or ("Pp" if "%" in r.get("unit", "") or r.get("unit", "").startswith("Pp") else "Pkt.")
        elif r.get("change") == "diff":
            diff = lambda a, b: (a - b) * float(r.get("change_scale", 1))
            cunit = r.get("change_unit", "")
        else:
            diff = lambda a, b: (a / b - 1) * 100
            cunit = "%"
        prev = diff(s.iloc[-1], s.iloc[-2])
        yoy = diff(s.iloc[-1], s.iloc[-1 - lag_y]) if len(s) > lag_y else None
        m3 = None if q else diff(s.iloc[-3:].mean(), s.iloc[-6:-3].mean())
        if r.get("mom_from") in data:
            prev = float(data[r["mom_from"]].dropna().iloc[-1])
        if r.get("yoy_from") in data:
            yoy = float(data[r["yoy_from"]].dropna().iloc[-1])
        if r.get("seasonal"):
            prev = m3 = None
        tend = _tendency(prev if prev is not None else yoy, cd)
        spark = s[s.index >= s.index[-1] - pd.DateOffset(years=5)] * scale
        rnd = lambda v: None if v is None or pd.isna(v) else round(float(v), 4)
        rows.append(dict(r, group=titles.get(r.get("topic"), r.get("group", "")), value=rnd(s.iloc[-1] * scale),
                         prev=rnd(prev), yoy=rnd(yoy), m3=rnd(m3), change_unit=cunit, freq="Q" if q else "M",
                         period=period(s.index[-1], "Q" if q else "M"), date=s.index[-1].strftime("%Y-%m-%d"),
                         tendency=tend, prev_label="Vorquartal" if q else "Vormonat",
                         spark={"x": [d.strftime("%Y-%m-%d") for d in spark.index], "y": [round(float(x), 4) for x in spark]}))
    newest = max((x["date"] for x in rows if x["freq"] == "M"), default=None)
    for x in rows:  # ältere Stände kennzeichnen: Monatswerte, die zwei oder mehr Monate hinter dem jüngsten zurückliegen
        if x["freq"] == "M" and newest:
            lag = (pd.Timestamp(newest).to_period("M") - pd.Timestamp(x["date"]).to_period("M")).n
            x["older"] = lag >= 2
    return rows


def _heat(cfg: dict, data: dict, meta: dict) -> dict | None:
    """Wärmetabelle: je Branche die Veränderung gegenüber dem Vorjahresmonat in den letzten Monaten und der Dreimonatsvergleich."""
    months = int(cfg.get("months", 12))
    rows, cols = [], None
    for s in [m for m in meta.values() if m.chart_id == cfg["chart"]]:
        x = data.get(s.id)
        if x is None or len(x.dropna()) < 24:
            continue
        x = x.dropna()
        yoy = ((x / x.shift(12) - 1) * 100).dropna().iloc[-months:]
        m3 = (x.rolling(3).mean() / x.rolling(3).mean().shift(3) - 1) * 100
        cols = [d.strftime("%Y-%m-%d") for d in yoy.index] if cols is None or len(yoy) > len(cols) else cols
        rows.append({"label": s.label, "values": dict(zip([d.strftime("%Y-%m-%d") for d in yoy.index], [round(float(v), 1) for v in yoy])),
                     "m3": round(float(m3.iloc[-1]), 1), "level": round(float(x.iloc[-1] / x[(x.index >= "2019-01-01") & (x.index < "2020-01-01")].mean() * 100 - 100), 1)
                     if len(x[(x.index >= "2019-01-01") & (x.index < "2020-01-01")]) else None})
    if not rows:
        return None
    rows.sort(key=lambda r: r["m3"])
    return {"cols": cols, "rows": rows}


def _workdays(year: int, month: int) -> list:
    """Werktage (Montag bis Freitag) eines Monats; bundesweite Feiertage mit festem Datum ausgenommen."""
    fixed = {(1, 1), (5, 1), (10, 3), (12, 25), (12, 26)}
    days = pd.date_range(f"{year}-{month:02d}-01", periods=31, freq="D")
    return [d for d in days if d.month == month and d.weekday() < 5 and (d.month, d.day) not in fixed]


def _calendar(root: Path, start: pd.Timestamp, months: int = 2) -> dict | None:
    path = root / "data" / "static" / "kalender.yaml"
    if not path.exists():
        return None
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    events = []
    for k in range(months):
        m0 = (start + pd.DateOffset(months=k))
        y, m = m0.year, m0.month
        wd = _workdays(y, m)
        for it in cfg.get("items") or []:
            r = it.get("rule") or {}
            if r.get("months") and m not in r["months"]:
                continue
            dates = []
            if "workday" in r and len(wd) >= r["workday"]:
                dates = [wd[r["workday"] - 1]]
            elif "last_workday" in r:
                dates = [wd[-1 - int(r["last_workday"])]]
            elif "weekday" in r:
                dates = [d for d in pd.date_range(f"{y}-{m:02d}-01", periods=31) if d.month == m and d.weekday() == r["weekday"]]
            for d in dates:
                events.append({"date": d.strftime("%Y-%m-%d"), "name": it["name"], "source": it.get("source", ""), "topic": it.get("topic")})
    first = start.replace(day=1)
    return {"months": [(first + pd.DateOffset(months=k)).strftime("%Y-%m") for k in range(months)],
            "events": sorted(events, key=lambda e: e["date"]), "links": cfg.get("links") or []}


def _per(x: str, freq: str) -> str:
    from .answers import period
    return period(pd.Timestamp(x), freq) if freq in ("M", "Q") else (x[:4] if freq == "A" else f"Woche bis {x[8:10]}.{x[5:7]}.{x[:4]}")


def chart_text(c: dict) -> str:
    """Kopierfertiger Satz zum jüngsten Stand einer Abbildung (Werte, Zeitraum, Vergleich zum Vorjahr)."""
    from .answers import MONTHS
    typ, d = c.get("type"), int(c.get("decimals", 1))
    unit = (c.get("unit") or "").split(",")[0]
    u = unit if unit.startswith(("% des", "% der")) else "%" if unit.startswith("%") else "Prozentpunkte" if unit.startswith("Pp") else "Punkte" if unit.startswith("Saldo") else "" if unit.startswith("Index") else unit
    fmtv = lambda v: f"{num(v, d)} {u}".strip()
    from .answers import num as _num

    def num(v, dd=1, sign=False):  # gerundete Null ohne Vorzeichen
        v = round(float(v), dd)
        return _num(0.0 if v == 0 else v, dd, sign)
    try:
        if typ == "tiles":
            rows = sorted(c["tiles"]["rows"], key=lambda r: r["change"])
            return (f"{c['tiles']['span']} gegenüber demselben Zeitraum ein Jahr zuvor: am stärksten gestiegen in {rows[-1]['name']} "
                    f"({num(rows[-1]['change'], 1, True)} %), am stärksten gesunken oder am wenigsten gestiegen in {rows[0]['name']} ({num(rows[0]['change'], 1, True)} %).")
        if typ == "heat":
            rows = c["heat"]["rows"]
            return (f"Im Dreimonatsvergleich am stärksten gestiegen: {rows[-1]['label']} ({num(rows[-1]['m3'], 1, True)} %); "
                    f"am schwächsten: {rows[0]['label']} ({num(rows[0]['m3'], 1, True)} %).")
        if typ == "clock":
            k = c["clock"]
            x, y, t0 = k["x"][-1], k["y"][-1], pd.Timestamp(k["t"][-1])
            phase = "Boom" if x >= 0 and y >= 0 else "Abschwung" if x >= 0 else "Aufschwung" if y >= 0 else "Rezession"
            return (f"Im {MONTHS[t0.month - 1]} {t0.year} lag die Industrie im Feld „{phase}“: Auftragslage {num(x, 1, True)} Punkte, "
                    f"Produktionserwartungen {num(y, 1, True)} Punkte gegenüber dem Mittel 2005 bis 2019.")
        if typ == "seasonal":
            i = max(k for k, v in enumerate(c["y"]) if v is not None)
            s = f"Im {_per(c['x'][i], 'M')}: {num(c['y'][i], d)}"
            if c["ma12"][i] is not None and c["norm"][i] is not None:
                s += f"; Mittel der letzten zwölf Monate {num(c['ma12'][i], d)}, übliches Niveau desselben Monats 2015 bis 2019 {num(c['norm'][i], d)}"
            return s + "."
        if typ == "latest":
            b = c["bars"]
            return f"{c.get('bar_name', 'Zuletzt')} ({_per(b[0]['period'], c.get('freq', 'Q'))}): " + "; ".join(f"{x['label']} {num(x['value'], d, True)}" for x in b) + "."
        if typ in ("calendar", "forecast") or not c.get("series"):
            return ""
        series = [s for s in c["series"] if s.get("y")]
        if typ == "stacked":
            last = max(s["x"][-1] for s in series)
            bars = [s for s in series if s.get("style") == "bar" and s["x"][-1] == last]
            tot = [s for s in series if s.get("style") != "bar" and s["x"][-1] == last]
            head = f"{tot[0]['label']} im {_per(last, c.get('freq', 'M'))}: {num(tot[0]['y'][-1], d, True)} %. " if tot else ""
            return head + "Beiträge in Prozentpunkten: " + "; ".join(f"{s['label']} {num(s['y'][-1], d, True)}" for s in bars) + "."
        if c.get("emphasis"):
            series = [s for s in series if s["id"] == c["emphasis"]] or series
        series = series[:6]
        last = max(s["x"][-1] for s in series)
        parts = []
        for s in series:
            if s["x"][-1] != last:
                continue
            v = s["y"][-1]
            lag = {"M": 12, "Q": 4, "A": 1, "D": 52}.get(s.get("freq", "M"), 12)
            yago = s["y"][-1 - lag] if len(s["y"]) > lag else None
            add = ""
            if yago is not None and c.get("type") != "stacked" and s.get("style") != "bar":
                if unit.startswith(("%", "Pp", "Saldo")) or "Saldo" in unit:
                    add = f" ({num(v - yago, d, True)} {'Prozentpunkte' if unit.startswith(('%', 'Pp')) else 'Punkte'} gegenüber dem Vorjahr)"
                elif yago:
                    add = f" ({num((v / yago - 1) * 100, 1, True)} % gegenüber dem Vorjahr)"
            parts.append(f"{s['label']} {fmtv(v)}{add}")
        return f"Stand {_per(last, c.get('freq', 'M'))}: " + "; ".join(parts) + "." if parts else ""
    except (KeyError, IndexError, ValueError, TypeError):
        return ""


def _notes(root: Path) -> dict:
    """Von Hand gepflegte Hinweise auf Sondereffekte je Abbildung (data/static/hinweise.yaml)."""
    path = root / "data" / "static" / "hinweise.yaml"
    if not path.exists():
        return {}
    out = {}
    for n in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("notes") or []:
        out.setdefault(n["chart"], []).append({"date": str(n["date"]), "text": n["text"]})
    return out


def _outliers(c: dict) -> list[dict]:
    """Auffällige Ausschläge der letzten 24 Monate: Veränderung zum Vormonat mehr als drei Standardabweichungen
    (gemessen 2015 bis 2019) vom üblichen Wert entfernt. Ursache wird nicht automatisch bestimmt."""
    out = []
    for s in c.get("series") or []:
        if s.get("freq") != "M" or s.get("style") == "bar" or len(s["y"]) < 30:
            continue
        x = pd.Series(s["y"], index=pd.to_datetime(s["x"]), dtype=float).dropna()
        if (x <= 0).any():
            continue
        ch = x.pct_change() * 100
        ref = ch[(ch.index >= NORM[0]) & (ch.index < NORM[1])]
        ref = ref if len(ref) >= 24 else ch.iloc[:-24]
        if len(ref) < 24 or ref.std() == 0:
            continue
        z = (ch - ref.mean()) / ref.std()
        for dt, zz in z.iloc[-24:].items():
            if abs(zz) > 3:
                out.append({"date": dt.strftime("%Y-%m-%d"), "label": s["label"], "change": round(float(ch[dt]), 1)})
    return out[-4:]


def build_payload(root: Path = ROOT) -> dict:
    cfg = yaml.safe_load((root / "monitor.yaml").read_text(encoding="utf-8"))
    layout = cfg.get("layout") or {}
    data, stand = load_observations(root)
    meta, charts_cfg = _series_meta(root / "series.yaml")
    _META.clear()
    _META.update(meta)
    questions = []
    for q in cfg["questions"]:
        a = answer(q, data)
        if a is None:
            continue
        a["spark_data"] = _xy(data[a["spark"]], 5)
        questions.append(dict(q, answer=a))
    topics = []
    for t in cfg["topics"]:
        charts = []
        for c in t["charts"]:
            typ = c.get("type", "line")
            uy = layout.get("uniform_years")
            if uy and c.get("years") and 3 <= c["years"] <= 8:
                c = dict(c, years=int(uy))
            entry = dict(c, type=typ, title=(charts_cfg.get(c["chart"], {}) or {}).get("title", c.get("title", "")),
                         decimals=(charts_cfg.get(c["chart"], {}) or {}).get("decimals", 1))
            if typ == "clock":
                entry["clock"] = _clock(c, data)
                entry["sources"] = ["Europäische Kommission, Unternehmensumfrage Industrie (Eurostat ei_bsin_m_r2)"]
                entry["licenses"] = [SOURCE_LICENSES["eurostat"]]
                if not entry["clock"]:
                    continue
            elif typ == "seasonal":
                sid = c["series"]
                if sid not in data:
                    continue
                m = meta[sid]
                entry.update(_seasonal(data[sid], c.get("years")), unit=m.unit, freq=m.frequency, adjustment=m.adjustment,
                             label=m.label, sources=["Statistisches Bundesamt (GENESIS)"],
                             licenses=["Datenlizenz Deutschland – Namensnennung – Version 2.0 (Statistisches Bundesamt)"])
            elif typ == "tiles":
                windows = {m: _tiles(c["prefix"], data, meta, m) for m in (12, 6)}
                if not windows[12]:
                    continue
                entry.update(tiles=windows[12], tiles6=windows[6], sources=["Statistisches Bundesamt (GENESIS)"],
                             licenses=["Datenlizenz Deutschland – Namensnennung – Version 2.0 (Statistisches Bundesamt)"])
            elif typ == "contrib":
                res = _contrib(c, data)
                if not res:
                    continue
                entry.update(series=res["series"], unit="% gegenüber Vorjahresmonat, Beiträge in Prozentpunkten", freq="M", adjustment="nicht bereinigt",
                             alt={"label": "gegenüber Vormonat", "base": "gegenüber Vorjahresmonat", "series": res["series_mom"],
                                  "unit": "% gegenüber Vormonat, Beiträge in Prozentpunkten"},
                             weights=res["weights"], sources=["Deutsche Bundesbank (VPI des Statistischen Bundesamts)", "eigene Berechnung"],
                             licenses=[SOURCE_LICENSES["bundesbank"]], type="stacked")
                print(f"Inflationsbeiträge: Gewichte {res['weights']}, größte Abweichung der Identität {res['fit_max_abs']} Indexpunkte")
            elif typ == "heat":
                h = _heat(c, data, meta)
                if not h:
                    continue
                what = "Auftragseingang" if "order" in c["chart"] else "Produktionsindex"
                entry.update(heat=h, unit="% gegenüber Vorjahresmonat", freq="M", adjustment="saison- und kalenderbereinigt (Bundesbank)",
                             sources=[f"Deutsche Bundesbank ({what} des Statistischen Bundesamts)"], licenses=[SOURCE_LICENSES["bundesbank"]])
            elif typ == "since":
                specs = [s for s in meta.values() if s.chart_id == c["chart"] and s.id in data]
                base = pd.Timestamp(c["base"])
                bars = []
                for s in specs:
                    x = data[s.id].dropna()
                    b = x[x.index <= base]
                    if b.empty:
                        continue
                    bars.append({"label": s.label, "value": round(float(x.iloc[-1] - b.iloc[-1]), 1), "prev": None, "period": x.index[-1].strftime("%Y-%m-%d")})
                if not bars:
                    continue
                bars.sort(key=lambda r: r["value"], reverse=True)
                m = meta[specs[0].id]
                entry.update(type="latest", bars=bars, bar_name=c.get("bar_name", "Veränderung"), freq=m.frequency, adjustment=m.adjustment,
                             unit=c.get("unit", m.unit), sources=sorted({_source_name(s) for s in specs}), licenses=sorted({_license(s) for s in specs}),
                             series=[dict(id=s.id, label=s.label, unit=s.unit, freq=s.frequency, style="line", **_xy(data[s.id], 12)) for s in specs])
            elif typ == "calendar":
                cal = _calendar(root, pd.Timestamp(datetime.now(timezone.utc).date()), int(c.get("months", 2)))
                if not cal:
                    continue
                entry.update(calendar=cal, sources=["Eigene Zusammenstellung nach dem üblichen Veröffentlichungsrhythmus der Quellen"], licenses=[])
            elif typ == "forecast":
                entry["forecasts"] = _forecasts(root)
                entry["sources"] = sorted({f"{f['by']} ({f['round']})" for f in entry["forecasts"]})
                if not entry["forecasts"]:
                    continue
            else:
                specs = [s for s in meta.values() if s.chart_id == c["chart"]]
                series = []
                for s in specs:
                    if s.id not in data:
                        continue
                    xy = _xy(data[s.id] * float(c.get("scale", 1)), c.get("years"))
                    series.append(dict(id=s.id, label=s.label or s.title, unit=c.get("unit", s.unit), freq=s.frequency,
                                       style=getattr(s, "style", None) or "line", **xy))
                if c.get("total") and c["total"] in data:
                    s = meta[c["total"]]
                    series.append(dict(id=s.id, label="BIP insgesamt", unit=s.unit, freq=s.frequency, style="line",
                                       **_xy(data[s.id], c.get("years"))))
                if not series:
                    continue
                entry["series"] = series
                if layout.get("compare_band") and typ in ("line",) and not c.get("ma3") and (len(series) == 1 or c.get("emphasis")):
                    lead = next((s for s in specs if s.id == c.get("emphasis")), None) or next((s for s in specs if s.id in data), None)
                    b = _band(data[lead.id]) if lead is not None else None
                    if b:
                        entry["band"] = dict(b, label=f"Spanne 2015–2019 ({lead.label or lead.title})" if len(series) > 1 else "Spanne 2015–2019")
                entry["unit"] = series[0]["unit"]
                entry["freq"] = series[0]["freq"]
                entry["adjustment"] = meta[series[0]["id"]].adjustment
                specs_used = [meta[x["id"]] for x in series]
                entry["sources"] = sorted({_source_name(s) for s in specs_used})
                entry["licenses"] = sorted({lic for s in specs_used if (lic := _license(s))})
                if typ == "latest":
                    entry["bars"] = [dict(label=s["label"], value=s["y"][-1], prev=s["y"][-2] if len(s["y"]) > 1 else None,
                                          period=s["x"][-1]) for s in series]
                if typ == "threshold":
                    rec = root / "data" / "static" / "svr_recessions.csv"
                    if rec.exists():
                        entry["recessions"] = pd.read_csv(rec).to_dict("records")
            charts.append(entry)
        q = next((x for x in questions if x.get("topic") == t["id"]), None)
        topics.append(dict(t, charts=charts, question=q))
    notes = _notes(root)
    for tp in topics:
        for c in tp["charts"]:
            c["text"] = chart_text(c)
            c["notes"] = notes.get(c["chart"], [])
            if c.get("ma3") or c.get("outliers"):
                c["outliers"] = _outliers(c)
    no = 0
    for t in topics:
        for c in t["charts"]:
            no += 1
            c["no"] = no
    geo = _geo(root)
    return {"layout": layout, "start": _start_rows(cfg, data, meta, {t["id"]: t["title"] for t in cfg["topics"]}), "geo": geo, "geo_source": "Ländergrenzen: © GeoBasis-DE / BKG (VG2500), Datenlizenz Deutschland – Namensnennung – Version 2.0",
            "site": cfg["site"], "stand": stand, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "questions": questions, "topics": topics, "overview": overview({q["id"]: q["answer"] for q in questions}),
            "content_license": cfg["site"].get("license", "")}


def build_site(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out or root / "site"
    out.mkdir(parents=True, exist_ok=True)
    payload = build_payload(root)
    from .downloads import write_all
    from .reuse import mark_revisions, news, update_archive, write_all_series, write_feed

    write_all(payload, out)
    data, _ = load_observations(root)
    meta, _ = _series_meta(root / "series.yaml")
    stand_de = f"{payload['stand'][8:10]}.{payload['stand'][5:7]}.{payload['stand'][:4]}"
    cite = f"{payload['site']['author']} ({payload['stand'][:4]}): Konjunkturmonitor. Stand {stand_de}. {payload['site']['url']}"
    payload["all_series"] = write_all_series(data, meta, root, out, stand_de, cite)
    arch = update_archive(root, payload["start"], payload["stand"])
    mark_revisions(payload["start"], arch)
    items = news(arch, payload["stand"])
    payload["news"] = [i for i in items if i["stand"] == payload["stand"]]
    write_feed(items, payload["start"], payload["site"], out)
    (out / "dl").mkdir(exist_ok=True)
    arch.to_csv(out / "dl" / "kernzahlen_archiv.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
    tpl = resources.files("monitor").joinpath("templates/index.html").read_text(encoding="utf-8")
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    from html import escape
    url = payload["site"].get("url", "")
    desc = payload.get("overview") or payload["site"].get("claim", "")
    html = (tpl.replace("/*__DATA__*/null", js).replace("/*__STATIC__*/", static_table(payload["start"]))
            .replace("/*__OVERVIEW__*/", escape(payload.get("overview", ""))).replace("/*__DESC__*/", escape(desc, quote=True))
            .replace("/*__URL__*/", escape(url, quote=True)).replace("/*__OGIMG__*/", escape(url + "vorschau.png", quote=True)))
    (out / "index.html").write_text(html, encoding="utf-8")
    preview_image(payload, out / "vorschau.png")
    for page in ("impressum.html", "datenschutz.html"):
        (out / page).write_text(resources.files("monitor").joinpath(f"templates/{page}").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    plotly = resources.files("konjunkturwolf").joinpath("static/plotly.min.js")
    (out / "plotly.min.js").write_bytes(plotly.read_bytes())
    return out / "index.html"


def _fmt(v, d=1, sign=False) -> str:
    return num(float(v), d, sign=sign)


def static_table(rows: list[dict]) -> str:
    """Kernzahlen als schlichte HTML-Tabelle im Quelltext: lesbar ohne JavaScript, für Suchmaschinen und Vorschauen."""
    from html import escape

    if not rows:
        return ""
    out = ['<table class="stable"><thead><tr><th class="l">Kennzahl</th><th>Stand</th><th>Wert</th><th class="l">Einheit</th>'
           '<th>ggü. Vorperiode</th><th>ggü. Vorjahr</th></tr></thead><tbody>']
    for r in rows:
        cd = int(r.get("change_decimals", 1))
        ch = lambda v: "" if v is None else f"{_fmt(v, cd, True)} {r['change_unit']}"
        out.append(f'<tr><td><a href="#{escape(r["topic"])}">{escape(r["label"])}</a></td><td class="p">{escape(r["period"])}</td>'
                   f'<td class="v">{_fmt(r["value"], int(r.get("decimals", 1)))}</td><td class="u">{escape(r["unit"])}</td>'
                   f'<td class="d">{escape(ch(r["prev"]))}</td><td class="d">{escape(ch(r["yoy"]))}</td></tr>')
    return "".join(out) + "</tbody></table>"


def preview_image(payload: dict, path: Path) -> None:
    """Vorschaubild (1200 x 630) für Verweise in sozialen Netzen und Messengern: Titel, Stand und sechs Kernzahlen."""
    from PIL import Image, ImageDraw, ImageFont

    def font(size, bold=False):
        for name in (["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]):
            for d in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/liberation/", ""):
                try:
                    return ImageFont.truetype(d + name, size)
                except OSError:
                    continue
        return ImageFont.load_default(size)

    img = Image.new("RGB", (1200, 630), "#ffffff")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 1200, 12], fill="#002060")
    d.text((60, 50), "Konjunkturmonitor", font=font(54, True), fill="#002060")
    d.text((60, 122), f"Wie steht es um die deutsche Wirtschaft?  Stand {payload['stand'][8:10]}.{payload['stand'][5:7]}.{payload['stand'][:4]}",
           font=font(28), fill="#3f4752")
    pick = [r for r in payload.get("start", []) if r["series"] in ("de_gdp_index", "de_cpi_yoy", "de_alq_sa", "de_ip", "de_esi", "de_insolv")][:6]
    for k, r in enumerate(pick):
        x, y = 60 + (k % 3) * 370, 210 + (k // 3) * 200
        d.text((x, y), r["label"].split(" (")[0], font=font(26), fill="#3f4752")
        if r["kind"] == "level" and r.get("prev") is not None and r["series"] != "de_insolv":
            val, unit = _fmt(r["prev"], int(r.get("change_decimals", 1)), True) + " " + r["change_unit"], f"ggü. {r['prev_label']}"
        elif r["series"] == "de_insolv" and r.get("yoy") is not None:
            val, unit = _fmt(r["yoy"], 1, True) + " %", "ggü. Vorjahresmonat"
        else:
            val, unit = _fmt(r["value"], int(r.get("decimals", 1))) + (" %" if "%" in r["unit"] else ""), ""
        d.text((x, y + 36), val, font=font(60, True), fill="#002060")
        d.text((x, y + 108), r["period"], font=font(22), fill="#3f4752")
        if unit:
            d.text((x, y + 136), unit, font=font(22), fill="#3f4752")
    d.text((60, 590), payload["site"].get("url", ""), font=font(22), fill="#3f4752")
    img.save(path, optimize=True)


__all__ = ["build_payload", "build_site", "num"]
