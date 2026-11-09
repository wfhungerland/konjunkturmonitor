"""Rohstoffpreise der Weltbank (Pink Sheet) als statische Monatsreihen für die El-Niño-Auswertung.

Läuft vor dem Datenabruf und schreibt nach data/static/wb_<key>.csv (date,value): Monatspreise in US-Dollar.
Die Weltbank ändert den Link zur Datei jeden Monat; er wird deshalb auf der Seite „Commodity Markets“ gesucht.
Ein gestörter Abruf oder ein unerwarteter Aufbau lässt die vorhandenen Dateien unverändert.
Lizenz: Weltbank-Datensätze stehen unter CC BY 4.0.
"""
from __future__ import annotations

import io
import logging
import re
import urllib.request
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
PAGE = "https://www.worldbank.org/en/research/commodity-markets"
# Schlüssel -> Anfang des Spaltennamens im Blatt „Monthly Prices“ (ohne Groß-/Kleinschreibung)
ITEMS = {"soybeans": "Soybeans", "maize": "Maize", "rice": "Rice, Thai 5%", "wheat": "Wheat, US HRW",
         "cocoa": "Cocoa", "coffee": "Coffee, Robusta", "palmoil": "Palm oil", "sugar": "Sugar, world"}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def parse(xlsx: bytes) -> dict[str, pd.Series]:
    """Monatspreise je Schlüssel aus dem Blatt „Monthly Prices“ (Kopfzeile mit Namen, darunter Einheiten, dann JJJJMmm)."""
    df = pd.read_excel(io.BytesIO(xlsx), "Monthly Prices", header=None, dtype=object)
    head = next(i for i in range(15) if any(str(v).startswith("Crude oil") for v in df.iloc[i].tolist()))  # Namenszeile, darunter Einheiten
    names = [str(v).strip() for v in df.iloc[head].tolist()]
    body = df.iloc[head + 2:]
    per = body[0].astype(str).str.strip()
    ok = per.str.fullmatch(r"\d{4}M\d{2}")
    idx = pd.to_datetime(per[ok].str.replace("M", "-") + "-01")
    out = {}
    for key, start in ITEMS.items():
        col = next((j for j, n in enumerate(names) if n.lower().startswith(start.lower())), None)
        if col is None:
            raise ValueError(f"Spalte „{start}“ fehlt")
        vals = pd.to_numeric(body.loc[ok, col], errors="coerce")
        s = pd.Series(vals.values, index=idx).dropna()
        if len(s) < 240 or (s <= 0).any():
            raise ValueError(f"{key}: unplausible Werte ({len(s)} Monate)")
        out[key] = s
    return out


def update_pinksheet(static: Path) -> None:
    page = _get(PAGE).decode("utf-8", "replace")
    url = next((u for u in re.findall(r'https://thedocs\.worldbank\.org/[^"\s]+\.xlsx', page) if "Historical-Data-Monthly" in u), None)
    if not url:
        raise ValueError("Monatsdatei auf der Seite nicht gefunden")
    for key, s in parse(_get(url)).items():
        pd.DataFrame({"date": s.index.strftime("%Y-%m-%d"), "value": s.round(4).values}).to_csv(static / f"wb_{key}.csv", index=False)
    log.info("Weltbank Pink Sheet: %s", url.rsplit("/", 1)[-1])
