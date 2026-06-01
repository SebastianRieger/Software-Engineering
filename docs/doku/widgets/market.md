# Market

**Dateiname:** `Market.vue`

## Was es macht

Zeigt Echtzeit-Kurse für Aktien und Kryptowährungen an, geliefert von der **Twelve Data API** über den Backend-Proxy `/api/v1/market`. Zeigt Kurs, prozentuale Veränderung und Trendpfeil. Aktualisiert sich automatisch.

## Größenverhalten

| Größe | Darstellung |
|-------|-------------|
| Klein (1×1) | 2 Symbole |
| Mittel (2×1) | 4 Symbole |
| Groß (2×2) | Alle konfigurierten Symbole |

## Konfiguration

### `.env` (Backend, Pflicht)

```env
TWELVE_DATA_API_KEY=dein_api_key_hier
```

> **Woher?** Kostenloser Key auf [twelvedata.com](https://twelvedata.com) (Free-Tier: 800 Requests/Tag).

### `config/app_config.json` (optional)

```json
{
  "widgets": {
    "market": {
      "symbols": ["AAPL", "MSFT", "NVDA", "BTC/USD", "ETH/USD"],
      "refresh_seconds": 900
    }
  }
}
```

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `symbols` | string[] | `["AAPL","MSFT","NVDA","BTC/USD","ETH/USD"]` | Ticker-Symbole. Aktien: `"AAPL"`. Krypto: `"BTC/USD"` |
| `refresh_seconds` | int | `900` | Aktualisierungsintervall in Sekunden |

## Aktivieren

1. `TWELVE_DATA_API_KEY` in `.env` setzen.
2. Gewünschte Symbole in `app_config.json` eintragen.
3. Shop öffnen (`E`) → **Market** in eine Zelle ziehen.
