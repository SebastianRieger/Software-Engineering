# Nimrag Smart Mirror – Dokumentation

## Inhalt

### Widget-Dokumentation

| Widget | Datei | API-Key? |
|--------|-------|----------|
| [ClockWidget](widgets/clock.md) | `ClockWidget.vue` | Nein |
| [WeatherWidget](widgets/weather.md) | `WeatherWidget.vue` | Ja (`WEATHER_API_KEY`) |
| [News (Tagesschau)](widgets/news.md) | `News.vue` | Nein |
| [Market](widgets/market.md) | `Market.vue` | Ja (`TWELVE_DATA_API_KEY`) |
| [CameraWidget](widgets/camera.md) | `CameraWidget.vue` | Nein |
| [NINA Warnings](widgets/nina-warnings.md) | `NinaWarningsWidget.vue` | Nein (ARS-Code nötig) |
| [Rotating GIF](widgets/rotating-gif.md) | `rotating.gif.vue` | Nein |
| [Question of the Day](widgets/question-of-the-day.md) | `QuestionOfTheDay.vue` | Nein |
| [Useless Fact of the Day](widgets/useless-fact-of-the-day.md) | `UselessFactOfTheDay.vue` | Nein |
| [Corporate Bullshit of the Hour](widgets/corporate-bullshit-of-the-hour.md) | `CorporateBullshitOfTheHour.vue` | Nein |
| [Random Meme](widgets/random-meme.md) | `RandomMeme.vue` | Nein |

### Konfiguration

- [Konfigurationsdokumentation](configdocu.md) – alle `.env`- und `app_config.json`-Felder, Herkunft der API-Keys, Beispiel-Config

## Schnellstart

1. `.env` anlegen und API-Keys eintragen (mindestens `WEATHER_API_KEY` und `TWELVE_DATA_API_KEY` für die entsprechenden Widgets)
2. `config/app_config.json` anlegen oder anpassen (ARS-Code für NINA, Koordinaten für Wetter)
3. Backend starten: `uvicorn src.main:app --reload`
4. Frontend starten: `npm run dev`
5. Im Grid-View `E` drücken → Widget aus dem Shop in eine Zelle ziehen
