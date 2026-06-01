# Random Meme

**Dateiname:** `RandomMeme.vue`

## Was es macht

Zeigt zufällige Memes aus einem konfigurierbaren **Subreddit**, geliefert über die **meme-api.com**-API. Die Memes wechseln automatisch alle 10 Minuten. Unterstützt einen optionalen SFW-Filter, der NSFW- und Spoiler-Inhalte serverseitig herausfiltert.

**Datenquelle:** `https://meme-api.com/gimme` – kein API-Key benötigt.

## Größenverhalten

| Größe | Anzahl Memes | Layout |
|-------|-------------|--------|
| Klein (1×1) | 2 | Nebeneinander (2 Spalten) |
| Mittel (2×1) | 4 | Nebeneinander (4 Spalten) |
| Groß (2×2) | 2 | Nebeneinander (2 Spalten), höhere Auflösung |

Alle Memes werden vollständig angezeigt (`object-fit: contain`). Beim stündlichen Wechsel gibt es eine dezente Fade-Transition.

## Konfiguration

Kein API-Key nötig.

### `config/app_config.json`

```json
{
  "widgets": {
    "meme": {
      "subreddit": "memes",
      "sfw_only": true
    }
  }
}
```

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `subreddit` | string | `"memes"` | Subreddit, aus dem Memes geholt werden (ohne `r/`) |
| `sfw_only` | bool | `true` | `true`: Filtert NSFW- und Spoiler-Memes serverseitig heraus |

**Empfohlene SFW-Subreddits:** `memes`, `wholesomememes`, `ProgrammerHumor`, `dankmemes`, `AdviceAnimals`

> Bei `sfw_only: true` werden bis zu 15 Memes auf einmal abgerufen und die ersten 4 sauberen zurückgegeben. Falls kein sauberes Meme gefunden wird, wird bis zu 3× erneut versucht. Bei `sfw_only: false` wird kein Filter angewendet.

## Bild-Fehler

Lädt ein Bild nicht (z.B. gelöschter Reddit-Post), werden automatisch neue Memes nachgeladen. Ein Guard verhindert dabei Endlosschleifen.

## Fallback

Das zuletzt erfolgreich geladene Meme-Batch wird in der Datenbank gespeichert (`meme:latest`) und bei API-Ausfall als Fallback ausgespielt.

## Aktivieren

Shop öffnen (`E`) → **RandomMeme** in eine Zelle ziehen.
