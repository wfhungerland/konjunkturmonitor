"""Wetter (Deutscher Wetterdienst) und Rheinpegel Kaub (PEGELONLINE) als statische Reihen für die Pipeline.

Läuft vor dem Datenabruf (python -m monitor run) und schreibt nach data/static/<key>.csv (date,value):
- dwd_temp_anom: Monatsmittel der Lufttemperatur in Deutschland minus Mittel desselben Kalendermonats 1991 bis 2020, °C.
- dwd_rain_pct: Niederschlag in Deutschland in % des Mittels desselben Kalendermonats 1991 bis 2020.
- dwd_hdd_pct: Heizgradtage (VDI 3807, 20/15 °C), ungewichtetes Mittel aller Stationen, in % des Mittels desselben
  Kalendermonats 2015 bis 2019. Der DWD veröffentlicht keinen Deutschlandwert; Daten ab 2010.
- rhine_kaub: Tagesmittel des Wasserstands am Pegel Kaub, cm. PEGELONLINE liefert nur die letzten 31 Tage; die Reihe wird
  deshalb bei jedem Lauf fortgeschrieben (data/static/rhine_kaub.csv liegt im Repository).
- rhine_lowdays: Tage je Monat mit einem Tagesmittel in Kaub unter 78 cm; rhine_lowdays_year: dasselbe je Kalenderjahr.
  Die Tageswerte seit November 1969 stammen aus den geprüften Pegeldaten der WSV, die die Bundesanstalt für Gewässerkunde
  (BfG) für das R-Paket hyd1d bereitstellt (bis Ende des Vorjahres geprüft); sie werden einmal je Jahr nachgeladen.
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
BFG = "https://hyd1d.bafg.de/downloads/df.gauging_data_latest.RDS"  # geprüfte WSV-Pegeldaten Elbe und Rhein (BfG, hyd1d)
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


def _hdd_month(url: str) -> float | None:
    """Ungewichtetes Mittel der Monatsgradtage aller Stationen einer DWD-Monatsdatei."""
    vals = []
    for z in _get(url).splitlines():
        f = [c.strip() for c in z.split(";")]
        if z.startswith("#") or len(f) < 8:
            continue
        try:
            g = float(f[6])
        except ValueError:
            continue
        if g >= 0:
            vals.append(g)
    return sum(vals) / len(vals) if vals else None


def _hdd(cache: Path, refresh: int = 3) -> pd.Series:
    """Heizgradtage je Monat. Bereits geladene Monate kommen aus dem Zwischenspeicher (data/static/dwd_hdd_raw.csv);
    neu geladen werden nur fehlende Monate und die jüngsten `refresh` Monate, die der DWD noch nachträglich ergänzt."""
    old = pd.read_csv(cache, parse_dates=["date"]).set_index("date")["value"] if cache.exists() else pd.Series(dtype=float)
    files = {}
    for part in ("historical/", "recent/"):
        for name in sorted(set(re.findall(r'href="(gradtage_\d{6}\.csv)"', _get(HDD + part)))):
            files[pd.Timestamp(int(name[9:13]), int(name[13:15]), 1)] = HDD + part + name  # recent überschreibt historical
    newest = sorted(files)[-refresh:]
    out = old.to_dict()
    n = 0
    for d, url in sorted(files.items()):
        if d in out and d not in newest:
            continue
        v = _hdd_month(url)
        n += 1
        if v is not None:
            out[d] = v
    s = pd.Series(out).sort_index()
    _write(cache, s)
    log.info("Heizgradtage: %d Dateien geladen, %d Monate aus dem Zwischenspeicher", n, len(s) - n)
    return s


def update_weather(static: Path) -> None:
    tm = _regional("air_temperature_mean", "tm")
    _write(static / "dwd_temp_anom.csv", tm - _by_month_norm(tm, 1991, 2020))
    rr = _regional("precipitation", "rr")
    _write(static / "dwd_rain_pct.csv", rr / _by_month_norm(rr, 1991, 2020) * 100)
    hdd = _hdd(static / "dwd_hdd_raw.csv")
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
    try:
        s = _bfg_history(s, static / "rhine_kaub_bfg.txt")
    except Exception as e:  # ohne Historie weiter mit den eigenen Werten
        log.warning("Pegel Kaub: BfG-Historie nicht geladen: %s", e)
    _write(path, s)
    low = (s < LOW).groupby([s.index.year, s.index.month]).sum()
    lows = pd.Series(low.values, index=[pd.Timestamp(y, m, 1) for y, m in low.index], dtype=float)
    _write(static / "rhine_lowdays.csv", lows)
    ly = (s < LOW).groupby(s.index.year).sum()
    _write(static / "rhine_lowdays_year.csv", pd.Series(ly.values, index=[pd.Timestamp(y, 1, 1) for y in ly.index], dtype=float).loc["1970":])
    log.info("Pegel Kaub: %d Tage, davon %d neu", len(s), len(set(new) - set(old.index)))


def _bfg_history(s: pd.Series, stamp: Path) -> pd.Series:
    """Tagesmittel Kaub seit 1969 aus den geprüften Pegeldaten (BfG). Nachgeladen, wenn die Reihe noch keine Historie hat
    oder seit dem letzten Abruf ein neues Jahr begonnen hat (die BfG ersetzt dann die ungeprüften Werte des Vorjahres).
    Geprüfte Werte haben Vorrang; danach gelten die eigenen Tagesmittel aus PEGELONLINE."""
    year = datetime.now(timezone.utc).year
    if len(s) and s.index.min() <= pd.Timestamp("1970-01-01") and stamp.exists() and stamp.read_text().strip() == str(year):
        return s
    import tempfile
    import pyreadr
    req = urllib.request.Request(BFG, headers={"User-Agent": "Konjunkturmonitor/1.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read()
    with tempfile.NamedTemporaryFile(suffix=".RDS", delete=False) as f:
        f.write(raw)
    df = pyreadr.read_r(f.name)[None]
    Path(f.name).unlink(missing_ok=True)
    kb = df[df["gauging_station"].astype(str).str.upper() == "KAUB"]
    h = pd.Series(kb["w"].astype(float).values, index=pd.to_datetime(kb["date"])).dropna().sort_index()
    cut = pd.Timestamp(year, 1, 1)  # bis Ende des Vorjahres geprüft; im laufenden Jahr gelten die eigenen Werte, BfG nur für Lücken
    checked, rest = h[h.index < cut], h[(h.index >= cut) & ~h.index.isin(s.index)]
    out = pd.concat([s[s.index >= cut], rest, checked])
    out = out[~out.index.duplicated(keep="first")].sort_index()
    stamp.write_text(str(year))
    log.info("Pegel Kaub: %d Tage aus den geprüften BfG-Daten (%s bis %s)", len(h), h.index.min().date(), h.index.max().date())
    return out


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


def _smard(filt: int, region: str, res: str = "month", since: pd.Timestamp | None = None) -> pd.Series:
    """Werte von SMARD (Bundesnetzagentur): Index der Dateien, dann je Datei die Werte.
    res="month": Monatswerte, Datum = Monatserster; res="day": Tageswerte (ab since)."""
    base = "https://www.smard.de/app/chart_data"
    stamps = json.loads(_get(f"{base}/{filt}/{region}/index_{res}.json"))["timestamps"]
    if since is not None:  # Dateien beginnen mit ihrem Zeitstempel; die letzte vor since wird noch gebraucht
        cut = since.tz_localize("Europe/Berlin").value // 10**6
        older = [t for t in stamps if t < cut]
        stamps = ([max(older)] if older else []) + [t for t in stamps if t >= cut]
    vals = {}
    for ts in stamps:
        for t, v in json.loads(_get(f"{base}/{filt}/{region}/{filt}_{region}_{res}_{ts}.json")).get("series", []):
            if v is not None:
                d = pd.Timestamp(t, unit="ms", tz="Europe/Berlin")
                vals[pd.Timestamp(d.year, d.month, 1) if res == "month" else pd.Timestamp(d.year, d.month, d.day)] = float(v)
    s = pd.Series(vals).sort_index()
    return s[s.index >= since] if since is not None else s


def update_smard(static: Path) -> None:
    """Stromverbrauch (Netzlast) und Großhandelspreis Day-Ahead DE/LU, Lizenz CC BY 4.0.
    Monatswerte (TWh, €/MWh) seit 2015 und Tageswerte (GWh, €/MWh) der letzten drei Jahre."""
    load = _smard(410, "DE") / 1e6
    _write(static / "smard_load.csv", load)
    price = _smard(4169, "DE-LU")
    _write(static / "smard_price.csv", price)
    since = pd.Timestamp.now().normalize() - pd.DateOffset(years=3)
    load_d = _smard(410, "DE", "day", since) / 1e3
    _write(static / "smard_load_d.csv", load_d)
    price_d = _smard(4169, "DE-LU", "day", since)
    _write(static / "smard_price_d.csv", price_d)
    log.info("SMARD: %d Monate Verbrauch, %d Monate Preis, %d Tage Verbrauch, %d Tage Preis", len(load), len(price), len(load_d), len(price_d))


MAUT_DAILY = ("https://www.destatis.de/DE/Themen/Branchen-Unternehmen/Industrie-Verarbeitendes-Gewerbe/Publikationen/"
              "Downloads-Konjunktur/statistischer-bericht-lkw-maut-fahrleistungsindex-5421901.xlsx?__blob=publicationFile")


def update_maut_daily(static: Path) -> None:
    """Täglicher Lkw-Maut-Fahrleistungsindex (Destatis/BALM, experimentell), kalender- und saisonbereinigt,
    2021 = 100. Quelle: Statistischer Bericht, Blatt csv-42191-b01; wöchentlich donnerstags aktualisiert."""
    import io
    req = urllib.request.Request(MAUT_DAILY, headers={"User-Agent": "Konjunkturmonitor/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
    df = pd.read_excel(io.BytesIO(raw), sheet_name="csv-42191-b01")
    df = df[df["Saisonbereinigung"].astype(str).str.contains("KSB")]
    s = pd.Series(pd.to_numeric(df["Indexwert"], errors="coerce").values, index=pd.to_datetime(df["Datum"]))
    _write(static / "maut_daily.csv", s)
    log.info("Lkw-Maut täglich: %d Tage bis %s", s.dropna().size, s.dropna().index.max().date())


def update_gas_storage(static: Path) -> None:
    """Füllstand der deutschen Gasspeicher (GIE AGSI), Tageswerte in % der Arbeitsgaskapazität.
    Braucht den API-Schlüssel in der Umgebungsvariablen GIE_API_KEY; Quellenangabe GIE (AGSI) ist Pflicht."""
    import os
    key = os.environ.get("GIE_API_KEY", "").strip()
    if not key:
        log.info("Gasspeicher: kein GIE_API_KEY gesetzt, übersprungen")
        return
    vals, page, last = {}, 1, 1
    to = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    while page <= last:
        req = urllib.request.Request(f"https://agsi.gie.eu/api?country=de&from=2015-01-01&to={to}&size=300&page={page}",
                                     headers={"User-Agent": "Konjunkturmonitor/1.0", "x-key": key})
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read().decode("utf-8"))
        last = int(j.get("last_page") or 1)
        for row in j.get("data", []):
            try:
                vals[pd.Timestamp(row["gasDayStart"])] = float(row["full"])
            except (KeyError, TypeError, ValueError):
                continue
        page += 1
    _write(static / "gie_storage_de.csv", pd.Series(vals))
    log.info("Gasspeicher: %d Tage", len(vals))


BBKRT = ("https://api.statistiken.bundesbank.de/rest/data/BBKRT/Q.DE.Y.A.AG1.CA010.A.I"
         "?startPeriod=2004-Q1&startVintage=2005-01-01&detail=dataonly")


def gdp_revisions(text: str) -> tuple[pd.Series, pd.Series]:
    """Aus allen Datenständen der Echtzeitdatenbank (BIP, preis-, saison- und kalenderbereinigt) die Wachstumsrate
    ggü. dem Vorquartal je Quartal: in der ersten Veröffentlichung und im jüngsten Datenstand, jeweils in %."""
    lines = [l for l in text.splitlines() if l.strip()]
    head = [h.strip().lstrip("\ufeff") for h in lines[0].split(";")]
    ix = {h: i for i, h in enumerate(head)}
    rows = []
    for l in lines[1:]:
        f = l.split(";")
        try:
            vint = pd.Timestamp(int(f[ix["BBK_RTD_REL_YEAR"]]), int(f[ix["BBK_RTD_REL_MONTH"]]), int(f[ix["BBK_RTD_REL_DAY"]]))
            rows.append((vint, pd.Period(f[ix["TIME_PERIOD"]], "Q").start_time, float(f[ix["OBS_VALUE"]])))
        except (KeyError, ValueError, IndexError):
            continue
    df = pd.DataFrame(rows, columns=["vintage", "period", "value"])
    first, latest = {}, None
    for v, g in df.sort_values("vintage").groupby("vintage", sort=True):
        s = g.set_index("period")["value"].sort_index()
        q = (s / s.shift(1) - 1) * 100
        for p in q.dropna().index:
            first.setdefault(p, round(float(q[p]), 2))  # erster Datenstand, in dem das Quartal vorkommt
        latest = q.dropna().round(2)
    return pd.Series(first).sort_index(), latest


def update_revisions(static: Path) -> None:
    """Revisionsanzeiger: erste Meldung und heutiger Stand des BIP-Wachstums (Echtzeitdatenbank der Bundesbank)."""
    req = urllib.request.Request(BBKRT, headers={"User-Agent": "Konjunkturmonitor/1.0", "Accept": "application/vnd.sdmx.data+csv;version=1.0.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        first, latest = gdp_revisions(r.read().decode("utf-8", "replace"))
    _write(static / "gdp_rt_first.csv", first)
    _write(static / "gdp_rt_latest.csv", latest)
    _write(static / "gdp_rt_rev.csv", (latest - first).dropna())
    log.info("Echtzeitdaten BIP: %d Quartale mit erster Meldung", len(first))


def _potential(static: Path) -> None:
    from .potenzial import update_potential
    update_potential(static)


def _pinksheet(static: Path) -> None:
    from .pinksheet import update_pinksheet
    update_pinksheet(static)


def update_all(root: Path) -> None:
    static = root / "data" / "static"
    static.mkdir(parents=True, exist_ok=True)
    for name, f in (("Wetter", update_weather), ("Pegel", update_pegel), ("El Niño", update_enso), ("SMARD", update_smard), ("Lkw-Maut täglich", update_maut_daily), ("Gasspeicher", update_gas_storage), ("Echtzeitdaten", update_revisions), ("Potenzial", _potential), ("Rohstoffpreise Weltbank", _pinksheet)):
        try:
            f(static)
        except Exception as e:  # ein gestörter Abruf hält den Lauf nicht auf
            log.warning("%s nicht aktualisiert: %s", name, e)
