# Konjunkturmonitor

Wie steht es um die deutsche Wirtschaft? Kennzahlen, Antworten in ganzen Sätzen und gut 90 Abbildungen, jeden Werktag neu aus amtlichen und offenen Daten.

Seite: https://wfhungerland.github.io/konjunkturmonitor/

## Aufbau

Eine lange Seite, deutsch unter `/` und englisch unter `/en/` (Sprachschalter unter dem Titel).

- **Kopfzeile (fixiert):** Titel, Sprachschalter und Stand; alle Themen als Links; Suche mit Vorschlägen (Taste `/`); Knopf zum Aus- und Einklappen aller Abbildungen.
- **Start:** zwei bis drei Sätze zur Gesamtlage, „Heute neu“, sechs Kennzahl-Kacheln mit Fünfjahresverlauf, alle Kennzahlen als Tabelle (aufklappbar).
- **Teil I Konjunktur, Teil II Analysen, Teil III Geopolitik, Teil IV Struktur, Teil V Anhang, Termine:** je Abschnitt eine Frage als Überschrift, ein Antwortsatz aus den Daten mit Erläuterung, eine Leitabbildung und weitere Abbildungen zum Aufklappen. Ab 1240 px Breite läuft links die Liste der Abbildungen des Abschnitts mit.
- **Diese Woche neu:** Abbildungen mit neuen Daten in den letzten sieben Tagen.
- **Quellen und Hinweise:** Methodik, Quellen und Lizenzen, fehlende Indikatoren, Gesamtdownloads, Abrufstatus, Zitiervorschlag.

Jede Abbildung hat Nummer, Unterfrage, Sätze zum jüngsten Stand, Titel, Erläuterung in der Randspalte, Quelle und Lizenz sowie das Menü „Download und Link“ (XLSX, PPTX, PNG, CSV, Stata, Link kopieren).

## Daten

| Thema | Quelle |
|---|---|
| Wachstum | Eurostat `namq_10_gdp` (BIP, Beiträge, Verwendung, Deflatoren), `namq_10_an6` (Investitionen nach Anlagearten) |
| Preise | Bundesbank `BBDP1` (VPI insgesamt, Kernrate, Bestandteile, HVPI, Außenhandelspreise), Eurostat `sts_inppd_m`; Inflationsbeiträge eigene Berechnung |
| Arbeit | Bundesbank `BBDL1` (BA-Reihen, Erwerbstätige, SV-Beschäftigte), Eurostat `namq_10_pe`; Kurzarbeit-Äquivalente aus der BA-Statistik (`data/static`) |
| Industrie und Bau | Bundesbank `BBDE1` (Produktion, Aufträge, Umsatz, Bau) |
| Konsum | Bundesbank `BBDE1` (Einzelhandel, Gastgewerbe, Pkw-Zulassungen), Destatis GENESIS `45212-0005` (Sortimente), Eurostat `ei_bsco_m` |
| Export | Bundesbank `BBDA1`, Eurostat `bop_c6_m` (Leistungsbilanz); Exportähnlichkeit eigene Berechnung aus UN Comtrade (`data/static`) |
| Stimmung | Eurostat, EU-Unternehmensumfragen (`ei_bssi_m_r2`, `ei_bsin_m_r2`, `ei_bsin_q_r2`, `ei_bsse_m_r2`, `ei_bsrt_m_r2`, `ei_bsbu_m_r2`) |
| Insolvenzen | Destatis GENESIS `52411`, `52311` |
| Zinsen und Energie | Bundesbank `BBSIS` (Zinsstruktur), FRED (`MCOILBRENTEU` der U.S. EIA, `PNGASEUUSDM` des IWF) |
| Aktivitätsindex | Bundesbank `BBDE1` (Wochenreihe WAI) |
| Struktur | Eurostat (`nama_10_gdp`, `namq_10_lp_ulc`, `namq_10_a10_e`, `demo_gind`); AMECO-Produktionspotenzial (über DBnomics) und OECD-Körperschaftsteuersätze als statische Dateien, von Hand zu aktualisieren |
| Geopolitik | Geopolitical Risk Index (Caldara und Iacoviello), werktäglich; von Hand nach neuen Ausgaben (`python -m monitor.geopolitik <quelle> <datei>`, Quelle leiden, sipri, cow, kiel oder gta); werktäglich: Exporte nach Russland und Nachbarländern (Eurostat Comext), Produktion von Waffen und Munition (Eurostat `sts_inpr_m`, C254): Universität Leiden, Russian Operations Against Europe Dataset (CC BY 4.0), SIPRI Military Expenditure Database, Correlates of War National Material Capabilities v7.0, Kiel Ukraine Support Tracker, Global Trade Alert (Export aller Eingriffe) |
| Kalender | `data/static/kalender.yaml`: Termine nach dem üblichen Rhythmus der Quellen, geschätzt |
| Prognosen | `data/static/prognosen.yaml`, nur veröffentlichte Werte mit Link |
| Gemeinschaftsdiagnose | `data/static/gd_prognosen.csv`: Prognosen der Wirtschaftsforschungsinstitute 1950 bis Frühjahr 2026 mit Fundstelle je Wert, abgeleitet aus den Gutachten; die Reihen der Abbildungen erzeugt `python -m monitor.gd` |
| Karten | Ländergrenzen © GeoBasis-DE / BKG (VG2500), Datenlizenz Deutschland – Namensnennung 2.0, vereinfacht (`data/static/vg2500_laender.json`) |

