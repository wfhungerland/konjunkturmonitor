"""Erfolgsbilanz der Signale: Hätte ein Signal die Rezessionen nach der Datierung des Sachverständigenrats angezeigt?

Ein Signal ist eine Folge von Monaten, in denen die Regel erfüllt ist; Folgen mit weniger als sechs Monaten Abstand
zählen als eine. Ein Signal gilt als Treffer, wenn es im Fenster von zwölf Monaten vor dem Beginn (Hoch) bis zwölf
Monate nach dem Ende (Tief) einer Rezession aktiv ist. Vorlauf: Monate vom Beginn des Signals bis zum Beginn der
Rezession (negativ: das Signal kam erst danach). Signale, die kein solches Fenster berühren, stehen als „Signal ohne
Rezession“ in der Liste.
Die Rechnung nutzt die heutigen Datenstände; in Echtzeit sahen die Werte teils anders aus.
"""
from __future__ import annotations

import pandas as pd

WINDOW = 12  # Monate vor dem Hoch, ab denen ein Signal als Vorwarnung zählt
GAP = 6  # Monate: kürzere Pausen verbinden zwei Folgen zu einem Signal


def episodes(flag: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Beginn und Ende jeder Signalfolge."""
    on = flag[flag.fillna(False).astype(bool)].index
    out = []
    for d in on:
        if out and (d.year - out[-1][1].year) * 12 + d.month - out[-1][1].month <= GAP:
            out[-1] = (out[-1][0], d)
        else:
            out.append((d, d))
    return out


def evaluate(flag: pd.Series, recessions: list[dict], min_history: int = 0) -> dict:
    """Treffer, Vorlauf und Signale ohne Rezession für eine Regel (flag: True, wenn die Regel erfüllt ist)."""
    flag = flag.dropna()
    if flag.empty:
        return {}
    first = flag.index[0] + pd.DateOffset(months=min_history)
    flag = flag[flag.index >= first]
    eps = episodes(flag)
    rows, used = [], set()
    for r in recessions:
        peak, trough = pd.Timestamp(r["peak"]), pd.Timestamp(r["trough"])
        w0, w1 = peak - pd.DateOffset(months=WINDOW), trough + pd.DateOffset(months=WINDOW)
        if w0 < first:
            continue  # Rezession liegt vor dem Beginn der Reihe
        hit = next((e for e in eps if e[0] <= w1 and e[1] >= w0), None)
        if hit is not None:
            used.add(hit)
        rows.append({"peak": peak.strftime("%Y-%m"), "trough": trough.strftime("%Y-%m"),
                     "signal": hit[0].strftime("%Y-%m") if hit is not None else None,
                     "lead": (peak.year - hit[0].year) * 12 + peak.month - hit[0].month if hit is not None else None})
    false = [e[0].strftime("%Y-%m") for e in eps if e not in used]
    return {"from": flag.index[0].strftime("%Y-%m"), "to": flag.index[-1].strftime("%Y-%m"), "rows": rows, "false": false,
            "hits": sum(1 for r in rows if r["signal"]), "n": len(rows)}
