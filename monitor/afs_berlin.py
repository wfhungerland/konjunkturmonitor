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


# BIP im ersten Halbjahr je Land: Arbeitskreis VGR der Länder, eine Excel-Datei je Jahr (Blatt „1.Hj<Jahr>“),
# Spalten Land, Veränderung in jeweiligen Preisen, preisbereinigt. Jedes Jahr kommt ein Wert dazu; frühere bleiben stehen.
VGRDL = "https://www.statistikportal.de/de/vgrdl/ergebnisse-laenderebene/bruttoinlandsprodukt-bruttowertschoepfung"
H1_ROWS = {"de30": "Berlin", "de": "Deutschland"}


def parse_h1(xlsx: bytes) -> tuple[int, dict[str, float]]:
    x = pd.ExcelFile(io.BytesIO(xlsx))
    sheet = next(s for s in x.sheet_names if re.search(r"Hj\s*\d{4}", s))
    year = int(re.search(r"(\d{4})", sheet).group(1))
    df = pd.read_excel(x, sheet, header=None)
    out = {}
    for key, name in H1_ROWS.items():
        hit = df[df[0].astype(str).str.strip() == name]
        if hit.empty:
            raise ValueError(f"Zeile {name} fehlt")
        v = _num(hit.iloc[0, 2])
        if v is None or not -15 < v < 15:
            raise ValueError(f"{name}: unplausibler Wert {hit.iloc[0, 2]!r}")
        out[key] = round(v, 1)
    return year, out


def update_vgrdl_h1(static: Path) -> None:
    page = _get(VGRDL).decode("utf-8", "replace")
    links = re.findall(r'href="([^"]*vgrdl_hjr[^"]*\.xlsx)"', page)
    if not links:
        raise ValueError("keine Halbjahresdatei auf der Seite gefunden")
    url = sorted(links)[-1]
    url = url if url.startswith("http") else "https://www.statistikportal.de" + url
    year, vals = parse_h1(_get(url))
    for key, v in vals.items():
        f = static / f"vgrdl_h1_{key}.csv"
        old = pd.read_csv(f, parse_dates=["date"]).set_index("date")["value"] if f.exists() else pd.Series(dtype=float)
        old[pd.Timestamp(year, 1, 1)] = v
        old = old.sort_index()
        pd.DataFrame({"date": old.index.strftime("%Y-%m-%d"), "value": old.values}).to_csv(f, index=False)
    log.info("VGR der Länder, 1. Halbjahr %s: %s", year, vals)
