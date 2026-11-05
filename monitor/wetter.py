"""Wetter (Deutscher Wetterdienst) und Rheinpegel Kaub (PEGELONLINE) als statische Reihen für die Pipeline.

Läuft vor dem Datenabruf (python -m monitor run) und schreibt nach data/static/<key>.csv (date,value):
- dwd_temp_anom: Monatsmittel der Lufttemperatur in Deutschland minus Mittel desselben Kalendermonats 1991 bis 2020, °C.
- dwd_rain_pct: Niederschlag in Deutschland in % des Mittels desselben Kalendermonats 1991 bis 2020.
- dwd_hdd_pct: Heizgradtage (VDI 3807, 20/15 °C), ungewichtetes Mittel aller Stationen, in % des Mittels desselben
  Kalendermonats 2015 bis 2019. Der DWD veröffentlicht keinen Deutschlandwert; Daten ab 2010.
- rhine_kaub: Tagesmittel des Wasserstands am Pegel Kaub, cm. PEGELONLINE liefert nur die letzten 31 Tage; die Reihe wird
  deshalb bei jedem Lauf fortgeschrieben (data/static/rhine_kaub.csv liegt im Repository).
- rhine_lowdays: Tage je Monat mit einem Tagesmittel in Kaub unter 78 cm.
Quellen: DWD Climate Data Center (opendata.dwd.de), Nutzungsbedingungen nach GeoNutzV mit Quellenangabe;
PEGELONLINE der Wasserstraßen- und Schifffahrtsverwaltung des Bundes, Datenlizenz Deutschland – Zero – Version 2.0.
Fehler eines Abrufs halten die übrigen nicht auf; vorhandene Dateien bleiben dann unverändert.
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CDC = "https://opendata.dwd.de/climate_environment/CDC/"
REGIONAL = CDC + "regional_averages_DE/monthly/"
HDD = CDC + "derived_germany/techn/monthly/heating_degreedays/hdd_3807/"
PEGEL = "https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations/KAUB/W/measurements.json?start=P31D"
LOW = 78  # cm, Schwelle nach IfW Kiel
log = logging.getLogger(__name__)


def _get(url: str, tries: int = 5) -> str:
    """Abruf mit Wiederholung; der DWD-Server bricht Verbindungen gelegentlich ab."""
    import time
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Konjunkturmonitor/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("latin-1")
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(2 * 2 ** k)


def _write(path: Path, s: pd.Series) -> None:
    s = s.dropna().sort_index()
    pd.DataFrame({"date": s.index.strftime("%Y-%m-%d"), "value": s.round(3).values}).to_csv(path, index=False)


def _regional(folder: str, code: str) -> pd.Series:
    """Monatswerte der Spalte „Deutschland“ aus den zwölf Monatsdateien des DWD."""
    vals = {}
    for m in range(1, 13):
        lines = _get(f"{REGIONAL}{folder}/regional_averages_{code}_{m:02d}.txt").splitlines()
        head = next(i for i, z in enumerate(lines) if z.startswith("Jahr;"))
        cols = [c.strip() for c in lines[head].split(";")]
        de = cols.index("Deutschland")
        for z in lines[head + 1:]:
            f = [c.strip() for c in z.split(";")]
            if len(f) > de and f[0].isdigit() and f[de]:
                vals[pd.Timestamp(int(f[0]), int(f[1]), 1)] = float(f[de])
    return pd.Series(vals).sort_index()


def _by_month_norm(s: pd.Series, y0: int, y1: int) -> pd.Series:
    base = s[(s.index.year >= y0) & (s.index.year <= y1)]
    norm = base.groupby(base.index.month).mean()
    return pd.Series([norm.get(d.month) for d in s.index], index=s.index)


def _hdd() -> pd.Series:
    out = {}
    for part in ("historical/", "recent/"):
        for name in sorted(set(re.findall(r'href="(gradtage_\d{6}\.csv)"', _get(HDD + part)))):
            vals = []
            for z in _get(HDD + part + name).splitlines():
                f = [c.strip() for c in z.split(";")]
                if z.startswith("#") or len(f) < 8:
                    continue
                try:
                    g = float(f[6])
                except ValueError:
                    continue
                if g >= 0:
                    vals.append(g)
            if vals:
                out[pd.Timestamp(int(name[9:13]), int(name[13:15]), 1)] = sum(vals) / len(vals)
    return pd.Series(out).sort_index()


def update_weather(static: Path) -> None:
    tm = _regional("air_temperature_mean", "tm")
    _write(static / "dwd_temp_anom.csv", tm - _by_month_norm(tm, 1991, 2020))
    rr = _regional("precipitation", "rr")
    _write(static / "dwd_rain_pct.csv", rr / _by_month_norm(rr, 1991, 2020) * 100)
    hdd = _hdd()
    _write(static / "dwd_hdd_pct.csv", hdd / _by_month_norm(hdd, 2015, 2019) * 100)
    log.info("Wetter: %d Monate Temperatur, %d Monate Heizgradtage", len(tm), len(hdd))


def update_pegel(static: Path) -> None:
    days = defaultdict(list)
    for m in json.loads(_get(PEGEL)):
        if m.get("value") is not None:
            days[m["timestamp"][:10]].append(float(m["value"]))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    oldest = min(days) if days else None
    new = {pd.Timestamp(d): sum(v) / len(v) for d, v in days.items() if d < today and not (d == oldest and len(v) < 90)}
    path = static / "rhine_kaub.csv"
    old = pd.read_csv(path, parse_dates=["date"]).set_index("date")["value"] if path.exists() else pd.Series(dtype=float)
    s = pd.concat([old, pd.Series(new)])
    s = s[~s.index.duplicated(keep="last")].sort_index()
    _write(path, s)
    low = (s < LOW).groupby([s.index.year, s.index.month]).sum()
    lows = pd.Series(low.values, index=[pd.Timestamp(y, m, 1) for y, m in low.index], dtype=float)
    _write(static / "rhine_lowdays.csv", lows)
    log.info("Pegel Kaub: %d Tage, davon %d neu", len(s), len(set(new) - set(old.index)))


def update_enso(static: Path) -> None:
    """RONI der NOAA; Datum ist der mittlere Monat des Dreimonatszeitraums (DJF -> Januar)."""
    seas = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    vals = {}
    for z in _get("https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt").splitlines():
        f = z.split()
        if len(f) >= 3 and f[0] in seas and f[1].isdigit():
            try:
                vals[pd.Timestamp(int(f[1]), seas.index(f[0]) + 1, 1)] = float(f[2])
            except ValueError:
                continue
    _write(static / "enso_roni.csv", pd.Series(vals))
    log.info("RONI: %d Monate", len(vals))


def update_all(root: Path) -> None:
    static = root / "data" / "static"
    static.mkdir(parents=True, exist_ok=True)
    for name, f in (("Wetter", update_weather), ("Pegel", update_pegel), ("El Niño", update_enso)):
        try:
            f(static)
        except Exception as e:  # ein gestörter Abruf hält den Lauf nicht auf
            log.warning("%s nicht aktualisiert: %s", name, e)
