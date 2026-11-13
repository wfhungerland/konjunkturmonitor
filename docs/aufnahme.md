# Aufnahmefähigkeit der Kreise für Infrastrukturinvestitionen

Frage: Wie viel Bau-, Ausbau- und Handwerksleistung kann ein Kreis zusätzlich aufnehmen, und lässt sich das vorhersagen? Idee und Indexaufbau: `docs/ideen.md`, Abschnitt „Analysen“.

## Vergabedaten aus TED

Abruf und Auswertung: `python -m monitor.aufnahme`, nur Standardbibliothek.

1. `abzug C:\Daten\TED` zieht alle deutschen Bauzuschläge ab 2025, eine JSONL-Datei je Monat. Paginiert wird über `iterationNextToken`, weil die Seitenzählung bei 15.000 Treffern endet. Abgeschlossene Monate bekommen einen Marker `.fertig` und werden beim nächsten Lauf übersprungen.
2. `orte C:\Daten\TED` holt die Mittelpunkte der deutschen NUTS-3-Regionen (GISCO, NUTS 2024).
3. `auswertung C:\Daten\TED --ziel <ordner>` schreibt `aufnahme_ted.md` (Füllgrad, Distanzabfall, Sitzprüfung) und `aufnahme_kanten.csv` (Zuschläge je Kreispaar und Gewerk, ohne Firmennamen).

Die Rohdaten bleiben unter `C:\Daten\TED`; ins Repo kommen nur die beiden Auswertungsdateien.

Methode, erste Stufe: Ausgewertet werden Bekanntmachungen mit genau einem Sitz-Kreis und einem Leistungskreis. Distanz ist die Luftlinie zwischen den Kreismittelpunkten. Jenseits des eigenen Kreises wird ein exponentieller Abfall angenommen; die Halbwertsdistanz ist dann der Mittelwert der Distanzen mal ln 2. Fahrzeiten und ein Schwerkraftmodell auf Basis der Kantenliste folgen.

Sitz oder Niederlassung: Für die 30 häufigsten Auftragnehmer zählt die Auswertung die verschiedenen gemeldeten Postleitzahlen. Viele Postleitzahlen je Firma sprechen für gemeldete Niederlassungen, eine einzige für den eingetragenen Sitz. Den Befund danach für einzelne Konzerne gegen deren Niederlassungslisten prüfen.

Netz: Die Cloud-Umgebung und die Shell auf dem Rechner erreichen `api.ted.europa.eu` derzeit nicht (Freigabeliste). Möglich ist der Lauf mit dem Windows-Python des Rechners oder nach Freigabe der Domains.

## Kreisreihen von BA und Regionalstatistik (Schreibtischprüfung 14.11.2026)

| Baustein | Quelle | Kreisebene | Stand der Prüfung |
|---|---|---|---|
| Beschäftigte nach WZ 41-43 | BA, Beschäftigungsstatistik | ja | Standard, Tabellenabruf noch nicht getestet |
| Beschäftigte in Berufshauptgruppen 32/33 | BA, Beschäftigungsstatistik | wahrscheinlich | zu prüfen, ob Kreis mal Berufshauptgruppe frei verfügbar ist |
| Ausländische Beschäftigte nach Staatsangehörigkeit | BA, „Beschäftigte nach Staatsangehörigkeiten – Deutschland, Länder und Kreise“, quartalsweise | ja | Inhalt nennt Beruf und Wirtschaftszweig; ob die Kreuzung mit dem Beruf auf Kreisebene vorliegt, ist offen |
| Gemeldete Stellen, Vakanzzeit nach Berufshauptgruppen | BA, dynamische Tabellen „Gemeldete Arbeitsstellen“ | ja (auch Agenturen, Geschäftsstellen) | brauchbar für Engpass; Arbeitslose je Stelle aus Arbeitslosenstatistik ergänzen |
| Engpassanalyse (6 Indikatoren) | BA | nein, nur Bund und Länder | nur als Kalibrierung |
| Zustimmungen zur Arbeitsaufnahme Drittstaatsangehöriger | BA, jährlich | ja | Ergänzung zur Migration |
| Betriebe, tätige Personen, baugewerblicher Umsatz | Regionalstatistik 44231-01-03-4, Stichtag 30.06., ab 2017 | ja | Kreisergebnisse der Jahreserhebungen beziehen sich teils auf den Unternehmenssitz, dasselbe Problem wie bei TED |

Entsendungen (SOKA-BAU, A1-Bescheinigungen) und laufende Großprojekte: noch nicht geprüft.

## Aufträge unter der EU-Schwelle

Der Datenservice Öffentlicher Einkauf des Beschaffungsamts (oeffentlichevergabe.de) bündelt seit dem 25.10.2023 die Bekanntmachungen von Bund, Ländern und Kommunen im Format eForms-DE. Unterschwellige Bekanntmachungen gehen nach der Prüfung direkt an den Bekanntmachungsservice. Die Daten sind CC0 und als tägliche Exporte (OCDS oder eForms) über eine offene Schnittstelle abrufbar. Offen: wie vollständig die Vergabeplattformen unterschwellige Zuschläge melden und ob Auftragnehmer-Postleitzahl und Leistungsort dort ebenso gefüllt sind wie bei TED. Dafür einen Monat Exporte ziehen und den Füllgrad wie bei TED auswerten.
