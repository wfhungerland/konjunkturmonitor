# Das D*-Modell von Kiel Economics: Rechercheergebnis und Nachbauplan

Stand: 11.11.2026

## Vorbemerkung zur Quellenlage

- Die Originaldokumente (kieleconomics.de, bbsr.bund.de, link.springer.com, iwh-halle.de) waren aus dieser Arbeitsumgebung nicht direkt abrufbar. Alle Belege stammen aus Suchauszügen dieser Originalquellen. Die Links zeigen direkt auf die Originale.
- Eine eigenständige technische Modelldokumentation mit Gleichungen ist öffentlich nicht auffindbar. Die ausführlichste bekannte Darstellung steht im Anhang „Das D*-Modell von Kiel Economics“ der [BBSR-Online-Publikation 28/2022](https://www.bbsr.bund.de/BBSR/DE/veroeffentlichungen/bbsr-online/2022/bbsr-online-28-2022-dl.pdf?__blob=publicationFile&v=2). Dieser Anhang ist die wichtigste Quelle für den nächsten Leseschritt.
- Kennzeichnung im Text: **[B]** belegt, **[R]** Rekonstruktionsannahme, **[U]** unbekannt oder proprietär.

## 1. Modellidentität

- **[B]** D* ist das makroökonometrische Strukturmodell der **Kiel Economics Research & Forecasting GmbH & Co. KG**, einer 2009 gegründeten Ausgründung des IfW Kiel ([Unternehmen](https://kieleconomics.de/en/company/), [Projektsteckbrief zukunftbau.de](https://www.zukunftbau.de/projekte/ressortforschung/1008177-xxxx-54-6)). Geschäftsführer und Hauptautor ist Carsten-Patrick Meier.
- **[B]** Kiel Economics hat das Modell entwickelt, um die gesamtwirtschaftliche Entwicklung Deutschlands zu analysieren und wirtschaftspolitische Eingriffe zu bewerten ([Niedrigzinsstudie 2022](https://kieleconomics.de/wp-content/uploads/2022/03/Kiel-Economics-Makrooekonomische-Auswirkungen-der-langen-Niedrigzinsphase-in-Deutschland.pdf)).
- **[B] Bezeichnungen und Versionen:** In Quellen erscheinen „D-Modell“, „D*-Modell“ und „D+-Modell“. Das BMF-Gutachten von IWH und Kiel Economics (2015) nennt „das D*-Modell und das D+-Modell von Kiel Economics“ als getrennte Modelle ([IWH-Publikationsseite](https://www.iwh-halle.de/en/publications/detail/oekonomische-wirksamkeit-der-konjunktur-stuetzenden-finanzpolitischen-massnahmen-der-jahre-2008-und-2009-forschungsvorhaben-im-auftrag-des-bundesministeriums-der-finanzen), [Textkopie](https://studylibde.com/doc/6233892/%C3%B6konomische-wirksamkeit-der-konjunktur)). **[U]** Was D+ von D* unterscheidet, ist nirgends dokumentiert. „D-Modell“ ist vermutlich eine Schreibvariante, weil der Stern in Textextraktionen verloren geht. Versionsnummern oder Änderungshistorien sind nicht veröffentlicht.
- **Abgrenzung (nicht vermischen):**
  - **Konjunkturampel** von Kiel Economics für die Börsen-Zeitung: eigenes Indikatorverfahren mit über 50 erwartungsbasierten Indikatoren, das eine Rezessionswahrscheinlichkeit liefert ([Börsen-Zeitung](https://www.boersen-zeitung.de/konjunktur-politik/konjunkturampel-zeigt-vorerst-intakten-aufschwung)). **[B]** Kein Teil von D*, soweit dokumentiert.
  - **IfW Kiel** (Kieler Konjunkturberichte, Mittelfristprojektion, Gemeinschaftsdiagnose): eigene Prognosen des Instituts ([Konjunktur IfW](https://www.kielinstitut.de/topics/economic-outlook/)). Andere IfW-Modelle wie das CGE-Modell DART ([RePEc](https://ideas.repec.org/p/zbw/ifwkie/4236.html)) haben mit D* nichts zu tun.
  - **IWH-Modell / HEPM** (Halle): wurde in Studien parallel zu D* gerechnet, ist aber ein anderes Modell.

## 2. Fähigkeiten

| Bereich | Befund | Status |
|---|---|---|
| Länderabdeckung | Deutschland als Kernland; Handel mit zwei Regionen: Euroraum ohne Deutschland und Rest der Welt. Euroraum-Variablen wie Preisanstieg und Produktionslücke kommen vor ([Niedrigzinsstudie](https://kieleconomics.de/wp-content/uploads/2022/03/Kiel-Economics-Makrooekonomische-Auswirkungen-der-langen-Niedrigzinsphase-in-Deutschland.pdf)) | [B] |
| Sektoren | Nur die aggregierte Volkswirtschaft; im Gegensatz zu INFORGE mit 59 Sektoren ([Hennecke/Neuberger/Ulbricht 2019](https://link.springer.com/article/10.1007/s11187-018-0069-6)) | [B] |
| Nachfrage | Verwendungsseite der VGR; Bauinvestitionen gesondert, Konsumfunktion empirisch geschätzt (BBSR 28/2022) | [B] |
| Angebot | Produktionsfunktion vom Typ Cobb-Douglas mit technischem Fortschritt; NAWRU modelliert ([BMWK-Beteiligungsprozess, Anhang](https://www.bundeswirtschaftsministerium.de/Redaktion/DE/Downloads/P-R/potenzialschaetzung-und-produktionsluecken-der-bundesregierung-appendix.pdf?__blob=publicationFile&v=4)) | [B] |
| Fiskalische Schocks | Abgabensenkungen, Transfers, Staatskonsum, öffentliche Investitionen (BMF-Gutachten 2015); Bauinvestitionsimpuls von 1 % des BIP mit Gegenfinanzierung über Steuern (BBSR 28/2022, [Projektseite](https://www.bbsr.bund.de/BBSR/DE/forschung/programme/zb/Auftragsforschung/1Wertschoepfung/2020/effekte-bauinvestitionen/01-start.html)) | [B] |
| Wohnungsbauförderung | Degressive gegenüber linearer AfA, Zinsverbilligung, Zuschüsse ([BBSR-Online 24/2026](https://www.bbsr.bund.de/BBSR/DE/veroeffentlichungen/bbsr-online/2026/bbsr-online-24-2026-dl.pdf?__blob=publicationFile&v=4)) | [B] |
| Geld- und Zinsschocks | Lange Niedrigzinsphase seit 2011 (Niedrigzinsstudie 2022) | [B] |
| Außenschocks | Ölpreisschock mit Exportkanal: Exporte profitieren zunächst von höheren Ölpreisen ([Börsen-Zeitung 2026](https://www.boersen-zeitung.de/konjunktur-politik/konjunkturampel-zeigt-vorerst-intakten-aufschwung)) | [B] |
| Kredit-/Bürgschaftsprogramme | Gesamtwirtschaftliche Effekte von Bürgschaftsbanken (Hennecke/Neuberger/Ulbricht 2019) | [B] |
| Prognosen | Halbjährliche Prognosen von Kiel Economics (Juni, Dezember), „auf Basis eigener Analysen und Modelle“ ([Economic Forecasts](https://kieleconomics.de/en/economic-forecasts/)) | [B] Rolle von D* darin nicht im Detail belegt |
| Prognosehorizont | Unbekannt; Simulationsstudien reichen über mehrere Jahre bis zum langfristigen Gleichgewicht | [U] |
| Ergebnisse | Impulsantworten, Multiplikatoren, Abweichungen vom Basisszenario | [B] |
| Unsicherheitsmaße | Keine Konfidenzbänder oder Fan Charts dokumentiert | [U] |
| Frequenz | Nicht dokumentiert; Quartalsfrequenz ist bei dieser Modellklasse Standard | [R] |

## 3. Modellaufbau

**Belegt:**

- **[B] Klasse:** dynamisches makroökonometrisches Simultangleichungsmodell, umgesetzt als System simultaner Gleichgewichtskorrekturgleichungen (Equilibrium Correction, ECM). Langfristig verhält es sich wie ein neukeynesianisches DSGE-Modell (Niedrigzinsstudie 2022).
- **[B] Einordnung:** „semi-strukturell“, konzeptionell ähnlich zu FRB/US der Fed und ECB-BASE der EZB (BBSR 28/2022, zukunftbau.de). Das BMF-Gutachten 2015 ordnet es den strukturellen ökonometrischen Modellen in der Tradition der London School of Economics zu.
- **[B] Kern:** Nachfrageseite nach der Verwendungsrechnung der VGR, neoklassische Angebotsseite mit Cobb-Douglas-Produktionsfunktion. Die Langfristlösung ist ein neoklassisches Wachstumsgleichgewicht (Steady State). Zusätzliche Investitionen erhöhen vorübergehend Kapitalstock und Produktionspotenzial (Hennecke/Neuberger/Ulbricht 2019).
- **[B] Verhaltensgleichungen, soweit bekannt:**
  - Bauinvestitionen aus theoretisch abgeleiteter Investitionsnachfrage, positiv abhängig vom Wachstum, negativ von den realen Kapitalnutzungskosten (BBSR 28/2022).
  - Empirische Konsumfunktion mit Konsumglättung (BBSR 28/2022, Niedrigzinsstudie).
  - NAWRU als modellierter Bestandteil des Arbeitsmarkts (BMWK-Beitrag von Meier).
- **[U]** Gleichungsanzahl, genaue Spezifikationen, Erwartungsbildung (VAR-basiert wie ECB-BASE oder modellkonsistent), Zinsregel, fiskalische Schließungsregel, Preis- und Lohnblock, Finanzsektor.

**Plausible Rekonstruktion [R]** (aus der Ähnlichkeit zu FRB/US und ECB-BASE abgeleitet, nicht aus D*-Dokumenten):

- Jede Verhaltensgleichung hat die Form Δx_t = Kurzfristdynamik − γ(x_{t-1} − x*_{t-1}) + Erwartungsterme, wobei x* aus einer Optimierungsbedingung folgt.
- Erwartungen kommen entweder aus einem kleinen VAR-Satellitenmodell oder werden modellkonsistent gelöst.
- Die EZB-Zinsregel reagiert auf Euroraum-Inflation und Euroraum-Produktionslücke; dafür braucht das Modell die belegten Euroraum-Variablen.
- Eine fiskalische Regel stabilisiert langfristig die Schuldenquote, damit ein Steady State existiert. Die BBSR-Studie erwähnt Steuerfinanzierung des Impulses, was in diese Richtung weist.

## 4. Daten

- **[B]** VGR-Verwendungsrechnung als Grundlage der Nachfrageseite.
- **[U]** Quellen, Stützzeitraum, Frequenz, Transformationen, Umgang mit Revisionen, Datenlücken und Veröffentlichungsverzögerungen. Nichts davon ist öffentlich beschrieben.
- **[R]** Wahrscheinlich Destatis-VGR (Quartale, saison- und kalenderbereinigt), Bundesbank-Zinsen, Eurostat/EZB für den Euroraum, IWF/OECD für die Weltnachfrage. Zum Vergleich: ECB-BASE schätzt auf 1995Q1 bis 2016Q4 ([ECB WP 2315](https://ideas.repec.org/p/ecb/ecbwps/20192315.html)).

## 5. Schätzung und Betrieb

- **[B]** Die Gleichungen werden ökonometrisch geschätzt (Bezeichnung als „makroökonometrisch“, Bauinvestitionen „geschätzt“).
- **[U]** Schätzverfahren (OLS je Gleichung, zweistufig nach Engle-Granger, Systemschätzung), Kalibrierung einzelner Parameter, Lösungsalgorithmus, Umgang mit Expertenanpassungen.
- **[B]** Szenarien laufen als Abweichung vom Basispfad und werden als Impulsantworten dargestellt. In der Niedrigzinsstudie werden Impulsantworten reskaliert; der Grund ist im Auszug nicht erkennbar.
- **[R]** Expertenurteil fließt bei Modellen dieser Klasse über Add-Faktoren (Residuenanpassungen) ein, wie bei FRB/US und dem [Bundesbank-Modell](https://www.bundesbank.de/resource/blob/888376/7495ae46eccc5fa1dcdfe29a461e0833/472B63F073F071307366337C94F8C870/2022-01-technical-paper-data.pdf).

## 6. Validierung

- **[B]** Vergleich der Impulsantworten von D* mit anderen Makromodellen in der Niedrigzinsstudie 2022. Parallelrechnungen mit dem IWH-Modell (BMF 2015, Bürgschaftsbanken 2019). In der BBSR-Studie fallen die Multiplikatoren etwas geringer aus als in einer Vergleichsrechnung.
- **[B]** Ergebnis BBSR 28/2022: Ein Bauimpuls von 1 % des BIP (rund 30 Mrd. Euro) erhöht das BIP um mehr als das Doppelte der eingesetzten Mittel; dem stehen langfristig Effekte höherer Steuern gegenüber.
- **[U]** Keine öffentlichen Out-of-sample-Prognosetests, keine historischen dynamischen Simulationen, kein Vergleich mit naiven Referenzmodellen wie Random Walk oder AR-Prozess gefunden. Auch die Prognosegüte der Kiel-Economics-Prognosen ist nicht systematisch ausgewertet worden, soweit auffindbar.

## 7. Nachbau in Python

### Leitentscheidung

Ein semi-struktureller ECM-Ansatz nach dem Vorbild von ECB-BASE und dem Bundesbank-Modell. Diese beiden Modelle sind öffentlich dokumentiert und liefern geprüfte Spezifikationen, die D* nach eigener Aussage konzeptionell ähneln.

### Datenquellen (frei)

| Block | Reihen | Quelle |
|---|---|---|
| VGR Deutschland | BIP, privater Konsum, Staatskonsum, Ausrüstungen, Bauten (Wohnbau, Nichtwohnbau), Exporte, Importe, jeweils real und Deflator; verfügbares Einkommen, Arbeitnehmerentgelt | Destatis GENESIS-API (Tabellen 81000-*), Eurostat `namq_10_gdp`, `nasq_10_nf_tr` |
| Arbeitsmarkt | Erwerbstätige, Arbeitsvolumen, Arbeitslose, Erwerbspersonen | Destatis, Bundesagentur für Arbeit, Eurostat |
| Kapitalstock | Nettoanlagevermögen nach Anlagearten | Destatis (jährlich, auf Quartale interpoliert) |
| Preise, Löhne | HVPI, Tariflöhne, Lohnstückkosten | Eurostat, Bundesbank |
| Zinsen, Finanzen | €STR/EONIA, Rendite 10J, Kreditzinsen, Wohnimmobilienpreise | EZB Data Portal (SDMX), Bundesbank |
| Euroraum ohne DE | BIP, HVPI, Produktionslücke | Eurostat, EZB, AMECO |
| Rest der Welt | Weltimportnachfrage, Ölpreis, Wechselkurse | IWF, OECD, FRED, EZB (effektiver Wechselkurs) |
| Echtzeitdaten | VGR-Vintages ab 2005 | [Bundesbank-Echtzeitdatenbank](https://www.bundesbank.de/en/statistics/time-series-databases/-/macroeconomic-real-time-database-622290) |

### Bibliotheken

- Daten: `pandas`, `sdmx1` (Eurostat, EZB, Bundesbank via SDMX), `requests` (GENESIS-API), `fredapi`.
- Schätzung: `statsmodels` (OLS, ARDL mit Bounds-Test, VECM, Johansen, Kalman-Filter über `UnobservedComponents`), `linearmodels` (IV, falls Simultanität es verlangt).
- Lösung: `scipy.optimize` (Newton) oder ein eigener Gauss-Seidel-Löser; alternativ `sympy` zur Ableitung von Jacobi-Matrizen. Für modellkonsistente Erwartungen ein Stacked-Time-Newton-Verfahren wie bei FRB/US.
- Prüfung und Darstellung: `pytest`, `matplotlib`.

### Prototyp (Stufe 1): kleines Deutschlandmodell, Quartale ab 1995

Endogene Variablen und Gleichungen (Kleinbuchstaben = Logarithmen, * = Gleichgewichtswert):

1. Produktionspotenzial: y* = a + α k + (1−α)(l̄ + h̄), wobei l̄ = Erwerbspersonen × (1 − NAWRU), a = geglätteter Solow-Rest (HP- oder Kalman-Filter), α ≈ 0,35.
2. Produktionslücke: gap = y − y*.
3. Privater Konsum (ECM): Δc = β₀ + β₁ Δyd + β₂ Δc₋₁ − γ_c (c₋₁ − yd₋₁ − θ r₋₁) + ε.
4. Ausrüstungsinvestitionen (ECM): Langfristig i − y = const − σ uc, mit Kapitalnutzungskosten uc = p_I/p_Y × (r + δ − π^e_I) (Hall-Jorgenson).
5. Bauinvestitionen: gleiche Form wie 4, getrennt für Wohnbau und Nichtwohnbau (entspricht der belegten D*-Spezifikation: positiv vom Wachstum, negativ von realen Kapitalnutzungskosten).
6. Exporte (ECM): x = wd + η_x reer; wd = Weltnachfrage aus Euroraum ohne DE und Rest der Welt mit Handelsgewichten.
7. Importe (ECM): m = Σ ω_j d_j + η_m (p_M − p_Y), mit importgewichteter Endnachfrage d_j.
8. Preis-Phillips-Kurve: π = λ π₋₁ + (1−λ) π^e + κ gap + μ Δp_M.
9. Lohn-Phillips-Kurve: Δw = π^e + Δprod − φ (u − NAWRU).
10. Beschäftigung (ECM): l = y − Produktivitätstrend, Anpassung mit Verzögerung; Okun-Beziehung als Prüfung.
11. Identität BIP: Y = C + G + I_A + I_B + ΔV + X − M (real, verkettet: Näherung über Vorjahrespreise).
12. Identitäten für Einkommen, Kapitalstock (K = (1−δ)K₋₁ + I) und Arbeitslosenquote.
13. Exogen im Prototyp: Zinsen, Staatskonsum, Steuersätze, Weltnachfrage, Ölpreis, Wechselkurs.

Erwartungen im Prototyp adaptiv oder aus einem kleinen VAR (π, gap, r), wie in ECB-BASE.

Funktionsnachweis: dynamische Ex-post-Simulation 2010 bis 2019, Impulsantwort auf öffentlichen Investitionsimpuls von 1 % des BIP, Abgleich der Größenordnung mit BBSR 28/2022.

### Stufenweiser Ausbau

1. **Stufe 2, Angebot und Arbeitsmarkt:** NAWRU per Kalman-Filter aus Lohn-Phillips-Kurve (Methode der EU-Kommission als Referenz), Partizipation und Arbeitszeit als Trendgleichungen, TFP-Trend mit Kapazitätsauslastung.
2. **Stufe 3, Staat:** Steuern als Satz × Bemessungsgrundlage (Lohnsteuer, Sozialbeiträge, Umsatzsteuer, Unternehmenssteuern), Transfers mit automatischen Stabilisatoren, Schuldendynamik, fiskalische Regel zur Stabilisierung der Schuldenquote. Erlaubt die belegten Schocks: Abgabensenkung, Transfers, Staatskonsum, öffentliche Investitionen, AfA-Regeln in den Kapitalnutzungskosten.
3. **Stufe 4, Außenwelt:** kleiner Euroraum-Block (IS-Kurve, Phillips-Kurve, Taylor-Regel der EZB) und Rest der Welt (Weltnachfrage, Ölpreis exogen oder AR). Ölpreis wirkt über Importpreise, Realeinkommen und Exportnachfrage der Ölförderländer.
4. **Stufe 5, Erwartungen und Steady State:** modellkonsistente Erwartungen per Stacked-Time-Lösung als Alternative zur VAR-Variante; Prüfung, dass das Modell zu einem balancierten Wachstumspfad konvergiert.
5. **Stufe 6, Prognosebetrieb:** Ragged-Edge-Behandlung mit Nowcast (Brückengleichungen aus Industrieproduktion, Lkw-Maut-Fahrleistungsindex, ifo-Index) für das laufende Quartal; Add-Faktoren mit Protokoll; Szenarien als Abweichung vom Basispfad.
6. **Stufe 7, Unsicherheit:** stochastische Simulation durch Bootstrap der historischen Residuen; alternativ Bänder aus empirischen Prognosefehlern. Ausgabe als Fan Chart und Rezessionswahrscheinlichkeit.
7. **Stufe 8, Erweiterungen:** Wohnimmobilienpreise und Hypothekenzinsen, Kreditbedingungen, gegebenenfalls Sektoraufteilung über Input-Output-Tabellen.

### Prüfverfahren

- Je Gleichung: Kointegrationstest (Engle-Granger, Johansen oder ARDL-Bounds-Test nach Pesaran, Shin und Smith), Residuendiagnostik, rekursive Schätzung und CUSUM für Stabilität, Vorzeichen- und Größenplausibilität.
- Gesamtmodell: dynamische Ex-post-Simulation mit RMSE je Variable, Konvergenz zum Steady State, Standard-Impulsantworten (Zins, Staatsausgaben, Ölpreis, Weltnachfrage) im Vergleich mit Bundesbank-Modell, ECB-BASE und Multiplikatorliteratur.
- Prognosegüte: Pseudo-Echtzeit-Prognosen mit Bundesbank-Vintages, Vergleich mit Random Walk, AR(p) und BVAR, Diebold-Mariano-Test, Mincer-Zarnowitz-Regression, Vergleich mit Gemeinschaftsdiagnose und Projektionen der Bundesregierung.

## 8. Übersichtstabelle

| Funktion des Originals | Dokumentierte Umsetzung | Offene Fragen | Mögliche Umsetzung im Nachbau |
|---|---|---|---|
| Modellklasse | Simultane ECM-Gleichungen, semi-strukturell, ähnlich FRB/US und ECB-BASE | Gleichungsanzahl, Spezifikationen | ECM-System nach ECB-BASE und Bundesbank-Modell |
| Langfristgleichgewicht | Neoklassischer Steady State, Eigenschaften wie NK-DSGE | Wie erzwungen (Restriktionen, Kalibrierung) | Langfristbeziehungen aus Optimierungsbedingungen, Steady-State-Test |
| Angebot | Cobb-Douglas mit technischem Fortschritt, NAWRU | Schätzung von TFP und NAWRU | Kalman-Filter für NAWRU, gefilterter Solow-Rest |
| Konsum | Empirische Konsumfunktion mit Glättung | Vermögens- und Zinseffekte | ECM mit Einkommen, Realzins, Vermögen |
| Investitionen | Bauinvestitionen über Wachstum und reale Kapitalnutzungskosten | Steuerliche Elemente in den Nutzungskosten | Hall-Jorgenson-Kosten inklusive AfA |
| Außenwirtschaft | Euroraum ohne DE und Rest der Welt; Ölpreis-Exportkanal | Modellierung der Partnerregionen | Kleiner Euroraum-Block, exogene Weltvariablen |
| Geldpolitik | Euroraum-Inflation und -Lücke im Modell | Zinsregel, Zinsstruktur | Taylor-Regel auf Euroraum-Ebene, Laufzeitprämie exogen |
| Fiskalpolitik | Abgaben, Transfers, Staatskonsum, Investitionen, AfA, Steuerfinanzierung | Fiskalregel, Steuerelastizitäten | Steuerblock Satz × Basis, Schuldenregel |
| Erwartungen | Nicht dokumentiert | VAR-basiert oder modellkonsistent | Beide Varianten umschaltbar |
| Daten | VGR-Verwendungsrechnung | Quellen, Zeitraum, Frequenz, Revisionen | Destatis, Eurostat, EZB, Bundesbank-Echtzeitdaten |
| Schätzung | Ökonometrisch geschätzt | Verfahren, Kalibrierung | OLS/ARDL je Gleichung, einzelne Parameter kalibriert |
| Prognosebetrieb | Halbjährliche Prognosen von Kiel Economics | Rolle von D*, Add-Faktoren, Nowcast | Nowcast-Kopplung, protokollierte Add-Faktoren |
| Szenarien | Impulsantworten, Multiplikatoren | Reskalierung der Impulsantworten | Abweichung vom Basispfad, standardisierte Schocks |
| Unsicherheit | Nicht dokumentiert | Ob es Bänder gibt | Residuen-Bootstrap, Fan Charts |
| Validierung | Vergleich der Impulsantworten mit anderen Modellen | Prognosetests, Ex-post-Simulation | Pseudo-Echtzeit-Evaluation gegen Benchmarks |
| Versionen | D*, D+ (2015) | Unterschied D* zu D+ | Entfällt |

## 9. Fragen an die Entwickler

1. Wie viele Verhaltensgleichungen und Identitäten hat D* aktuell, und gibt es eine Gleichungsliste?
2. Was unterscheidet D* vom D+-Modell, und welches wird für die laufenden Prognosen verwendet?
3. Wie werden Erwartungen gebildet: VAR-basiert, adaptiv oder modellkonsistent?
4. Welche Zinsregel und welche Fiskalregel schließen das Modell, und wie wird die Langfristlösung erzwungen?
5. Welche Frequenz, welcher Stützzeitraum und welche Datenquellen werden genutzt; wie werden Revisionen und Datenränder behandelt?
6. Wie werden NAWRU und TFP-Trend geschätzt, und wie verhält sich das Potenzial zum Verfahren der Bundesregierung?
7. Welches Schätzverfahren wird verwendet, und welche Parameter sind kalibriert?
8. Wie fließen Expertenurteil und Nowcasts in die Prognose ein?
9. Gibt es stochastische Simulationen oder Prognosebänder?
10. Gibt es interne Evaluationen der Prognosegüte gegenüber einfachen Benchmarks?
11. Ist der Anhang in BBSR-Online 28/2022 die aktuellste Modelldarstellung?

## Quellen

- Kiel Economics: [Leistungen](https://kieleconomics.de/leistungen/), [Company](https://kieleconomics.de/en/company/), [Economic Forecasts](https://kieleconomics.de/en/economic-forecasts/), [Publications](https://kieleconomics.de/en/publications/)
- Kiel Economics (2022): [Gesamtwirtschaftliche Auswirkungen der langen Niedrigzinsphase in Deutschland](https://kieleconomics.de/wp-content/uploads/2022/03/Kiel-Economics-Makrooekonomische-Auswirkungen-der-langen-Niedrigzinsphase-in-Deutschland.pdf)
- BBSR (2022): [BBSR-Online 28/2022, Produktions- und Beschäftigungswirkungen von Bauinvestitionen](https://www.bbsr.bund.de/BBSR/DE/veroeffentlichungen/bbsr-online/2022/bbsr-online-28-2022-dl.pdf?__blob=publicationFile&v=2); [Projektseite](https://www.bbsr.bund.de/BBSR/DE/forschung/programme/zb/Auftragsforschung/1Wertschoepfung/2020/effekte-bauinvestitionen/01-start.html); [zukunftbau.de](https://www.zukunftbau.de/projekte/ressortforschung/1008177-xxxx-54-6)
- Meier, Dahl (2026): [BBSR-Online 24/2026](https://www.bbsr.bund.de/BBSR/DE/veroeffentlichungen/bbsr-online/2026/bbsr-online-24-2026-dl.pdf?__blob=publicationFile&v=4)
- Hennecke, Neuberger, Ulbricht (2019): [The economic and fiscal benefits of guarantee banks in Germany](https://link.springer.com/article/10.1007/s11187-018-0069-6), Small Business Economics 53, 771–794
- IWH, Kiel Economics (2015): [Ökonomische Wirksamkeit der konjunkturstützenden finanzpolitischen Maßnahmen 2008 und 2009](https://www.iwh-halle.de/en/publications/detail/oekonomische-wirksamkeit-der-konjunktur-stuetzenden-finanzpolitischen-massnahmen-der-jahre-2008-und-2009-forschungsvorhaben-im-auftrag-des-bundesministeriums-der-finanzen)
- BMWK (2023): [Eingereichte Beiträge zum Beteiligungsprozess zur Potenzialschätzung](https://www.bundeswirtschaftsministerium.de/Redaktion/DE/Downloads/P-R/potenzialschaetzung-und-produktionsluecken-der-bundesregierung-appendix.pdf?__blob=publicationFile&v=4), darin Meier: „Modellierung der NAWRU im D*-Modell von Kiel Economics“
- Börsen-Zeitung: [Konjunkturampel zeigt vorerst intakten Aufschwung](https://www.boersen-zeitung.de/konjunktur-politik/konjunkturampel-zeigt-vorerst-intakten-aufschwung)
- Vergleichsmodelle: [Angelini et al. (2019), ECB-BASE, ECB WP 2315](https://ideas.repec.org/p/ecb/ecbwps/20192315.html); [Bundesbank Technical Paper 01/2022](https://www.bundesbank.de/resource/blob/888376/7495ae46eccc5fa1dcdfe29a461e0833/472B63F073F071307366337C94F8C870/2022-01-technical-paper-data.pdf)
- Daten: [Bundesbank-Echtzeitdatenbank](https://www.bundesbank.de/en/statistics/time-series-databases/-/macroeconomic-real-time-database-622290)
