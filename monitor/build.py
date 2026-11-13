"""Seite des Konjunkturmonitors aus den Beobachtungen der Pipeline bauen."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .answers import answer, fazit, num, overview

ROOT = Path.cwd()

SOURCE_NAMES = {"bundesbank": "Deutsche Bundesbank", "eurostat": "Eurostat", "genesis": "Statistisches Bundesamt (GENESIS)", "fred": "FRED (Federal Reserve Bank of St. Louis)", "ecb": "EZB", "static": "BA-Statistik (aufbereitet)",
                "derived": "eigene Berechnung"}
SOURCE_LICENSES = {"genesis": "Datenlizenz Deutschland – Namensnennung – Version 2.0 (Statistisches Bundesamt)", "bundesbank": "Wiederverwendung mit Quellenangabe (Deutsche Bundesbank)", "eurostat": "CC BY 4.0 (Eurostat)",
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


def _xy(s: pd.Series, years: int | None, start: str | None = None) -> dict:
    """Werte ab start (Jahresanfang, siehe layout.window_start), sonst die letzten years Jahre."""
    s = s.dropna()
    if start == "year" and years and len(s):  # lange Fenster: rund years Jahre, ab Anfang des Startjahrs
        s = s[s.index.year >= (s.index[-1] - pd.DateOffset(years=years)).year]
    elif start:
        s = s[s.index >= start]
    elif years:
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


def _tiles(prefix: str, data: dict, meta: dict, months: int = 12, measure: str = "sum") -> dict | None:
    """Veränderung der letzten `months` Monate gegenüber demselben Zeitraum ein Jahr zuvor, je Land.
    measure "diff": jüngster Wert einer Quote je Land (level) und Veränderung zum vorigen Wert in Prozentpunkten (change)."""
    if measure == "diff":
        rows, last = [], None
        for code, abbr in LAND_ABBR.items():
            s = data.get(f"{prefix}{code}")
            if s is None or len(s.dropna()) < 2:
                continue
            s = s.dropna()
            last = s.index[-1] if last is None else max(last, s.index[-1])
            rows.append({"code": code, "abbr": abbr, "name": meta[f"{prefix}{code}"].label, "level": round(float(s.iloc[-1]), 1),
                         "change": round(float(s.iloc[-1] - s.iloc[-2]), 1), "sum": round(float(s.iloc[-1]), 1)})
        if not rows:
            return None
        return {"rows": rows, "span": str(last.year), "months": None, "last": last.strftime("%Y-%m-%d"), "measure": "diff"}
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
    return {"rows": rows, "span": span, "months": months, "last": last.strftime("%Y-%m-%d")}


def _forecasts(root: Path) -> list[dict]:
    """Prognosen je Herausgeber und Runde; die jüngste Runde je Herausgeber ist als latest markiert."""
    path = root / "data" / "static" / "prognosen.yaml"
    if not path.exists():
        return []
    conv = lambda m: {int(k): float(v) for k, v in m.items()}
    rows = [dict(r, date=str(r["date"]), **{k: conv(r[k]) for k in ("values", "inflation", "core") if r.get(k)})
            for r in (yaml.safe_load(path.read_text(encoding="utf-8")) or [])]
    newest = {}
    for r in rows:
        if r["by"] not in newest or r["date"] > newest[r["by"]]:
            newest[r["by"]] = r["date"]
    return sorted((dict(r, latest=r["date"] == newest[r["by"]]) for r in rows), key=lambda r: r["date"])


def _projection(c: dict, data: dict, root: Path) -> dict | None:
    """Abgleich mit der jüngsten Projektion der Bundesregierung für das Jahr des jüngsten BIP-Quartals.

    Die Jahresrate der Projektion ist unbereinigt. Sie entspricht näherungsweise dem gewogenen Mittel der unbereinigten
    Raten ggü. Vorjahresquartal, gewichtet mit dem Anteil jedes Quartals am Vorjahr (Gewichte aus dem bereinigten Index).
    Für die noch fehlenden Quartale folgt daraus die gleiche Rate je Quartal, die das Jahresziel gerade erreicht.
    """
    yoy_id, idx_id = c.get("yoy", "de_gdp_yoy"), c.get("index", "de_gdp_index")
    if yoy_id not in data or idx_id not in data:
        return None
    yoy, idx = data[yoy_id].dropna(), data[idx_id].dropna()
    year = int(yoy.index[-1].year)
    rounds = [f for f in _forecasts(root) if f["by"] == "Bundesregierung" and year in (f.get("values") or {})]
    if not rounds:
        return None
    rounds.sort(key=lambda f: f["date"])
    cur, prev = rounds[-1], (rounds[-2] if len(rounds) > 1 else None)
    target = float(cur["values"][year])
    base = idx[idx.index.year == year - 1]
    if len(base) != 4:
        return None
    w = {d.month: float(v) / float(base.sum()) for d, v in base.items()}  # Anteil je Quartal am Vorjahr
    known = yoy[yoy.index.year == year]
    done = sum(w[d.month] * float(v) for d, v in known.items())
    rest = [m for m in (1, 4, 7, 10) if m not in {d.month for d in known.index}]
    need = (target - done) / sum(w[m] for m in rest) if rest else None
    need_qoq = None
    if rest:  # bereinigt: nötiges Niveau im nächsten Quartal ggü. dem jüngsten bereinigten Stand, ohne Kalendereffekt
        nxt = pd.Timestamp(year=year, month=rest[0], day=1)
        ago = idx.get(nxt - pd.DateOffset(years=1))
        if ago is not None and idx.index[-1] == nxt - pd.DateOffset(months=3):
            need_qoq = (float(ago) * (1 + need / 100) / float(idx.iloc[-1]) - 1) * 100
    alt = None
    if "de_gdp_qoq" in data and rest and idx.index[-1] == pd.Timestamp(year=year, month=rest[0], day=1) - pd.DateOffset(months=3):
        # zweite Ansicht: bereinigt ggü. Vorquartal. Nötiges bereinigtes Niveau je fehlendem Quartal = Vorjahresquartal mal (1 + nötige Rate),
        # wie bei need_qoq; daraus die Raten ggü. dem jeweiligen Vorquartal
        prev_lv, path = float(idx.iloc[-1]), []
        for m in rest:
            ago = idx.get(pd.Timestamp(year=year - 1, month=m, day=1))
            if ago is None:
                path = []
                break
            lv = float(ago) * (1 + need / 100)
            path.append(round((lv / prev_lv - 1) * 100, 2))
            prev_lv = lv
        if path:
            q = data["de_gdp_qoq"].dropna()
            q = q[q.index.year >= year - 1]
            alt = {"label": "ggü. Vorquartal", "base": "ggü. Vorjahresquartal", "label_en": "on previous quarter", "base_en": "on same quarter a year earlier",
                   "unit": "% ggü. Vorquartal", "refs": [], "sub": "Vierteljährlich · preis-, saison- und kalenderbereinigt", "sub_en": "Quarterly · price, seasonally and calendar adjusted",
                   "series": [{"id": "de_gdp_qoq", "label": "BIP ggü. Vorquartal", "unit": "% ggü. Vorquartal", "freq": "Q", "style": "bar",
                               "x": [d.strftime("%Y-%m-%d") for d in q.index] + [f"{year}-{m:02d}-01" for m in rest],
                               "y": [round(float(v), 4) for v in q.values] + path, "req": len(rest)}]}
    hist = yoy[yoy.index.year >= year - 1]
    xs = [d.strftime("%Y-%m-%d") for d in hist.index] + [f"{year}-{m:02d}-01" for m in rest]
    ys = [round(float(v), 4) for v in hist.values] + [round(need, 2)] * len(rest)
    return {"year": year, "target": target, "round": cur["round"], "date": cur["date"], "source": cur.get("source"),
            "prev": {"round": prev["round"], "value": float(prev["values"][year])} if prev else None,
            "known": [{"q": (d.month + 2) // 3, "v": float(v)} for d, v in known.items()], "rest": [(m + 2) // 3 for m in rest],
            "need": need, "need_qoq": need_qoq, "done_rate": done if not rest else None,
            "last_qoq": float(data["de_gdp_qoq"].dropna().iloc[-1]) if "de_gdp_qoq" in data else None,
            "alt": alt,
            "series": [{"id": yoy_id, "label": "BIP ggü. Vorjahresquartal", "unit": "% ggü. Vorjahresquartal", "freq": "Q", "style": "bar",
                        "x": xs, "y": ys, "req": len(rest)}]}


def _diffusion(c: dict, data: dict, meta: dict) -> dict | None:
    """Breite: Anteil der Branchen, deren Dreimonatsdurchschnitt über dem der drei Monate davor liegt, in %.
    Ungewichtet: jede Branche zählt gleich, unabhängig von ihrer Größe."""
    series, counts = [], {}
    for label, chart in (c.get("groups") or {}).items():
        cols = {s.id: data[s.id].dropna() for s in meta.values() if s.chart_id == chart and s.id in data}
        if len(cols) < 5:
            continue
        w = pd.DataFrame(cols)
        m = w.rolling(3).mean()
        g = (m / m.shift(3) - 1) * 100
        n = g.notna().sum(axis=1)
        up = (g > 0).sum(axis=1)
        share = (up / n * 100)[n >= max(5, len(cols) // 2)].dropna()
        if share.empty:
            continue
        last, ago = share.index[-1], share.index[-1] - pd.DateOffset(years=1)
        counts[label] = {"up": int(up[last]), "n": int(n[last]), "period": last.strftime("%Y-%m-%d"),
                         "up_ago": int(up[ago]) if ago in up.index and n.get(ago, 0) else None, "n_ago": int(n[ago]) if ago in n.index else None,
                         "ma3": round(float(share.iloc[-3:].mean()), 1)}
        series.append(dict(id=f"diff_{chart}", label=f"{label} ({len(cols)} Branchen)", unit="% der Branchen", freq="M", style="line", **_xy(share, c.get("years"))))
    return {"series": series, "counts": counts} if series else None


def _merge_toggles(topics: list[dict]) -> None:
    """Abbildungen mit toggle: {chart, label, base} nehmen die genannte Abbildung als zweite Ansicht auf.
    Die zweite Abbildung verschwindet aus dem Abschnitt; Sätze, Quellen und Erläuterung beider stehen in der Karte."""
    where = {c["chart"]: t for t in topics for c in t["charts"] if c.get("chart")}
    for t in topics:
        for c in list(t["charts"]):
            tg = c.get("toggle")
            if not isinstance(tg, dict) or tg.get("chart") not in where:
                continue
            src = where[tg["chart"]]
            o = next((x for x in src["charts"] if x.get("chart") == tg["chart"]), None)
            if o is None or o is c:
                continue
            src["charts"].remove(o)
            c["variant"] = o
            c["texts"] = list(c.get("texts") or []) + list(o.get("texts") or [])
            c["text"] = " ".join(c["texts"])
            if o.get("caption"):
                c["caption"] = f"{c.get('caption', '')} Ansicht „{tg['label']}“: {o['caption']}".strip()
            for k in ("sources", "licenses"):
                c[k] = list(dict.fromkeys(list(c.get(k) or []) + list(o.get(k) or [])))


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
    """Richtung der jüngsten Veränderung: ↗ steigt, ↘ sinkt, → unverändert (in der angezeigten Genauigkeit)."""
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
            cunit = r.get("change_unit") or ("Pp" if "%" in r.get("unit", "") or r.get("unit", "").startswith(("Pp", "Saldo")) else "Pkt.")
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


def update_release_log(root: Path) -> pd.DataFrame:
    """Protokoll, wann der Monitor einen neuen Zeitraum je Reihe zum ersten Mal abgerufen hat (data/archive/erscheinen.csv).
    Beim ersten Lauf werden die vorhandenen Zeiträume ohne Datum eingetragen, weil ihr Erscheinungstag unbekannt ist."""
    path = root / "data" / "archive" / "erscheinen.csv"
    status = root / "data" / "processed" / "run_status.json"
    cols = ["series", "period", "first_seen"]
    log = pd.read_csv(path, dtype=str, keep_default_na=False) if path.exists() else pd.DataFrame(columns=cols)
    if not status.exists():
        return log
    first_run = not path.exists()
    today = pd.Timestamp.now(tz="Europe/Berlin").strftime("%Y-%m-%d")
    seen = set(zip(log["series"], log["period"]))
    new = []
    for s in json.loads(status.read_text(encoding="utf-8")).get("series", []):
        if s.get("status") not in ("ok", "cache") or not s.get("last"):
            continue
        key = (s["series_id"], str(s["last"]))
        if key not in seen:
            new.append({"series": key[0], "period": key[1], "first_seen": "" if first_run else today})
    if new:
        log = pd.concat([log, pd.DataFrame(new, columns=cols)], ignore_index=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        log.to_csv(path, index=False)
    return log


def _learned_rule(dates: list[pd.Timestamp]) -> dict | None:
    """Üblicher Erscheinungstag aus beobachteten Terminen: n-ter Werktag oder n Werktage vor Monatsende, je nachdem, was stabiler ist."""
    if len(dates) < 2:
        return None
    first, last = [], []
    for d in dates:
        wd = _workdays(d.year, d.month)
        days = [x.strftime("%Y-%m-%d") for x in wd]
        k = d.strftime("%Y-%m-%d")
        if k not in days:
            continue
        i = days.index(k)
        first.append(i + 1)
        last.append(len(days) - 1 - i)
    if len(first) < 2:
        return None
    spread = lambda v: max(v) - min(v)
    med = lambda v: int(sorted(v)[len(v) // 2])
    rule = {"workday": med(first)} if spread(first) <= spread(last) else {"last_workday": med(last)}
    return dict(rule, n=len(first))


def _calendar(root: Path, start: pd.Timestamp, months: int = 2, weeks: int | None = None) -> dict | None:
    path = root / "data" / "static" / "kalender.yaml"
    if not path.exists():
        return None
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    logp = root / "data" / "archive" / "erscheinen.csv"
    rel = pd.read_csv(logp, dtype=str, keep_default_na=False) if logp.exists() else pd.DataFrame(columns=["series", "period", "first_seen"])
    rel = rel[rel["first_seen"] != ""]
    for it in cfg.get("items") or []:  # gelernte Regel ersetzt die geschätzte, sobald mindestens zwei Erscheinungstage vorliegen
        ser = it.get("series") or []
        if not ser or rel.empty:
            continue
        days = sorted({pd.Timestamp(x) for x in rel.loc[rel["series"].isin(ser), "first_seen"]})
        lr = _learned_rule(days)
        if lr:
            it["rule"] = dict({k: v for k, v in (it.get("rule") or {}).items() if k == "months"}, **{k: v for k, v in lr.items() if k != "n"})
            it["learned"] = lr["n"]
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
                if weeks and not (start.normalize() <= d < start.normalize() + pd.Timedelta(weeks=weeks)):
                    continue
                events.append({"date": d.strftime("%Y-%m-%d"), "name": it["name"], "source": it.get("source", ""), "topic": it.get("topic"),
                               "charts": it.get("charts") or [], "estimated": not it.get("fixed"), "learned": it.get("learned", 0)})
    first = start.replace(day=1)
    return {"months": [(first + pd.DateOffset(months=k)).strftime("%Y-%m") for k in range(months)],
            "events": sorted(events, key=lambda e: e["date"]), "links": cfg.get("links") or []}


def _per(x: str, freq: str) -> str:
    from .answers import period
    if freq == "B":
        from .answers import MONTHS
        return f"{int(x[8:10])}. {MONTHS[int(x[5:7]) - 1]} {x[:4]}"
    return period(pd.Timestamp(x), freq) if freq in ("M", "Q") else (x[:4] if freq == "A" else f"Woche bis {x[8:10]}.{x[5:7]}.{x[:4]}")


def _when(x: str, freq: str) -> str:
    """Zeitangabe am Satzanfang: „Im September 2026“, „Im 3. Quartal 2026“, „Im Jahr 2025“, „In der Woche bis …“."""
    if freq == "A":
        return f"Im Jahr {x[:4]}"
    if freq == "D":
        return f"In der Woche bis zum {int(x[8:10])}.{int(x[5:7])}.{x[:4]}"
    if freq == "B":
        return f"Am {_per(x, freq)}"
    return f"Im {_per(x, freq)}"


def tidy(s: str) -> str:
    """Schreibweise der Seite: „ggü.“ statt „gegenüber (dem)“, „Pp“ statt „Prozentpunkte“, schmales geschütztes Leerzeichen vor %."""
    import re
    if not s:
        return s
    s = re.sub(r"(G|g)egenüber (dem |der |den )?(?=Vor|Durchschnitt|Mittel)", lambda m: m.group(1) + "gü. ", s)
    s = re.sub(r"(?<![\w])(G|g)egenüber ", lambda m: m.group(1) + "gü. ", s)
    s = re.sub(r"Prozentpunkte[n]?", "Pp", s)
    s = re.sub(r"(\d) ?%", "\\1\u202f%", s)
    s = s.replace("\u2212", "-")
    return s


def _last_x(c: dict) -> str | None:
    """Jüngster Zeitpunkt mit Wert in einer Abbildung."""
    if c.get("type") == "seasonal":
        return max((x for x, y in zip(c["x"], c["y"]) if y is not None), default=None)
    if c.get("type") in ("heat", "heatbars"):
        return c["heat"]["cols"][-1]
    if c.get("type") == "clock":
        return c["clock"]["t"][-1]
    if c.get("type") == "tiles":
        return c["tiles"].get("last")
    ss = [s for s in c.get("series") or [] if isinstance(s, dict) and s.get("x")]
    if c.get("type") == "stacked" and any(s.get("style") == "bar" for s in ss):
        ss = [s for s in ss if s.get("style") == "bar"]
    xs = [s["x"][-1] for s in ss]
    return max(xs) if xs else None


def _next_period(c: dict) -> str | None:
    """Zeitraum, für den die nächste Veröffentlichung voraussichtlich Daten bringt: der auf den jüngsten Wert folgende."""
    from .answers import MONTHS
    x = c.get("last_x")
    if not x:
        return None
    t, f = pd.Timestamp(x), c.get("freq", "M")
    if f == "Q":
        n = t + pd.DateOffset(months=3)
        return f"das {(n.month - 1) // 3 + 1}. Quartal {n.year}"
    if f == "A":
        return str(t.year + 1)
    if f in ("D", "B"):
        return None
    n = t + pd.DateOffset(months=1)
    return f"{MONTHS[n.month - 1]} {n.year}"


_SAETZE: dict = {}
ZAHLWORT = {2: "zwei", 3: "drei", 4: "vier", 5: "fünf", 6: "sechs", 7: "sieben", 8: "acht", 9: "neun", 10: "zehn", 11: "elf", 12: "zwölf"}


def load_saetze(root: Path) -> None:
    path = root / "data" / "static" / "saetze.yaml"
    _SAETZE.clear()
    if path.exists():
        _SAETZE.update(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def _subject(sid: str | None, label: str = "", chart: str = "") -> dict | None:
    """Satzgegenstand einer Reihe: {subj, pl} oder {tpl}; sonst None."""
    def conv(x):
        if isinstance(x, dict):
            return x
        if isinstance(x, list) and x:
            return {"subj": x[0].replace("{label}", label), "pl": len(x) > 1 and x[1] == "p"}
        return None
    if sid and sid in (_SAETZE.get("series") or {}):
        return conv(_SAETZE["series"][sid])
    if chart in (_SAETZE.get("charts") or {}):
        return conv(_SAETZE["charts"][chart])
    if label in (_SAETZE.get("labels") or {}):
        return conv(_SAETZE["labels"][label])
    return None


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _enso_comm(c: dict, data: dict) -> dict | None:
    """Rohstoffpreise nach El Niño: mittlere Veränderung ggü. Vorjahr, lag Monate nach Monaten mit El Niño
    (RONI >= 0,5) und nach neutralen Monaten (|RONI| < 0,5), seit dem ersten gemeinsamen Jahr.
    Unterschied mit Welch-t-Test; |t| > 1,96 gilt als deutlich (Näherung, aufeinanderfolgende Monate sind nicht unabhängig)."""
    roni = data.get("enso_roni")
    if roni is None:
        return None
    roni = roni.dropna()
    roni.index = roni.index.to_period("M").to_timestamp()
    lag, rows, first, last = int(c.get("lag", 6)), [], None, None
    for sid, label in (c.get("items") or {}).items():
        s = data.get(sid)
        if s is None or s.dropna().empty:
            continue
        s = s.dropna()
        s.index = s.index.to_period("M").to_timestamp()
        yoy = (s / s.reindex(s.index - pd.DateOffset(years=1)).values - 1) * 100
        ahead = pd.Series(yoy.values, index=yoy.index - pd.DateOffset(months=lag))  # Veränderung lag Monate später, am Ausgangsmonat
        df = pd.concat({"roni": roni, "chg": ahead}, axis=1).dropna()
        if len(df) < 120:
            continue
        nino, neut = df.loc[df.roni >= 0.5, "chg"], df.loc[df.roni.abs() < 0.5, "chg"]
        if len(nino) < 24 or len(neut) < 24:
            continue
        se = (nino.var() / len(nino) + neut.var() / len(neut)) ** 0.5
        t = (nino.mean() - neut.mean()) / se if se else 0.0
        first = min(first or df.index[0], df.index[0]); last = max(last or df.index[-1], df.index[-1])
        rows.append({"id": sid, "label": label, "nino": round(float(nino.mean()), 2), "neutral": round(float(neut.mean()), 2),
                     "n_nino": int(len(nino)), "n_neutral": int(len(neut)), "t": round(float(t), 2), "sig": bool(abs(t) > 1.96)})
    if len(rows) < 3:
        return None
    rows.sort(key=lambda r: r["nino"] - r["neutral"])
    print("Rohstoffe nach El Niño (% ggü. Vorjahr, El Niño / neutral / t):",
          "; ".join(f"{r['label']} {r['nino']:+.1f} / {r['neutral']:+.1f} / {r['t']:+.1f}" for r in reversed(rows)))
    return {"rows": rows, "lag": lag, "from": first.strftime("%Y-%m"), "to": last.strftime("%Y-%m")}


def _und(xs: list[str]) -> str:
    return ", ".join(xs[:-1]) + " und " + xs[-1] if len(xs) > 1 else xs[0]


def chart_sentences(c: dict) -> list[str]:
    """Kopierfertige Sätze zum jüngsten Stand einer Abbildung. Jeder Satz steht für sich: Zeitraum, Größe, Wert, Vergleich."""
    from .answers import MONTHS
    from .answers import num as _num
    if c.get("heute"):  # Gremien: zuerst die jüngste Empfehlung, dann der feste Satz
        from .gremien import heute
        return [x for x in [heute(c["heute"]["attach"], c["heute"]["who"])] + list(c.get("say") or []) if x]
    if c.get("say"):  # fester Satz aus monitor.yaml statt des automatischen
        return list(c["say"])
    from . import schulden
    if c.get("chart") in schulden.CHARTS:  # Schuldenstruktur: eigene Sätze
        return schulden.saetze(c, "de")
    typ, d = c.get("type"), int(c.get("decimals", 1))
    unit = (c.get("unit") or "").split(",")[0]
    unit = "Pp" if unit.startswith("Prozentpunkte") else unit  # Abstände in Prozentpunkten wie Pp behandeln
    is_rate = unit.startswith(("%", "Pp", "Saldo")) and not unit.startswith(("% des", "% der"))
    u = unit if unit.startswith(("% des", "% der")) else "%" if unit.startswith("%") else "Pp" if unit.startswith(("Pp", "Saldo")) else "" if unit.startswith("Index") else unit
    freq = c.get("freq", "M")
    prev_word = {"M": "Vormonat", "Q": "Vorquartal", "A": "Vorjahr", "D": "Vorwoche", "B": "Vortag"}.get(freq, "Vormonat")
    yoy_word = {"M": "Vorjahresmonat", "Q": "Vorjahresquartal", "A": "Vorjahr", "D": "Vorjahr", "B": "Vorjahr"}.get(freq, "Vorjahr")

    def num(v, dd=1, sign=False):  # gerundete Null ohne Vorzeichen
        v = round(float(v), dd)
        return _num(0.0 if v == 0 else v, dd, sign)

    def val(v, dd=d, sign=False):
        return f"{num(v, dd, sign or unit.startswith('Saldo'))} {u}".strip()

    def name(s):
        lab = s.get("label") or ""
        return f"der Wert für „{lab}“" if lab else "der Wert"
    try:
        if c.get("pot_names"):  # Dynamik: BIP-Wachstum gegenüber der Spanne der Potenzialschätzungen
            bar = next(x for x in c["series"] if x.get("style") == "bar")
            lo, hi = (next(x for x in c["series"] if x.get("style") == st) for st in ("band_lo", "band_hi"))
            band = {d[:4]: (a, b) for d, a, b in zip(lo["x"], lo["y"], hi["y"])}
            y, g = bar["x"][-1][:4], bar["y"][-1]
            who = ", ".join(n.split("(")[-1].rstrip(")") for n in c["pot_names"])
            who = " und ".join(who.rsplit(", ", 1))
            out = []
            if y in band:
                a, b = band[y]
                cmp = "langsamer als" if g < a else "schneller als" if g > b else "etwa so schnell wie"
                out.append(f"{y} wuchs das BIP um {num(g, 1)} % und damit {cmp} das Produktionspotenzial nach den Schätzungen von {who} ({num(a, 1)} bis {num(b, 1)} %).")
            y1 = str(int(y) + 1)
            if y1 in band:
                a, b = band[y1]
                s1 = f"Für {y1} schätzen sie das Potenzialwachstum auf {num(a, 1)} bis {num(b, 1)} %"
                gv = (c.get("gov_values") or {}).get(y1)
                out.append(s1 + (f"; die {c['gov_round']} der Bundesregierung erwartet ein BIP-Wachstum von {num(gv, 1)} %." if gv is not None else "."))
            return out
        if c.get("annual_count"):  # Zählreihen: Summe im jüngsten vollständigen Jahr und im Jahr davor
            ac, sums = c["annual_count"], []
            for s in c["series"]:
                if s.get("id") not in ac["series"]:
                    continue
                by = {}
                for x, y in zip(s["x"], s["y"]):
                    if y is not None:
                        by.setdefault(int(x[:4]), []).append(y)
                sums.append((ac["series"][s["id"]], by))
            full = [y for y in sums[0][1] if len(sums[0][1][y]) == ac.get("per_year", 4)]
            if not full:
                return []
            y = max(full)
            now = _und([f"{num(sum(by.get(y, [0])), 0)} {ph}" for ph, by in sums])
            out = f"Im Jahr {y} {ac['verb']} {now}"
            if y - 1 in sums[0][1]:
                out += ", nach " + _und([num(sum(by.get(y - 1, [0])), 0) for _, by in sums]) + f" im Jahr {y - 1}"
            return [out + "."]
        if c.get("diff"):  # Breite: Zahl der Branchen mit Zuwachs
            parts = []
            for label, k in c["diff"].items():
                inv = {"Produktion": ("wuchs die Produktion", "die Produktion wuchs"), "Auftragseingang": ("stieg der Auftragseingang", "der Auftragseingang stieg")}
                verb = inv.get(label, (f"stieg {label}", f"{label} stieg"))[0 if not parts else 1]  # nach Semikolon Subjekt zuerst
                ago = f", ein Jahr zuvor in {k['up_ago']}" if k.get("up_ago") is not None else ""
                parts.append(f"{verb} in {k['up']} von {k['n']} Branchen{ago}")
            t = pd.Timestamp(max(k["period"] for k in c["diff"].values()))
            return [f"Im Dreimonatsvergleich bis {MONTHS[t.month - 1]} {t.year} " + "; ".join(parts) + "."]
        if c.get("proj"):  # Abgleich mit der Projektion der Bundesregierung
            p = c["proj"]
            qs = lambda l: f"im {l[0]}. Quartal" if len(l) == 1 else f"im {l[0]}. bis {l[-1]}. Quartal je" if len(l) > 2 else f"im {l[0]}. und {l[1]}. Quartal je"
            if p["rest"]:
                k = p["known"][-1] if p["known"] else None
                out = [f"Um die {p['round']} der Bundesregierung von {num(p['target'], 1)} % für {p['year']} zu erreichen, müsste das BIP {qs(p['rest'])} um "
                       f"{num(p['need'], 1)} % über dem Vorjahresquartal liegen" + (f"; im {k['q']}. Quartal waren es {num(k['v'], 1)} %." if k else ".")]
                if p.get("need_qoq") is not None and p.get("last_qoq") is not None:
                    out.append(f"Saison- und kalenderbereinigt entspräche das im {p['rest'][0]}. Quartal einem Anstieg ggü. dem Vorquartal um "
                               f"{num(p['need_qoq'], 1)} %; zuletzt waren es {num(p['last_qoq'], 1)} %.")
            else:
                out = [f"Nach den vier Quartalen wuchs das BIP {p['year']} um etwa {num(p['done_rate'], 1)} %; die {p['round']} der Bundesregierung erwartete {num(p['target'], 1)} %."]
            if p.get("prev"):
                out.append(f"Die {p['prev']['round']} hatte für {p['year']} {num(p['prev']['value'], 1)} % erwartet.")
            return out
        if typ == "tiles" and c["tiles"].get("measure") == "diff":
            w = c["tiles"]
            loc = lambda n: {"Saarland": "im Saarland"}.get(n, "in " + n)
            hi, lo = max(w["rows"], key=lambda r: r["level"]), min(w["rows"], key=lambda r: r["level"])
            up = max(w["rows"], key=lambda r: r["change"])
            out = [f"Im Jahr {w['span']} war die {c.get('what') or 'Quote'} {loc(hi['name'])} mit {num(hi['level'], 1)} % am höchsten und {loc(lo['name'])} mit {num(lo['level'], 1)} % am niedrigsten."]
            if up["change"] > 0:
                out.append(f"Am stärksten gestiegen ist sie im Jahr {w['span']} {loc(up['name'])}: um {num(up['change'], 1)} Pp ggü. dem Vorjahr.")
            return out
        if typ == "tiles":
            w = c["tiles"]
            big = sorted(w["rows"], key=lambda r: r.get("sum") or 0)[len(w["rows"]) // 2:] if all(r.get("sum") is not None for r in w["rows"]) else w["rows"]
            rows = sorted(big, key=lambda r: r["change"])  # nur die größere Hälfte der Länder: Prozentwerte kleiner Länder beruhen auf wenigen Fällen
            what, noun = c.get("what") or "Zahl", c.get("count_noun") or "Fälle"
            cnt = lambda r: f" ({int(r['sum']):,} {noun})".replace(",", ".") if r.get("sum") is not None else ""
            dat = noun if noun.endswith("n") else noun + "n"  # Dativ Plural
            pre = f"{w['span']}, unter den {ZAHLWORT.get(len(big), len(big))} Ländern mit den meisten {dat}: " if len(big) < len(w["rows"]) else f"{w['span']}: "
            out = [f"{pre}Den stärksten Anstieg ggü. demselben Zeitraum ein Jahr zuvor verzeichnete {rows[-1]['name']} mit {num(rows[-1]['change'], 1, True)} %{cnt(rows[-1])}."]
            low = rows[0]
            loc = lambda n: {"Saarland": "im Saarland"}.get(n, "in " + n)
            out.append(f"Am {'stärksten gesunken' if low['change'] < 0 else 'wenigsten gestiegen'} ist die {what} {loc(low['name'])} mit {num(low['change'], 1, True)} %{cnt(low)}.")
            return out
        if typ == "enso_comm" and c.get("enso"):
            E = c["enso"]
            und = lambda xs: ", ".join(xs[:-1]) + " und " + xs[-1] if len(xs) > 1 else xs[0]
            up = [r["label"] for r in reversed(E["rows"]) if r["sig"] and r["nino"] > r["neutral"]]
            dn = [r["label"] for r in E["rows"] if r["sig"] and r["nino"] < r["neutral"]]
            span = f"Von {E['from'][:4]} bis {E['to'][:4]}"
            out = [f"{span} stiegen die Preise von {und(up)} {E['lag']} Monate nach El-Niño-Monaten deutlich stärker als nach neutralen Monaten." if up else
                   f"{span} stiegen die Preise {E['lag']} Monate nach El-Niño-Monaten bei keinem der Rohstoffe deutlich stärker als nach neutralen Monaten."]
            if dn:
                out.append(f"Bei {und(dn)} war der Anstieg nach El Niño deutlich schwächer.")
            top = E["rows"][-1]
            if top["nino"] > top["neutral"]:
                out.append(f"Den größten Vorsprung nach El Niño zeigt {top['label']}: {num(top['nino'], 1, True)} % ggü. Vorjahr nach El Niño, {num(top['neutral'], 1, True)} % nach neutralen Monaten.")
            return out
        if typ == "event" and c.get("kind") == "history":
            out = []
            for p in c["event"]["panels"]:
                cur = next((l for l in p["lines"] if l["current"]), None)
                if not cur or len(cur["y"]) < 2 or cur["y"][-1] is None:
                    continue
                k, v, pk = len(cur["y"]) - 1, cur["y"][-1], cur["start"][:4]
                old = [l for l in p["lines"] if not l["current"] and len(l["y"]) > k and l["y"][k] is not None]
                cmp = "; zum selben Zeitpunkt " + ", ".join(f"{l['label']} {num(l['y'][k] - p['base'], 1, True)} {'Pp' if p['unit'] == 'Pp' else '%'}" for l in old) if old else ""
                if p.get("mode") == "level":
                    out.append(f"{k} {'Jahr' if k == 1 else 'Jahre'} nach dem Inflationshoch {pk} lag die Inflationsrate bei {num(v, 1)} %{cmp.replace(' %', ' %').replace('+', '')}.")
                elif p["unit"] == "Pp":
                    out.append(f"Seit dem Hoch {pk} ist die Erwerbslosenquote um {num(abs(v), 1)} Pp {'gestiegen' if v > 0 else 'gesunken'} ({k} {'Jahr' if k == 1 else 'Jahre'}){cmp}.")
                else:
                    out.append(f"{k} {'Jahr' if k == 1 else 'Jahre'} nach dem Hoch {pk} lag das reale BIP {num(abs(v - 100), 1)} % {'unter' if v < 100 else 'über'} dem Hoch{cmp}.")
            return out
        if typ == "event" and c.get("kind") == "downturn":
            out = []
            for p in c["event"]["panels"]:
                cur = next((l for l in p["lines"] if l["current"]), None)
                if not cur or len(cur["y"]) < 2:
                    continue
                k, v, st = len(cur["y"]) - 1, cur["y"][-1], pd.Timestamp(cur["start"])
                step = "Quartal" if p["step"] == "Quartal" else "Monat"
                span = f"{k} {step}{'' if k == 1 else ('e' if step == 'Quartal' else 'e')}"
                if p["unit"] == "Pp":
                    s = f"Seit dem Hoch der Produktion im {MONTHS[st.month - 1]} {st.year} ist die Arbeitslosenquote um {num(abs(v), 1)} Pp {'gestiegen' if v > 0 else 'gesunken'} ({span})."
                else:
                    s = f"{span} nach dem Hoch im {MONTHS[st.month - 1] if step == 'Monat' else str((st.month - 1) // 3 + 1) + '. Quartal'} {st.year} lag {'die Industrieproduktion' if 'Industrie' in p['title'] else 'das BIP'} {num(abs(v - 100), 1)} % {'unter' if v < 100 else 'über'} dem Hoch."
                old = [l for l in p["lines"] if not l["current"] and len(l["y"]) > k]
                if old:
                    s = s[:-1] + "; zum selben Zeitpunkt " + ", ".join(f"{l['label']} {num(l['y'][k] - p['base'], 1, True)} {'Pp' if p['unit'] == 'Pp' else '%'}" for l in old) + "."
                out.append(s)
            return out
        if typ == "event":
            out = []
            for p in c["event"]["panels"]:
                what = "die realen Nahrungsmittelpreise" if "Nahrungs" in p["title"] else "die realen Erzeugerpreise landwirtschaftlicher Produkte"
                cur = next((l for l in p["lines"] if l["current"]), None)
                if cur and len(cur["y"]) > 4:
                    m = len(cur["y"]) - 5
                    v = cur["y"][-1] - 100
                    st = pd.Timestamp(cur["start"])
                    out.append(f"Seit Beginn des laufenden El Niño im {MONTHS[st.month - 1]} {st.year} sind {what} in Deutschland "
                               f"{'um ' + num(abs(v), 1) + ' % gestiegen' if v > 0.05 else 'um ' + num(abs(v), 1) + ' % gesunken' if v < -0.05 else 'kaum verändert'} "
                               f"({m} {'Monat' if m == 1 else 'Monate'} nach Beginn).")
                ref = next((l for l in p["lines"] if l["label"].startswith("2015")), None)
                if ref and cur and len(cur["y"]) > 4 and len(ref["y"]) >= len(cur["y"]) and ref["y"][len(cur["y"]) - 1] is not None:
                    v = ref["y"][len(cur["y"]) - 1] - 100  # zum selben Zeitpunkt wie das laufende Ereignis
                    m = len(cur["y"]) - 5
                    out.append(f"Nach dem sehr starken El Niño von 2015/16 lagen {what} zum selben Zeitpunkt ({m} {'Monat' if m == 1 else 'Monate'} nach Beginn) {num(abs(v), 1)} % {'höher' if v >= 0 else 'niedriger'} als zu Beginn.")
            return out
        if typ == "heatbars":
            rows = c["heat"]["rows"]
            per = _per(c["heat"]["cols"][-1], "M")
            lv = sorted([r for r in rows if r.get("level") is not None], key=lambda r: r["level"])
            if not lv:
                return []
            below = sum(1 for r in lv if r["level"] < 0)
            m3 = sorted([r for r in rows if r.get("m3") is not None], key=lambda r: r["m3"])
            first = [f"In den drei Monaten bis {per} legte die Branche „{m3[-1]['label']}“ am stärksten zu ({num(m3[-1]['m3'], 1, True)} % ggü. den drei Monaten davor), "
                     f"„{m3[0]['label']}“ entwickelte sich am schwächsten ({num(m3[0]['m3'], 1, True)} %)."] if m3 else []
            return first + [f"Im {per} lagen {below} von {len(lv)} Branchen unter ihrem Durchschnitt des Jahres 2019, dem letzten vollen Jahr vor der Pandemie.",
                    f"Am weitesten über dem Stand von 2019 lag im {per} die Branche „{lv[-1]['label']}“ ({num(lv[-1]['level'], 1, True)} %), am weitesten darunter „{lv[0]['label']}“ ({num(lv[0]['level'], 1, True)} %)."]
        if typ == "heat":
            rows = c["heat"]["rows"]
            last = c["heat"]["cols"][-1]
            per = _per(last, "M")
            vol = lambda r: " (von Großaufträgen geprägt, stark schwankend)" if r["label"] in (c.get("volatile") or []) else ""
            out = [f"In den drei Monaten bis {per} wuchs die Branche „{rows[-1]['label']}“{vol(rows[-1])} am stärksten: {num(rows[-1]['m3'], 1, True)} % ggü. den drei Monaten davor.",
                   f"In den drei Monaten bis {per} entwickelte sich die Branche „{rows[0]['label']}“ am schwächsten: {num(rows[0]['m3'], 1, True)} % ggü. den drei Monaten davor."]
            return out
        if typ == "clock":
            k = c["clock"]
            x, y, t0 = k["x"][-1], k["y"][-1], pd.Timestamp(k["t"][-1])
            phase = "Boom" if x >= 0 and y >= 0 else "Abschwung" if x >= 0 else "Aufschwung" if y >= 0 else "Rezession"
            when = f"Im {MONTHS[t0.month - 1]} {t0.year}"
            return [f"{when} stand die Industrie in der Konjunkturuhr im Feld „{phase}“.",
                    f"{when} bewerteten die Industrieunternehmen ihre Aufträge {'besser' if x >= 0 else 'schlechter'} als im Mittel 2005 bis 2019 (Saldo {num(x, 1, True)} Pp).",
                    f"{when} erwarteten die Industrieunternehmen für die nächsten drei Monate eine {'stärkere' if y >= 0 else 'schwächere'} Produktion als im Mittel 2005 bis 2019 (Saldo {num(y, 1, True)} Pp)."]
        if typ == "seasonal":
            i = max(k for k, v in enumerate(c["y"]) if v is not None)
            su = "" if c.get("unit") in ("Anzahl", None, "") else " " + c["unit"]
            lab = c.get("label") or c.get("title", "")
            when = f"Im {_per(c['x'][i], 'M')}"
            sp = _subject(c.get("series") if isinstance(c.get("series"), str) else None, lab) or {"subj": f"der Wert für „{lab}“", "pl": False}
            subj, lv = sp["subj"], "lagen" if sp["pl"] else "lag"
            out = [f"{when} {lv} {subj} bei {num(c['y'][i], d)}{su}."]
            if c["ma12"][i] is not None:
                out.append(f"In den zwölf Monaten bis {_per(c['x'][i], 'M')} {lv} {subj} im Mittel bei {num(c['ma12'][i], d)}{su} je Monat.")
            if c["norm"][i] is not None:
                m = MONTHS[int(c['x'][i][5:7]) - 1]
                out.append(f"Vor der Pandemie (2015 bis 2019) {lv} {subj} in einem {m} im Schnitt bei {num(c['norm'][i], d)}{su}.")
            return out
        if typ == "latest":
            b = c["bars"]
            if c.get("base"):  # Veränderung seit einem Stichtag, etwa Erwerbstätige je Bereich
                base = _per(c["base"], freq)
                bs = sorted(b, key=lambda x: x["value"])
                pc = lambda x: f" ({num(x['pct'], 1, True)} %)" if x.get("pct") is not None else ""
                out = [f"Vom {base} bis zum {_per(bs[-1]['period'], freq)} stieg die Zahl der Erwerbstätigen im Bereich „{bs[-1]['label']}“ am stärksten: um {num(bs[-1]['value'], d)} {u}{pc(bs[-1])}."]
                if bs[0]["value"] < 0:
                    out.append(f"Vom {base} bis zum {_per(bs[0]['period'], freq)} sank die Zahl der Erwerbstätigen im Bereich „{bs[0]['label']}“ am stärksten: um {num(abs(bs[0]['value']), d)} {u}{pc(bs[0])}.")
                return out
            when = _when(b[0]["period"], freq)
            if isinstance(c.get("combine"), dict):  # alle Balken in einem Satz
                items = [f"{x['label']} {num(x['value'], d, True)} %" for x in b]
                return [f"{when} {c['combine']['lead']} " + (", ".join(items[:-1]) + " und " + items[-1] if len(items) > 1 else items[0]) + "."]
            out = []
            for x in b:
                v = x["value"]
                sx = _subject(None, x["label"]) or {"subj": f"der Wert für „{x['label']}“", "pl": False}
                pl = sx["pl"]
                verb = ("stiegen" if pl else "stieg") if v > 0.05 else ("sanken" if pl else "sank") if v < -0.05 else ("veränderten sich kaum" if pl else "veränderte sich kaum")
                tail = f" um {num(abs(v), d)} %" if "kaum" not in verb else f" ({num(v, d, True)} %)"
                out.append(f"{when} {verb} {sx['subj']}{tail} ggü. dem {prev_word}.")
            return out
        if typ == "forecast":
            fs = c.get("forecasts") or []
            what = {"gdp": "ein Wachstum des realen BIP", "inflation": "eine Inflationsrate", "core": "eine Kerninflationsrate"}.get(c.get("measure", "gdp"))
            out = []
            gov = sorted([f for f in fs if f["by"] == "Bundesregierung"], key=lambda f: f["date"])
            years = sorted({int(k) for f in fs for k in f["values"] if int(k) >= datetime.now().year})
            if gov:
                g = gov[-1]
                ys = [y for y in years if y in g["values"]]
                if ys:
                    vs = [f"{num(g['values'][y], 1)} % für {y}" for y in ys]
                    out.append(f"Die Bundesregierung erwartet in ihrer {g['round']} {what} von " + (vs[0] if len(vs) == 1 else ", ".join(vs[:-1]) + " und " + vs[-1]) + ".")
            for y in years:
                latest = {}
                for f in sorted(fs, key=lambda f: f["date"]):
                    if y in f["values"]:
                        latest[f["by"]] = f["values"][y]
                if len(latest) < 2:
                    continue
                v = sorted(latest.values())
                out.append(f"Die jüngsten Prognosen von {ZAHLWORT.get(len(v), len(v))} Institutionen für {y} reichen von {num(v[0], 1)} bis {num(v[-1], 1)} %.")
            return out
        if typ == "calendar" or not c.get("series"):
            return []
        series = [s for s in c["series"] if s.get("y")]
        if typ == "stacked":  # Stichtag ist das jüngste Quartal mit Beiträgen (die Rate liegt oft früher vor)
            bars0 = [s for s in series if s.get("style") == "bar"]
            last = max(s["x"][-1] for s in bars0) if bars0 else max(s["x"][-1] for s in series)
            bars = [s for s in bars0 if last in s["x"]]
            tot = [s for s in series if s.get("style") != "bar" and last in s["x"]]
            at = lambda s: s["y"][s["x"].index(last)]
            when = _when(last, freq)
            whole = c.get("whole") or ("das Wachstum des BIP" if "gdp" in c.get("chart", "") else "die Rate insgesamt")
            if tot and "gdp" in c.get("chart", ""):
                g = at(tot[0])
                out = [f"{when} {'wuchs' if g > 0.05 else 'schrumpfte' if g < -0.05 else 'stagnierte'} das reale BIP{' um ' + num(abs(g), d) + ' % ggü. dem Vorquartal' if abs(g) > 0.05 else ''}."]
            elif tot and c.get("chart") == "cpi_contrib":
                out = [f"{when} lag die Inflationsrate bei {num(at(tot[0]), d)} % ggü. dem Vorjahresmonat."]
            elif tot:
                out = [f"{when} lag die Rate insgesamt bei {num(at(tot[0]), d)} %."]
            else:
                out = []
            if bars:
                hi, lo = max(bars, key=at), min(bars, key=at)
                sh = _subject(None, hi["label"]) or {"subj": f"„{hi['label']}“", "pl": False}
                out.append(f"{when} {'trugen' if sh['pl'] else 'trug'} {sh['subj']} am meisten bei: {num(at(hi), d, True)} Pp.")
                if round(at(lo), d) < 0:
                    sl = _subject(None, lo["label"]) or {"subj": f"„{lo['label']}“", "pl": False}
                    out.append(f"{when} {'dämpften' if sl['pl'] else 'dämpfte'} {sl['subj']} am stärksten: {num(at(lo), d, True)} Pp.")
            return out
        if c.get("mad_band"):  # Korrekturen: mittlere absolute Korrektur, größte Korrektur, jüngstes Quartal
            rv = next((s for s in series if s.get("style") == "bar"), None)
            hv = {s["id"]: s for s in series if s.get("style") == "hover"}
            if rv and rv["y"]:
                pts = [(x, v) for x, v in zip(rv["x"], rv["y"]) if v is not None]
                m = sum(abs(v) for _, v in pts) / len(pts)
                xb, vb = max(pts, key=lambda p: abs(p[1]))
                out = [f"Vom {_per(pts[0][0], freq)} bis zum {_per(pts[-1][0], freq)} wurde das BIP-Wachstum eines Quartals nachträglich im Mittel um {num(m, 2)} Pp korrigiert, "
                       f"am stärksten im {_per(xb, freq)} ({num(vb, 1, True)} Pp)."]
                f0, l0 = hv.get("gdp_rt_first"), hv.get("gdp_rt_latest")
                if f0 and l0 and f0["x"][-1] == l0["x"][-1]:
                    out.append(f"Für das {_per(f0['x'][-1], freq)} lag die erste Meldung bei {num(f0['y'][-1], 1)} %, der heutige Stand bei {num(l0['y'][-1], 1)} %; junge Quartale sind meist noch wenig überarbeitet.")
                return out
        norm = next((s for s in series if s.get("style") == "norm"), None)
        series = [s for s in series if s.get("style") != "norm"]
        if c.get("emphasis"):
            series = [s for s in series if s["id"] == c["emphasis"]] or series
        cb = c.get("combine")
        if isinstance(cb, dict):  # gleich gebaute Reihen in einem Satz, etwa Länder oder Bereiche
            last = min(s["x"][-1] for s in series) if cb.get("common") else max(s["x"][-1] for s in series)  # common: jüngster Zeitraum, den alle haben
            sym = "%" if unit.startswith("%") else "Pp" if unit.startswith(("Pp", "Saldo")) else u
            at = lambda s: s["y"][s["x"].index(last)] if last in s["x"] else None
            items = [f"{cb.get('pre', '')}{s.get('label', '')} {num(at(s), d, cb.get('sign', True))} {sym}".strip() for s in series if at(s) is not None]
            if items:
                return [f"{_when(last, freq)} {cb['lead']} " + (", ".join(items[:-1]) + " und " + items[-1] if len(items) > 1 else items[0]) + "."]
        if c.get("combine") and unit.startswith("Index"):  # gleich gebaute Reihen, etwa Branchen: ein Satz mit allen Werten
            last = max(s["x"][-1] for s in series)
            parts = []
            for s in series:
                if s["x"][-1] == last and len(s["y"]) > 12 and s["y"][-13]:
                    parts.append((re.sub(r"^\d+\s+", "", s.get("label", "")), (s["y"][-1] / s["y"][-13] - 1) * 100))
            if parts:
                below = sum(1 for _, p in parts if round(p, 1) < 0)
                n = ZAHLWORT.get(len(parts), len(parts))
                return [f"{_when(last, freq)} lag die Produktion in {ZAHLWORT.get(below, below) if below else 'keiner'} von {n} {c['combine']} unter dem Stand des {yoy_word}s: "
                        + "; ".join(f"{lab} {num(p, 1, True)} %" for lab, p in parts) + "."]
        series = series[:6]
        last = max(s["x"][-1] for s in series)
        if c.get("forecast_after_bars"):  # Prognosejahre nicht als Ist-Werte berichten
            bars0 = [s for s in c["series"] if s.get("style") == "bar"]
            if bars0:
                last = max(s["x"][-1] for s in bars0)
                series = [dict(s, x=s["x"][:s["x"].index(last) + 1], y=s["y"][:s["x"].index(last) + 1]) for s in series if last in s["x"]]
        when = _when(last, freq)
        prev_lbl = {"M": "im Vormonat", "Q": "im Vorquartal", "A": "im Vorjahr", "D": "in der Vorwoche", "B": "am Vortag"}
        out = []
        for s in series:
            if s["x"][-1] != last and not c.get("each_last"):
                continue
            when = _when(s["x"][-1], freq) if c.get("each_last") else _when(last, freq)  # each_last: jede Reihe mit ihrem jüngsten Stand
            v = s["y"][-1]
            f = s.get("freq", freq)
            lag = {"M": 12, "Q": 4, "A": 1, "D": 52}.get(f, 12)
            yago = s["y"][-1 - lag] if len(s["y"]) > lag else None
            if f == "B":  # Tageswerte: Wert ein Jahr zuvor nach Kalenderdatum
                ago = (pd.Timestamp(last) - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
                k = max((i for i, x in enumerate(s["x"]) if x <= ago), default=None)
                yago = s["y"][k] if k is not None else None
            su = s.get("unit") if c.get("own_scale") else unit
            su = (su or "").split(",")[0]
            su = "Pp" if su.startswith("Prozentpunkte") else su
            uu = su if su.startswith(("% des", "% der")) else "%" if su.startswith("%") else "Pp" if su.startswith(("Pp", "Saldo")) else "" if su.startswith("Index") else su
            vv = f"{num(v, d, su.startswith('Saldo'))} {uu}".strip() if not su.startswith("Index 0") else f"{num(v, d)} von 100 Punkten"
            sp = _subject(s.get("id"), s.get("label", ""), c.get("chart", ""))
            no_cmp = c.get("no_yoy") or yago is None
            if sp and sp.get("tpl0") and round(v, d) == 0:  # eigene Vorlage für den Wert null, etwa „unverändert“
                out.append(sp["tpl0"].format(when=when))
                continue
            if sp and sp.get("tpl"):  # ganzer Satz als Vorlage
                chg = num((v / yago - 1) * 100, 1, True) + " %" if yago else ""
                out.append(sp["tpl"].format(when=when, year=s["x"][-1][:4], v=vv, n=num(v, d), abs=num(abs(v), d), ueber="über" if v >= 0 else "unter", zu_ab="zu" if v >= 0 else "ab",
                                            waermer="wärmer" if v >= 0 else "kälter", hoeher="höher" if v >= 0 else "niedriger", oben_unten="oben" if v >= 0 else "unten", chg=chg).replace(" ( ggü. Vorjahr)", ""))
                continue
            if not sp:  # Rückfall: neutrale Formulierung mit Beschriftung
                sp = {"subj": name(s), "pl": False}
            subj, pl = sp["subj"], sp["pl"]
            lag_v = "lagen" if pl else "lag"
            if su.startswith(("% ggü", "Pp ggü")):  # Veränderungsrate: stieg/sank um
                ref = su.split(" ", 1)[1] if " " in su else ""
                if round(v, d) == 0:
                    sent = f"{when} {'veränderten' if pl else 'veränderte'} sich {subj} kaum ({ref})"
                else:
                    sent = f"{when} {('stiegen' if pl else 'stieg') if v > 0 else ('sanken' if pl else 'sank')} {subj} um {num(abs(v), d)} {'%' if su.startswith('%') else 'Pp'} {ref}"
                if len(s["y"]) > 1 and s["y"][-2] is not None and not c.get("no_yoy"):
                    sent += f", nach {num(s['y'][-2], d, True)} {'%' if su.startswith('%') else 'Pp'} {prev_lbl.get(f, 'zuvor')}"
                out.append(sent + ".")
                continue
            if su.startswith("Index") and not su.startswith("Index 0") and c.get("sent_ma3") and len(s["y"]) >= 15 and None not in s["y"][-15:]:
                ch = (sum(s["y"][-3:]) / sum(s["y"][-15:-12]) - 1) * 100  # drei Monate ggü. denselben drei Monaten ein Jahr zuvor
                out.append(f"In den drei Monaten bis {_per(last, f)} {lag_v} {subj} {num(abs(ch), 1)} % {'über' if ch > 0 else 'unter'} dem Vorjahreszeitraum.")
                continue
            if su.startswith("Index") and not su.startswith("Index 0"):  # Indexstände: Abstand zum Vorjahr
                if not yago:
                    continue
                ch = (v / yago - 1) * 100
                ref = {"M": "des Vorjahresmonats", "Q": "des Vorjahresquartals"}.get(f, "von vor einem Jahr")
                out.append(f"{when} {lag_v} {subj} {'auf dem Stand ' + ref if round(ch, 1) == 0 else num(abs(ch), 1) + ' % ' + ('über' if ch > 0 else 'unter') + ' dem Stand ' + ref}.")
                continue
            sent = f"{when} {lag_v} {subj} bei {vv}"
            if not no_cmp:
                diff = v - yago
                level_like = su.startswith(("%", "Pp", "Saldo", "Punkte", "Index 0", "°C", "cm")) or "je" in su
                neg = any(q is not None and q < 0 for x in c["series"] for q in x["y"])
                if level_like or neg or "saldo" in subj.lower():
                    du = "Pp" if su.startswith(("%", "Pp", "Saldo")) else ("Punkt" if round(abs(diff), d) == 1 else "Punkte") if su.startswith(("Punkte", "Index 0")) else uu
                    if round(diff, d) == 0:
                        sent += ", so hoch wie ein Jahr zuvor"
                    else:
                        sent += f", {num(abs(diff), d)} {du} {'höher' if diff > 0 else 'niedriger'} als ein Jahr zuvor"
                elif yago:
                    pc = (v / yago - 1) * 100
                    sent += ", so viel wie ein Jahr zuvor" if round(pc, 1) == 0 else f", {num(abs(pc), 1)} % {'mehr' if pc > 0 else 'weniger'} als ein Jahr zuvor"
            out.append(sent + ".")
        if c.get("long_mean") and out and series:  # lange Reihen: Einordnung gegenüber dem Durchschnitt des ganzen Zeitraums
            su0 = unit
            u0 = "%" if su0.startswith("%") and not su0.startswith(("% des", "% der")) else su0
            skip = lambda x: any(int(a) <= int(x[:4]) <= int(b) for a, b in c.get("mean_skip") or [])  # etwa Hyperinflation beim Realzins
            parts = [(s.get("label", ""), [v for x, v in zip(s["x"], s["y"]) if v is not None and not skip(x)]) for s in series if s.get("y")]
            parts = [(lab, v) for lab, v in parts if v]
            if parts:
                many = len(parts) > 1
                out.append(f"Zum Vergleich, Durchschnitt {series[0]['x'][0][:4]} bis {series[0]['x'][-1][:4]} {c.get('mean_note', 'ohne Kriegsjahre')}: "
                           + "; ".join(f"{lab + ' ' if many else ''}{num(sum(v) / len(v), d)} {u0}".strip() for lab, v in parts) + ".")
        if typ == "threshold" and c.get("threshold") is not None and out and series and series[0]["y"][-1] is not None:
            th = float(c["threshold"])
            out.append("Ein Rezessionssignal liegt damit vor." if series[0]["y"][-1] >= th else "Ein Rezessionssignal liegt damit nicht vor.")
        if norm and out and norm["x"][-1] == last and series and series[0]["y"][-1] is not None and norm["y"][-1]:
            v, m = series[0]["y"][-1], norm["y"][-1]
            a0, a1 = c.get("norm") or ("", "")
            out.append(f"Das sind {num(v / m * 100, 0)} % des Mittels desselben Monats {a0} bis {a1} ({num(m, d)}).")
        return out
    except (KeyError, IndexError, ValueError, TypeError, ZeroDivisionError):
        return []


def chart_text(c: dict) -> str:
    return " ".join(chart_sentences(c))


def _notes(root: Path) -> dict:
    """Von Hand gepflegte Hinweise auf Sondereffekte je Abbildung (data/static/hinweise.yaml)."""
    path = root / "data" / "static" / "hinweise.yaml"
    if not path.exists():
        return {}
    out = {}
    for n in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("notes") or []:
        out.setdefault(n["chart"], []).append({"date": str(n["date"]), "text": n["text"]})
    return out


def _health(root: Path, topics: list, meta: dict) -> dict:
    """Status des letzten Datenabrufs: Hinweis je Abbildung bei fehlgeschlagenem Abruf oder veralteten Daten."""
    path = root / "data" / "processed" / "run_status.json"
    if not path.exists():
        return {}
    run = json.loads(path.read_text(encoding="utf-8"))
    st = {s["series_id"]: s for s in run.get("series", [])}
    for tp in topics:
        for c in tp["charts"]:
            sids = {s.id for s in meta.values() if s.chart_id == c.get("chart")}
            if isinstance(c.get("series"), list):
                sids |= {s.get("id") for s in c["series"] if isinstance(s, dict)}
            elif isinstance(c.get("series"), str):
                sids.add(c["series"])
            if c.get("type") == "tiles":
                sids |= {k for k in st if k.startswith(c.get("prefix", "@"))}
            if c.get("type") == "event":  # Ereignisstudien rechnen mit festen Reihen
                sids |= {"de_ip", "de_alq_sa", "de_gdp_index"} if c.get("kind") == "downturn" else {x for p in (c.get("panels") or HIST_PANELS) for x in (p["hist"], p["cur"])} if c.get("kind") == "history" else {"enso_roni", "de_vpi", "de_vpi_food", "de_agri"}
            bad = [st[k] for k in sids if k in st and st[k].get("status") in ("failed", "skipped")]
            old = [st[k] for k in sids if k in st and st[k].get("outdated")]
            if bad:
                c["warn"] = (f"Der letzte Abruf von {len(bad)} {'Reihe' if len(bad) == 1 else 'Reihen'} dieser Abbildung ist fehlgeschlagen; "
                             "angezeigt wird der zuletzt erfolgreich abgerufene Stand.")
            elif old:
                c["warn"] = f"Die Quelle hat für {len(old)} {'Reihe' if len(old) == 1 else 'Reihen'} dieser Abbildung länger als üblich keine neuen Werte geliefert."
    ser = run.get("series", [])
    return {"finished_at": run.get("finished_at"), "n": len(ser), "ok": sum(1 for s in ser if s.get("status") in ("ok", "cache")),
            "failed": sorted(s["series_id"] for s in ser if s.get("status") in ("failed", "skipped")),
            "outdated": sorted(s["series_id"] for s in ser if s.get("outdated"))}


def _enso_episodes(roni: pd.Series, strong: float = 2.0) -> list[dict]:
    """El-Niño-Folgen: mindestens fünf Dreimonatswerte ab 0,5 °C (die laufende Folge zählt auch kürzer). Beginn = erster Monat."""
    s = roni.dropna().sort_index()
    out, run = [], []
    for d, v in s.items():
        if v >= 0.5:
            run.append((d, v))
            continue
        if len(run) >= 5:
            out.append(run)
        run = []
    current = bool(run)
    if run:
        out.append(run)
    eps = []
    for k, r in enumerate(out):
        peak = max(v for _, v in r)
        cur = current and k == len(out) - 1
        if peak >= strong or (cur and peak >= 1.5):
            eps.append({"start": r[0][0], "peak": peak, "current": cur, "label": f"{r[0][0].year}/{str(r[0][0].year + 1)[2:]}"})
    return eps


def _enso_event(data: dict, pre: int = 4, post: int = 22) -> dict | None:
    """Ereignisstudie: reale Nahrungsmittel- und Agrarpreise ab Beginn sehr starker El-Niño-Ereignisse, Monat 0 = 100."""
    roni = data.get("enso_roni")
    if roni is None or roni.dropna().empty:
        return None
    eps = _enso_episodes(roni)
    cpi = data.get("de_vpi")
    oecd = data.get("de_cpi_oecd")
    defl = cpi.dropna() if cpi is not None else None
    if defl is not None and oecd is not None and not oecd.dropna().empty:  # vor 1991 mit OECD-Index verketten
        o = oecd.dropna()
        joint = defl.index.intersection(o.index)
        if len(joint):
            f = defl[joint[0]] / o[joint[0]]
            defl = pd.concat([o[o.index < defl.index[0]] * f, defl]).sort_index()
    panels = []
    for title, num, den in (("Nahrungsmittel im Verbraucherpreisindex", data.get("de_vpi_food"), cpi),
                            ("Erzeugerpreise landwirtschaftlicher Produkte", data.get("de_agri"), defl)):
        if num is None or den is None:
            continue
        real = (num / den).dropna()
        lines = []
        for e in eps:
            k0 = real.index.searchsorted(e["start"])
            if k0 >= len(real) or real.index[k0] != e["start"] or k0 - pre < 0:
                continue
            seg = real.iloc[k0 - pre:k0 + post + 1]
            base = real.iloc[k0]
            lines.append({"label": e["label"], "start": e["start"].strftime("%Y-%m-%d"), "current": e["current"], "peak": round(e["peak"], 2),
                          "x": list(range(-pre, -pre + len(seg))), "y": [round(float(v / base * 100), 2) for v in seg]})
        if not lines:
            continue
        past = [l for l in lines if not l["current"]]
        xs = list(range(-pre, post + 1))
        lo = [min((l["y"][i] for l in past if i < len(l["y"])), default=None) for i in range(len(xs))]
        hi = [max((l["y"][i] for l in past if i < len(l["y"])), default=None) for i in range(len(xs))]
        panels.append({"title": title, "lines": lines, "x": xs, "lo": lo, "hi": hi})
    if not panels:
        return None
    return {"panels": panels, "episodes": [{"label": e["label"], "start": e["start"].strftime("%Y-%m-%d"), "peak": round(e["peak"], 2), "current": e["current"]} for e in eps]}


def _downturn_event(c: dict, data: dict) -> dict | None:
    """Abschwünge im Vergleich: Verlauf ab dem Hoch der Industrieproduktion vor früheren Krisen und im aktuellen Abschwung.
    Produktion und BIP als Index (Hoch = 100), Arbeitslosenquote als Veränderung in Prozentpunkten seit dem Hoch."""
    ip = data.get("de_ip")
    if ip is None or ip.dropna().empty:
        return None
    ip = ip.dropna()
    eps = [{"label": e["label"], "start": pd.Timestamp(e["start"]), "current": False} for e in c.get("episodes") or []]
    cur = ip[-60:].idxmax()  # aktuelles Hoch: höchster Stand der letzten fünf Jahre
    post = int(c.get("months", 36))
    if all(abs((cur - e["start"]).days) > 400 for e in eps) and cur < ip.index[-3]:
        eps.append({"label": f"laufend, seit {cur.strftime('%m/%Y')}", "start": cur, "current": True})
        post = max(post, (ip.index[-1].year - cur.year) * 12 + ip.index[-1].month - cur.month)  # aktuelle Kurve vollständig zeigen
    panels = []
    for title, sid, mode, freq, sub in (("Industrieproduktion", "de_ip", "index", "M", "Hoch = 100; waagerecht: Monate seit dem Hoch"),
                                        ("Arbeitslosenquote", "de_alq_sa", "diff", "M", "Veränderung seit dem Hoch der Produktion in Pp; waagerecht: Monate"),
                                        ("Wirtschaftsleistung (BIP)", "de_gdp_index", "index", "Q", "Quartal des Hochs = 100; waagerecht: Quartale")):
        s = data.get(sid)
        if s is None or s.dropna().empty:
            continue
        s = s.dropna()
        n = post if freq == "M" else post // 3
        lines = []
        for e in eps:
            t0 = e["start"] if freq == "M" else pd.Timestamp(e["start"].year, (e["start"].month - 1) // 3 * 3 + 1, 1)
            k0 = s.index.searchsorted(t0)
            if k0 >= len(s) or s.index[k0] != t0:
                continue
            seg, base = s.iloc[k0:k0 + n + 1], s.iloc[k0]
            ys = [round(float(v / base * 100 if mode == "index" else v - base), 2) for v in seg]
            lines.append({"label": e["label"], "start": t0.strftime("%Y-%m-%d"), "current": e["current"], "x": list(range(len(ys))), "y": ys})
        if lines:
            panels.append({"title": title, "sub": sub, "lines": lines, "x": list(range(n + 1)), "lo": [None] * (n + 1), "hi": [None] * (n + 1),
                           "base": 100 if mode == "index" else 0, "prefix": "", "unit": "" if mode == "index" else "Pp", "step": "Quartal" if freq == "Q" else "Monat"})
    return {"panels": panels} if panels else None


HIST_PANELS = [  # Standard: Abschwünge (reales BIP und Arbeitslosenquote)
    {"title": "Reales BIP", "sub": "Jahr des Hochs = 100; waagerecht: Jahre seit dem Hoch", "hist": "hist_rgdp_deu", "cur": "de_gdp_index", "per_year": 4, "mode": "index"},
    {"title": "Arbeitslosenquote", "sub": "Veränderung seit dem Jahr des Hochs in Pp; waagerecht: Jahre", "hist": "hist_unemp_deu", "cur": "de_ilo", "per_year": 12, "mode": "diff"},
]


def _history_event(c: dict, data: dict) -> dict | None:
    """Episoden seit dem 19. Jahrhundert in Jahreswerten, etwa Abschwünge (BIP, Arbeitslosenquote) oder Inflationsschübe.
    Historische Episoden aus der Global Macro Database (Reihe hist); die laufende Episode aus amtlichen Reihen (cur), als Mittel
    vollständiger Jahre. Ausgangspunkt der laufenden Episode ist der höchste Jahreswert der letzten sechs Jahre in der ersten
    Felderreihe, sofern das jüngste Jahr darunter liegt. Hervorgehobene Episoden als Linien, die übrigen als graue Spanne.
    mode: index (Ausgangsjahr = 100), diff (Veränderung in Pp), level (Wert selbst)."""
    n = int(c.get("years", 8))
    pcfg = c.get("panels") or HIST_PANELS
    yearly = lambda s: s.dropna().groupby(s.dropna().index.year).last() if s is not None else pd.Series(dtype=float)

    def current(sid, per_year):
        s = data.get(sid)
        if s is None or s.dropna().empty:
            return pd.Series(dtype=float)
        a = s.dropna().groupby(s.dropna().index.year).agg(["mean", "count"])
        return a.loc[a["count"] >= per_year, "mean"]  # nur vollständige Jahre
    hist = [yearly(data.get(p["hist"])) for p in pcfg]
    cur = [current(p["cur"], int(p.get("per_year", 12))) for p in pcfg]
    if hist[0].empty:
        return None
    eps = [dict(e, current=False) for e in c.get("episodes") or []]
    if len(cur[0]) >= 3:
        pk = int(cur[0].iloc[-6:].idxmax())
        if pk < int(cur[0].index[-1]):
            eps.append({"peak": pk, "label": f"laufend, seit {pk}", "highlight": True, "current": True})
    stop = [int(x) for x in c.get("stop_before", [])]  # Kriegsjahre nicht durchlaufen
    panels = []
    for k, pc in enumerate(pcfg):
        mode, lines, rest = pc.get("mode", "index"), [], []
        for e in eps:
            s = cur[k] if e["current"] else hist[k]
            pk = int(e["peak"])
            if pk not in s.index or pd.isna(s.loc[pk]):
                continue
            end = min([pk + n] + [w - 1 for w in stop if w > pk])
            ys = []
            for y in range(pk, end + 1):
                v = s.get(y)
                ys.append(None if v is None or pd.isna(v) else round(float(v / s.loc[pk] * 100 if mode == "index" else v - s.loc[pk] if mode == "diff" else v), 2))
            while ys and ys[-1] is None:
                ys.pop()
            if len(ys) < 2:
                continue
            ln = {"label": e.get("label") or str(pk), "start": f"{pk}-01-01", "current": e["current"], "x": list(range(len(ys))), "y": ys}
            (lines if e.get("highlight") else rest).append(ln)
        if not lines:
            continue
        if len(rest) < 3:  # wenige übrige Episoden: als dünne graue Linien statt als Spanne
            lines += [dict(r, grey=True) for r in rest]
            rest = []
        lo = [min([r["y"][i] for r in rest if i < len(r["y"]) and r["y"][i] is not None], default=None) for i in range(n + 1)]
        hi = [max([r["y"][i] for r in rest if i < len(r["y"]) and r["y"][i] is not None], default=None) for i in range(n + 1)]
        panels.append({"title": pc["title"], "sub": pc["sub"], "lines": lines, "x": list(range(n + 1)), "lo": lo, "hi": hi, "band_label": c.get("band_label"),
                       "base": 100 if mode == "index" else 0, "prefix": "", "unit": {"index": "", "diff": "Pp", "level": "%"}[mode], "step": "Jahr",
                       "mode": mode, "others": [r["label"] for r in rest]})
    return {"panels": panels} if panels else None


def week_review(root: Path, topics: list, today: pd.Timestamp, days: int = 7) -> list[dict]:
    """Abbildungen mit neuen Daten in den letzten sieben Tagen (aus dem Erscheinungsprotokoll data/archive/erscheinen.csv)."""
    path = root / "data" / "archive" / "erscheinen.csv"
    if not path.exists():
        return []
    rel = pd.read_csv(path, dtype=str, keep_default_na=False)
    rel = rel[rel["first_seen"] >= (today - pd.Timedelta(days=days - 1)).strftime("%Y-%m-%d")]
    if rel.empty:
        return []
    out, seen = [], set()
    for t in topics:
        for c in t["charts"]:
            ids = {s.get("id") for s in c.get("series") or [] if isinstance(s, dict)} if isinstance(c.get("series"), list) else set()
            hit = rel[rel["series"].isin(ids)]
            if hit.empty or c.get("no") in seen:
                continue
            seen.add(c.get("no"))
            out.append({"no": c.get("no"), "title": c.get("title", ""), "topic": t["id"], "date": hit["first_seen"].max()})
    return sorted(out, key=lambda x: (x["date"], -(x["no"] or 0)), reverse=True)


def _weather_notes(c: dict, data: dict) -> list[dict]:
    """Automatische Hinweise: ungewöhnliche Witterung bei der Bauproduktion, Niedrigwasser am Rhein bei der Industrie."""
    from .answers import MONTHS, num
    out = []
    xs = [x for s in c.get("series") or [] if isinstance(s, dict) for x in s.get("x", [])]
    if not xs:
        return out
    x0 = min(xs)
    if c.get("chart") == "bau_prod":
        t, r = data.get("de_temp_anom"), data.get("de_rain_pct")
        for d, v in (t.dropna().items() if t is not None else []):
            if d.strftime("%Y-%m-%d") < x0 or d.month not in (11, 12, 1, 2, 3):
                continue
            if abs(v) >= 2.5:
                out.append({"date": d.strftime("%Y-%m-%d"), "text": f"{MONTHS[d.month - 1]} {d.year} {'ungewöhnlich mild' if v > 0 else 'ungewöhnlich kalt'}: "
                            f"{num(abs(v), 1)} °C {'über' if v > 0 else 'unter'} dem Mittel 1991–2020 (Deutscher Wetterdienst)", "auto": True})
        for d, v in (r.dropna().items() if r is not None else []):
            if d.strftime("%Y-%m-%d") >= x0 and v >= 170:
                out.append({"date": d.strftime("%Y-%m-%d"), "text": f"{MONTHS[d.month - 1]} {d.year} sehr nass: Niederschlag {num(v, 0)} % des Mittels 1991–2020 (Deutscher Wetterdienst)", "auto": True})
    if c.get("chart") == "industry":
        lw = data.get("rhine_lowdays")
        for d, v in (lw.dropna().items() if lw is not None else []):
            if d.strftime("%Y-%m-%d") >= x0 and v >= 10:
                out.append({"date": d.strftime("%Y-%m-%d"), "text": f"{MONTHS[d.month - 1]} {d.year}: an {int(v)} Tagen Niedrigwasser am Rhein (Pegel Kaub unter 78 cm)", "auto": True})
    return sorted(out, key=lambda n: n["date"])


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
    update_release_log(root)
    layout = cfg.get("layout") or {}
    data, stand = load_observations(root)
    meta, charts_cfg = _series_meta(root / "series.yaml")
    _META.clear()
    _META.update(meta)
    load_saetze(root)
    questions = []
    for q in cfg["questions"]:
        a = answer(q, data)
        if a is None:
            continue
        a["spark_data"] = _xy(data[a["spark"]], 5)
        questions.append(dict(q, answer=a))
    topics = []
    chart_freq = {}
    for s in meta.values():
        if getattr(s, "chart_id", None):
            chart_freq.setdefault(s.chart_id, s.frequency)
    for t in cfg["topics"]:
        charts = []
        for c in t["charts"]:
            typ = c.get("type", "line")
            fy = layout.get("freq_years") or {}  # feste Zeitfenster je Takt, ab Jahresanfang: gleiche Breite heißt gleiche Zeit
            f0 = "D" if c.get("daily") else chart_freq.get(c.get("chart"))
            if fy and f0 in fy and typ in ("line", "stacked") and c.get("years") and not c.get("keep_years") and not c.get("x_start"):
                c = dict(c, years=int(fy[f0]), x_start="year")
            uy = layout.get("uniform_years")
            if uy and c.get("years") and 3 <= c["years"] <= 8 and not c.get("keep_years") and not c.get("x_start"):
                c = dict(c, years=int(uy))
            ws = layout.get("window_start") or {}
            if ws and typ == "line" and c.get("years") and not c.get("keep_years") and not c.get("x_start"):
                # feste Startjahre statt Rückzählen vom jüngsten Wert: kurz bis 8 Jahre, mittel 10 bis 12, lang ab 20 auf Jahresanfang
                y = int(c["years"])
                start = ws.get("short") if y <= 8 else ws.get("mid") if y <= 12 else "year"
                if start:
                    c = dict(c, x_start=str(start))
            entry = dict(c, type=typ, title=(charts_cfg.get(c["chart"], {}) or {}).get("title", c.get("title", "")),
                         decimals=c.get("decimals", (charts_cfg.get(c["chart"], {}) or {}).get("decimals", 1)))
            if c.get("attach"):  # Zusatzdaten aus data/static, etwa Sätze und Fundstellen für den Tooltip
                entry["attach"] = json.loads((root / "data" / "static" / c["attach"]).read_text(encoding="utf-8"))
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
                rec = root / "data" / "static" / "svr_recessions.csv"
                if rec.exists():
                    entry.update(recessions=pd.read_csv(rec).to_dict("records"), recessions_on=False)
                entry.update(_seasonal(data[sid], c.get("years")), unit=m.unit, freq=m.frequency, adjustment=m.adjustment,
                             label=m.label, sources=["Statistisches Bundesamt (GENESIS)"],
                             licenses=["Datenlizenz Deutschland – Namensnennung – Version 2.0 (Statistisches Bundesamt)"])
            elif typ == "tiles":
                windows = ({12: _tiles(c["prefix"], data, meta, 12, "diff"), 6: None} if c.get("measure") == "diff"
                           else {m: _tiles(c["prefix"], data, meta, m) for m in (12, 6)})
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
                    bars.append({"label": s.label, "value": round(float(x.iloc[-1] - b.iloc[-1]), 1), "prev": None, "period": x.index[-1].strftime("%Y-%m-%d"),
                                 "pct": round(float((x.iloc[-1] / b.iloc[-1] - 1) * 100), 1) if b.iloc[-1] else None})
                if not bars:
                    continue
                bars.sort(key=lambda r: r["value"], reverse=True)
                m = meta[specs[0].id]
                entry.update(type="latest", bars=bars, bar_name=c.get("bar_name", "Veränderung"), freq=m.frequency, adjustment=m.adjustment,
                             unit=c.get("unit", m.unit), sources=sorted({_source_name(s) for s in specs}), licenses=sorted({_license(s) for s in specs}),
                             series=[dict(id=s.id, label=s.label, unit=s.unit, freq=s.frequency, style="line", **_xy(data[s.id], 12)) for s in specs])
            elif typ == "event" and c.get("kind") == "history":
                ev = _history_event(c, data)
                if not ev:
                    continue
                curs = [meta[p["cur"]] for p in (c.get("panels") or HIST_PANELS) if p["cur"] in meta]
                entry.update(event=ev, freq="A", unit="Jahr des Hochs = 100" if (ev["panels"][0].get("mode") != "level") else "%", adjustment="Jahreswerte",
                             sources=["Global Macro Database (Müller, Xu, Lehbib und Chen 2025, NBER Working Paper 33714)"]
                                     + sorted({f"{_source_name(s)} (laufende Episode)" for s in curs}) + ["eigene Berechnung"],
                             licenses=["CC BY-NC-SA 4.0 (Global Macro Database)"] + sorted({_license(s) for s in curs if _license(s)}), content_license="CC BY-NC-SA 4.0")
            elif typ == "event" and c.get("kind") == "downturn":
                ev = _downturn_event(c, data)
                if not ev:
                    continue
                entry.update(event=ev, freq="M", unit="Hoch = 100", adjustment="saison- und kalenderbereinigt",
                             sources=["Deutsche Bundesbank (Produktion, Arbeitslosenquote)", "Eurostat (BIP)", "eigene Berechnung"],
                             licenses=[SOURCE_LICENSES["bundesbank"], SOURCE_LICENSES["eurostat"]])
            elif typ == "enso_comm":
                ec = _enso_comm(c, data)
                if not ec:
                    continue
                entry.update(enso=ec, freq="M", unit="% ggü. Vorjahr", adjustment="nicht bereinigt", last_x=ec["to"] + "-01",
                             sources=["Weltbank, Commodity Price Data (Pink Sheet)", "NOAA Climate Prediction Center (RONI)", "eigene Berechnung"],
                             licenses=["CC BY 4.0 (Weltbank)", "NOAA: gemeinfrei, mit Quellenangabe"])
            elif typ == "event":
                ev = _enso_event(data)
                if not ev:
                    continue
                entry.update(event=ev, freq="M", unit="Monat 0 = 100", adjustment="nicht bereinigt",
                             sources=["NOAA Climate Prediction Center (RONI)", "Deutsche Bundesbank (VPI und Erzeugerpreise des Statistischen Bundesamts)",
                                      "OECD über FRED (Verbraucherpreise vor 1991)", "eigene Berechnung"],
                             licenses=["NOAA: gemeinfrei, mit Quellenangabe", SOURCE_LICENSES["bundesbank"]])
            elif typ == "calendar":
                weeks = int(c.get("weeks", 12))
                cal = _calendar(root, pd.Timestamp(datetime.now(timezone.utc).date()), weeks // 4 + 2, weeks)
                if not cal:
                    continue
                entry.update(calendar=cal, sources=["Eigene Zusammenstellung nach dem üblichen Veröffentlichungsrhythmus der Quellen"], licenses=[])
            elif typ == "diffusion":
                df_ = _diffusion(c, data, meta)
                if not df_:
                    continue
                entry.update(type="line", diff=df_["counts"], series=df_["series"], unit="% der Branchen mit Zuwachs", freq="M", decimals=0, ma3=True, raw_hidden=True, y_range=[0, 100],
                             refs=[{"y": 50, "label": "Hälfte der Branchen"}], adjustment="saison- und kalenderbereinigt (Bundesbank)",
                             sources=["Deutsche Bundesbank (Produktion und Auftragseingang des Statistischen Bundesamts)", "eigene Berechnung"],
                             licenses=[SOURCE_LICENSES["bundesbank"]])
            elif typ == "projection":
                pj = _projection(c, data, root)
                if not pj:
                    continue
                series = pj.pop("series")
                if pj.get("alt"):
                    entry["alt"] = pj.pop("alt")
                else:
                    pj.pop("alt", None)
                entry.update(type="line", proj=pj, series=series, unit="% ggü. Vorjahresquartal", freq="Q", decimals=1, recessions=False,
                             adjustment="preisbereinigt, nicht saison- und kalenderbereinigt (wie die Jahresrate der Projektion)",
                             refs=[{"y": pj["target"], "x0": f"{pj['year']}-01-01", "label": f"{pj['round']}: {str(round(pj['target'], 1)).replace('.', ',')} %"}],
                             sources=["Eurostat (BIP des Statistischen Bundesamts)", f"Bundesregierung ({pj['round']})", "eigene Berechnung"],
                             licenses=[SOURCE_LICENSES["eurostat"]])
            elif typ == "cellgrid":  # Raster je Zeile und Jahr, Daten ganz aus data/static (attach), etwa Themen der Gemeinschaftsdiagnose
                if not entry.get("attach"):
                    continue
                entry.update(sources=list(c.get("sources") or []), licenses=list(c.get("licenses") or []), freq="A",
                             unit=c.get("unit", entry["attach"].get("unit", "")))
            elif typ == "treemap":  # Grundriss: Daten ganz aus data/static (attach), von Hand aktualisiert
                if not entry.get("attach"):
                    continue
                entry.update(sources=list(c.get("sources") or []), licenses=list(c.get("licenses") or []), freq="A",
                             unit=c.get("unit", entry["attach"].get("unit", "")))
            elif typ == "forecast":
                key = {"gdp": "values", "inflation": "inflation", "core": "core"}[c.get("measure", "gdp")]
                fs = [dict(f, values=f[key], by=f["by"] + (f" ({f['inflation_measure']})" if key != "values" and f.get("inflation_measure") else ""))
                      for f in _forecasts(root) if f.get(key)]
                newest = {}
                for f in fs:
                    newest[f["by"]] = max(newest.get(f["by"], ""), f["date"])
                entry["forecasts"] = [dict(f, latest=f["date"] == newest[f["by"]]) for f in fs]
                entry["sources"] = sorted({f"{f['by']} ({f['round']})" for f in entry["forecasts"]})
                if len({f["by"] for f in fs}) < 2:
                    continue
            else:
                if any(x not in data for x in c.get("need") or []):  # Abbildung nur mit diesen Reihen zeigen (etwa Berlin ohne Berliner Werte)
                    continue
                specs = [meta[x] for x in c["pick"] if x in meta] if c.get("pick") else [s for s in meta.values() if s.chart_id == c["chart"]]
                series, full = [], {}
                for s in specs:
                    if s.id not in data:
                        continue
                    ser = data[s.id]
                    if c.get("fx") and c["fx"] in data:  # US-Dollar je MMBtu in Euro je MWh: durch US-Dollar je Euro (Monatsmittel) und 0,293071 MWh je MMBtu
                        fx = data[c["fx"]].dropna()
                        fx = fx.groupby(fx.index.to_period("M")).mean()
                        fx.index = fx.index.to_timestamp()
                        ser = (ser / fx.reindex(ser.index) / float(c.get("fx_factor", 1))).dropna()
                    if c.get("transform") == "yoy":  # Veränderung ggü. Vorjahr in %
                        ser = ser.dropna()
                        ago = ser.reindex(ser.index - pd.DateOffset(years=1))
                        ser = pd.Series((ser.values / ago.values - 1) * 100, index=ser.index).dropna()
                    elif c.get("transform") == "sum12":  # Summe der letzten zwölf Monate
                        ser = ser.dropna().rolling(12, min_periods=12).sum().dropna()
                    elif c.get("transform") == "cagr10":  # durchschnittliches jährliches Wachstum der letzten zehn Jahre, in %
                        ser = ser.dropna()
                        ago = ser.reindex(ser.index - pd.DateOffset(years=10))
                        ser = pd.Series(((ser.values / ago.values) ** 0.1 - 1) * 100, index=ser.index).dropna()
                    for y0, y1 in c.get("blank_years") or []:  # Kriegs- und Inflationsjahre auslassen: Lücke statt Werte
                        ser = ser[(ser.index.year < int(y0)) | (ser.index.year > int(y1))]
                    xy = _xy(ser * float(c.get("scale", 1)), c.get("years"), c.get("x_start"))
                    fx = _xy(ser * float(c.get("scale", 1)), None, None)  # ganze Reihe für den Schalter „Ganze Reihe“ (eigene Datei, lädt erst beim Klick)
                    if len(fx["x"]) > len(xy["x"]) + 3:
                        full[s.id] = fx
                    series.append(dict(id=s.id, label=(c.get("labels") or {}).get(s.id) or s.label or s.title, unit=c.get("unit", s.unit), freq="B" if c.get("daily") else s.frequency,
                                       style=(c.get("styles") or {}).get(s.id) or getattr(s, "style", None) or "line", **({"of": c["of"][s.id]} if s.id in (c.get("of") or {}) else {}), **xy))
                if c.get("total") and c["total"] in data:
                    s = meta[c["total"]]
                    series.append(dict(id=s.id, label="BIP insgesamt", unit=s.unit, freq=s.frequency, style="line",
                                       **_xy(data[s.id], c.get("years"), c.get("x_start"))))
                if not series:
                    continue
                if full and not c.get("curve"):  # Zinskurve: Vergleich mit dem Vorjahr, keine ganze Reihe
                    entry["_full"] = full
                if c.get("ref_mean"):  # Mittel eines Zeitraums als graue Referenzlinie
                    a0, a1 = c["ref_mean"]
                    s0 = data[series[0]["id"]].dropna()
                    w = s0[(s0.index.year >= a0) & (s0.index.year <= a1)] * float(c.get("scale", 1))
                    if len(w):
                        entry["refs"] = list(c.get("refs") or []) + [{"y": round(float(w.mean()), 1), "label": f"Mittel {a0}–{a1}"}]
                if c.get("norm"):  # Mittel desselben Kalendermonats als Vergleichsmarke, etwa 2015 bis 2019
                    a0, a1 = c["norm"]
                    s0 = data[series[0]["id"]].dropna()
                    w = s0[(s0.index.year >= a0) & (s0.index.year <= a1)]
                    m = w.groupby(w.index.month).mean()
                    series.append(dict(series[0], id="norm_" + series[0]["id"], label=f"Mittel {a0}–{a1}", style="norm",
                                       y=[round(float(m[int(x[5:7])]), 1) for x in series[0]["x"]]))
                if typ == "stacked":  # Vorzeichenlogik der Importe sichtbar machen
                    series = [dict(s, label="Importe (negativ gerechnet)") if s["label"] == "Importe" else s for s in series]
                if c.get("groups"):  # Beiträge zu Gruppen bündeln, etwa Außenhandel = Exporte + (negative) Importe
                    bars = {s["id"]: s for s in series if s.get("style") == "bar"}
                    grouped = []
                    for label, items in c["groups"].items():
                        members = [s for sid, s in bars.items() if any(sid.endswith("_" + str(i).lower()) for i in items)]
                        if not members:
                            continue
                        xs = sorted(set.intersection(*[set(m["x"]) for m in members]))
                        vals = [round(sum(m["y"][m["x"].index(x)] for m in members), 4) for x in xs]
                        grouped.append(dict(members[0], id=f"group_{label}", label=label, x=xs, y=vals))
                    series = grouped + [s for s in series if s.get("style") != "bar"]
                if c.get("pot_band"):  # Spanne mehrerer Schätzungen als Band; die Einzelschätzungen nur im Tooltip
                    ps = [x for x in series if x["id"] in c["pot_band"]]
                    if len(ps) >= 2:
                        vals = {}
                        for x in ps:
                            for d, v in zip(x["x"], x["y"]):
                                vals.setdefault(d, []).append(v)
                        xs = sorted(d for d, v in vals.items() if len(v) >= 2)
                        band = dict(ps[0], unit=ps[0]["unit"], freq=ps[0]["freq"], x=xs)
                        cut = lambda x: dict(x, style="hover", x=[d for d in x["x"] if d <= xs[-1]], y=[v for d, v in zip(x["x"], x["y"]) if d <= xs[-1]])  # nicht über das Band hinaus
                        series = [cut(x) if x in ps else x for x in series] + [
                            dict(band, id="band_lo", label="Spanne der Schätzungen, untere Grenze", style="band_lo", y=[round(min(vals[d]), 3) for d in xs]),
                            dict(band, id="band_hi", label="Spanne der Schätzungen, obere Grenze", style="band_hi", y=[round(max(vals[d]), 3) for d in xs])]
                        entry["pot_names"] = [x["label"] for x in ps]
                        gov = sorted((f for f in _forecasts(root) if f["by"] == "Bundesregierung"), key=lambda f: f["date"])
                        entry["gov_values"] = {str(k): v for k, v in gov[-1]["values"].items()} if gov else {}
                        entry["gov_round"] = gov[-1]["round"] if gov else None
                entry["series"] = series
                if layout.get("compare_band") and typ in ("line",) and not c.get("ma3") and (len(series) == 1 or c.get("emphasis")):
                    lead = next((s for s in specs if s.id == c.get("emphasis")), None) or next((s for s in specs if s.id in data), None)
                    b = _band(data[lead.id]) if lead is not None else None
                    if b:
                        entry["band"] = dict(b, label=f"Spanne 2015–2019 ({lead.label or lead.title})" if len(series) > 1 else "Spanne 2015–2019")
                entry["unit"] = series[0]["unit"]
                entry["freq"] = series[0]["freq"]
                entry["adjustment"] = (meta.get(series[0]["id"]) or specs[0]).adjustment
                specs_used = ([meta[x["id"]] for x in series if x["id"] in meta] or specs) + ([meta[c["fx"]]] if c.get("fx") in meta else [])
                entry["sources"] = sorted({_source_name(s) for s in specs_used})
                entry["licenses"] = sorted({lic for s in specs_used if (lic := _license(s))})
                if any(_base(s).source == "gmd" for s in specs_used):  # Global Macro Database: Abbildung und Download unter CC BY-NC-SA 4.0
                    entry["content_license"] = "CC BY-NC-SA 4.0"
                if c.get("crises") and c["crises"] in data:  # Bankenkrisen als Hintergrundbänder
                    cs = data[c["crises"]].dropna()
                    x0 = min(s["x"][0] for s in series)
                    entry["crisis_years"] = [d.strftime("%Y") for d, v in cs.items() if v >= 1 and d.strftime("%Y-%m-%d") >= x0]
                    gdp = data.get(c.get("recession_from", "hist_rgdp_deu"))
                    if gdp is not None:  # Rezessionen in langen Reihen: Jahre mit sinkendem realem BIP
                        g = gdp.dropna()
                        g = g.groupby(g.index.year).last()
                        entry["recession_years"] = [str(y) for y in g.index[1:] if g[y] < g[y - 1] and y - 1 in g.index and f"{y}-01-01" >= x0]
                if typ == "latest":
                    entry["bars"] = [dict(label=s["label"], value=s["y"][-1], prev=s["y"][-2] if len(s["y"]) > 1 else None,
                                          period=s["x"][-1]) for s in series]
                rec = root / "data" / "static" / "svr_recessions.csv"
                if c.get("recessions") is False:  # etwa Steuersätze oder Vergleiche anderer Länder
                    entry["recessions"] = False  # bleibt False, damit die Nachbearbeitung keine Rezessionen ergänzt
                elif rec.exists() and typ != "latest":
                    entry["recessions"] = pd.read_csv(rec).to_dict("records")
                    entry["recessions_on"] = typ == "threshold"
            charts.append(entry)
            if typ == "heat":  # Balken zur Wärmetabelle als eigene Abbildung
                what = "Auftragseingang" if "order" in c["chart"] else "Produktion"
                charts.append(dict(entry, chart=c["chart"] + "_bars", type="heatbars", ask=c.get("bars_ask") or f"Welche Branchen haben bei {'den Aufträgen' if 'order' in c['chart'] else 'der Produktion'} zugelegt, welche liegen unter 2019?",
                                   title=f"{what} nach Branchen: Dreimonatsvergleich und Niveau ggü. 2019", unit="%",
                                   caption=f"{what} je Branche als Balken, umschaltbar. Dreimonatsvergleich: letzte drei Monate ggü. den drei Monaten davor, saisonbereinigt. "
                                           "Niveau ggü. 2019: jüngster Monat ggü. dem Durchschnitt 2019, dem letzten vollen Jahr vor der Pandemie und vor dem Energiepreisschock 2022; "
                                           "der Vergleich zeigt, welche Branchen ihr Vorkrisenniveau wieder erreicht haben. Orange: Zunahme, blau: Abnahme."))
        if t.get("charts") and not charts and t.get("part") == "anhang":
            continue  # Anhang-Abschnitt ohne Daten (etwa Berlin, wenn GENESIS ausfällt) nicht als leere Überschrift zeigen
        q = next((x for x in questions if x.get("topic") == t["id"]), None)
        topics.append(dict(t, charts=charts, question=q))
    notes = _notes(root)
    rec_path = root / "data" / "static" / "svr_recessions.csv"
    recs = pd.read_csv(rec_path).to_dict("records") if rec_path.exists() else []
    for tp in topics:
        for c in tp["charts"]:
            if recs and "recessions" not in c and c.get("type") in ("line", "stacked", "threshold") and isinstance(c.get("series"), list):
                c["recessions"], c["recessions_on"] = recs, False  # etwa Inflationsbeiträge, die einen eigenen Zweig haben
            if c.get("recessions") is False:
                c.pop("recessions")
            c["texts"] = [] if c.get("no_texts") else [x.replace(" in Euroraum", " im Euroraum").replace(" in Europäische Union", " in der Europäischen Union") for x in chart_sentences(c)]  # no_texts: etwa Tageswerte, deren Einzeltag nur Rauschen zeigt
            c["text"] = " ".join(c["texts"])
            c["last_x"] = _last_x(c)
            c["notes"] = notes.get(c["chart"], []) + _weather_notes(c, data)
            if c.get("ma3") or c.get("outliers"):
                c["outliers"] = _outliers(c)
    _merge_toggles(topics)  # zwei Abbildungen mit Umschalter in einer Karte
    no = 0
    for t in topics:
        lab = t.get("code") or t["title"].split()[0]  # festes Kurzzeichen je Abbildung: Kapitel und Platz im Kapitel, etwa „Preise-3“
        for k, c in enumerate(t["charts"], 1):
            no += 1
            c["no"], c["k"], c["code"], c["anchor"] = no, k, f"{lab}-{k}", f"{t['id']}-{k}"
    # Nächste voraussichtliche Aktualisierung je Abbildung und Verweise vom Kalender auf die Abbildungen
    numbers = {c["chart"]: c["no"] for t in topics for c in t["charts"]}
    cal = next((c["calendar"] for t in topics for c in t["charts"] if c.get("type") == "calendar"), None)
    if cal:
        cal_id = next(c["no"] for t in topics for c in t["charts"] if c.get("type") == "calendar")
        for e in cal["events"]:
            e["figs"] = [numbers[k] for k in e.get("charts", []) if k in numbers]
        for t in topics:
            for c in t["charts"]:
                e = next((e for e in cal["events"] if c["chart"] in e.get("charts", [])), None)
                if e:
                    c["next_update"] = {"date": e["date"], "name": e["name"], "calendar": cal_id, "period": _next_period(c)}
    for q in questions:
        a = q["answer"]
        a["head"], a["more"] = tidy(a["head"]), [tidy(m) for m in a["more"]]
        q["explain"] = tidy(q.get("explain", ""))
    for tp in topics:
        for c in tp["charts"]:
            c["texts"] = [tidy(s) for s in c["texts"]]
            c["text"] = " ".join(c["texts"])
            for k in ("caption", "unit", "ask"):
                if c.get(k):
                    c[k] = tidy(c[k])
            for n in c.get("notes", []):
                n["text"] = tidy(n["text"])
            if c.get("alt"):
                c["alt"] = dict(c["alt"], label=tidy(c["alt"]["label"]), base=tidy(c["alt"]["base"]), unit=tidy(c["alt"]["unit"]))
    if recs:  # Erfolgsbilanz der Signale gegen die Rezessionsdatierung des Sachverständigenrats
        from .bilanz import evaluate
        for tp in topics:
            for c in tp["charts"]:
                rule, flag = None, None
                if c["chart"] == "sahm" and "de_sahm" in data:
                    thr = float(c.get("threshold", 0.25))
                    flag, rule = data["de_sahm"] >= thr, f"Signal ab {str(thr).replace('.', ',')} Pp"
                elif c["chart"] == "diffusion" and c.get("series"):
                    s0 = c["series"][0]
                    m3 = pd.Series(s0["y"], index=pd.to_datetime(s0["x"])).rolling(3).mean()
                    flag, rule = (m3 < 40).where(m3.notna()), "Dreimonatsmittel der Produktion unter 40 % der Branchen"
                elif c.get("type") == "clock" and c.get("x") in data and c.get("y") in data:
                    df = pd.concat({"x": data[c["x"]], "y": data[c["y"]]}, axis=1).dropna()
                    dev = df - df[(df.index >= "2005-01-01") & (df.index < "2020-01-01")].mean()
                    both = (dev["x"] < 0) & (dev["y"] < 0)
                    flag, rule = both & both.shift(1, fill_value=False), "zwei Monate in Folge im Feld „Rezession“ (Aufträge und Erwartungen unter dem Mittel)"
                if flag is not None:
                    b = evaluate(flag, recs, 12 if c["chart"] == "sahm" else 0)
                    if b:
                        c["bilanz"] = dict(b, rule=rule)
    from .satzpruefung import apply as check_sentences
    text_issues = check_sentences(topics)  # durchgefallene Sätze entfallen, Funde gehen ins Ticket
    for line in text_issues:
        print("Satzprüfung:", line)
    from .ausschreiben import spell, GLOSSAR
    for q in questions:  # Abkürzungen in Sätzen ausschreiben, erst nach der Satzprüfung
        a = q["answer"]
        a["head"], a["more"], q["explain"] = spell(a["head"]), [spell(m) for m in a["more"]], spell(q.get("explain", ""))
    for tp in topics:
        for c in tp["charts"]:
            c["texts"] = [spell(x) for x in c["texts"]]
            c["text"] = " ".join(c["texts"])
            if c.get("caption"):
                c["caption"] = spell(c["caption"])
            if c.get("kommentar"):  # eigene Einschätzung je Grafik (monitor.yaml, Feld kommentar), auf Klick in der linken Spalte
                c["kommentar"] = spell(c["kommentar"])
            for n in c.get("notes", []):
                n["text"] = spell(n["text"])
    health = _health(root, topics, meta)
    geo = _geo(root)
    return {"layout": layout, "health": health, "start": _start_rows(cfg, data, meta, {t["id"]: t["title"] for t in cfg["topics"]}), "geo": geo, "geo_source": "Ländergrenzen: © GeoBasis-DE / BKG (VG2500), Datenlizenz Deutschland – Namensnennung – Version 2.0",
            "site": cfg["site"], "stand": stand, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "questions": questions, "topics": topics, "overview": spell(tidy(overview({q["id"]: q["answer"] for q in questions}))),
            "fazit": spell(tidy(fazit({q["id"]: q["answer"] for q in questions}))) if cfg["site"].get("kommentar", True) else "", "glossar": GLOSSAR,
            "content_license": cfg["site"].get("license", ""), "text_issues": text_issues, "lage": _lage(data, root)}


def _lage(data: dict, root: Path) -> dict:
    """Erster Bildschirm: Kernzahlen, Lage-Satz, Warnlampen, Ausblick und was die Gremien raten, deutsch und englisch."""
    from . import lage
    from .gremien import heute
    fc = _forecasts(root)
    out = {lang: lage.build(data, fc, lang) for lang in ("de", "en")}
    for lang in ("de", "en"):
        out[lang]["gremien"] = [x for x in (heute("svr_positionen.json", "svr", lang), heute("gd_positionen.json", "gd", lang)) if x]
    return out


def write_embeds(payload: dict, tpl: str, out: Path) -> int:
    from html import escape
    """Je Abbildung site/abb/<abbildung>.html: dieselbe Vorlage, aber nur diese Abbildung, ohne Kopf und Fuß, zum Einbetten per iframe.
    Pfade zu Plotly, Schrift, Downloads und Methodenblättern zeigen eine Ebene höher."""
    d = out / "abb"
    d.mkdir(parents=True, exist_ok=True)
    base = (tpl.replace('const PLOTLY_SRC = "plotly.min.js";', 'const PLOTLY_SRC = "../plotly.min.js";').replace('url("fonts/', 'url("../fonts/')
            .replace('METH_BASE = "methodik/"', 'METH_BASE = "../methodik/"'))
    url = payload["site"].get("url", "")
    n = 0
    for t in payload["topics"]:
        for c in t["charts"]:
            if not c.get("chart") or c.get("type") == "calendar":
                continue
            cc = dict(c, files={k: "../" + v for k, v in (c.get("files") or {}).items() if isinstance(v, str)})
            p = dict(payload, topics=[dict(t, charts=[cc], question=None, ask=c.get("ask") or t.get("ask"))], start=[], questions=[], news=[], week=[], overview="", embed=True,
                     geo=payload.get("geo") if c.get("type") == "tiles" else None, all_series={}, deck=None)
            js = json.dumps(p, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
            title = f"{c.get('title', '')} · Konjunkturmonitor"
            desc = (c.get("texts") or [""])[0] or c.get("caption", "")
            html = (base.replace("/*__DATA__*/null", js).replace("/*__STATIC__*/", "").replace("/*__OVERVIEW__*/", "")
                    .replace("/*__DESC__*/", escape(desc, quote=True)).replace("/*__URL__*/", escape(f"{url}abb/{c['chart']}.html", quote=True))
                    .replace("/*__OGIMG__*/", escape(url + "vorschau.png", quote=True))
                    .replace("<title>Konjunkturmonitor</title>", f"<title>{escape(title)}</title>")
                    .replace('<meta property="og:title" content="Konjunkturmonitor: Wie steht es um die deutsche Wirtschaft?">', f'<meta property="og:title" content="{escape(title, quote=True)}">'))
            (d / f"{c['chart']}.html").write_text(html, encoding="utf-8")
            n += 1
    return n


def code_versions(root: Path = ROOT) -> dict:
    """Code-Stand für Reproduzierbarkeit: Commit des Monitors (GITHUB_SHA oder git) und der installierten Pipeline konjunkturwolf."""
    import os
    import subprocess
    mon = os.environ.get("GITHUB_SHA", "")
    if not mon:
        try:
            mon = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            mon = ""
    kw = ""
    try:
        from importlib.metadata import distribution
        du = json.loads(distribution("konjunkturwolf").read_text("direct_url.json") or "{}")
        kw = (du.get("vcs_info") or {}).get("commit_id", "")
    except Exception:  # lokale Installation ohne Angabe
        kw = ""
    return {"monitor": mon[:12], "konjunkturwolf": kw[:12]}


def build_site(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out or root / "site"
    out.mkdir(parents=True, exist_ok=True)
    payload = build_payload(root)
    payload["code"] = code_versions(root)
    code_txt = f"Konjunkturmonitor {payload['code']['monitor'][:7] or 'lokal'}, konjunkturwolf {payload['code']['konjunkturwolf'][:7] or 'lokal'}"
    for t in payload["topics"]:
        for c in t["charts"]:
            c["_code"] = code_txt
    from .downloads import write_all
    from .reuse import mark_revisions, news, update_archive, write_all_series, write_feed

    write_all(payload, out, root)
    data, _ = load_observations(root)
    meta, _ = _series_meta(root / "series.yaml")
    stand_de = f"{payload['stand'][8:10]}.{payload['stand'][5:7]}.{payload['stand'][:4]}"
    cite = f"{payload['site']['author']} ({payload['stand'][:4]}): Konjunkturmonitor. Stand {stand_de}. {payload['site']['url']}"
    payload["all_series"] = write_all_series(data, meta, root, out, stand_de, cite, payload["generated_at"][:10])
    arch = update_archive(root, payload["start"], payload["stand"])
    mark_revisions(payload["start"], arch)
    items = news(arch, payload["stand"])
    payload["news"] = [i for i in items if i["stand"] == payload["stand"]]
    payload["week"] = week_review(root, payload["topics"], pd.Timestamp(payload["generated_at"][:10]))
    write_feed(items, payload["start"], payload["site"], out)
    (out / "dl").mkdir(exist_ok=True)
    arch_name = f"Konjunkturmonitor ({payload['generated_at'][:10]}) Archiv Kernzahlen.csv"
    with open(out / "dl" / arch_name, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(arch_name[:-4] + "\n")
        arch.to_csv(fh, sep=";", decimal=",", index=False)
    payload["archive_file"] = "dl/" + arch_name
    (out / "full").mkdir(exist_ok=True)  # ganze Reihen je Abbildung, für den Schalter „Ganze Reihe“
    for t in payload["topics"]:
        for c in t["charts"]:
            for cc in (c, c.get("variant")):
                if isinstance(cc, dict) and cc.get("_full"):
                    name = f"{cc['chart']}.json"
                    (out / "full" / name).write_text(json.dumps(cc.pop("_full"), separators=(",", ":")), encoding="utf-8")
                    cc["full"] = "full/" + name
    tpl = resources.files("monitor").joinpath("templates/index.html").read_text(encoding="utf-8")
    payload["has_en"] = (root / "data" / "static" / "en.yaml").exists()
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    from html import escape
    url = payload["site"].get("url", "")
    desc = payload.get("overview") or payload["site"].get("claim", "")
    html = (tpl.replace("/*__DATA__*/null", js).replace("/*__STATIC__*/", static_table(payload["start"]))
            .replace("/*__OVERVIEW__*/", escape(payload.get("overview", ""))).replace("/*__DESC__*/", escape(desc, quote=True))
            .replace("/*__URL__*/", escape(url, quote=True)).replace("/*__OGIMG__*/", escape(url + "vorschau.png", quote=True)))
    (out / "index.html").write_text(html, encoding="utf-8")
    write_embeds(payload, tpl, out)  # je Abbildung eine Einzelseite zum Einbetten (site/abb/)
    if payload["has_en"]:  # englische Fassung unter site/en/
        from .english import english_payload
        from .ui_en import apply
        pen = english_payload(payload, data, root)
        tpl_en, missing = apply(tpl)
        if missing:
            print(f"Englische Oberfläche: {len(missing)} Texte im Template nicht gefunden, z. B. {missing[:3]}")
        js_en = json.dumps(pen, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        desc_en = pen.get("overview") or pen["site"]["claim"]
        html_en = (tpl_en.replace("/*__DATA__*/null", js_en).replace("/*__STATIC__*/", "")
                   .replace("/*__OVERVIEW__*/", escape(pen.get("overview", ""))).replace("/*__DESC__*/", escape(desc_en, quote=True))
                   .replace("/*__URL__*/", escape(pen["site"]["url"], quote=True)).replace("/*__OGIMG__*/", escape(url + "vorschau.png", quote=True)))
        (out / "en").mkdir(exist_ok=True)
        (out / "en" / "index.html").write_text(html_en, encoding="utf-8")
    from .methodik import write_method_pages
    write_method_pages(payload, meta, root, out, _license)  # Methodenblatt je Abbildung (site/methodik/)
    preview_image(payload, out / "vorschau.png")
    from .korrekturen import load as load_corr, write_page as write_corr
    write_corr(load_corr(root), payload, out)  # Korrekturen und Änderungen (site/korrekturen.html)
    for page in ("impressum.html", "datenschutz.html"):
        (out / page).write_text(resources.files("monitor").joinpath(f"templates/{page}").read_text(encoding="utf-8"), encoding="utf-8")
    (out / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    fonts = out / "fonts"  # Source Sans 3 (OFL) liegt neben der Seite
    fonts.mkdir(exist_ok=True)
    for f in resources.files("monitor").joinpath("static/fonts").iterdir():
        (fonts / f.name).write_bytes(f.read_bytes())
    # schlanke Plotly-Fassung (nur Linien und Balken, MIT-Lizenz) statt des vollen Pakets aus konjunkturwolf: 0,4 statt 1,5 MB komprimiert
    plotly = resources.files("monitor").joinpath("static/plotly/plotly-basic.min.js")
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
