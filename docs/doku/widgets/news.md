# News (Tagesschau)

**Dateiname:** `News.vue`

## Was es macht

Zeigt aktuelle deutsche Nachrichten von der **Tagesschau-API** (`tagesschau.de/api2u/news`). Der Backend-Proxy cached die Ergebnisse, um unnötige Requests zu vermeiden. Aktualisiert sich automatisch.

## Größenverhalten

| Größe | Darstellung |
|-------|-------------|
| Klein (1×1) | 2 Meldungen als kompakte Liste (Topline + Titel) |
| Mittel (2×1) | 4 Zeilen: Ressort-Badge + Titel |
| Groß (2×2) | 2 Karten nebeneinander mit Bild, Titel, Teaser und Metadaten |

Eilmeldungen werden mit rotem Streifen hervorgehoben.

## Konfiguration

Kein API-Key nötig.

### `config/app_config.json` (optional)

```json
{
  "widgets": {
    "news": {
      "ressort": null,
      "regions": [1],
      "refresh_seconds": 3600
    }
  }
}
```

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `ressort` | string \| null | `null` (alle) | Nachrichtenressort filtern |
| `regions` | int[] | `[1]` | Bundesland-IDs (1–16, siehe unten) |
| `refresh_seconds` | int | `3600` | Aktualisierungsintervall in Sekunden |

**Verfügbare Ressorts:** `inland`, `ausland`, `wirtschaft`, `sport`, `video`, `investigativ`, `wissen`

**Regions-IDs (Bundesländer):**

| ID | Bundesland |
|----|-----------|
| 1 | Baden-Württemberg |
| 2 | Bayern |
| 3 | Berlin |
| 4 | Brandenburg |
| 5 | Bremen |
| 6 | Hamburg |
| 7 | Hessen |
| 8 | Mecklenburg-Vorpommern |
| 9 | Niedersachsen |
| 10 | Nordrhein-Westfalen |
| 11 | Rheinland-Pfalz |
| 12 | Saarland |
| 13 | Sachsen |
| 14 | Sachsen-Anhalt |
| 15 | Schleswig-Holstein |
| 16 | Thüringen |

## Aktivieren

Shop öffnen (`E`) → **News** in eine Zelle ziehen.
