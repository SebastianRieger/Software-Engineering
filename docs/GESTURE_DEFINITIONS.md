# Kanonische Gestendefinitionen

Diese Seite beschreibt die verbindliche Ausfuehrung fuer neue Trainings-, Tuning- und Demo-Videos. Dieselben Definitionen liegen auch im Backend als zentrale Gesture-Contracts vor und steuern dort Runtime-Specs sowie den Video-Tuner.

## Allgemeine Regeln

- Jede Aufnahme beginnt mit einer klaren Startpose und endet mit einer klaren Endpose.
- Zwischen zwei Wiederholungen die Hand in eine neutrale Ruhelage zuruecknehmen.
- Keine rueckfedernden Gegenbewegungen direkt nach dem Commit ausfuehren.
- Wenn moeglich dieselbe Distanz zur Kamera und dieselbe mittlere Startzone beibehalten.

## Swipe-Gesten

- `swipe_left`, `swipe_right`, `swipe_up`, `swipe_down` beginnen immer mit offener Handflaeche in der mittleren Kamerazone.
- Von dieser Mittelposition wird stabil in genau eine Richtung gewischt.
- Die Handflaeche soll am Ende in die Wischrichtung zeigen.
- Rueckfuehrbewegungen in die Mitte gehoeren nicht mehr zur Geste, sondern erst zur Pause danach.

## Kreisgeste

- `circle` beginnt mit einer Faust in der mittleren Kamerazone.
- Falls die Hand vor der Mitte noch offen ist, wird sie spaetestens in der Mittelposition geschlossen.
- Von dort wird ein geschlossener Kreis bis zur Ursprungsposition gezogen.
- Erst nach dem vollstaendigen Kreis wird die Hand wieder geoeffnet und nach unten genommen.

## Push-Klicks

- `push_click_short` und `push_click_long` verwenden dieselbe zentrierte Index-Pose mit eingeklappten restlichen Fingern.
- Der kurze Klick hat einen schnelleren Vorwaerts-Commit und loest frueh wieder.
- Der lange Klick hat eine ruhigere Einleitung und eine klar sichtbare stabile Haltephase.
- Die Unterscheidung erfolgt also nicht nur ueber Haltedauer, sondern auch ueber das Bewegungsprofil.

## Zwei-Hand-Zoom

- `zoom_out_hands` startet mit zwei nahen Haenden und fuehrt sie symmetrisch auseinander.
- `zoom_in_hands` startet mit zwei getrennten Haenden und fuehrt sie symmetrisch zusammen.
- Beide Haende sollen moeglichst gleichzeitig laufen.

## Verwendung

- Neue Kameraaufnahmen und Tuning-Videos sollen nur noch nach diesen Definitionen erstellt werden.
- Die manuelle Validierung in `GESTURE_VALIDATION.md` verwendet dieselben Contracts.
- Nutzerdokumentation, Demo-Skripte und spaetere Kalibrierungshinweise sollen sich auf diese Seite beziehen.