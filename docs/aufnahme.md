# Aufnahmefähigkeit der Kreise für Infrastrukturinvestitionen

Frage: Wie viel Bau-, Ausbau- und Handwerksleistung kann ein Kreis zusätzlich aufnehmen, und lässt sich das vorhersagen? Idee und Indexaufbau: `docs/ideen.md`, Abschnitt „Analysen“.

## Vergabedaten aus TED

Abruf und Auswertung: `python -m monitor.aufnahme`, nur Standardbibliothek.

1. `abzug C:\Daten\TED` zieht alle deutschen Bauzuschläge ab 2025, eine JSONL-Datei je Monat. Paginiert wird über `iterationNextToken`, weil die Seitenzählung bei 15.000 Treffern endet. Abgeschlossene Monate bekommen einen Marker `.fertig` und werden beim nächsten Lauf übersprungen.
2. `orte C:\Daten\TED` holt die Mittelpunkte der deutschen NUTS-3-Regionen (GISCO, NUTS 2024).
3. `auswertung C:\Daten\TED --ziel <ordner>` schreibt `aufnahme_ted.md` (Füllgrad, Distanzabfall, Sitzprüfung) und `aufnahme_kanten.csv` (Zuschläge je Kreispaar und Gewerk, ohne Firmennamen).

Die Rohdaten bleiben unter `C:\Daten\TED`; ins Repo kommen nur die beiden Auswertungsdateien.

Methode, erste Stufe: Ausgewertet werden Bekanntmachungen mit genau einem Sitz-Kreis und einem Leistungskreis. Distanz ist die Luftlinie zwischen den Kreismittelpunkten. Jenseits des eigenen Kreises wird ein exponentieller Abfall angenommen; die Halbwertsdistanz ist dann der Mittelwert der Distanzen mal ln 2. Ein Schwerkraftmodell auf Basis der Kantenliste folgt.

Sitz oder Niederlassung (geprüft 13.11.2026): Die Auswertung führt Schreibvarianten derselben Firma zusammen und teilt die Firmen ein. Regional sind Firmen mit Zuschlägen in weniger als vier Ländern. Überregionale Firmen „melden die Niederlassung“, wenn sie mindestens drei Postleitzahlen angeben und keine davon die Hälfte der Meldungen erreicht, sonst „melden sie die Zentrale“.

| Firmentyp | Zuschläge | Median km | Halbwertsdistanz km |
|---|---:|---:|---:|
| alle | 38.052 | 52 | 86 |
| regional | 28.935 | 41 | 65 |
| überregional, meldet Niederlassung | 1.361 | 45 | 81 |
| überregional, meldet Zentrale | 7.571 | 175 | 151 |

Abgleich mit Standortangaben der Firmen: STRABAG AG meldet 47 Postleitzahlen bei rund 50 deutschen Standorten (älteres Firmenprofil), also die Niederlassungen. KONE (80 % Hannover, Länderzentrale; mehr als 50 Standorte in DACH), Lindner SE (98 % Arnstorf; weitere Standorte unter anderem Berlin, Hamburg, Hannover, Nürnberg) und LEONHARD WEISS (59 % Göppingen; Hauptsitz Satteldorf, zahlreiche weitere Standorte) melden dagegen ihre Zentrale. Fliesen Röhlich (97 % Wendelstein) hat nach den gefundenen Angaben nur diesen einen Standort und reist tatsächlich weit. Die Gruppe „meldet Zentrale“ mischt also verzerrte Meldungen von Konzernen mit echten Wanderbetrieben. Der Distanzabfall der regionalen Firmen (Halbwertsdistanz 65 km) ist darum die Untergrenze, der Wert für alle (86 km) die Obergrenze. Für die Gewichtung der Nachbarkreise taugt die Untergrenze je Gewerk (Tabelle „nur regionale Firmen“ in `docs/aufnahme_ted.md`).

