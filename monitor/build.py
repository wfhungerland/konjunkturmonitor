"""Seite des Konjunkturmonitors aus den Beobachtungen der Pipeline bauen."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import pandas as pd
import yaml

from .answers import answer, num

ROOT = Path.cwd()

SOURCE_NAMES = {"bundesbank": "Deutsche Bundesbank", "eurostat": "Eurostat", "ecb": "EZB", "static": "BA-Statistik (aufbereitet)",
                "derived": "eigene Berechnung"}
SOURCE_LICENSES = {"bundesbank": "Wiederverwendung mit Quellenangabe (Deutsche Bundesbank)", "eurostat": "CC BY 4.0 (Eurostat)",
                   "ecb": "Wiederverwendung mit Quellenangabe (EZB)", "static": "Statistik der Bundesagentur für Arbeit, mit Quellenangabe"}


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


def build_payload(root: Path = ROOT) -> dict:
    cfg = yaml.safe_load((root / "monitor.yaml").read_text(encoding="utf-8"))
    data, stand = load_observations(root)
    meta, charts_cfg = _series_meta(root / "series.yaml")
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
            entry = dict(c, type=typ, title=(charts_cfg.get(c["chart"], {}) or {}).get("title", c.get("title", "")),
                         decimals=(charts_cfg.get(c["chart"], {}) or {}).get("decimals", 1))
            if typ == "clock":
                entry["clock"] = _clock(c, data)
                entry["sources"] = ["Europäische Kommission, Unternehmensumfrage Industrie (Eurostat ei_bsin_m_r2)"]
                entry["licenses"] = [SOURCE_LICENSES["eurostat"]]
                if not entry["clock"]:
                    continue
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
                entry["unit"] = series[0]["unit"]
                entry["freq"] = series[0]["freq"]
                entry["adjustment"] = meta[series[0]["id"]].adjustment
                srcs = {meta[x["id"]].source for x in series}
                entry["sources"] = sorted({SOURCE_NAMES.get(x, x) for x in srcs})
                entry["licenses"] = sorted({SOURCE_LICENSES[x] for x in srcs if x in SOURCE_LICENSES})
                if typ == "threshold":
                    rec = root / "data" / "static" / "svr_recessions.csv"
                    if rec.exists():
                        entry["recessions"] = pd.read_csv(rec).to_dict("records")
            charts.append(entry)
        q = next((x for x in questions if x.get("topic") == t["id"]), None)
        topics.append(dict(t, charts=charts, question=q))
    return {"site": cfg["site"], "stand": stand, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "questions": questions, "topics": topics}


def build_site(root: Path = ROOT, out: Path | None = None) -> Path:
    out = out or root / "site"
    out.mkdir(parents=True, exist_ok=True)
    payload = build_payload(root)
    tpl = resources.files("monitor").joinpath("templates/index.html").read_text(encoding="utf-8")
    js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    (out / "index.html").write_text(tpl.replace("/*__DATA__*/null", js), encoding="utf-8")
    (out / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    plotly = resources.files("konjunkturwolf").joinpath("static/plotly.min.js")
    (out / "plotly.min.js").write_bytes(plotly.read_bytes())
    return out / "index.html"


__all__ = ["build_payload", "build_site", "num"]
