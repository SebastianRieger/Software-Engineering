# Manuelle Gesten-Validierung

Diese Checkliste deckt jetzt sowohl die normale Gestensteuerung als auch den neuen In-App-Kalibrierungsmodus ab.

## Ziel

Pruefen, dass die Anwendung auf echter Kamera- oder Raspberry-Pi-Hardware stabil startet, rohe Gestenerkennung sauber liefert, UI-Aktionen korrekt ausloest und eine Gestenkalibrierung mit Apply und Rollback reproduzierbar funktioniert.

## Vorbereitung

- Backend starten.
- Frontend starten oder aktuelles Build ausliefern.
- Kamera anschliessen und vom Betriebssystem verifizieren.
- Einen Browser mit geoeffneter Anwendung bereithalten.
- Optional einen WebSocket-Monitor fuer `/ws` oeffnen.
- Vor der Session die kanonischen Ausfuehrungen in `docs/GESTURE_DEFINITIONS.md` lesen und die Testperson darauf festlegen.
- Testgesten bereitlegen: `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down`, `circle`, `push_click_short`, `push_click_long`, `zoom_out_hands`, `zoom_in_hands`.

## Pflichtchecks Normale Gestensteuerung

1. Start- und Stop-Stabilitaet
   - Gestensession mehrfach starten und stoppen.
   - Pruefen, dass kein haengender Thread, blockierter Kamerazugriff oder festhaengender Preview-Stream sichtbar bleibt.

2. Preview- und Statusverhalten
   - Waehren einer aktiven Session Preview und Status-Endpunkte pruefen.
   - Nach Stop sicherstellen, dass Status, Fehlerzustand und Neustartpfad nachvollziehbar bleiben.

3. Rohe Basisgesten
   - `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down` und `circle` jeweils mehrfach ausfuehren.
   - fuer Swipes immer mit offener Handflaeche in der mittleren Startzone beginnen und die Endpose in Wischrichtung halten.
   - fuer `circle` immer mit Faust in der Mitte starten und erst nach geschlossenem Kreis wieder oeffnen.
   - Verifizieren, dass `GestureDetected` fachlich plausibel ist und im Idle-Zustand kein Event-Spam auftritt.
   - Im WebSocket oder Statusmodell pruefen, dass `active_phase`, `spec_id`, `candidate_scores` und `primitive_hits` zu einer erkannten Geste passen.

4. Push-Klicks und Zwei-Hand-Zoom
   - kurzen und langen Push-Klick pruefen
   - sicherstellen, dass der kurze Klick sichtbar schneller committed als der lange Klick und nicht nur kuerzer gehalten wird
   - `zoom_out_hands` und `zoom_in_hands` pruefen
   - verifizieren, dass Push und Zoom nicht mehrfach oder in Idle-Rauschen feuern
   - bei bewusst falsch ausgefuehrten Versuchen auf `reject_reason` achten, damit Ablehnungen nachvollziehbar bleiben

5. Semantische UI-Aktionen
   - WebSocket-Nachrichten auf `UIActionRequested` pruefen.
   - Fokusnavigation, Shop-Toggle, Primaeraktion, ArrangeMode und Resize muessen konsistent ausgeloest werden.

## Pflichtchecks Kalibrierungsmodus

1. Wizard-Start
   - Kalibrierungswizard oeffnen.
   - Profilname setzen oder `default` verwenden.
   - genau eine Geste fuer die Sitzung auswaehlen.
   - Wiederholungszahl zwischen 10 und 20 pruefen.

2. Interaktionssperre
   - Waehren der Kalibrierung duerfen Shop, ArrangeMode und Fokusnavigation nicht mehr auf Gesten oder Tastatureingaben reagieren.
   - Stattdessen muessen Kalibrierungsfeedback und Zielstatus sichtbar sein.

3. Sample-Aufnahme
   - jede ausgewaehlte Geste korrekt wiederholen, bis das Ziel abgeschlossen ist.
   - WebSocket oder Wizard muessen `SampleAccepted`, moegliche Rejects und `TargetCompleted` nachvollziehbar anzeigen.

4. Analyse
   - Nach Abschluss aller Ziele Analyse starten.
   - Verifizieren, dass pro Geste Metriken und konkrete Schwellenempfehlungen angezeigt werden.
   - Pose- und Temporal-Snapshots pruefen: Fingerzustand, Push-Tiefe, Hold-Stability, Peak-Speed und Delta-Distance muessen zum aufgenommenen Bewegungsmuster passen.

5. Apply
   - Profil anwenden.
   - Danach normale Gestensteuerung erneut pruefen.
   - Verhalten soll mindestens stabiler oder konsistenter als vor der Kalibrierung sein.

6. Rollback
   - Rollback ausfuehren.
   - Verifizieren, dass die ursprüngliche Gesture-Config wiederhergestellt wird.
   - Danach normale Gestensteuerung erneut pruefen.

7. Discard
   - Eine neue Kalibrierung starten und vor Apply verwerfen.
   - Verifizieren, dass keine neue Gesture-Config aktiv wird und eine neue Sitzung wieder gestartet werden kann.

## Beobachtungspunkte

- Latenzeindruck von Bewegung bis Event und bis sichtbarer UI-Reaktion
- False Positives im Idle-Zustand
- Konsistenz zwischen `GestureDetected`, `UIActionRequested` und Kalibrierungsfeedback
- Konsistenz zwischen Basiskandidat und Runtime-Metadaten wie `active_phase`, `spec_id`, `candidate_scores`, `primitive_hits` und `reject_reason`
- Unterschiede zwischen heller und dunkler Umgebung
- Stabilitaet von Apply und Rollback ueber mehrere Sitzungen hinweg

## Zielwerte fuer den aktuellen Meilenstein

- Start und Stop ohne haengenden Prozess
- reproduzierbare Fokusnavigation, Shop-Steuerung und ArrangeMode
- Kalibrierung ueber 10 bis 20 Wiederholungen pro Geste ohne externe Videos oder Skripte
- sichtbare Empfehlungen statt Auto-Apply
- deterministischer Rollback auf den gespeicherten Vorher-Snapshot