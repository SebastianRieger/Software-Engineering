# RMMM Table

Version: 0.2  
Stand: 2026-04-14

## Kontext

Diese RMMM-Tabelle basiert auf den Aufgaben- und Kontext-PDFs [02_Risikomanagment.pdf](02_Risikomanagment.pdf), [02_Quality Management.pdf](02_Quality%20Management.pdf) und [09_Risikomanagement.pdf](09_Risikomanagement.pdf). Die Datei orientiert sich außerdem am realen Projektstand in [CURRENT_STATE.md](CURRENT_STATE.md), [TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md), [PRODUCT_SCOPE.md](PRODUCT_SCOPE.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) sowie am tatsächlichen Repo-Zustand.

Die Tabelle folgt damit direkt der Wochenaufgabe: versionierte RMMM-Dokumentation mit Risk ID, Category, Risk Description, Probability, Impact, Risk Score, Mitigation Strategy, Indicator, Contingency Plan, Responsible, Status und Last Modified Date. Die Risikobewertung nutzt eine einfache $1$-$5$-Skala für Wahrscheinlichkeit und Impact; der Risk Score ist $Probability \times Impact$.

## Framework-Abgleich

Die Tabelle wurde nach dem in den PDFs vermittelten Ablauf aufgebaut:

1. Risiken identifizieren: mit Vorlesungs-Checkliste aus [09_Risikomanagement.pdf](09_Risikomanagement.pdf) und Literatur-Checkliste aus [IMECS2011_pp732-737.pdf](IMECS2011_pp732-737.pdf).
2. Wahrscheinlichkeit und Auswirkung bewerten: über Probability, Impact und Risk Score.
3. Mitigation und Contingency planen: jede Zeile enthält präventive und reaktive Maßnahmen.
4. Monitoring festlegen: über die Spalte Indicator.
5. Verantwortung und Status pflegen: über Responsible, Status und Last Modified Date.

