"""Sperre vor der Veröffentlichung: auffällige Reihen bleiben auf dem zuletzt geprüften Stand.

Nach dem Abruf vergleicht der Lauf jede Reihe mit dem zuletzt gespeicherten Stand (data/processed/observations.csv).
Eine Reihe wird angehalten, wenn
  1. sie mehr als ein Fünftel ihrer bisherigen Werte verliert,
  2. mehr als ein Viertel ihrer bisherigen Werte stark vom letzten Stand abweicht (neue Basis, andere Einheit, Abruffehler,
     veränderte Quelle) oder
  3. ihr jüngster Wert neu ist und dreimal so stark springt wie je zuvor.
Angehaltene Reihen zeigen auf der Seite den alten Stand mit Hinweis; Reihen, die aus ihnen berechnet werden, bleiben ebenfalls
stehen. Die Liste steht in data/processed/sperre.json, ein Ticket nennt sie (monitor/alert.py).

Freigabe von Hand: Eintrag in data/static/freigaben.yaml mit Reihe (oder "*" für alle), Datum „bis“ und Grund. Bis zu diesem
Datum übernimmt der Lauf die neuen Werte ungeprüft; danach gelten sie als geprüfter Stand.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

log = logging.getLogger(__name__)

MIN_OBS = 24        # kürzere Reihen prüft die Sperre nicht
LOST_SHARE = 0.2    # Regel 1
MOVED_SHARE = 0.25  # Regel 2
K_MAD = 8.0         # „stark“: mehr als K_MAD robuste Standardabweichungen der üblichen Veränderung
JUMP_FACTOR = 3.0   # Regel 3: Vielfaches der bisher größten Veränderung


def _scale(diffs: np.ndarray) -> float:
    """Übliche Veränderung von Periode zu Periode: Median der absoluten Abweichungen × 1,4826, ersatzweise Standardabweichung."""
    if len(diffs) == 0:
        return 0.0
    mad = float(np.median(np.abs(diffs - np.median(diffs))) * 1.4826)
    return mad if mad > 0 else float(np.std(diffs))


def anomaly(prev: pd.Series, new: pd.Series) -> str | None:
    """Grund, warum die neue Fassung einer Reihe nicht ungeprüft erscheinen soll; None, wenn nichts auffällt.
    prev und new: Werte mit Datum als Index."""
    prev, new = prev.dropna().sort_index(), new.dropna().sort_index()
    if len(prev) < MIN_OBS:
        return None
    if len(new) == 0:
        return "keine Werte mehr"
    lost = 1 - prev.index.isin(new.index).mean()
    if lost > LOST_SHARE:
        return f"{lost:.0%} der bisherigen Werte fehlen"
    s = _scale(np.diff(prev.values))
    if s > 0:
        common = prev.index.intersection(new.index)
        moved = float((np.abs(new[common].values - prev[common].values) > K_MAD * s).mean()) if len(common) else 0.0
        if moved > MOVED_SHARE:
            return f"{moved:.0%} der bisherigen Werte weichen stark vom letzten Stand ab (neue Basis, Einheit oder Abruffehler?)"
    edge_new = new.index.max() > prev.index.max() or not np.isclose(new.iloc[-1], prev.reindex(new.index).iloc[-1], rtol=1e-9, atol=1e-12)
    if edge_new and len(new) >= 36:
        d = np.diff(new.values)
        hist, last = d[:-1], d[-1]
        sc = _scale(hist)
        if sc > 0 and abs(last - np.median(hist)) > K_MAD * sc and abs(last) > JUMP_FACTOR * np.abs(hist).max():
            return f"jüngste Veränderung {last:+.3g}, bisher höchstens ±{np.abs(hist).max():.3g}"
    return None


def load_releases(root: Path, today: date | None = None) -> set[str]:
    """Reihen mit gültiger Freigabe (data/static/freigaben.yaml); "*" gibt alle frei."""
    path = root / "data" / "static" / "freigaben.yaml"
    if not path.exists():
        return set()
    today = today or date.today()
    out = set()
    for e in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("freigaben") or []:
        if e.get("reihe") and e.get("bis") and date.fromisoformat(str(e["bis"])) >= today:
            out.add(str(e["reihe"]))
    return out


def load_frozen(root: Path) -> list[dict]:
    path = root / "data" / "processed" / "sperre.json"
    return json.loads(path.read_text(encoding="utf-8")).get("angehalten", []) if path.exists() else []


def _bases(spec) -> set[str]:
    d = getattr(spec, "derive", None) or {}
    return {str(v) for k in ("from", "minus", "plus") if (v := d.get(k))} | {str(v) for v in (d.get("with") or {}).values()}


def apply(result, previous: pd.DataFrame, catalog, root: Path, today: date | None = None, only: list[str] | None = None) -> list[dict]:
    """Hält auffällige Reihen im Ergebnis eines Laufs an: ersetzt ihre Werte durch den letzten Stand und schreibt sperre.json.
    result: RunResult von konjunkturwolf; previous: Beobachtungen vor dem Lauf; only: Reihen eines Teil-Laufs (andere bleiben,
    wie sie waren). Gibt die angehaltenen Reihen zurück."""
    from konjunkturwolf.periods import period_label

    today = today or date.today()
    released = load_releases(root, today)
    obs = result.observations
    prev_ids = set(previous["series_id"].unique()) if len(previous) else set()
    reasons: dict[str, str] = {}
    if "*" not in released and prev_ids and len(obs):
        new_by = {sid: g.set_index("date")["value"] for sid, g in obs.groupby("series_id", sort=False)}
        prev_by = {sid: g.set_index("date")["value"] for sid, g in previous.groupby("series_id", sort=False)}
        fresh = {s.series_id for s in result.statuses if s.status in ("ok", "cache")}
        for sid in fresh & prev_ids - released:
            if sid in new_by and (why := anomaly(prev_by[sid], new_by[sid])):
                reasons[sid] = why
        changed = bool(reasons)
        while changed:  # berechnete Reihen folgen ihrer Basis
            changed = False
            for spec in catalog.series:
                hit = sorted(_bases(spec) & set(reasons))
                if hit and spec.id not in reasons and spec.id in prev_ids and spec.id in new_by:
                    reasons[spec.id] = f"berechnet aus angehaltener Reihe {hit[0]}"
                    changed = True
    old = load_frozen(root)
    since = {e["series_id"]: e.get("seit") for e in old}
    carried = [e for e in old if only and e["series_id"] not in only and e["series_id"] not in reasons]  # Teil-Lauf: nicht abgerufene bleiben angehalten
    frozen = [{"series_id": sid, "grund": reasons[sid], "seit": since.get(sid) or today.isoformat()} for sid in sorted(reasons)]
    if reasons:
        cols = list(obs.columns)
        keep = previous[previous["series_id"].isin(reasons)][cols]
        obs = pd.concat([obs[~obs["series_id"].isin(reasons)], keep], ignore_index=True)
        obs["date"] = pd.to_datetime(obs["date"])
        order = {s.id: i for i, s in enumerate(catalog.series)}
        obs = obs.sort_values(["series_id", "date"], key=lambda c: c.map(order) if c.name == "series_id" else c)
        result.observations = obs.reset_index(drop=True)
        freq = {s.id: s.frequency for s in catalog.series}
        for st in result.statuses:
            if st.series_id in reasons:
                g = keep[keep["series_id"] == st.series_id].sort_values("date")
                st.n_obs, st.last_value = len(g), float(g["value"].iloc[-1])
                st.last = period_label(pd.Timestamp(g["date"].iloc[-1]).date(), freq.get(st.series_id, "M"))
                st.retrieved_at = str(g["retrieved_at"].iloc[0])
                st.message = f"angehalten: {reasons[st.series_id]}"
                log.warning("%-28s angehalten: %s", st.series_id, reasons[st.series_id])
    frozen = sorted(frozen + carried, key=lambda e: e["series_id"])
    path = root / "data" / "processed" / "sperre.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"angehalten": frozen}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return frozen
