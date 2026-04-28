# Demo Runbook

Dieses Runbook beschreibt den vorfuehrbaren End-to-End-Ablauf fuer die aktuelle Gesten-UI-Integration mit placement-basiertem Grid, Fokuszustand, Widget-Shop und ArrangeMode.

## Zielbild

Die Demo zeigt drei Ebenen, die zusammenarbeiten:

- rohe Gestenerkennung ueber `GestureDetected`
- semantische Eingabe ueber `UIActionRequested`
- sichtbare UI-Reaktion ueber Fokusnavigation, Shop-Aktionen und ArrangeMode

## Voraussetzungen

- Backend laeuft und die Gestensession kann gestartet werden.
- Frontend ist gebaut oder im Dev-Modus gestartet.
- Kamera ist verfuegbar.
- Ein Browser mit der aktuellen Anwendung ist offen.
- Optional ist ein WebSocket-Monitor fuer `/ws` offen.

## Startsequenz

1. Backend starten.
2. Frontend starten oder das aktuelle Build bereitstellen.
3. Anwendung oeffnen und pruefen, dass das Grid sichtbar ist.
4. Gestensession aktivieren.
5. Im Overlay verifizieren, dass rohes Input-Feedback, letzte UI-Aktion und Fokusstatus sichtbar sind.

## Demo-Ablauf

1. Fokusnavigation zeigen.
   - Mit Swipes den Fokus ueber mehrere Zellen bewegen.
   - Im Overlay und im Grid zeigen, dass Fokuszustand konsistent aktualisiert wird.

2. Widget-Shop oeffnen.
   - Mit `circle` den Shop toggeln.
   - Zeigen, dass der Shop sich am aktuellen Fokus orientiert und nur leere Zellen neu belegt werden.

3. Widget einfuegen.
   - Auf einer leeren Fokuszelle per Primaeraktion ein Widget einfuegen.
   - Zeigen, dass das Widget placement-basiert gespeichert und sofort im Grid gerendert wird.

4. ArrangeMode aktivieren.
   - Ein Widget fokussieren.
   - Per Langklick den ArrangeMode betreten.
   - Im Overlay die aktive Auswahl und den Moduswechsel zeigen.

5. Widget verschieben.
   - Im ArrangeMode mit Swipes das selektierte Widget verschieben.
   - Zeigen, dass Kollisionen und Grid-Grenzen eingehalten werden.

6. Widget skalieren.
   - Im ArrangeMode mit Zwei-Hand-Zoom vergroessern oder verkleinern.
   - Zeigen, dass die Groesse im Raster erhalten bleibt und ungueltige Groessen abgefangen werden.

7. ArrangeMode verlassen.
   - Mit `circle` oder durch passende Aktion den ArrangeMode verlassen.
   - Pruefen, dass Fokus und Auswahl konsistent zurueckgesetzt werden.

## Erwartete Zuordnungen

- `swipe_left` -> `move_focus_left`
- `swipe_right` -> `move_focus_right`
- `swipe_up` -> `move_focus_up`
- `swipe_down` -> `move_focus_down`
- `circle` -> `toggle_shop`
- `push_click_short` -> `primary_click`
- `push_click_long` -> `secondary_select`
- `zoom_out_hands` -> `resize_expand`
- `zoom_in_hands` -> `resize_shrink`

Die konkrete Zuordnung ist absichtlich konfigurierbar. Fuer die Demo sollte vorab geprueft werden, dass die gespeicherte Mapping-Konfiguration zu diesem Ablauf passt.

## Fallbacks waehrend der Demo

- Wenn die Kamera keine stabile Erkennung liefert, kann dieselbe Navigation ueber die Tastatur gezeigt werden.
- Pfeiltasten bewegen Fokus oder im ArrangeMode das selektierte Widget.
- `Enter` oder Leertaste fuehrt die Primaeraktion aus.
- `e` toggelt den Shop.
- `[` und `]` skalieren das ausgewaehlte Widget.
- `Escape` beendet den ArrangeMode oder schliesst den Shop.

## Abbruch- und Recovery-Punkte

- Wenn die Gestensession haengt, Session stoppen und neu starten.
- Wenn der Shop offen bleibt, per `circle` oder `Escape` schliessen.
- Wenn ein Widget nicht platzierbar ist, Fokus auf freie Zelle setzen und erneut versuchen.
- Wenn Realtime ausfaellt, die sichtbare UI weiterhin ueber Tastatur demonstrieren und den WebSocket-Zustand separat erklaeren.

## Nach der Demo

- Gestensession sauber stoppen.
- Optional das Layout ueber die Config-API sichern.
- Beobachtete False Positives, Latenz und Schwellenwertprobleme dokumentieren.
