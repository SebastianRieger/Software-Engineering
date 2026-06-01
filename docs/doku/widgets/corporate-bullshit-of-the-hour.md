# Corporate Bullshit of the Hour

**Dateiname:** `CorporateBullshitOfTheHour.vue`

## Was es macht

Zeigt stündlich wechselnde **Corporate-Buzzword-Phrasen**, geliefert vom **Corporate BS Generator**. Zur vollen Stunde werden automatisch neue Phrasen geladen. Das Hauptwort jeder Phrase wird lila hervorgehoben vorangestellt. Reines Anzeige-Widget.

**Datenquelle:** `https://corporatebs-generator.sameerkumar.website/` – kein API-Key benötigt.

## Größenverhalten

| Größe | Anzahl Phrasen | Darstellung |
|-------|---------------|-------------|
| Klein (1×1) | 1 | Phrase in größerer Schrift, ohne Nummerierung |
| Mittel (2×1) | 3 | Buzzword + Restphrase, nummeriert |
| Groß (2×2) | 5 | Buzzword + Restphrase, nummeriert, mehr Padding |

## Konfiguration

Keine Konfiguration nötig. Keine API-Keys.

## Caching & Timing

Die Phrasen werden stündlich gecacht (Key: `bullshit:YYYY-MM-DD-HH`). Der Frontend-Timer feuert zur nächsten vollen Stunde und danach stündlich. Stündlich werden 5 parallele Requests an die API gesendet; bei Teil-Fehlern werden die erfolgreichen Phrasen zurückgegeben. Bei vollständigem API-Ausfall wird die letzte gecachte Stundenliste als Fallback genutzt.

## Aktivieren

Shop öffnen (`E`) → **CorporateBullshitOfTheHour** in eine Zelle ziehen.