Für die Identifikation wurden insbesondere die wiederkehrenden Risikodimensionen aus der Vorlesung und der Top-Ten-Literatur verwendet:

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
| R-01 | Project / Scope | Der Produktumfang der Endvision ist deutlich breiter als der aktuell belastbare Kern. Wetter und Konfiguration sind integriert, Kalender und Smart Home sind aber im laufenden Repo noch Platzhalter, wodurch Scope Drift und falsche Erwartungshaltung drohen. | 4 | 5 | 20 | Aktive Doku als verbindliche Quelle pflegen, Kernumfang aus [PRODUCT_SCOPE.md](PRODUCT_SCOPE.md) und [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) bei neuen Tasks priorisieren, neue Features erst nach stabilem Kern zulassen. | Neue Aufgaben oder Blogziele adressieren Features, die im Repo nur als Platzhalter existieren; aktive Docs und Implementierungsstand laufen auseinander. | Umfang sofort auf Kernfunktionen reduzieren und zusätzliche Features explizit als nachgelagerte Roadmap markieren. | Team | Open | 2026-04-13 |
| R-02 | Technical | Frontend und Backend sind nur teilweise integriert. Der aktuelle produktive Schnitt deckt Wetter, Konfiguration und einen schmalen Hardware-/WebSocket-Slice ab, waehrend Kalender, Smart Home und breitere Event-Consumer im Frontend noch fehlen. | 4 | 4 | 16 | Weiter in kleinen vertikalen Slices arbeiten, API-Verträge stabil halten, erst bestehende Domains ganz integrieren bevor neue Frontend-Features entstehen. | Frontend nutzt Wetter-/Config-Client und Hardware-Realtime, aber weitere Backend-Domänen bleiben im UI unsichtbar. | Fuer Demo und Vorlesung nur den belastbaren Kern zeigen und fehlende Domänen explizit als naechste Verticals kennzeichnen. | Frontend + Backend | Mitigating | 2026-04-14 |
| R-03 | Technical | Die Zielplattform Raspberry Pi mit Kamera, LED und später MQTT ist nur teilweise real validiert. Besonders Gestenerkennung, Kamera-Latenz und Hardwarestabilität sind trotz grüner Tests noch nicht auf echter Hardware abgesichert. | 4 | 5 | 20 | Checkliste aus [GESTURE_VALIDATION.md](GESTURE_VALIDATION.md) als Pflichtprozess nutzen, Hardwaretests früh und regelmäßig einplanen, Mock-/Null-Adapter beibehalten. | Features funktionieren lokal oder in Tests, zeigen aber auf Pi/Kamera abweichendes Timing, Fehlverhalten oder Performanceeinbrüche. | Hardwarepfade für Demo deaktivierbar halten und auf Mock/Backend-Kern zurückfallen, falls Zielhardware instabil bleibt. | Hardware / Backend | Open | 2026-04-13 |
| R-04 | Technical | Kalender ist laut Zielbild Kernfunktion, im Repo aber weiter nur ein Platzhalterpfad in [../Backend/src/api/data_endpoints.py](../Backend/src/api/data_endpoints.py). Dadurch ist eine der zentralen MVP-Funktionen aktuell nicht als echter Verticalschnitt vorhanden. | 4 | 4 | 16 | Kalender als naechsten echten vertikalen Slice nach demselben Muster wie Wetter und Konfiguration umsetzen: klarer Adapter, Repository/Fallback, UI-Anbindung. | Kalender-Endpoint liefert nur `coming soon`; keine echte Backend- oder Frontend-Funktion vorhanden. | Kalender fuer die naechste Abgabe als bewusst offene Kernluecke benennen und keine Vollstaendigkeit suggerieren. | Backend + Frontend | Open | 2026-04-14 |
| R-05 | Technical | LED- und Smart-Home-Integration sind nicht auf dem Niveau der Zielarchitektur. LED-Endpunkte und Voice-/Hardware-Steuerung laufen ueber [../Backend/src/api/device_endpoints.py](../Backend/src/api/device_endpoints.py), Smart Home bleibt Platzhalter in [../Backend/src/api/data_endpoints.py](../Backend/src/api/data_endpoints.py). | 4 | 4 | 16 | Adaptergrenzen aus [TARGET_ARCHITECTURE.md](TARGET_ARCHITECTURE.md) beibehalten, LED zuerst als austauschbaren Adapter stabilisieren, MQTT erst fuer echte Geraetfaelle erweitern. | Endpunkte existieren, aber kein belastbarer Zielhardware- oder Domainpfad dahinter; Tests pruefen vor allem Mock-Verhalten. | Nicht als fertige Features praesentieren; fuer Demos nur Mock-Zustand zeigen oder die Features deaktivieren. | Backend / Hardware | Open | 2026-04-14 |
| R-06 | Technical | Die Gestenerkennung ist backendseitig stark verbessert, bleibt aber ein optionales High-Risk-Feature. Abhängigkeiten wie MediaPipe/OpenCV, reale Lichtverhältnisse, Kameraabstand und Pi-Performance können die Zuverlässigkeit trotzdem brechen. | 3 | 5 | 15 | Hands-only-Pfad als Default beibehalten, Konfigurationspersistenz und Hardware-Checkliste weiter nutzen, optionale Arm-/Pose-Erweiterungen erst nach realen Messungen angehen. | Hohe False Positives, instabile Performance, Import-/Deploy-Probleme oder Kamera-/Thread-Fehler auf Zielhardware. | Gesten für Live-Betrieb abschaltbar halten und bei Problemen auf REST-/UI-Steuerung ohne Vision zurückfallen. | Backend | Mitigating | 2026-04-13 |
| R-07 | Quality | Im Frontend fehlen automatisierte Tests und eine konsolidierte State-Strategie fuer groessere Erweiterungen. Das erhoeht Regressionsrisiko bei Grid-, Widget- und spaeteren Realtime-Integrationen. | 4 | 4 | 16 | Vor naechsten groesseren Frontend-Slices Testbasis und klaren State-Ansatz definieren; den vorhandenen datengetriebenen Vue-Ansatz plus neue Helper-Schicht nicht wieder mit Inline-Orchestrierung ueberladen. | Keine Test-Skripte in [../Frontend/nimrag-frontend/package.json](../Frontend/nimrag-frontend/package.json); Fehler werden weiter erst manuell sichtbar. | Frontend-Umfang voruebergehend klein halten und Aenderungen nur in schmalen, manuell verifizierten Slices ausliefern. | Frontend | Open | 2026-04-14 |
| R-08 | Quality / Maintenance | Historische Architektur- und SRS-Artefakte beschreiben weiterhin eine deutlich größere oder abweichende Welt als die aktive Kern-Doku. Das Risiko von Fehlentscheidungen durch veraltete Dokumente bleibt hoch. | 3 | 4 | 12 | Aktive Doku in [../README.md](../README.md) und [README.md](README.md) klar hervorheben, neue Entscheidungen immer zuerst in den aktiven Kernseiten nachziehen, alte Artefakte im Zweifel nur als Verlauf behandeln. | Teamentscheidungen referenzieren alte Diagramme oder SRS-Dokumente statt aktiver Kernseiten; widersprüchliche Aussagen in Reviews. | Bei Konflikten immer aktive Doku und Repo-Code als Quelle der Wahrheit priorisieren und veraltete Artefakte nur zitieren, wenn sie explizit historisch gebraucht werden. | Team | Mitigating | 2026-04-13 |
| R-09 | Security / Operational | Es gibt noch keine Authentifizierung, keine Rollenlogik und keine produktionsreife Secret-Verwaltung. Für einen Hochschulprototyp ist das tolerierbar, für echtes Deployment oder öffentliche Exposition aber kritisch. | 3 | 5 | 15 | Scope weiter klar als Prototyp kommunizieren, keine öffentliche Bereitstellung ohne Absicherung, Secrets nur lokal und nicht im Repo pflegen. | Backend wird außerhalb kontrollierter Entwicklungsumgebungen betrieben oder in Demos mit produktionsnahen Erwartungen gezeigt. | Deployment auf lokale, geschlossene Entwicklungsumgebungen beschränken und sicherheitskritische Features vor öffentlicher Nutzung nachziehen. | Backend / Team | Open | 2026-04-13 |
| R-10 | Business / External Dependency | Kernfunktionen hängen an externen Diensten und Rahmenbedingungen, insbesondere Wetter-API heute und potenziell Kalender-API später. Ausfälle, Quoten, API-Änderungen oder fehlende Keys können zentrale Mirror-Funktionen ausbremsen. | 3 | 4 | 12 | Timeout-, Cache- und Fallback-Strategie aus der bestehenden Wetterarchitektur konsequent beibehalten, externe Integrationen nur hinter klaren Adaptern einbauen und Konfiguration sauber trennen. | Häufigere HTTP-Fehler, leere API-Keys, stale Daten, instabile externe Antworten oder Integrationsstopp bei neuer Provider-Änderung. | Auf Cache, Mock oder reduzierte lokale Anzeige zurückfallen und die betroffene Integration für Demo bzw. Zwischenstand explizit als degradiert markieren. | Backend | Mitigating | 2026-04-13 |
| R-11 | Team / Resource | Wissen und Verantwortung sind in einem kleinen Team zwangsläufig auf wenige Personen konzentriert. Wenn einzelne Bereiche wie Frontend-Integration, Hardware oder Backend-Slices an nur einer Person hängen, steigt das Risiko für Verzug, Integrationsbrüche und fehlende Reviews. | 3 | 4 | 12 | Aktive Doku aktuell halten, kleine vertikale Slices mit klaren Contracts liefern, Code-Reviews und kurze Handover zwischen den Verantwortlichen erzwingen, statt große Einzeloasen zu bauen. | Ein Teilbereich kommt nur voran, wenn genau eine Person daran arbeitet; andere Teammitglieder meiden Änderungen in diesem Bereich. | Umfang des betroffenen Bereichs reduzieren, Ownership kurzfristig teilen und für Abgaben nur den stabil übernehmbaren Kern zeigen. | Team | Open | 2026-04-13 |

