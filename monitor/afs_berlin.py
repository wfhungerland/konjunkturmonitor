"""Verbraucherpreise Berlin aus dem Statistischen Bericht M I 2 des Amts für Statistik Berlin-Brandenburg.

Läuft vor dem Datenabruf und schreibt Indexstände (2020 = 100) nach data/static/afs_vpi_be_<teil>.csv (date,value):
gesamt (Blatt 6), nahrung (Blatt 7, Nahrungsmittel und alkoholfreie Getränke), energie (Blatt 8, Energie).
Die Blätter haben je Reihe einen Block: Name, „Indexstand“, Jahreszeilen (Jahr, Januar bis Dezember, Durchschnitt),
dann „Veränderung …“. Gelesen werden nur die Indexstände. Ältere Werte aus der vorhandenen Datei bleiben erhalten,
neuere Werte aus dem Bericht ersetzen sie. Ein gestörter Abruf oder ein unerwarteter Aufbau lässt die Dateien unverändert.
"""
from __future__ import annotations

import io
import logging
import re
import urllib.request
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)
PAGE = "https://www.statistik-berlin-brandenburg.de/m-i-2-m"
PARTS = {"gesamt": ("6", "Verbraucherpreisindex"), "nahrung": ("7", "Nahrungsmittel und alkoholfreie Getränke"), "energie": ("8", "Energie")}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "konjunkturmonitor"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


def _num(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def index_block(sheet: pd.DataFrame, name: str) -> pd.Series:
    """Indexstände des Blocks, dessen Namenszeile genau name lautet (Leerzeichen und Zeilenumbrüche egal)."""
    norm = lambda v: re.sub(r"\s+", " ", str(v)).strip() if pd.notna(v) else ""
    rows = sheet.index.tolist()
    hit = lambda v: bool(re.fullmatch(re.escape(name) + r"[\s\d¹²³⁴*)]*", v)) or (len(name) > 20 and v.startswith(name[:25]))
    head = next((i for i in rows if hit(norm(sheet.at[i, 1])) or hit(norm(sheet.at[i, 0]))), None)
    if head is None:
        raise ValueError(f"Block „{name}“ nicht gefunden")
    k = rows.index(head) + 1
    while k < len(rows) and "Indexstand" not in norm(sheet.at[rows[k], 1]) + norm(sheet.at[rows[k], 0]):
        k += 1
    out = {}
    for i in rows[k + 1:]:
        first = norm(sheet.at[i, 0])
        if not first and not any(norm(sheet.at[i, c]) for c in range(1, 13)):
            continue  # Leerzeile im Block
        if not re.fullmatch(r"\d{4}", first):
            break  # „Veränderung …“ oder nächster Block
        year = int(first)
        for m in range(1, 13):
            v = _num(sheet.at[i, m])
            if v is not None:
                out[pd.Timestamp(year, m, 1)] = v
    s = pd.Series(out, dtype=float).sort_index()
    # Tippfehler im Bericht (etwa 2926 statt 2026) fallen hier heraus: nur Jahre bis zum laufenden
    return s[s.index <= pd.Timestamp.now()]


def parse(xlsx: bytes) -> dict[str, pd.Series]:
    x = pd.ExcelFile(io.BytesIO(xlsx))
    out = {}
    for key, (sheet, name) in PARTS.items():
        s = index_block(pd.read_excel(x, sheet, header=None), name)
        if len(s) < 24 or not s.between(40, 300).all():
            raise ValueError(f"{key}: unplausible Werte ({len(s)} Monate)")
        out[key] = s
    return out


def update_afs_berlin(static: Path) -> None:
    page = _get(PAGE).decode("utf-8", "replace")
    urls = re.findall(r'https://download\.statistik-berlin-brandenburg\.de/[^"\s]+_\d{4}m\d{2}_BE\.xlsx', page)
    if not urls:
        raise ValueError("kein Bericht für Berlin auf der Seite gefunden")
    url = max(urls, key=lambda u: re.search(r"_(\d{4}m\d{2})_BE", u).group(1))
    for key, s in parse(_get(url)).items():
        f = static / f"afs_vpi_be_{key}.csv"
        old = pd.read_csv(f, parse_dates=["date"]).set_index("date")["value"] if f.exists() else pd.Series(dtype=float)
        merged = pd.concat([old[~old.index.isin(s.index)], s]).sort_index()
        pd.DataFrame({"date": merged.index.strftime("%Y-%m-%d"), "value": merged.values}).to_csv(f, index=False)
    log.info("AfS Berlin: %s", url.rsplit("/", 1)[-1])
