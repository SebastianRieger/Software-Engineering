# Question of the Day

**Dateiname:** `QuestionOfTheDay.vue`

## Was es macht

Zeigt täglich **eine zufällige Trivia-Frage** aus der **Open Trivia Database (OpenTDB)**. Die Frage bleibt den ganzen Tag identisch (tagesbasiertes Caching im Backend). Multiple-Choice-Antworten werden in zufälliger Reihenfolge angezeigt. Die korrekte Antwort kann im Edit-Modus per „Antwort aufdecken"-Button enthüllt werden.

**Datenquelle:** `https://opentdb.com/api.php` – kein API-Key benötigt.

## Größenverhalten

| Größe | Darstellung |
|-------|-------------|
| Klein (1×1) | Nur Fragetext (größere Schrift) |
| Mittel (2×1) | Kategorie + Frage + Antworten als 2-spaltigem Raster + Reveal-Button |
| Groß (2×2) | Kategorie + Frage + Antworten als Liste + Reveal-Button |

## Antwort aufdecken (Reveal)

1. Edit-Modus aktivieren (Taste `F` oder entsprechende Geste).
2. Im Widget erscheint der Button **„Antwort aufdecken"**.
3. Per Gestencursor auf den Button zeigen/drücken.
4. Die korrekte Antwort wird grün hervorgehoben, falsche Antworten werden abgedunkelt.

## Konfiguration

Keine Konfiguration nötig. Keine API-Keys.

## Caching

Die Frage wird serverseitig pro Tag gecacht (Key: `trivia:YYYY-MM-DD`). Auch nach einem Neustart des Spiegels bleibt die Frage für den ganzen Tag identisch. Bei Nichterreichbarkeit der API wird die letzte gecachte Frage als Fallback ausgespielt.

## Aktivieren

Shop öffnen (`E`) → **QuestionOfTheDay** in eine Zelle ziehen.
