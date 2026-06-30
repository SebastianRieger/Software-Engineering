# Getting Started – Nimrag Smart Mirror

## Voraussetzungen

- **Node.js** 16 oder neuer
- **Python 3.11–3.13** (3.12 empfohlen) inkl. Python Launcher (`py`)
- **Git**

---

## 1. Repository klonen

```bash
git clone https://github.com/SebastianRieger/Software-Engineering.git
cd Software-Engineering
```

---

## 2. Setup ausführen

```bash
node setup.js
```

Das Skript installiert die Frontend-Dependencies und legt automatisch `Backend/.venv` mit einem passenden Python-Interpreter an.

---

## 3. Backend `.env` anlegen

```bash
cp Backend/.env.example Backend/.env
```

Dann `Backend/.env` befüllen — welche Keys du brauchst hängt davon ab, welche Widgets du aktivieren willst (siehe [Widgets](#widgets)).

---

## 4. Starten

**Backend:**
```bash
npm run dev:backend
```

**Frontend (separates Terminal):**
```bash
npm run dev
```

Frontend läuft unter `http://localhost:5173`, Backend unter `http://localhost:8000`.

---

## Frontend `.env` (optional)

Standardmäßig ist keine Frontend-`.env` nötig — der Vite-Proxy leitet `/api` automatisch zum Backend durch.

Falls du das Backend auf einem anderen Host oder Port betreibst, erstelle `Frontend/nimrag-frontend/.env.local`:

```env
VITE_BACKEND_HTTP_ORIGIN=http://localhost:8000
VITE_BACKEND_WS_ORIGIN=ws://localhost:8000

# Nur setzen wenn du den WebSocket direkt ansprechen willst (unüblich):
# VITE_WS_URL=ws://localhost:8000/ws
```

---

## Widgets

### Wetter-Widget

Zeigt aktuelle Temperatur, Wetterlage und Vorhersage.

**Benötigt:** OpenWeatherMap API-Key (kostenloser Free-Tier reicht)
→ [openweathermap.org/api](https://openweathermap.org/api)

**`Backend/.env`:**
```env
WEATHER_API_KEY=dein_key_hier
```

**Standort** in `Backend/config/app_config.json`:
```json
"system": {
  "location_name": "Karlsruhe",
  "latitude": 49.0069,
  "longitude": 8.4037
}
```

Refresh-Intervall (in Sekunden):
```json
"widgets": {
  "weather": {
    "refresh_seconds": 900
  }
}
```

---

### Markt-Widget (Aktien & Crypto)

Zeigt Kurse für konfigurierte Symbole (z. B. BTC/USD, AAPL).

**Benötigt:** Twelve Data API-Key (kostenloser Free-Tier reicht)
→ [twelvedata.com/account/api-key](https://twelvedata.com/account/api-key)

**`Backend/.env`:**
```env
TWELVE_DATA_API_KEY=dein_key_hier
```

**Symbole** in `Backend/config/app_config.json`:
```json
"widgets": {
  "market": {
    "symbols": ["BTC/USD", "NVDA", "AAPL", "MSFT", "ETH/USD"],
    "refresh_seconds": 900
  }
}
```

---

### Spotify-Widget

Zeigt den aktuell spielenden Track und erlaubt Steuerung (Play/Pause/Skip).

**Benötigt:** Spotify Developer App
1. Geh zu [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) und erstelle eine App.
2. Trage als Redirect URI exakt `http://127.0.0.1:8000/api/v1/spotify/callback` ein.
3. Kopiere Client ID und Client Secret.

**`Backend/.env`:**
```env
SPOTIFY_CLIENT_ID=deine_client_id
SPOTIFY_CLIENT_SECRET=dein_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/api/v1/spotify/callback
```

**OAuth-Flow:** Nach dem Backend-Start einmalig `http://localhost:8000/api/v1/spotify/login` aufrufen und den Spotify-Login abschließen. Das Backend speichert das Token für spätere Starts.

---

### News-Widget

Zeigt Nachrichten vom Tagesschau-Feed. Kein externer API-Key nötig — das Backend proxyt Tagesschau intern.

**Konfiguration** in `Backend/config/app_config.json`:
```json
"widgets": {
  "news": {
    "ressort": null,
    "regions": [1],
    "refresh_seconds": 3600
  }
}
```

- `ressort`: `null` für alle Ressorts oder z. B. `"inland"`, `"ausland"`, `"wirtschaft"`, `"sport"`.
- `regions`: Liste von Tagesschau-Regionen-IDs (`1` = Baden-Württemberg, `2` = Bayern, usw.).

---

### NINA-Warnungen-Widget

Zeigt amtliche Katastrophenschutzwarnungen für einen Landkreis. Kein API-Key nötig.

**Konfiguration** in `Backend/config/app_config.json`:
```json
"widgets": {
  "nina": {
    "ars": "082150000000",
    "refresh_seconds": 300
  }
}
```

`ars` ist der 12-stellige amtliche Regionalschlüssel deines Landkreises.
Den passenden Schlüssel findest du auf [warnung.bund.de](https://warnung.bund.de) oder in der NINA-API-Dokumentation.

---

### Kamera-Widget

Zeigt einen Live-Preview der Webcam. Läuft komplett im Browser, kein API-Key nötig.

- Erfordert `localhost` oder HTTPS (Browsersicherheit für `getUserMedia`).
- Beim ersten Aufruf fragt der Browser nach der Kameraberechtigung — einmalig erlauben.
- Falls mehrere Kameras vorhanden sind, kann in `Backend/config/app_config.json` eine bevorzugte Kamera vorkonfiguriert werden:

```json
"widgets": {
  "camera": {
    "preferred_device_id": null,
    "preferred_device_label": null
  }
}
```

Die `device_id` bekommst du aus den Browser-DevTools unter `navigator.mediaDevices.enumerateDevices()`.

---

### Weitere Widgets (kein Setup nötig)

| Widget | Beschreibung |
|---|---|
| **Uhr** | Analoge/digitale Uhr |
| **Zufälliges Meme** | Zufälliges Bild aus dem Meme-Pool |
| **Nutzlose Fakten** | Täglicher Fun-Fact |
| **Frage des Tages** | Tägliche Trivia-Frage |
| **Corporate Bullshit** | Stündlich generierter Corporate-Satz |

---

## Standort zentral setzen

Wetter und andere standortabhängige Features lesen den Standort einmalig aus `Backend/config/app_config.json`:

```json
"system": {
  "location_name": "Meine Stadt",
  "latitude": 48.7758,
  "longitude": 9.1829
}
```

---

## Troubleshooting

**Python-Version nicht gefunden (Windows):**
```powershell
py -3.12 --version
```
Falls das fehlschlägt: Python 3.12 von [python.org](https://python.org) installieren inkl. Python Launcher.

Wenn Python 3.12 installiert ist aber nicht erkannt wird:
```powershell
$env:SMART_MIRROR_PYTHON="C:\Users\<Name>\AppData\Local\Programs\Python\Python312\python.exe"
npm run setup:backend
```

**Backend startet nicht:**
```bash
npm run setup:backend -- --force
npm run dev:backend
```

**Frontend startet nicht:**
```bash
cd Frontend/nimrag-frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```
