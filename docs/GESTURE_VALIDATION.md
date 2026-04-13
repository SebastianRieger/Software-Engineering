# Manuelle Gesten-Validierung

Diese Checkliste definiert den manuellen Mindesttest fuer den aktuellen Wochenstand der Gestensteuerung auf echter Kamera- oder Raspberry-Pi-Hardware.

## Ziel

Pruefen, dass die aktuelle Backend-Basis nicht nur in Unit- und API-Tests gruen ist, sondern unter realen Kamera-Bedingungen stabil startet, sauber stoppt und fachlich plausible Events liefert.

## Vorbereitung

- Backend in der Zielumgebung starten
- Kamera anschliessen und vom Betriebssystem verifizieren
- optional WebSocket-Client oder Browser-Konsole fuer `GestureDetected`-Events oeffnen
- bekannte Testgesten vorbereiten: `swipe_left`, `swipe_right`, `swipe_down`, `circle`

## Pflichtchecks

1. Start/Stop-Stabilitaet
   - Session mehrfach hintereinander starten und stoppen
   - pruefen, dass kein haengender Thread oder blockierter Kamerazugriff sichtbar bleibt

2. Preview- und Statusverhalten
   - waehrend einer aktiven Session den Preview-Endpunkt pruefen
   - nach Stop sicherstellen, dass Status und Fehlerzustand nachvollziehbar bleiben

3. Basisgesten unter realer Kamera
   - jede der vier Basisgesten mindestens mehrfach ausfuehren
   - verifizieren, dass die Events fachlich plausibel und nicht extrem verrauscht sind

4. Kameraabstand und Handgroesse
   - dieselbe Swipe-Geste einmal naeher und einmal weiter von der Kamera entfernt testen
   - pruefen, dass die Handgroessen-Normalisierung das Verhalten stabiler macht als reine Bildkoordinaten

5. Fehlerszenarien
   - Kamera waehrend inaktiver oder aktiver Session kurz trennen oder blockieren, soweit sicher moeglich
   - pruefen, dass Fehler im Statusmodell sichtbar und nach Neustart wieder bereinigbar sind

## Beobachtungspunkte

- Latenzeindruck von Bewegung bis Event
- erkennbare False Positives im Idle-Zustand
- CPU- oder Temperaturauffaelligkeiten auf Raspberry Pi
- Unterschiede zwischen heller und dunkler Umgebung

## Zielwerte fuer den Wochencheckpoint

- Start/Stop ohne haengenden Prozess
- subjektiv fluessige Reaktion ohne grobe Aussetzer
- keine dauernden Idle-Fehler oder Event-Spam
- Kameraabstandswechsel verschlechtern die Basiserkennung nicht massiv

## Offene Anschlussfragen

- Reicht die aktuelle Hands-only-Basis auf Raspberry Pi fuer die geplante Nutzung aus?
- Braucht die Erkennung spaeter wirklich Arm-/Pose-Kontext oder reicht die Handbasis mit besserem Tuning?
- Welche False-Positive-Muster treten auf echter Hardware am haeufigsten auf?