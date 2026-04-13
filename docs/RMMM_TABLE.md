# RMMM Table

Version: 0.1  
Stand: 2026-04-13

## Kontext

Diese RMMM-Tabelle basiert auf den Aufgaben- und Kontext-PDFs [02_Risikomanagment.pdf](02_Risikomanagment.pdf), [02_Quality Management.pdf](02_Quality%20Management.pdf) und [09_Risikomanagement.pdf](09_Risikomanagement.pdf). Die Datei orientiert sich ausserdem am realen Projektstand in [CURRENT_STATE.md](CURRENT_STATE.md), [TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md), [PRODUCT_SCOPE.md](PRODUCT_SCOPE.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) sowie am tatsaechlichen Repo-Zustand.

Die Tabelle folgt damit direkt der Wochenaufgabe: versionierte RMMM-Dokumentation mit Risk ID, Category, Risk Description, Probability, Impact, Risk Score, Mitigation Strategy, Indicator, Contingency Plan, Responsible, Status und Last Modified Date. Die Risikobewertung nutzt eine einfache $1$-$5$-Skala fuer Wahrscheinlichkeit und Impact; der Risk Score ist $Probability \times Impact$.

## Framework-Abgleich

Die Tabelle wurde nach dem in den PDFs vermittelten Ablauf aufgebaut:

1. Risiken identifizieren: mit Vorlesungs-Checkliste aus [09_Risikomanagement.pdf](09_Risikomanagement.pdf) und Literatur-Checkliste aus [IMECS2011_pp732-737.pdf](IMECS2011_pp732-737.pdf).
2. Wahrscheinlichkeit und Auswirkung bewerten: ueber Probability, Impact und Risk Score.
3. Mitigation und Contingency planen: jede Zeile enthaelt praeventive und reaktive Massnahmen.
4. Monitoring festlegen: ueber die Spalte Indicator.
5. Verantwortung und Status pflegen: ueber Responsible, Status und Last Modified Date.

Fuer die Identifikation wurden insbesondere die wiederkehrenden Risikodimensionen aus der Vorlesung und der Top-Ten-Literatur verwendet:

- Planning and Control
- Requirements / Scope
- Technical Complexity
- Team / Skill Mix
- Organizational / External Dependencies
- Quality Factors wie Reliability, Usability, Maintainability und Security

## Bewertungslogik

| Wert | Probability | Impact |
| --- | --- | --- |
| 1 | sehr gering | geringe Auswirkung |
| 2 | gering | begrenzte Auswirkung |
| 3 | mittel | merkliche Auswirkung |
| 4 | hoch | starke Auswirkung |
| 5 | sehr hoch | kritische Auswirkung |

## RMMM-Tabelle

