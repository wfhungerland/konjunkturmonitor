# Konjunkturmonitor

Wie geht es der deutschen Wirtschaft? Sieben Fragen, sieben Antworten, jeden Werktag neu aus amtlichen und offenen Daten.

Seite: https://wfhungerland.github.io/konjunkturmonitor/

## Aufbau

- **Auf einen Blick:** sieben Fragen in Alltagssprache. Jede bekommt eine große Zahl, ein kurzes Urteil, einen Antwortsatz und eine Mini-Grafik der letzten fünf Jahre.
  - Wächst die Wirtschaft?
  - Steigen die Preise?
  - Gibt es genug Arbeit?
  - Läuft die Industrie?
  - Kaufen die Leute ein?
  - Läuft der Export?
  - Was erwarten die Unternehmen?
- **Themen:** je Frage ein Abschnitt mit dem Antwortsatz, Vergleichen, einer Erklärung („Was heißt das?“) und Abbildungen.
- **Abbildungen:** nach dem Grafikstandard (Werteachse rechts, Jahresbänder, Arial Narrow, feste Farbfolge, Einheit an der obersten Zahl). Wo es klarer ist, gibt es eigene Formen:
  - Wachstumsbeiträge als gestapelte Balken
  - Konjunkturuhr aus der EU-Industrieumfrage
  - Prognosespektrum
  - Rezessionssignal mit Rezessionsbändern

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
| Kalender | `data/static/kalender.yaml`: Termine nach dem üblichen Rhythmus der Quellen, geschätzt |
| Prognosen | `data/static/prognosen.yaml`, nur veröffentlichte Werte mit Link |
| Karten | Ländergrenzen © GeoBasis-DE / BKG (VG2500), Datenlizenz Deutschland – Namensnennung 2.0, vereinfacht (`data/static/vg2500_laender.json`) |

Lizenzpflichtige Reihen bleiben draußen, etwa Macrobond, die PMI von S&P Global, GfK-Detailreihen und Terminpreise. Die ifo-Zeitreihen setzen eine Anmeldung voraus. Die Stimmung kommt deshalb aus den offenen EU-Umfragen.

## Darstellung

Die Darstellung nach Tufte steuern Schalter im Bereich `layout` von `monitor.yaml`. Jeder lässt sich einzeln mit `false` zurücknehmen:
`start_table` (Kennzahlentabelle statt Fragekarten), `minimal` (ohne Rahmen und Etiketten, Erläuterungen als Randnotiz), `direct_labels` (Beschriftung am Linienende), `small_multiples` (kleine Einzeldiagramme für Abbildungen mit `multiples: true`), `compare_band` (Spanne 2015 bis 2019), `uniform_years` (einheitliches Zeitfenster), `lead_chart_only` (eine Leitgrafik je Thema, weitere aufklappbar), `overview` (zwei bis drei Sätze zur Gesamtlage) und `red_zero_line` (rote Nulllinie wie im Grafikstandard; ausgeschaltet bleibt Rot den Warnsignalen vorbehalten).

Die Kennzahlentabelle zeigt je Zeile Wert, Vergleich zur Vorperiode, zum Vorjahr und den Dreimonatsvergleich sowie die Tendenz (▲ ▼ ■). `kind: rate` vergleicht als Differenz, `kind: level` prozentual; `up_bad: true` färbt einen Anstieg rot. Die Seite enthält die Kernzahlen auch als statisches HTML und ein Vorschaubild (`vorschau.png`). Impressum und Datenschutzerklärung liegen in `monitor/templates/`. Eigene Texte und Abbildungen stehen unter CC BY 4.0.

## Downloads

Zu jeder Abbildung erzeugt der Lauf Excel (Daten, Diagramm, Info), eine PowerPoint-Folie mit bearbeitbarem Diagramm und CSV (`site/dl/`); das PNG entsteht im Browser. Die Folie übernimmt Format und Aufteilung des vorgegebenen Folienmasters (16:9, grauer Rahmen, Übertitel, Titel, Quellenzeile), aber ohne Logo und Behördenkennzeichnung.

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

Der Workflow `update.yml` läuft werktags zweimal, bei Änderungen auf `main` und von Hand. Er committet die Daten und veröffentlicht `site/` auf GitHub Pages; unter Settings, Pages muss als Quelle „GitHub Actions“ gewählt sein.

## Prognosen pflegen

Neue Prognoserunde: in `data/static/prognosen.yaml` einen Eintrag mit Herausgeber, Runde, Datum, Werten und Link zur Veröffentlichung ergänzen. Der Monitor zeigt je Herausgeber die jüngste Runde voll, frühere Runden hohl.
