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
   - Verifizieren, dass `GestureDetected` fachlich plausibel ist und im Idle-Zustand kein Event-Spam auftritt.

4. Push-Klicks und Zwei-Hand-Zoom
   - kurzen und langen Push-Klick pruefen
   - `zoom_out_hands` und `zoom_in_hands` pruefen
   - verifizieren, dass Push und Zoom nicht mehrfach oder in Idle-Rauschen feuern

5. Semantische UI-Aktionen
   - WebSocket-Nachrichten auf `UIActionRequested` pruefen.
   - Fokusnavigation, Shop-Toggle, Primaeraktion, ArrangeMode und Resize muessen konsistent ausgeloest werden.

## Pflichtchecks Kalibrierungsmodus

1. Wizard-Start
   - Kalibrierungswizard oeffnen.
   - Profilname setzen oder `default` verwenden.
   - alle Gesten oder eine Teilmenge auswaehlen.
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
- Unterschiede zwischen heller und dunkler Umgebung
- Stabilitaet von Apply und Rollback ueber mehrere Sitzungen hinweg

## Zielwerte fuer den aktuellen Meilenstein

- Start und Stop ohne haengenden Prozess
- reproduzierbare Fokusnavigation, Shop-Steuerung und ArrangeMode
- Kalibrierung ueber 10 bis 20 Wiederholungen pro Geste ohne externe Videos oder Skripte
- sichtbare Empfehlungen statt Auto-Apply
- deterministischer Rollback auf den gespeicherten Vorher-Snapshot