Lizenzpflichtige Reihen bleiben draußen, etwa Macrobond, die PMI von S&P Global, GfK-Detailreihen und Terminpreise. Die ifo-Zeitreihen setzen eine Anmeldung voraus. Die Stimmung kommt deshalb aus den offenen EU-Umfragen.

## Darstellung

- **Schrift:** Source Sans 3 in vier Schnitten, mitgeliefert unter `monitor/static/fonts/` (SIL Open Font License); keine fremden Server.
- **Größen:** 12, 13,5, 15, 17, 19 und 26 px, Kennzahlen 32 px.
- **Farben:** Text außerhalb der Grafiken schwarz, Links ohne Unterstrich. Datenfarben nur in Grafiken, erste Reihe #002060. Rot (#C00000) nur für Warnsignale: ungünstige Anstiege und Schwellen. Die Nulllinie ist schwarz.
- **Grafiken (Plotly):** Werteachse rechts, runde Schritte, waagerechte Gitterlinien, Einheit über der obersten Zahl, keine Werkzeugleiste. Die hellen Flächen für jedes zweite Kalenderjahr sind standardmäßig aus, weil sie am rechten Rand wie eine Rezession wirkten. Der Schalter „Jahresflächen“ unter den Kennzahlen blendet sie ein (die Wahl merkt sich der Browser); das laufende Jahr bleibt dabei immer frei. `layout: year_bands: true` schaltet sie für alle ein.
- **Tendenz:** ▲ ▼ ● (gestiegen, gesunken, unverändert), blau günstig, rot ungünstig; in der Tabelle `kind: rate` als Differenz, `kind: level` prozentual; `up_bad: true` färbt einen Anstieg rot.
- **Kurzzeichen:** Jede Abbildung heißt nach Kapitel und Platz, etwa „Preise-3“ (Anker `#preise-3`, englisch „Prices-3“). Abweichende Kapitelkürzel stehen als `code:` am Kapitel in `monitor.yaml` und `data/static/en.yaml`. Alte Links `#abb-12` lenkt die Seite um.
- **Fazit:** Der Knopf im Kopf zeigt einen regelbasierten Urteilssatz (`answers.fazit`) und die Urteile an den Kacheln; ohne ihn bleibt die Seite neutral. Die Wahl merkt sich der Browser.
- **Abkürzungen:** In Sätzen ausgeschrieben (`monitor/ausschreiben.py`, nach der Satzprüfung); in Köpfen, Einheiten und Kacheln gepunktet unterstrichen mit Erklärung beim Darauftippen (`GLOSSAR`).
- **Grafik | Tabelle:** Zeitreihen-Grafiken haben oben rechts einen Umschalter; die Tabelle zeigt die letzten zwölf Werte, jüngster zuerst.
- **Vorschaubilder:** `node monitor/previews.js site` fotografiert nach dem Bau jede einfache Zeitreihen-Grafik (breit und Handy, WebP, zusammen rund 6 MB) und trägt die Liste in die Seite ein. Die Seite zeigt zuerst das Bild und lädt die lebendige Grafik beim Überfahren, Antippen oder Bedienen. Ohne diesen Lauf, bei Jahresflächen und auf Einbettseiten zeichnet sie sofort.

Weitere Schalter stehen im Bereich `layout` von `monitor.yaml`; jeder lässt sich einzeln mit `false` zurücknehmen:
- `start_table`: Kennzahlentabelle statt Fragekarten
- `minimal`: ohne Rahmen; Erläuterungen kursiv in der Randspalte
- `direct_labels`: „Jüngste Werte einblenden“ am Linienende
- `small_multiples`, `compare_band`, `uniform_years`, `lead_chart_only`, `overview`, `red_zero_line`

