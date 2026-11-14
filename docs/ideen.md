# Ideen und Wiedervorlagen

Gesammelte Notizen für später, grob geordnet. Stand: 13.11.2026.

## Funktionen
- Eigene Startseite aus den Lesezeichen (Sternchen).
- Darauf aufbauend: Knopf, der aus den gemerkten Grafiken einen inhaltlichen Onepager als Word-Datei erstellt.
- Ausgabeformate: PPTX, Onepager, Expertenanhang.
- Daten direkt von der Quelle ziehen, mit URL je Reihe? Stand 10.11. prüfen.

## Inhalte
- Lieferengpässe, Materialengpässe
- EU und Mitgliedstaaten: Verschuldung und Schuldenstruktur
- EZB-Bilanz, QE, TPI
- Kapitalmarktdaten, Kapitalmarktintegration
- Weltwirtschaft
- Sozialstaat
- PISA, Bildung
- Klimaschutz
- Innovation
- Kiel Military Procurement Tracker
- Tankrabatt: ifo- und DIW-Tracker
- Maddison
- „Big G“ für Deutschland: https://www.journals.uchicago.edu/doi/10.1086/730426
- Inflation nach COICOP-Vierstellern
- Landwirtschaft, Ernte
- Was wäre für einen Staatsfonds wichtig?

## Analysen
- Red Tape, Ungleichheit, Frachtverkehr
- Energiemix, Energieintensität des Wachstums
- Liquidität: Deutschland, Euroraum, global
- Anleihemärkte, Bundeshaushalt(e)
- Aufnahmefähigkeit der Landkreise für Infrastrukturinvestitionen (Bau, Ausbau, Handwerk, Bahnbedarf): Index aus Kapazität (Beschäftigte nach WZ 41–43 und KldB 32/33, Betriebe Bauhauptgewerbe), Engpass (Arbeitslose je offene Stelle, Vakanzzeit, Altersstruktur) und Auslastung (Baugenehmigungen, laufende Projekte). Prüfen an Vergabedaten (Angebote je Ausschreibung, Zuschlag gegen Schätzung, TED/NUTS-3) und an Schocks wie Ahrtal-Wiederaufbau oder Generalsanierungen der Bahn.
  - Migration: ausländische Beschäftigte in Bauberufen nach Staatsangehörigkeit je Kreis (BA), Entsendungen in den Bau (SOKA-BAU, A1-Bescheinigungen), Zuzüge. Zeigt, wie stark ein Kreis Engpässe über Zuwanderung schließt.
  - Reichweite der Firmen: Kapazität nicht je Kreis zählen, sondern als Einzugsgebiet. Distanzabfall empirisch schätzen aus TED-Zuschlägen (Sitz des Auftragnehmers gegen Ort der Leistung), getrennt nach Gewerk und Auftragsgröße. Kapazität der Nachbarkreise dann mit diesem Abfall nach Fahrzeit gewichten; Pendlerverflechtungen der BA als Gegenprobe.
  - TED geprüft 13.11.2026: Such-API (POST api.ted.europa.eu/v3/notices/search, ohne Schlüssel) liefert winner-post-code, winner-country-sub (NUTS-3), winner-city, winner-name, place-of-performance-subdiv-lot und -proc, received-submissions-type-code/-val, tender-value. Abfrage: notice-type IN (can-standard can-social can-desg can-modif) AND buyer-country=DEU AND classification-cpv IN (45000000) AND publication-date>=20250101; can-util wird nicht angenommen. Rund 56.700 Bauzuschläge seit 2025. Stichprobe der ersten 500 (nicht zufällig): 281 mit Auftragnehmer und Sitz-Kreis, 244 mit Sitz und Leistungskreis, davon 56 im selben Kreis, 3 Auftragnehmer aus dem Ausland. DB InfraGO: 6.892 Zuschläge, Leistungsort immer auf Verfahrensebene, Auftragnehmer in 150 von 250 Fällen. Grenzen: nur Aufträge über der EU-Schwelle; gemeldet ist womöglich der eingetragene Sitz statt der ausführenden Niederlassung.
  - Umsetzung und Datenlage: docs/aufnahme.md, Abruf und Auswertung mit python -m monitor.aufnahme.

## Faustregeln (back of the envelope)
- Taylor-Regel, Calvo-Parameter, Okun

## Tracker
- EU-Regulierung, deutsche Regulierung, Industriepolitik

## Karten
- KRITIS

## Datenbanken
- Correlates of War, Allianzen; Pahre
- Handbuch der deutschen Aktiengesellschaften
- Global Trade Alert, nichttarifäre Handelshemmnisse
- IWF, OECD, EU-Kommission

## Personen
- Hetmeier, Kaelble, Nils

## Trivia
- Kriminalität; soziale Repräsentativität der Abgeordneten; Bundesbeamte; Kitas
- gefühlte Inflation; Konsumneigung; Bahnausfälle; Leerstand; Baulücken; Streiks
- KI-Nutzung und Produktivität; Start-ups; M&A-Deals und Betriebslandschaft

## Darstellung
- Analyse grün, Beschreibung blau
- Sunburst, Treemap
- Wiedervorlage (13.11.2026): Aussagetitel für Abbildungen, also ein Satz mit der Botschaft statt eines Sachtitels („Die Aufträge laufen der Produktion davon“). Im Teil Geopolitik ausprobiert und zurückgenommen. Offen: Feste Titel veralten, wenn die Daten kippen; denkbar wären Titel, die der Bau aus den Daten erzeugt.
- Wortgrafik-Tabellen nach Tufte (Typ `sparktable`) auch für andere Abschnitte, z. B. Arbeit oder Staat.
- Jahresbalken auch bei Episodenvergleichen
- Empfehlungen von Gremien, weitere Darstellungen aus der Tufte-Runde: Stufenlinie je Frage (Höhe statt Farbe), Tabelle nach Jahrzehnten (häufigste Empfehlung und wie oft), Zeichen ▲●▼ statt Farben, Richtung je Jahrzehnt (Balken Lockern nach oben, Bremsen nach unten)
- Phasenansicht mit „Heute“ und Wendepunkten auch für den Sachverständigenrat; Reiter „Gesamtschau“ mit Vergleich Institute und Rat
