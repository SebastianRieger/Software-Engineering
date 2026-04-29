# Multimodale Command-Validierung

Dieses Runbook beschreibt die manuelle End-to-End-Validierung fuer die gemeinsame Command-Konfiguration, den Input-Orchestrator und die drei aktuell relevanten Modalitaeten `gesture`, `voice` und `musical_audio`.

## Ziel

Pruefen, dass alle Eingabepfade nur ueber den gemeinsamen `InputOrchestrator` semantische UI-Aktionen ausloesen, dass Command-Profile und Device-Praeferenzen konsistent persistiert werden und dass Realtime-Diagnostik zwischen rohem Input, Match-Entscheidung und veroeffentlichter UI-Aktion sauber unterscheidet.

## Voraussetzungen

- Backend laeuft mit aktueller Datenbank und aktueller `app_config`.
- Frontend ist gestartet oder gebaut.
- Kamera fuer Gesten ist verfuegbar.
- Mikrofon fuer Voice und Musical Audio ist verfuegbar.
- Ein Browser mit geoeffneter Anwendung ist offen.
- Optional ist ein WebSocket-Monitor fuer `/ws` geoeffnet.

## Vorbereitende Sichtpruefung

1. `Command Settings` oeffnen.
2. Aktives Profil, Mappings, Device-Praeferenzen und Musical-Audio-Artefakte laden lassen.
3. Pruefen, dass fuer Gesten, Voice und Musical Audio jeweils Enablement und Device-Zuordnung sichtbar sind.
4. Pruefen, dass das Overlay im normalen Betriebsmodus `Raw`, `Match` und `Action` getrennt anzeigen kann.

## Persistenz- und Profilchecks

1. Aktives Command-Profil anpassen.
   - mindestens ein Mapping fuer `voice.*` und eins fuer `musical_audio.*` aendern
   - ein Kamera- oder Mikrofon-Geraet auf Profilebene umstellen
2. Profil speichern.
3. Seite neu laden.
4. Verifizieren, dass erhalten bleiben:
   - aktives Profil
   - geaenderte Mappings
   - modality-weite Enablement-Flags
   - Gesture-, Voice- und Musical-Audio-Device-Praeferenzen
5. Optional die Legacy-Kompatibilitaet pruefen.
   - sicherstellen, dass bestehende Gesture- oder Voice-Konfiguration weiterhin lesbar bleibt
   - bestaetigen, dass die UI trotz `/config/input-actions` nicht von der alten Alias-Route abhaengt

## Realtime- und Orchestrator-Checks

1. WebSocket-Ereignisse beobachten.
2. Fuer jede spaetere Eingabe pruefen, dass die Reihenfolge fachlich plausibel bleibt:
   - modality-spezifisches Rohereignis wie `GestureDetected` oder `VoiceCommandDetected`
   - gemeinsames `RawInputDetected`
   - `CommandMatchEvaluated`
   - `UIActionRequested` nur bei akzeptiertem Match
3. Verifizieren, dass unterdrueckte oder deaktivierte Matches keine direkte UI-Aktion publizieren.

## Gestenpfad

1. Gestenruntime starten.
2. `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down`, `circle`, `push_click_short`, `push_click_long`, `zoom_out_hands` und `zoom_in_hands` jeweils mehrfach ausfuehren.
3. Pro Geste pruefen:
   - `GestureDetected` ist plausibel
   - `RawInputDetected` enthaelt den erwarteten normalisierten Raw Input
   - `CommandMatchEvaluated` zeigt `accepted`, `suppressed`, `unmapped` oder `disabled` nachvollziehbar
   - `UIActionRequested` fuehrt zur erwarteten UI-Reaktion
4. Danach das aktive Profil so aendern, dass `gesture` deaktiviert ist.
5. Erneut eine bekannte Geste ausfuehren.
6. Verifizieren:
   - rohe Erkennung kann weiter sichtbar sein
   - `CommandMatchEvaluated` meldet `disabled`
   - keine UI-Aktion wird angewendet

## Voice-Pfad