| Risk ID | Category | Risk Description | Probability | Impact | Risk Score | Mitigation Strategy | Indicator | Contingency Plan | Responsible | Status | Last Modified Date |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-01 | Project / Scope | Der Produktumfang der Endvision ist deutlich breiter als der aktuell belastbare Kern. Wetter und Konfiguration sind integriert, Kalender und Smart Home sind aber im laufenden Repo noch Platzhalter, wodurch Scope Drift und falsche Erwartungshaltung drohen. | 4 | 5 | 20 | Aktive Doku als verbindliche Quelle pflegen, Kernumfang aus [PRODUCT_SCOPE.md](PRODUCT_SCOPE.md) und [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) bei neuen Tasks priorisieren, neue Features erst nach stabilem Kern zulassen. | Neue Aufgaben oder Blogziele adressieren Features, die im Repo nur als Platzhalter existieren; aktive Docs und Implementierungsstand laufen auseinander. | Umfang sofort auf Kernfunktionen reduzieren und zusaetzliche Features explizit als nachgelagerte Roadmap markieren. | Team | Open | 2026-04-13 |
| R-02 | Technical | Frontend und Backend sind nur teilweise integriert. Der aktuelle produktive Schnitt deckt Wetter und Konfiguration ab, waehrend gemeinsamer WebSocket, Kalender, Smart Home und Gesten-Consumer im Frontend noch fehlen. | 4 | 4 | 16 | Weiter in kleinen vertikalen Slices arbeiten, API-Vertraege stabil halten, erst bestehende Domains ganz integrieren bevor neue Frontend-Features entstehen. | Frontend nutzt nur Wetter-/Config-Client; kein produktiver WebSocket-Consumer; weitere Backend-Domaenen bleiben im UI unsichtbar. | Fuer Demo und Vorlesung nur den vorhandenen Verticalschnitt zeigen und fehlende Domaenen explizit als Backend-Vorbereitung kennzeichnen. | Frontend + Backend | Mitigating | 2026-04-13 |
| R-03 | Technical | Die Zielplattform Raspberry Pi mit Kamera, LED und spaeter MQTT ist nur teilweise real validiert. Besonders Gestenerkennung, Kamera-Latenz und Hardwarestabilitaet sind trotz gruener Tests noch nicht auf echter Hardware abgesichert. | 4 | 5 | 20 | Checkliste aus [GESTURE_VALIDATION.md](GESTURE_VALIDATION.md) als Pflichtprozess nutzen, Hardwaretests frueh und regelmaessig einplanen, Mock-/Null-Adapter beibehalten. | Features funktionieren lokal oder in Tests, zeigen aber auf Pi/Kamera abweichendes Timing, Fehlverhalten oder Performanceeinbrueche. | Hardwarepfade fuer Demo deaktivierbar halten und auf Mock/Backend-Kern zurueckfallen, falls Zielhardware instabil bleibt. | Hardware / Backend | Open | 2026-04-13 |
| R-04 | Technical | Kalender ist laut Zielbild Kernfunktion, im Repo aber noch ein Platzhalter-Endpunkt in [Backend/src/api/api_v1/endpoints/calendar.py](Backend/src/api/api_v1/endpoints/calendar.py). Dadurch ist eine der zentralen MVP-Funktionen aktuell nicht als echter Verticalschnitt vorhanden. | 4 | 4 | 16 | Kalender als naechsten echten vertikalen Slice nach demselben Muster wie Wetter und Konfiguration umsetzen: klarer Adapter, Repository/Fallback, UI-Anbindung. | Kalender-Endpoint liefert nur `coming soon`; keine echte Backend- oder Frontend-Funktion vorhanden. | Kalender fuer die naechste Abgabe als bewusst offene Kernluecke benennen und keine Vollstaendigkeit suggerieren. | Backend + Frontend | Open | 2026-04-13 |
| R-05 | Technical | LED- und Smart-Home-Integration sind nicht auf dem Niveau der Zielarchitektur. LED-Endpunkte halten nur In-Memory-State in [Backend/src/api/api_v1/endpoints/led.py](Backend/src/api/api_v1/endpoints/led.py), Smart Home liefert Platzhalterdaten in [Backend/src/api/api_v1/endpoints/smart_home.py](Backend/src/api/api_v1/endpoints/smart_home.py). | 4 | 4 | 16 | Adaptergrenzen aus [TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md) beibehalten, LED zuerst als austauschbaren Adapter stabilisieren, MQTT erst fuer echte Geraetefaelle erweitern. | Endpunkte existieren, aber kein belastbarer Hardware- oder Domainpfad dahinter; Tests pruefen vor allem Mock-Verhalten. | Nicht als fertige Features praesentieren; fuer Demos nur Mock-Zustand zeigen oder die Features deaktivieren. | Backend / Hardware | Open | 2026-04-13 |
| R-06 | Technical | Die Gestenerkennung ist backendseitig stark verbessert, bleibt aber ein optionales High-Risk-Feature. Abhaengigkeiten wie MediaPipe/OpenCV, reale Lichtverhaeltnisse, Kameraabstand und Pi-Performance koennen die Zuverlaessigkeit trotzdem brechen. | 3 | 5 | 15 | Hands-only-Pfad als Default beibehalten, Konfigurationspersistenz und Hardware-Checkliste weiter nutzen, optionale Arm-/Pose-Erweiterungen erst nach realen Messungen angehen. | Hohe False Positives, instabile Performance, Import-/Deploy-Probleme oder Kamera-/Thread-Fehler auf Zielhardware. | Gesten fuer Live-Betrieb abschaltbar halten und bei Problemen auf REST-/UI-Steuerung ohne Vision zurueckfallen. | Backend | Mitigating | 2026-04-13 |
| R-07 | Quality | Im Frontend fehlen automatisierte Tests und eine konsolidierte State-Strategie fuer groessere Erweiterungen. Das erhoeht Regressionsrisiko bei Grid-, Widget- und spaeteren Realtime-Integrationen. | 4 | 4 | 16 | Vor naechsten groesseren Frontend-Slices Testbasis und klaren State-Ansatz definieren; vorhandenen datengetriebenen Vue-Ansatz nicht wieder mit DOM-Manipulation unterlaufen. | Keine Test-Skripte in [Frontend/nimrag-frontend/package.json](../Frontend/nimrag-frontend/package.json); Fehler werden erst manuell sichtbar. | Frontend-Umfang voruebergehend klein halten und Aenderungen nur in schmalen, manuell verifizierten Slices ausliefern. | Frontend | Open | 2026-04-13 |
| R-08 | Quality / Maintenance | Historische Architektur- und SRS-Artefakte beschreiben weiterhin eine deutlich groessere oder abweichende Welt als die aktive Kern-Doku. Das Risiko von Fehlentscheidungen durch veraltete Dokumente bleibt hoch. | 3 | 4 | 12 | Aktive Doku in [../README.md](../README.md) und [README.md](README.md) klar hervorheben, neue Entscheidungen immer zuerst in den aktiven Kernseiten nachziehen, alte Artefakte im Zweifel nur als Verlauf behandeln. | Teamentscheidungen referenzieren alte Diagramme oder SRS-Dokumente statt aktiver Kernseiten; widerspruechliche Aussagen in Reviews. | Bei Konflikten immer aktive Doku und Repo-Code als Quelle der Wahrheit priorisieren und veraltete Artefakte nur zitieren, wenn sie explizit historisch gebraucht werden. | Team | Mitigating | 2026-04-13 |
| R-09 | Security / Operational | Es gibt noch keine Authentifizierung, keine Rollenlogik und keine produktionsreife Secret-Verwaltung. Fuer einen Hochschulprototyp ist das tolerierbar, fuer echtes Deployment oder oeffentliche Exposition aber kritisch. | 3 | 5 | 15 | Scope weiter klar als Prototyp kommunizieren, keine oeffentliche Bereitstellung ohne Absicherung, Secrets nur lokal und nicht im Repo pflegen. | Backend wird ausserhalb kontrollierter Entwicklungsumgebungen betrieben oder in Demos mit produktionsnahen Erwartungen gezeigt. | Deployment auf lokale, geschlossene Entwicklungsumgebungen beschraenken und sicherheitskritische Features vor oeffentlicher Nutzung nachziehen. | Backend / Team | Open | 2026-04-13 |
| R-10 | Project / Schedule | Der Projektfortschritt ist real, aber die Endvision umfasst mehr als ein kleines Team bis Semesterende stabil liefern kann. Das groesste Terminrisiko liegt darin, an zu vielen Bereichen parallel zu bauen statt vertikale Kernfeatures fertigzustellen. | 4 | 5 | 20 | Prioritaeten aus [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) hart anwenden, Work in Progress begrenzen, zuerst Wetter, Konfiguration, Kalender und belastbare Kernprozesse abschliessen. | Viele halb angefangene Domaenen, aber nur wenige end-to-end nutzbare Features; wiederholte Richtungswechsel zwischen Hardware, UI und optionalen High-Risk-Features. | Features fuer die Vorlesung explizit auf Kernfunktionen reduzieren und optionale Themen nur als vorbereitet oder experimentell ausweisen. | Team | Open | 2026-04-13 |
| R-11 | Business / External Dependency | Kernfunktionen haengen an externen Diensten und Rahmenbedingungen, insbesondere Wetter-API heute und potenziell Kalender-API spaeter. Ausfaelle, Quoten, API-Aenderungen oder fehlende Keys koennen zentrale Mirror-Funktionen ausbremsen. | 3 | 4 | 12 | Timeout-, Cache- und Fallback-Strategie aus der bestehenden Wetterarchitektur konsequent beibehalten, externe Integrationen nur hinter klaren Adaptern einbauen und Konfiguration sauber trennen. | Haefigere HTTP-Fehler, leere API-Keys, stale Daten, instabile externe Antworten oder Integrationsstop bei neuer Provider-Aenderung. | Auf Cache, Mock oder reduzierte lokale Anzeige zurueckfallen und die betroffene Integration fuer Demo bzw. Zwischenstand explizit als degradiert markieren. | Backend | Mitigating | 2026-04-13 |
| R-12 | Team / Resource | Wissen und Verantwortung sind in einem kleinen Team zwangslaeufig auf wenige Personen konzentriert. Wenn einzelne Bereiche wie Frontend-Integration, Hardware oder Backend-Slices an nur einer Person haengen, steigt das Risiko fuer Verzug, Integrationsbrueche und fehlende Reviews. | 3 | 4 | 12 | Aktive Doku aktuell halten, kleine vertikale Slices mit klaren Contracts liefern, Code-Reviews und kurze Handover zwischen den Verantwortlichen erzwingen, statt grosse Einzeloasen zu bauen. | Ein Teilbereich kommt nur voran, wenn genau eine Person daran arbeitet; andere Teammitglieder meiden Aenderungen in diesem Bereich. | Umfang des betroffenen Bereichs reduzieren, Ownership kurzfristig teilen und fuer Abgaben nur den stabil uebernehmbaren Kern zeigen. | Team | Open | 2026-04-13 |