Die Seite enthält die Kernzahlen auch als statisches HTML und ein Vorschaubild (`vorschau.png`). Impressum und Datenschutzerklärung liegen in `monitor/templates/`. Eigene Texte und Abbildungen stehen unter CC BY 4.0.

### Quellenweg und Lizenzgrenzen

Alle Reihen werden bei jedem Lauf direkt bei der Quelle abgerufen: Bundesbank (SDMX-REST), Eurostat (JSON-API), Destatis (GENESIS-Webservice, Zugang über Repository-Secrets), FRED (CSV). Statische Reihen in `data/static` (AMECO, OECD-Steuersätze, Kartengrenzen, Kalenderregeln, Hinweise auf Sondereffekte) werden von Hand aktualisiert; der Abrufstand steht jeweils im Katalog (`note`). Nicht aufgenommen sind Daten, deren Weiterverbreitung eine Lizenz erfordert (ifo, ZEW, S&P Global PMI, GfK/NIM, HDE, IAB-Barometer, IWH-Insolvenztrend, EEX-Terminpreise, RWI/ISL-Containerindex), und Größen ohne abrufbare Zeitreihe (Unterbeschäftigung der BA, Finanzlage der Sozialversicherung, Investitionshemmnisse, Zerlegung des Produktionspotenzials). Die Seite nennt diese Lücken im Abschnitt „Was fehlt und warum“.

Die Zuordnung der Abschnitte zu den Teilen steht je Abschnitt in `monitor.yaml` (`part`: konjunktur, analysen, struktur, anhang, service). Teil II Analysen sammelt eigene Auswertungen wie Rezessionssignal, Konjunkturuhr, Revisionsanzeiger und Exportähnlichkeit. Texte für die englische Seite stehen in `data/static/en.yaml`, Satzvorlagen in `data/static/saetze.yaml`.

## Downloads

Ein Export der ganzen Seite als Word-Datei war gebaut, ist aber auf Wiedervorlage; der Code liegt im Git-Verlauf (`monitor/worddoc.py`, `monitor/shots.py`, zuletzt in Commit 0acaf59).

Zu jeder Abbildung erzeugt der Lauf Excel (Daten, Diagramm, Info), eine PowerPoint-Folie mit bearbeitbarem Diagramm, CSV und eine Stata-Datei (`.dta`, Version 118, mit Variablenlabels; `site/dl/`); das PNG entsteht im Browser. Die Folie übernimmt Format und Aufteilung des vorgegebenen Folienmasters (16:9, grauer Rahmen, Übertitel, Titel, Quellenzeile), aber ohne Logo und Behördenkennzeichnung.

### Gesamtdownload, Archiv und Feed

`dl/konjunkturmonitor_alle_reihen.xlsx` und `.csv` enthalten alle Reihen mit Verzeichnis (Titel, Einheit, Bereinigung, Quelle, Lizenz, Abruf-URL). Jeder Lauf schreibt die Kernzahlen der Tabelle mit Stand und Zeitraum nach `data/archive/kernzahlen.csv`; der Workflow committet die Datei. Weicht ein Wert später für denselben Zeitraum vom zuerst veröffentlichten ab, markiert die Tabelle ihn mit „r“. Neu erschienene Zeiträume stehen als „Heute neu“ über der Tabelle und im Feed `feed.xml` (RSS 2.0).

## Technik