1. Voice-Runtime starten.
2. Einen konfigurierten Sprachbefehl aussprechen, zum Beispiel einen Satz, der auf `voice.shop_auf` gemappt ist.
3. Verifizieren:
   - `VoiceCommandDetected` enthaelt Transkript und `raw_input`
   - `RawInputDetected` nutzt denselben normalisierten `voice.*`-Identifier
   - `CommandMatchEvaluated` ist bei gueltigem Mapping `accepted`
   - `UIActionRequested` loest die erwartete UI-Reaktion aus
4. Danach einen bewusst unbekannten oder nicht gemappten Sprachbefehl aussprechen.
5. Verifizieren:
   - `CommandMatchEvaluated` meldet `unmapped`
   - keine UI-Aktion wird publiziert

## Musical-Audio-Pfad

1. Im Command-Settings-Flow ein vorhandenes Artefakt laden oder ein neues Artefakt anlegen.
2. Mindestens mehrere Takes aufnehmen, freigeben und daraus ein Template ableiten.
3. Artefakt als aktives Template markieren und speichern.
4. Musical-Audio-Runtime starten.
5. Das trainierte Pfeif- oder Melodiemuster ausfuehren.
6. Verifizieren:
   - `RawInputDetected` verwendet den konfigurierten `musical_audio.*`- oder `melody.*`-Identifier
   - `CommandMatchEvaluated` zeigt Score-Kontext in den Metadaten oder im Statuspfad nachvollziehbar
   - `UIActionRequested` wird nur fuer erfolgreiche Matches publiziert
7. Danach ein deutlich anderes oder absichtlich falsches Muster ausfuehren.
8. Verifizieren:
   - kein akzeptiertes Match
   - keine fehlerhafte UI-Aktion

## Arbitration- und Konfliktchecks

1. Im Profil eine kurze globale Cooldown-Phase und sinnvolle Prioritaeten setzen.
2. Erst einen hoch priorisierten Voice-Befehl ausloesen.
3. Direkt danach innerhalb des Cooldowns eine niedriger priorisierte Geste ausfuehren.
4. Verifizieren:
   - zweites Match wird als `suppressed` markiert
   - Grund verweist auf `global_cooldown`
   - keine zweite UI-Aktion wird ausgefuehrt
5. Dasselbe mit wiederholter identischer Eingabe pruefen.
6. Verifizieren:
   - Unterdrueckung ueber das Wiederholfenster ist sichtbar
   - Overlay zeigt den letzten Match-Zustand und nicht nur die letzte Aktion

## UI- und Overlay-Checks

1. Leere Zelle fokussieren und Shop oeffnen.
2. Per Geste, Tastatur, Voice oder Musical Audio eine Aktion ausloesen, die auf `primary_click`, `secondary_select` oder Shop-Navigation gemappt ist.
3. Verifizieren:
   - Shop-Navigation bleibt konsistent
   - Widget-Platzierung funktioniert weiterhin
   - Overlay zeigt getrennt `Raw`, `Match` und `Action`
4. ArrangeMode betreten und erneut multimodale Eingaben ausloesen.
5. Verifizieren, dass der Frontend-Reducer den Kontext korrekt beruecksichtigt.

## Negative Betriebsfaelle

1. Kamera oder Mikrofon vor dem Runtime-Start entziehen oder ein nicht verfuegbares Geraet waehlen.
2. Verifizieren, dass Status und Fehlermeldung nachvollziehbar bleiben.
3. Musical Audio mit fehlendem Live-Zugriff pruefen.
4. Verifizieren, dass gespeicherte Artefakte und die Settings-Oberflaeche trotzdem benutzbar bleiben.

## Abschlusskriterien

- Alle drei Modalitaeten erreichen semantische UI-Aktionen nur ueber den gemeinsamen Orchestrator.
- `RawInputDetected`, `CommandMatchEvaluated` und `UIActionRequested` sind im Frontend sichtbar und logisch getrennt.
- Device-Praeferenzen und Mappings ueberleben Reloads.
- Unterdrueckte, deaktivierte und ungemappte Eingaben fuehren nicht zu verdeckten UI-Aktionen.
- Die UI bleibt bei Shop, ArrangeMode, Kalibrierung und Command Settings stabil.