Fahrzeit (13.11.2026): `python -m monitor.aufnahme fahrzeiten <ordner>` fragt die Pkw-Fahrzeiten zwischen allen 400 Kreismittelpunkten beim öffentlichen OSRM-Server ab (OpenStreetMap, ohne Verkehr, 64 Teilabfragen zu 50 mal 50 Kreisen, etwa zwei Minuten). Der Host `router.project-osrm.org` muss freigegeben sein. Die Auswertung nutzt die Matrix, sobald `fahrzeiten_nuts3.csv` im Ordner liegt. Ins Repo kommen die Paare bis vier Stunden: `data/static/aufnahme_fahrzeiten.csv`.

| Firmentyp | Median min | Halbwertszeit min | bis 60 min |
|---|---:|---:|---:|
| alle | 64 | 80 | 48 % |
| regional | 53 | 65 | 56 % |
| überregional, meldet Niederlassung | 54 | 74 | 54 % |
| überregional, meldet Zentrale | 160 | 129 | 15 % |

Bei den regionalen Firmen reicht die Halbwertszeit von 50 Minuten (Sanitär, Heizung) bis 72 Minuten (Hochbau); Anlagenbau und Gebäudetechnik liegen bei 99 und 122 Minuten.

Erster Lauf 13.11.2026 (Cloud): 56.734 Bauzuschläge seit Januar 2025, je Monat vollständig gegen die Trefferzahl von TED. Ergebnis: `docs/aufnahme_ted.md`, Kantenliste `data/static/aufnahme_kanten.csv`. Die Antwortfelder kommen als Listen oder Sprach-Wörterbücher; `tender-value` ist eine Liste von Texten, fehlende Werte stehen als -1. TED meldet Thüringer Kreise teils mit NUTS-2021-Codes; das Skript schlüsselt sie auf NUTS 2024 um. Für die Rohdaten unter `C:\Daten\TED` den Abzug dort wiederholen (`TED abrufen.bat`).

## Kreisreihen von BA und Regionalstatistik

Abruf: `python -m monitor.aufnahme_kreise kreise <ordner>` (Kreisliste von Destatis mit NUTS 3, Fläche, Bevölkerung) und `python -m monitor.aufnahme_kreise ba <ordner> --stichtag 202603 --ziel data/static`. Nur Standardbibliothek. Ergebnis: `data/static/aufnahme_ba_kreise.csv` im Langformat (ags, nuts3, stichtag, merkmal, wert).

Quelle ist der „Regionalreport über Beschäftigte (Quartalszahlen)“ der BA, eine Excel-Datei je Kreis und Quartal (`.../Statistikdaten/Detail/<JJJJMM>/iiia6/beschaeftigung-reg-bst-reg/bst-reg-<AGS>-0-<JJJJMM>-xlsx.xlsx`), jeweils mit fünf Quartalsstichtagen, Arbeitsort. Ausgelesen werden sozialversicherungspflichtig Beschäftigte insgesamt, Ausländer, Baugewerbe (WZ-Abschnitt F), die BA-Aggregate Bauberufe und Handwerksberufe, die Berufshauptgruppen 31 bis 34 der KldB 2010 sowie Helfer und Fachkräfte. Die BA drosselt Massenabrufe (HTTP 429); das Skript wartet dann und nimmt bereits geladene Dateien aus dem Zwischenspeicher.