Datenabruf, Katalogformat und Pipeline kommen aus [konjunkturwolf](https://github.com/wfhungerland/konjunkturwolf) (Paketabhängigkeit). Dieses Repo enthält nur Katalog (`series.yaml`), Inhalte (`monitor.yaml`), statische Daten und die Seite (`monitor/`).

```bash
pip install -e ".[dev]"
```

```bash
python -m monitor run
```

```bash
python -m monitor build
```

`run` holt die Daten und baut die Seite. `build` baut nur die Seite aus `data/processed`.

Der Workflow `update.yml` läuft werktags zweimal (7:23 und 12:23 UTC), bei Änderungen auf `main`, in Pull Requests und von Hand. Er committet die Daten, prüft die fertige Seite im Browser (`tests/smoke.js`, deutsch und englisch) und veröffentlicht `site/` auf GitHub Pages; unter Settings, Pages muss als Quelle „GitHub Actions“ gewählt sein. Fallen Reihen aus, legt er ein Issue „Datenabruf: Ausfälle“ an.

## Betrieb

### Was automatisch läuft
- **Datenlauf** (`.github/workflows/update.yml`): werktags 7:23 und 12:23 UTC Daten holen, Seite bauen, testen, veröffentlichen.
- **Datenarchiv:** der erste geplante Lauf jeder Woche legt den vollständigen Datenstand (`observations.csv.gz`, `run_status.json`, Katalog, Seitenaufbau) als Release `daten-JJJJ-KWnn` ab, mit dem Code-Stand in der Beschreibung.
- **Tickets:** `monitor/alert.py` pflegt drei Issues: „Datenabruf: Ausfälle“ (fehlgeschlagene oder veraltete Reihen) , „Datenabruf: auffällige Werte“ (jüngste Veränderung weit außerhalb des Bisherigen) und „Automatische Sätze: Auffälligkeiten“ (Sätze, die die Satzprüfung in `monitor/satzpruefung.py` nicht bestehen und deshalb entfallen). Alle schließen sich selbst, sobald alles wieder stimmt.
- **Wächter** (`.github/workflows/waechter.yml`, täglich): prüft, ob die veröffentlichte Seite erreichbar ist und ihr Stand höchstens drei Werktage alt ist; sonst Issue „Wächter: Seite veraltet oder nicht erreichbar“.
- **Pipeline-Stand** (`.github/workflows/pipeline-stand.yml`, montags): konjunkturwolf ist in `pyproject.toml` auf einen Commit festgelegt. Gibt es einen neueren Stand, testet der Lauf ihn und öffnet einen Pull Request. Dafür einmalig unter Settings › Actions › General „Allow GitHub Actions to create and approve pull requests“ aktivieren.

Damit Tickets ankommen: Repository auf „Watch“ stellen (mindestens „Issues“) und Benachrichtigungen per E-Mail einschalten.

### Korrekturen dokumentieren
Jede Änderung, die Zahlen oder Aussagen berührt (behobener Fehler, neue Quelle, geänderte Rechnung), bekommt einen Eintrag in `data/static/korrekturen.yaml`: Datum, Art, betroffene Abbildungen, ein bis zwei Sätze und die Nummer des Pull Requests. Daraus entstehen die Seite `korrekturen.html` und der Abschnitt „Änderungen“ im Methodenblatt der Abbildung.

### Was zu tun ist, wenn …
- **eine Quelle ausfällt** (Ticket „Ausfälle“): Meldung im Ticket lesen. Bei Zeitüberschreitung oder Serverfehler reicht meist Abwarten; die Seite zeigt solange den letzten Stand mit Hinweis. Bei geänderter Tabelle oder Kennung die Reihe in `series.yaml` anpassen (Schlüssel, `params`, bei GENESIS `query`), lokal mit `python -m monitor run` prüfen, Pull Request.
- **Werte auffällig springen** (Ticket „auffällige Werte“): bei der Quelle nachsehen, ob sich Einheit, Basisjahr oder Abgrenzung geändert haben. Echte Ausschläge brauchen nichts; das Ticket schließt sich, sobald der Sprung nicht mehr der jüngste Wert ist.
- **die Seite veraltet ist** (Ticket „Wächter“): unter Actions den letzten Lauf von „Daten holen und Seite veröffentlichen“ öffnen; meist bricht ein Schritt ab (Test, Seitentest, Veröffentlichung). Nach der Korrektur den Lauf über „Run workflow“ neu starten.
- **Zugangsdaten ablaufen** (GENESIS, GIE): unter Settings › Secrets and variables › Actions `GENESIS_USER`, `GENESIS_PASSWORD` oder `GIE_API_KEY` neu setzen. Die Werte nie in Dateien oder Tickets schreiben.
- **eine Abbildung dazukommt:** Reihe in `series.yaml`, Abbildung in `monitor.yaml`, englische Texte in `data/static/en.yaml`, bei besonderer Rechnung einen Methodentext in `data/static/methodik.yaml`. Lokal bauen und `node tests/smoke.js site/index.html`.
- **ein früherer Stand nachgerechnet werden soll:** Release `daten-JJJJ-KWnn` laden, das Repository auf den dort genannten Commit setzen, `observations.csv.gz` nach `data/processed/observations.csv` entpacken, `python -m monitor build`.

### Lokal bauen
```
pip install -e ".[dev]"
python -m monitor build      # Seite aus vorhandenen Daten
python -m monitor run        # Daten holen (GENESIS nur mit GENESIS_USER/GENESIS_PASSWORD) und bauen
pytest -q && node tests/smoke.js site/index.html
```

## Prognosen pflegen

Neue Prognoserunde: in `data/static/prognosen.yaml` einen Eintrag mit Herausgeber, Runde, Datum, Werten und Link zur Veröffentlichung ergänzen. Der Monitor zeigt je Herausgeber die jüngste Runde voll, frühere Runden hohl.
