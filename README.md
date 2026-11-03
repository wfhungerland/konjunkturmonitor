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
| Wachstum | Eurostat `namq_10_gdp` |
| Preise | Bundesbank `BBDP1` (VPI insgesamt und Bestandteile: Energie, Nahrungsmittel, Waren ohne Energie, Dienstleistungen ohne Miete, Wohnungsmiete), Eurostat `sts_inppd_m`; Einfuhrpreise der Bundesbank |
| Arbeit | Bundesbank (BA-Reihen, saisonbereinigt), Eurostat `namq_10_pe`; Kurzarbeit-Äquivalente aus der BA-Statistik (`data/static`) |
| Industrie | Bundesbank `BBDE1` (Produktion, Auftragseingang) |
| Konsum | Bundesbank `BBDE1` (Einzelhandel), Eurostat `ei_bsco_m` (Verbrauchervertrauen) |
| Export | Bundesbank `BBDA1` |
| Stimmung | Eurostat, EU-Unternehmensumfragen (`ei_bssi_m_r2`, `ei_bsin_m_r2`, `ei_bsse_m_r2`, `ei_bsrt_m_r2`, `ei_bsbu_m_r2`) |
| Prognosen | `data/static/prognosen.yaml`, nur veröffentlichte Werte mit Link |

Lizenzpflichtige Reihen bleiben draußen, etwa Macrobond, die PMI von S&P Global, GfK-Detailreihen und Terminpreise. Die ifo-Zeitreihen setzen eine Anmeldung voraus. Die Stimmung kommt deshalb aus den offenen EU-Umfragen.

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
