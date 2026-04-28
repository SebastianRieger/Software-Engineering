# Demo Runbook

Dieses Runbook beschreibt den vorfuehrbaren End-to-End-Ablauf fuer die aktuelle Gesten-UI mit In-App-Kalibrierung.

## Zielbild

Die Demo zeigt vier Ebenen, die zusammenarbeiten:

- rohe Gestenerkennung ueber `GestureDetected`
- semantische UI-Eingabe ueber `UIActionRequested`
- sichtbare UI-Reaktion ueber Fokusnavigation, Shop und ArrangeMode
- profilorientierte Kalibrierung mit Analyse, Apply und Rollback

## Voraussetzungen

- Backend laeuft.
- Frontend ist gestartet oder gebaut.
- Kamera ist verfuegbar.
- Ein Browser mit der aktuellen Anwendung ist offen.
- Optional ist ein WebSocket-Monitor fuer `/ws` offen.

## Startsequenz

1. Backend starten.
2. Frontend starten.
3. Anwendung oeffnen und Grid pruefen.
4. Gestensession aktivieren.
5. Im Overlay verifizieren, dass rohes Input-Feedback und UI-Aktionsfeedback sichtbar sind.

## Empfohlener Demo-Ablauf

1. Basisnavigation zeigen.
   - Mit Swipes den Fokus ueber mehrere Zellen bewegen.
   - Mit `circle` den Shop toggeln.

2. Widget-Einfuegen zeigen.
   - Auf einer leeren Fokuszelle per Primaeraktion ein Widget einfuegen.
   - Placement-basierte Speicherung und Rendering zeigen.

3. ArrangeMode zeigen.
   - Widget fokussieren.
   - Per Langklick den ArrangeMode betreten.
   - Mit Swipes verschieben und mit Zwei-Hand-Zoom skalieren.

4. Kalibrierungswizard zeigen.
   - Button `Kalibrieren` oeffnen.
   - Profilname und Zielgesten waehlen.
   - erklaeren, dass normale UI-Steuerung jetzt gesperrt wird.

5. Eine kurze Kalibrierung demonstrieren.
   - eine oder zwei Gesten mit wenigen korrekten Wiederholungen vorfuehren
   - Fortschritt und Realtime-Feedback im Wizard zeigen
   - Analyse starten und Empfehlungen erklaeren

6. Apply und Rollback zeigen.
   - Profil anwenden.
   - danach kurz normale Gestensteuerung pruefen.
   - anschliessend Rollback demonstrieren.

## Erwartete Zuordnungen fuer die Demo

- `swipe_left` -> `move_focus_left`
- `swipe_right` -> `move_focus_right`
- `swipe_up` -> `move_focus_up`
- `swipe_down` -> `move_focus_down`
- `circle` -> `toggle_shop`
- `push_click_short` -> `primary_click`
- `push_click_long` -> `secondary_select`
- `zoom_out_hands` -> `resize_expand`
- `zoom_in_hands` -> `resize_shrink`

## Fallbacks waehrend der Demo

- Wenn die Kamera keine stabile Erkennung liefert, dieselben UI-Schritte ueber die Tastatur demonstrieren.
- Wenn die Kalibrierung nicht stabil wirkt, Session verwerfen und die vorhandene Basiskonfiguration weiter demonstrieren.
- Wenn Realtime ausfaellt, Fokus auf sichtbare UI-Reaktion und gespeicherte Konfiguration legen.

## Nach der Demo

- Gestensession sauber stoppen.
- Optional das Layout sichern.
- Beobachtete False Positives, Latenz oder auffaellige Schwellenwerte dokumentieren.