| Baustein | Quelle | Kreisebene | Stand der Prüfung (13.11.2026) |
|---|---|---|---|
| Beschäftigte im Baugewerbe | BA, Regionalreport | ja, nur Abschnitt F | WZ 41, 42, 43 einzeln nicht im Regionalreport; dafür bräuchte es die interaktive Statistik „Branchen im Fokus“ (CSV-Export) |
| Beschäftigte in Berufshauptgruppen 31-34, Bauberufe | BA, Regionalreport | ja | im Abruf |
| Ausländische Beschäftigte | BA, Regionalreport | ja, nur insgesamt | Kreuzung mit Beruf oder Staatsangehörigkeit nicht im Regionalreport; „Beschäftigte nach Staatsangehörigkeiten – Kreise“ noch zu prüfen |
| Gemeldete Stellen, Vakanzzeit nach Berufshauptgruppen | BA, dynamische Tabellen „Gemeldete Arbeitsstellen“ | ja | Dynamische Tabelle (Bestand, Zugang, Abgang, abgeschlossene Vakanzzeit, Berufshauptgruppen) ohne dokumentierten Export; offene Schnittstelle seit 12/2025 (`statistik-dr.arbeitsagentur.de/bifrontend/bids-api/ct/v1/tableFetch/csv/EckwerteTabelleSTEA?Kreis=<Name>`) liefert je Kreis nur Bestand und Zugang, ohne Beruf und Vakanzzeit; Host in der Cloud nicht freigegeben. „Fachkräftebedarf“ (interaktiv) hat Kreise mal KldB-Berufsgruppen, ab 60 Abgängen im Jahr |
| Engpassanalyse (6 Indikatoren) | BA | nein, nur Bund und Länder | nur als Kalibrierung |
| Zustimmungen zur Arbeitsaufnahme Drittstaatsangehöriger | BA, jährlich | ja | Ergänzung zur Migration |
| Betriebe, tätige Personen, baugewerblicher Umsatz | Regionalstatistik 44231-01-03-4, Stichtag 30.06., ab 2017 | ja | Schnittstelle (GENESIS-Webservice) verlangt ein registriertes Konto, Gastzugang abgewiesen; Kreisergebnisse beziehen sich teils auf den Unternehmenssitz |

Entsendungen (SOKA-BAU, A1-Bescheinigungen) und laufende Großprojekte: noch nicht geprüft.

## Aufträge unter der EU-Schwelle

Der Datenservice Öffentlicher Einkauf des Beschaffungsamts (oeffentlichevergabe.de) bündelt seit dem 25.10.2023 die Bekanntmachungen von Bund, Ländern und Kommunen im Format eForms-DE, auch die unterschwelligen. Die Daten sind CC0.

Abruf (geprüft 13.11.2026, ohne Schlüssel): `https://oeffentlichevergabe.de/api/notice-exports?pubMonth=2026-10&format=ocds.zip` oder `format=eforms.zip`; statt `pubMonth` auch `pubDay=2026-10-01`. Oktober 2026: 24.577 Bekanntmachungen, als ZIP 43 MB (OCDS) bzw. 101 MB (eForms). Der Host ohne „www“ muss freigegeben sein, `www.oeffentlichevergabe.de` leitet dorthin um. Das Regime steht nur im eForms-Export im Feld `RegulatoryDomain`: eine EU-Richtlinie (etwa 32014L0024) über der Schwelle, `de-vob`, `de-uvgo`, `de-vol` oder `de-hhr` darunter. Beide Exporte lassen sich über die Kennung der Bekanntmachung (Dateiname ohne Versionsendung) verknüpfen.

Füllgrad der Bauzuschläge (CPV 45) im Oktober 2026:

| Regime | Zuschläge | Auftragnehmer | Sitz-Kreis | Leistungskreis | beides eindeutig | Zahl der Angebote | Auftragswert |
|---|---:|---:|---:|---:|---:|---:|---:|
| über der EU-Schwelle | 1.688 | 94 % | 94 % | 99 % | 91 % | 94 % | 73 % |
| unter der EU-Schwelle | 963 | 0 % | 0 % | 0 % | 0 % | 0 % | 0 % |

Befund: Unterschwellige Zuschlagsbekanntmachungen nennen weder Auftragnehmer noch Wert noch Zahl der Angebote. Der Leistungsort steht nur als Freitext mit Postleitzahl (99 %), NUTS höchstens auf Landesebene. Für den Distanzabfall taugen sie nicht; sie zeigen nur, wie viele kleine Bauaufträge wo vergeben werden. Zum Vergleich: Im selben Monat gab es 4.239 unterschwellige Bauausschreibungen nach VOB (de-vob), aber nur 963 Zuschlagsmeldungen. Für die Reichweite der Firmen bleibt TED die Grundlage; die EU-Zuschläge im Datenservice sind besser gefüllt als in TED insgesamt, weil die DB dort kaum meldet.
