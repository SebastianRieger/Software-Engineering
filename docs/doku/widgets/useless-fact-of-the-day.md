# Useless Fact of the Day

**Dateiname:** `UselessFactOfTheDay.vue`

## Was es macht

Zeigt täglich **einen interessanten (nutzlosen) Fakt** auf Deutsch, geliefert von der **uselessfacts API**. Der Fakt bleibt den ganzen Tag identisch (tagesbasiertes Caching im Backend). Reines Anzeige-Widget ohne Interaktion.

**Datenquelle:** `https://uselessfacts.jsph.pl/api/v2/facts/today?language=de` – kein API-Key benötigt.

## Größenverhalten

| Größe | Darstellung |
|-------|-------------|
| Klein (1×1) | Fakttext, `13px`, bis zu 3 Zeilen |
| Mittel (2×1) | Fakttext, `16px`, bis zu 4 Zeilen |
| Groß (2×2) | Fakttext, `20px`, bis zu 6 Zeilen, mit dezentem Anführungszeichen-Akzent |

## Konfiguration

Keine Konfiguration nötig. Keine API-Keys.

## Caching

Der Fakt wird serverseitig pro Tag gecacht (Key: `fact:YYYY-MM-DD`). Bei Nichterreichbarkeit der API wird der letzte gecachte Fakt als Fallback ausgespielt.

## Aktivieren

Shop öffnen (`E`) → **UselessFactOfTheDay** in eine Zelle ziehen.
