# Market Widget

Zeigt Echtzeit-Kurse für Aktien und Kryptowährungen via [Twelve Data](https://twelvedata.com).

## Voraussetzungen

- Twelve Data Account (Free Tier: 800 Credits/Tag, 1 Credit pro Symbol pro Abruf)
- API-Key unter: https://twelvedata.com/account/api-key

---

## Setup

### 1. API-Key eintragen

Datei: `Backend/.env`

```
TWELVE_DATA_API_KEY=dein_key_hier
```

Die Datei existiert bereits nach dem ersten Setup. Einfach den Wert ersetzen.

### 2. Symbole konfigurieren

Datei: `Backend/config/app_config.json`

```json
"market": {
  "symbols": ["BTC/USD", "NVDA", "AAPL", "MSFT", "ETH/USD"],
  "refresh_seconds": 900
}
```

| Feld | Beschreibung |
|---|---|
| `symbols` | Liste der Symbole in gewünschter Anzeigereihenfolge |
| `refresh_seconds` | Aktualisierungsintervall in Sekunden (min. 60) |

**Symbolformat:**
- Aktien: Ticker-Symbol — `AAPL`, `NVDA`, `MSFT`
- Krypto: `BASIS/QUOTE` — `BTC/USD`, `ETH/USD`

Verfügbare Symbole: https://twelvedata.com/stocks und https://twelvedata.com/cryptocurrencies

### 3. Backend neu starten

Nach Änderungen an `.env` oder `app_config.json` den Backend-Prozess neu starten:

```
node setup.js --dev-backend
```

---

## Layouts

Das Widget passt sich der Zellgröße im Grid an:

| Größe | Zellen | Inhalt |
|---|---|---|
| **Small** (1×1) | 2 Einträge | Symbol · Preis · % |
| **Medium** (2×1) | 4 Einträge | Badge · Name · Preis · % |
| **Large** (2×2) | alle | Badge · Symbol · Name · Preis · % |

---

## Caching

Abgerufene Kurse werden 900 Sekunden (15 min) in der lokalen SQLite-Datenbank gecacht. Bei API-Ausfall liefert das Widget die zuletzt bekannten Werte.

Die Reihenfolge in `symbols` gilt immer — auch wenn die Daten aus dem Cache kommen.

---

## Credit-Verbrauch (Free Tier)

Pro Abruf werden so viele Credits verbraucht wie Symbole konfiguriert sind.

Beispiel mit 5 Symbolen und `refresh_seconds: 900`:

```
(86400 / 900) × 5 = 480 Credits/Tag
```

Der Free Tier (800/Tag) reicht für bis zu **8 Symbole** bei 15-Minuten-Intervall.
