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

from .answers import answer, num

ROOT = Path.cwd()

SOURCE_NAMES = {"bundesbank": "Deutsche Bundesbank", "eurostat": "Eurostat", "ecb": "EZB", "static": "BA-Statistik (aufbereitet)",
                "derived": "eigene Berechnung"}
SOURCE_LICENSES = {"bundesbank": "Wiederverwendung mit Quellenangabe (Deutsche Bundesbank)", "eurostat": "CC BY 4.0 (Eurostat)",
                   "ecb": "Wiederverwendung mit Quellenangabe (EZB)", "static": "Statistik der Bundesagentur für Arbeit, mit Quellenangabe"}


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
    """Monatswerte, 12-Monats-Mittel und das übliche Niveau desselben Monats 2016 bis 2019."""
    s = s.dropna()
    ma12 = s.rolling(12).mean()
    base = s[(s.index.year >= 2016) & (s.index.year <= 2019)]
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
    b = b[(b.index >= "2015-01-01") & (b.index < "2020-01-01")]
    if len(b) < 4:
        return None
    return {"lo": round(float(b.min()), 4), "hi": round(float(b.max()), 4), "mean": round(float(b.mean()), 4)}


def _start_rows(cfg: dict, data: dict) -> list[dict]:
    from .answers import period

    rows = []
    for r in cfg.get("start_table") or []:
        s = data.get(r["series"])
        if s is None or len(s.dropna()) < 7:
            continue
        s = s.dropna()
        q = s.index.to_series().diff().dt.days.median() > 60
        freq = "Q" if q else "M"
        show = r.get("show", "level")
        if show == "change":
            vals = s.diff()
        elif show == "pct3":
            vals = (s.rolling(3).mean() / s.rolling(3).mean().shift(3) - 1) * 100
        elif show == "yoy":
            vals = (s / s.shift(4 if q else 12) - 1) * 100
        else:
            vals = s
        vals = vals.dropna()
        if vals.empty:
            continue
        v, prev = float(vals.iloc[-1]), (float(vals.iloc[-2]) if len(vals) > 1 else None)
        band = _band(vals)
        rel = None
        if band:
            rel = "über der Spanne 2015 bis 2019" if v > band["hi"] else "unter der Spanne 2015 bis 2019" if v < band["lo"] else "innerhalb der Spanne 2015 bis 2019"
        spark = vals[vals.index >= vals.index[-1] - pd.DateOffset(years=5)]
        rows.append(dict(r, value=round(v, 4), prev=None if prev is None else round(prev, 4), period=period(vals.index[-1], freq),
                         band=band, rel=rel, spark={"x": [d.strftime("%Y-%m-%d") for d in spark.index], "y": [round(float(x), 4) for x in spark]}))
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
                entry.update(heat=h, unit="% gegenüber Vorjahresmonat", freq="M", adjustment="saison- und kalenderbereinigt (Bundesbank)",
                             sources=["Deutsche Bundesbank (Produktionsindex des Statistischen Bundesamts)"], licenses=[SOURCE_LICENSES["bundesbank"]])
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
                    series.append(dict(id=s.id, label=s.label or s.title, unit=s.unit, freq=s.frequency,
                                       style=getattr(s, "style", None) or "line", **_xy(data[s.id], c.get("years"))))
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
    no = 0
    for t in topics:
        for c in t["charts"]:
            no += 1
            c["no"] = no
    geo = _geo(root)
    return {"layout": layout, "start": _start_rows(cfg, data), "geo": geo, "geo_source": "Ländergrenzen: © GeoBasis-DE / BKG (VG2500), Datenlizenz Deutschland – Namensnennung – Version 2.0",
            "site": cfg["site"], "stand": stand, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "questions": questions, "topics": topics}


def build_site(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out or root / "site"
    out.mkdir(parents=True, exist_ok=True)
    payload = build_payload(root)
    from .downloads import write_all

    write_all(payload, out)
    tpl = resources.files("monitor").joinpath("templates/index.html").read_text(encoding="utf-8")
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    (out / "index.html").write_text(tpl.replace("/*__DATA__*/null", js), encoding="utf-8")
    (out / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    plotly = resources.files("konjunkturwolf").joinpath("static/plotly.min.js")
    (out / "plotly.min.js").write_bytes(plotly.read_bytes())
    return out / "index.html"


__all__ = ["build_payload", "build_site", "num"]
