# Manuelle Gesten-Validierung

Diese Checkliste beschreibt den manuellen Mindesttest fuer den aktuellen Demo-Stand der Gestensteuerung. Sie deckt nicht nur rohe Gestenerkennung ab, sondern auch die neue semantische UI-Aktionsschicht mit Fokus, Widget-Shop und ArrangeMode.

## Ziel

Pruefen, dass die Anwendung auf echter Kamera- oder Raspberry-Pi-Hardware stabil startet, nachvollziehbare `GestureDetected`-Events liefert und daraus die erwarteten `UIActionRequested`-Events fuer die Frontend-Steuerung entstehen.

## Vorbereitung

- Backend in der Zielumgebung starten.
- Frontend starten oder ein aktuelles Build ausliefern.
- Kamera anschliessen und vom Betriebssystem verifizieren.
- Einen WebSocket-Client oder die Browser-Konsole fuer den `/ws`-Kanal oeffnen.
- Sicherstellen, dass sowohl rohe Events als auch semantische UI-Aktionen sichtbar sind.
- Bekannte Testgesten vorbereiten: `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down`, `circle`, `push_click_short`, `push_click_long`, `zoom_out_hands`, `zoom_in_hands`.

## Pflichtchecks

1. Start- und Stop-Stabilitaet
   - Gestensession mehrfach hintereinander starten und stoppen.
   - Pruefen, dass kein haengender Thread, blockierter Kamerazugriff oder festhaengender Preview-Stream sichtbar bleibt.

2. Preview- und Statusverhalten
   - Waehren einer aktiven Session Preview und Status-Endpunkte pruefen.
   - Nach Stop sicherstellen, dass Status, Fehlerzustand und Neustartpfad nachvollziehbar bleiben.

3. Rohe Basisgesten
   - `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down` und `circle` jeweils mehrfach ausfuehren.
   - Verifizieren, dass `GestureDetected` fachlich plausibel ist und im Idle-Zustand kein dauerhafter Event-Spam auftritt.

4. Push-Klicks
   - Einen kurzen Push-Klick ausfuehren und auf `push_click_short` pruefen.
   - Einen langen Push-Klick ausfuehren und auf `push_click_long` pruefen.
   - Beobachten, ob die Unterscheidung reproduzierbar bleibt und kein Mehrfachfeuern pro Pose entsteht.

5. Zwei-Hand-Zoom
   - Beide Haende initial in naeherer Distanz platzieren und auseinanderbewegen, um `zoom_out_hands` zu pruefen.
   - Beide Haende initial weiter auseinander platzieren und zusammenbewegen, um `zoom_in_hands` zu pruefen.
   - Verifizieren, dass Zoom nur bei stabiler Zwei-Hand-Erfassung und nicht bei Einhandrauschen ausgeloest wird.

6. Semantische UI-Aktionen
   - WebSocket-Nachrichten auf `UIActionRequested` pruefen.
   - Erwartete Zuordnungen bestaetigen: horizontale und vertikale Swipes bewegen Fokus oder Widget, `circle` toggelt den Shop, kurzer Push ist Primaeraktion, langer Push aktiviert ArrangeMode, Zwei-Hand-Zoom skaliert Widgets im ArrangeMode.

7. Fokus, Shop und ArrangeMode in der UI
   - Mit Swipes den Fokus ueber das 4x4-Grid bewegen.
   - Auf einer leeren Zelle den Shop oeffnen und per Primaeraktion ein Widget einfuegen.
   - Auf einem bestehenden Widget per Langklick den ArrangeMode aktivieren.
   - Im ArrangeMode das selektierte Widget verschieben und mit Zoom vergroessern oder verkleinern.
   - ArrangeMode wieder sauber verlassen und pruefen, dass Fokus und Auswahl konsistent bleiben.

8. Kameraabstand und Licht
   - Dieselbe Swipe-Geste einmal naeher und einmal weiter von der Kamera entfernt testen.
   - Push- und Zoom-Gesten unter mindestens zwei Lichtbedingungen pruefen.
   - Verifizieren, dass die Handgroessen- und Tiefennormalisierung das Verhalten stabiler macht als reine Bildkoordinaten.

9. Fehlerszenarien
   - Kamera in sicherem Rahmen waehrend inaktiver oder aktiver Session kurz trennen oder blockieren.
   - Pruefen, dass Fehler im Statusmodell sichtbar werden und nach Neustart der Session bereinigt werden koennen.

## Beobachtungspunkte

- Latenzeindruck von Bewegung bis rohem Event und bis sichtbarer UI-Reaktion.
- False Positives im Idle-Zustand.
- Konsistenz zwischen `GestureDetected` und `UIActionRequested`.
- CPU- oder Temperaturauffaelligkeiten auf Raspberry Pi.
- Unterschiede zwischen heller und dunkler Umgebung.
- Versehentliches Oeffnen des Shops oder ungewolltes Betreten des ArrangeMode.

## Zielwerte fuer den Demo-Checkpoint

- Start und Stop ohne haengenden Prozess.
- Subjektiv fluessige Reaktion ohne grobe Aussetzer.
- Keine dauernden Idle-Fehler und kein Event-Spam.
- Fokusnavigation, Shop-Toggle und ArrangeMode sind vorfuehrbar reproduzierbar.
- Kameraabstand und Lichtwechsel verschlechtern die Erkennung nicht massiv.

## Offene Anschlussfragen

- Wie robust bleiben Push-Klick und Zwei-Hand-Zoom auf Raspberry Pi unter realer Last?
- Welche Gesten-Schwellwerte muessen fuer Demo versus Dauerbetrieb unterschiedlich sein?
- Soll die UI-Aktionszuordnung spaeter pro Nutzerprofil oder Szenario umschaltbar werden?
