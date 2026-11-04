"""Nachnutzung: Gesamtdownload aller Reihen, Archiv der Kernzahlen mit Revisionshinweis, Feed mit neuen Zahlen.

Das Archiv (data/archive/kernzahlen.csv) hält je Lauf und Kennzahl den angezeigten Wert und den Zeitraum fest.
Es wird vom Workflow mit den Daten committet und wächst um höchstens eine Zeile je Kennzahl und Tag.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path

import pandas as pd

ARCHIVE_COLUMNS = ["stand", "series", "label", "date", "period", "value"]


# ---------------------------------------------------------------------------
# Gesamtdownload
# ---------------------------------------------------------------------------
def write_all_series(data: dict, meta: dict, root: Path, out: Path, stand: str, cite: str, date: str = "") -> dict:
    """Alle Reihen als CSV (lang) und Excel (je Frequenz breit, dazu Verzeichnis mit Metadaten)."""
    from .build import _license, _source_name

    folder = out / "dl"
    folder.mkdir(parents=True, exist_ok=True)
    status = {}
    path = root / "data" / "processed" / "run_status.json"
    if path.exists():
        status = {s["series_id"]: s for s in json.loads(path.read_text(encoding="utf-8")).get("series", [])}
    rows, index = [], []
    for sid in sorted(data):
        s, m = data[sid].dropna(), meta.get(sid)
        if m is None or s.empty:
            continue
        rows.append(pd.DataFrame({"Reihe": sid, "Datum": s.index.strftime("%Y-%m-%d"), "Wert": s.values}))
        index.append({"Reihe": sid, "Titel": m.title, "Einheit": m.unit, "Frequenz": m.frequency, "Bereinigung": m.adjustment,
                      "Bereich": m.block, "Erster Wert": s.index[0].strftime("%Y-%m-%d"), "Letzter Wert": s.index[-1].strftime("%Y-%m-%d"),
                      "Quelle": _source_name(m), "Lizenz": _license(m), "Abruf": (status.get(sid) or {}).get("api_url", "")})
    if not rows:
        return {}
    long = pd.concat(rows, ignore_index=True)
    stem = f"Konjunkturmonitor ({date}) Alle Reihen"
    with open(folder / f"{stem}.csv", "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(stem + "\n")
        long.to_csv(fh, sep=";", decimal=",", index=False)
    idx = pd.DataFrame(index)
    with pd.ExcelWriter(folder / f"{stem}.xlsx", engine="xlsxwriter") as xw:
        info = pd.DataFrame({"Feld": ["Datei", "Inhalt", "Stand", "Zitiervorschlag", "Lizenz", "Aufbau"],
                             "Wert": [stem, "Alle Zeitreihen des Konjunkturmonitors", stand, cite,
                                      "Daten: Lizenz der jeweiligen Quelle (Blatt Verzeichnis). Zusammenstellung: CC BY 4.0, Wolf-Fabian Hungerland",
                                      "Blatt Verzeichnis: Metadaten je Reihe. Blätter Monat, Quartal, Jahr, Woche: Werte breit, eine Spalte je Reihe."]})
        info.to_excel(xw, sheet_name="Info", index=False)
        idx.to_excel(xw, sheet_name="Verzeichnis", index=False)
        for freq, name in (("M", "Monat"), ("Q", "Quartal"), ("A", "Jahr"), ("D", "Tag und Woche")):
            ids = idx.loc[idx["Frequenz"] == freq, "Reihe"].tolist()
            if not ids:
                continue
            wide = long[long["Reihe"].isin(ids)].pivot(index="Datum", columns="Reihe", values="Wert").sort_index()
            wide.reset_index().to_excel(xw, sheet_name=name, index=False)
        for ws in xw.sheets.values():
            ws.set_column(0, 0, 14)
            ws.set_column(1, 12, 18)
    return {"csv": f"dl/{stem}.csv", "xlsx": f"dl/{stem}.xlsx", "n": len(index)}


# ---------------------------------------------------------------------------
# Archiv und Revisionen
# ---------------------------------------------------------------------------
def load_archive(root: Path) -> pd.DataFrame:
    path = root / "data" / "archive" / "kernzahlen.csv"
    if not path.exists():
        return pd.DataFrame(columns=ARCHIVE_COLUMNS)
    return pd.read_csv(path, dtype={"stand": str, "series": str, "date": str})


def update_archive(root: Path, rows: list[dict], stand: str) -> pd.DataFrame:
    """Kernzahlen des heutigen Stands anhängen (ein Eintrag je Kennzahl und Stand) und das Archiv zurückgeben."""
    arch = load_archive(root)
    new = pd.DataFrame([{"stand": stand, "series": r["series"], "label": r["label"], "date": r["date"], "period": r["period"],
                         "value": r["value"]} for r in rows], columns=ARCHIVE_COLUMNS)
    arch = pd.concat([arch[arch["stand"] != stand], new], ignore_index=True).sort_values(["stand", "series"])
    path = root / "data" / "archive" / "kernzahlen.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    arch.to_csv(path, index=False)
    return arch


def mark_revisions(rows: list[dict], arch: pd.DataFrame) -> None:
    """Revisionshinweis: Weicht der Wert für denselben Zeitraum vom zuerst veröffentlichten Wert ab, wird er markiert."""
    if arch.empty:
        return
    for r in rows:
        first = arch[(arch["series"] == r["series"]) & (arch["date"] == r["date"])].sort_values("stand")
        if first.empty:
            continue
        v0 = float(first.iloc[0]["value"])
        d = int(r.get("decimals", 1))
        if round(v0, d) != round(float(r["value"]), d):
            r["revised"] = {"from": round(v0, 4), "stand": first.iloc[0]["stand"]}


def news(arch: pd.DataFrame, stand: str) -> list[dict]:
    """Kennzahlen, deren Zeitraum im jeweiligen Stand erstmals erscheint (neue Veröffentlichung), jüngste zuerst."""
    if arch.empty:
        return []
    out = []
    first_seen = arch.sort_values("stand").drop_duplicates(["series", "date"])
    starts = arch.groupby("series")["stand"].min()
    for _, r in first_seen.iterrows():
        if r["stand"] == starts.get(r["series"]):
            continue  # erster Archivtag einer Kennzahl ist keine Neuigkeit
        out.append({"stand": r["stand"], "series": r["series"], "label": r["label"], "period": r["period"], "value": float(r["value"])})
    out.sort(key=lambda x: (x["stand"], x["label"]), reverse=True)
    return out


def write_feed(items: list[dict], rows: list[dict], site: dict, out: Path) -> None:
    """RSS 2.0 mit den neu veröffentlichten Kennzahlen (höchstens 60 Einträge)."""
    from .answers import num

    by_series = {r["series"]: r for r in rows}
    url = site.get("url", "")
    parts = []
    for it in items[:60]:
        r = by_series.get(it["series"], {})
        unit = r.get("unit", "")
        title = f"{it['label']}, {it['period']}: {num(it['value'], int(r.get('decimals', 1)))} {unit}".strip()
        link = f"{url}#{r.get('topic', '')}"
        pub = format_datetime(datetime.fromisoformat(it["stand"]).replace(hour=12, tzinfo=timezone.utc))
        parts.append(f"<item><title>{escape(title)}</title><link>{escape(link)}</link><guid isPermaLink=\"false\">{escape(it['series'] + '/' + it['period'])}</guid>"
                     f"<pubDate>{pub}</pubDate><description>{escape(title)}. Quelle: Konjunkturmonitor, Stand {it['stand']}.</description></item>")
    xml = ('<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel>'
           f"<title>Konjunkturmonitor: neue Zahlen</title><link>{escape(url)}</link>"
           "<description>Neu veröffentlichte Kennzahlen zur deutschen Wirtschaft</description><language>de-de</language>"
           + "".join(parts) + "</channel></rss>\n")
    (out / "feed.xml").write_text(xml, encoding="utf-8")
