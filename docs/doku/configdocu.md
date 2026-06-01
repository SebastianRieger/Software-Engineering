# Konfigurationsdokumentation – Nimrag Smart Mirror

Es gibt zwei Konfigurationsebenen: die **Umgebungsvariablen** (`.env`) für Backend-Secrets und API-Keys, und die **App-Config** (`config/app_config.json`) für Widget- und Systemeinstellungen.

---

## 1. `.env` – Umgebungsvariablen (Backend)

Datei liegt im Backend-Wurzelverzeichnis: `Backend/.env`

```env
# ── API-Keys ──────────────────────────────────────────
WEATHER_API_KEY=
TWELVE_DATA_API_KEY=

# ── Google (Kalender-Integration) ────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# ── MQTT (Smart Home) ─────────────────────────────────
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# ── Datenbank ─────────────────────────────────────────
DATABASE_URL=sqlite:///./nimrag.db

# ── Sonstiges ─────────────────────────────────────────
SECRET_KEY=aendern-in-produktion
LOG_LEVEL=INFO
```

### Wo bekomme ich die Keys her?

| Variable | Woher | Kosten |
|----------|-------|--------|
| `WEATHER_API_KEY` | [open-meteo.com](https://open-meteo.com) (kein Account nötig) oder eigener Anbieter | Kostenlos |
| `TWELVE_DATA_API_KEY` | [twelvedata.com](https://twelvedata.com) → Registrieren → Dashboard → API Key | Kostenlos (800 Req/Tag) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | [console.cloud.google.com](https://console.cloud.google.com) → Projekt → APIs & Dienste → Anmeldedaten → OAuth 2.0 | Kostenlos |
| `MQTT_*` | Eigener MQTT-Broker (z.B. Mosquitto) oder Cloud-Broker (z.B. HiveMQ) | Abhängig vom Anbieter |
| `SECRET_KEY` | Beliebiger langer Zufallsstring, z.B. `openssl rand -hex 32` | – |

---

## 2. `config/app_config.json` – App-Konfiguration

Datei liegt unter: `Backend/config/app_config.json`

Wird beim ersten Start automatisch mit Standardwerten angelegt, falls sie nicht existiert.

### Vollständiges Beispiel

```json
{
  "version": 1,
  "system": {
    "location_name": "Stuttgart",
    "latitude": 48.7758,
    "longitude": 9.1829,
    "units": "metric",
    "theme": "dark",
    "weather_refresh_seconds": 900
  },
  "widgets": {
    "weather": {
      "refresh_seconds": 900
    },
    "news": {
      "ressort": null,
      "regions": [1],
      "refresh_seconds": 3600
    },
    "camera": {
      "preferred_device_id": null,
      "preferred_device_label": null
    },
    "market": {
      "symbols": ["AAPL", "MSFT", "NVDA", "BTC/USD", "ETH/USD"],
      "refresh_seconds": 900
    },
    "nina": {
      "ars": "08111000000",
      "refresh_seconds": 300
    },
    "meme": {
      "subreddit": "memes",
      "sfw_only": true
    }
  }
}
```

---

### `system`

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `location_name` | string \| null | `null` | Anzeigename des Standorts (nur Display) |
| `latitude` | float | `48.7758` | Breitengrad für Wetter-Abfragen |
| `longitude` | float | `9.1829` | Längengrad für Wetter-Abfragen |
| `units` | `"metric"` \| `"imperial"` | `"metric"` | Einheitensystem |
| `theme` | `"dark"` \| `"light"` \| `"system"` | `"dark"` | UI-Theme |
| `weather_refresh_seconds` | int | `900` | System-weites Wetter-Intervall |

---

### `widgets.weather`

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `refresh_seconds` | int | `900` | Aktualisierungsintervall (min. 60, max. 86400) |

---

### `widgets.news`

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `ressort` | string \| null | `null` | Nachrichtenressort. Werte: `inland`, `ausland`, `wirtschaft`, `sport`, `video`, `investigativ`, `wissen`. `null` = alle |
| `regions` | int[] | `[1]` | Liste der Bundesland-IDs (1–16). Mehrere möglich: `[1, 2, 7]` |
| `refresh_seconds` | int | `3600` | Aktualisierungsintervall |

**Bundesland-IDs:** 1=BW, 2=BY, 3=BE, 4=BB, 5=HB, 6=HH, 7=HE, 8=MV, 9=NI, 10=NW, 11=RP, 12=SL, 13=SN, 14=ST, 15=SH, 16=TH

---

### `widgets.camera`

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `preferred_device_id` | string \| null | `null` | Hardware-ID der bevorzugten Kamera |
| `preferred_device_label` | string \| null | `null` | Anzeigename der Kamera |

> Wird automatisch gesetzt, wenn im Widget eine Kamera ausgewählt wird (gespeichert in `localStorage`).

---

### `widgets.market`

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `symbols` | string[] | `["AAPL","MSFT","NVDA","BTC/USD","ETH/USD"]` | Ticker-Symbole. Aktien: `"AAPL"`, `"MSFT"`. Krypto: `"BTC/USD"`, `"ETH/USD"` |
| `refresh_seconds` | int | `900` | Aktualisierungsintervall |

> Ticker-Symbole nachschlagen: [twelvedata.com/symbol-search](https://twelvedata.com/symbol-search)

---

### `widgets.nina`

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `ars` | string | – | **Pflichtfeld.** 12-stelliger Amtlicher Regionalschlüssel des Landkreises |
| `refresh_seconds` | int | `300` | Aktualisierungsintervall |

**ARS-Code ermitteln:**
- Offizielle Liste: [nina.api.bund.dev](https://nina.api.bund.dev)
- Beispiele: Stuttgart `08111000000`, München `09162000000`, Berlin `11000000000`, Hamburg `02000000000`

> Ohne gültigen `ars`-Wert kann das NINA-Widget nicht funktionieren und wird einen Fehler anzeigen.

---

### `widgets.meme`

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `subreddit` | string | `"memes"` | Subreddit, aus dem Memes geholt werden (ohne `r/`). Beispiele: `wholesomememes`, `ProgrammerHumor`, `dankmemes` |
| `sfw_only` | bool | `true` | `true`: NSFW- und Spoiler-Memes werden serverseitig herausgefiltert |

---

## 3. Keine Konfiguration nötig

Folgende Widgets funktionieren ohne jegliche Konfigurationseinträge:

| Widget | Grund |
|--------|-------|
| ClockWidget | Rein lokale Systemzeit |
| Rotating GIF | Hardcodierte GIF-URLs |
| Question of the Day | OpenTDB ist key-frei |
| Useless Fact of the Day | uselessfacts API ist key-frei |
| Corporate Bullshit of the Hour | Corporate BS API ist key-frei |

---

## 4. Konfigurationsänderungen übernehmen

Nach Änderungen an `app_config.json` oder `.env`:

```bash
# Backend neu starten
cd Backend
uvicorn src.main:app --reload

# Frontend muss nicht neu gestartet werden –
# es liest die Config beim nächsten API-Call automatisch neu.
```
