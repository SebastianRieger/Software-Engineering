# WeatherWidget

**Dateiname:** `WeatherWidget.vue`

## Was es macht

Zeigt das aktuelle Wetter sowie eine mehrtägige Vorhersage an. Daten kommen von einer Wetter-API (über den FastAPI-Backend-Proxy `/api/v1/weather`). Aktualisiert sich automatisch im konfigurierbaren Intervall.

## Größenverhalten

| Größe | Darstellung |
|-------|-------------|
| Klein (1×1) | Temperatur + Wetter-Emoji |
| Mittel (2×1) | Temperatur, Zustand, Windgeschwindigkeit, Luftfeuchtigkeit |
| Groß (2×2) | Vollbild: aktuelle Werte + mehrtägige Vorhersage |

## Konfiguration

### `.env` (Backend, Pflicht)

```env
WEATHER_API_KEY=dein_api_key_hier
```

> **Woher?** Kostenloser Key auf [open-meteo.com](https://open-meteo.com) oder dem konfigurierten Wetter-API-Anbieter.

### `config/app_config.json` (optional)

```json
{
  "widgets": {
    "weather": {
      "refresh_seconds": 900
    }
  },
  "system": {
    "latitude": 48.7758,
    "longitude": 9.1829,
    "units": "metric"
  }
}
```

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `refresh_seconds` | int | `900` | Aktualisierungsintervall in Sekunden (min. 60) |
| `system.latitude` | float | `48.7758` | Breitengrad des Standorts |
| `system.longitude` | float | `9.1829` | Längengrad des Standorts |
| `system.units` | string | `"metric"` | `"metric"` oder `"imperial"` |

## Aktivieren

1. `WEATHER_API_KEY` in `.env` setzen.
2. Koordinaten in `app_config.json` anpassen.
3. Shop öffnen (`E`) → **WeatherWidget** in eine Zelle ziehen.