## Kritische Prüfung

Die drei aktuell wichtigsten Risiken sind `R-01`, `R-03` und `R-04`.

`R-01` ist kritisch, weil das Projekt in Dokumenten und Vision deutlich größer gedacht ist als der derzeit belastbare Kern. Wenn dieser Unterschied nicht aktiv gesteuert wird, entstehen falsche Erwartungen im Team und in der Bewertung.

`R-03` ist das größte technische Realisierungsrisiko, weil Raspberry-Pi-, Kamera- und Hardwarepfade nicht durch gute lokale Tests ersetzt werden können. Gerade für Gesten, LED und spätere Smart-Home-Anbindung ist reale Zielplattform-Verifikation entscheidend.

`R-04` ist für den Produktkern kritisch, weil Kalender laut Zielbild und Produktumfang kein Nice-to-have, sondern eine Kernfunktion ist. Solange diese Domäne nur als Platzhalter existiert, bleibt der MVP fachlich unvollständig.

Die Tabelle ist damit jetzt auch besser auf die im Framework betonten Risikoquellen verteilt: Scope (`R-01`), technische Unsicherheit (`R-02` bis `R-06`), Qualitäts- und Wartungsrisiken (`R-07`, `R-08`, `R-09`), externe Abhängigkeiten (`R-10`) sowie Team-/Ressourcenlage (`R-11`).

## Größtes technisches Risiko

Das aktuell größte technische Risiko ist `R-03`: fehlende echte Hardware- und Zielplattform-Verifikation.

**Warum genau dieses Risiko:** Die Zielidee von Nimrag lebt von Raspberry Pi, Kamera, LED und später Hardware-/IoT-Anbindung. Genau diese Bereiche lassen sich im Repo aktuell nur teilweise oder gar nicht real prüfen. Grüne Tests beweisen hier Architektur- und API-Stabilität, aber nicht Deployment-Reife.

**Mitigation Strategy:** Frühe, wiederholbare manuelle Zielplattform-Prüfung mit klarer Checkliste, Beginn bei Gesten und Kamera, danach LED und MQTT. Mock-Adapter bleiben erhalten, damit die Kernentwicklung nicht von Hardware allein blockiert wird.

**Contingency Plan:** Wenn reale Hardwarepfade instabil bleiben, wird für Reviews und Vorlesung nur der belastbare Kern gezeigt: Wetter, Konfiguration, Backend-Grundarchitektur und optional deaktivierbare High-Risk-Features.