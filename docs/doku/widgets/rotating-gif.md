# Rotating GIF

**Dateiname:** `rotating.gif.vue`

## Was es macht

Zeigt zufällige, rotierende/lustige GIFs aus einer fest eingebetteten Liste an. Das GIF wechselt alle paar Sekunden automatisch. Kein Backend-Aufruf – alle GIF-URLs sind direkt im Widget hinterlegt (Tenor CDN).

Aktuelle GIF-Auswahl enthält u.a.: Drehende Ente, Spinnendes Kapybara, Drehender Gorilla, Oiia-Cat, Spinning Chicken und weitere.

## Größenverhalten

Das GIF füllt die Zelle vollständig aus. Je nach Bild wird `object-fit: contain` (Ente) oder `object-fit: cover` (alle anderen) verwendet, damit nichts abgeschnitten wird.

## Konfiguration

Keine Konfiguration nötig. Keine API-Keys.

## GIFs anpassen

Die GIF-Liste ist direkt in `rotating.gif.vue` als Array `gifs[]` hinterlegt und kann dort einfach erweitert oder verändert werden.

## Aktivieren

Shop öffnen (`E`) → **rotating.gif** in eine Zelle ziehen.