## Kritische Pruefung

Die drei aktuell wichtigsten Risiken sind `R-01`, `R-03` und `R-10`.

`R-01` ist kritisch, weil das Projekt in Dokumenten und Vision deutlich groesser gedacht ist als der derzeit belastbare Kern. Wenn dieser Unterschied nicht aktiv gesteuert wird, entstehen falsche Erwartungen im Team und in der Bewertung.

`R-03` ist das groesste technische Realisierungsrisiko, weil Raspberry-Pi-, Kamera- und Hardwarepfade nicht durch gute lokale Tests ersetzt werden koennen. Gerade fuer Gesten, LED und spaetere Smart-Home-Anbindung ist reale Zielplattform-Verifikation entscheidend.

`R-10` ist das groesste Organisationsrisiko. Der Repo-Stand zeigt sichtbaren Fortschritt, aber auch mehrere parallel offene Domaenen. Ohne harte Priorisierung droht ein Zustand mit vielen angefangenen, aber wenigen wirklich vorzeigbaren End-to-End-Funktionen.

Die Tabelle ist damit jetzt auch besser auf die im Framework betonten Risikoquellen verteilt: Scope und Planung (`R-01`, `R-10`), technische Unsicherheit (`R-02` bis `R-06`), externe Abhaengigkeiten (`R-11`), Team-/Ressourcenlage (`R-12`) sowie Qualitaets- und Wartungsrisiken (`R-07`, `R-08`, `R-09`).

## Groesstes technisches Risiko

Das aktuell groesste technische Risiko ist `R-03`: fehlende echte Hardware- und Zielplattform-Verifikation.

**Warum genau dieses Risiko:** Die Zielidee von Nimrag lebt von Raspberry Pi, Kamera, LED und spaeter Hardware-/IoT-Anbindung. Genau diese Bereiche lassen sich im Repo aktuell nur teilweise oder gar nicht real pruefen. Gruene Tests beweisen hier Architektur- und API-Stabilitaet, aber nicht Deployment-Reife.

**Mitigation Strategy:** Fruehe, wiederholbare manuelle Zielplattform-Pruefung mit klarer Checkliste, Beginn bei Gesten und Kamera, danach LED und MQTT. Mock-Adapter bleiben erhalten, damit die Kernentwicklung nicht von Hardware allein blockiert wird.

**Contingency Plan:** Wenn reale Hardwarepfade instabil bleiben, wird fuer Reviews und Vorlesung nur der belastbare Kern gezeigt: Wetter, Konfiguration, Backend-Grundarchitektur und optional deaktivierbare High-Risk-Features.