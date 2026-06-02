# NinaWarningsWidget

**Dateiname:** `NinaWarningsWidget.vue`

## Was es macht

Zeigt aktuelle Bevölkerungsschutz-Warnungen des **Bundesamts für Bevölkerungsschutz und Katastrophenhilfe (BBK)** über die offizielle **NINA-API**. Warnungen werden nach Schweregrad farblich kodiert und rotieren automatisch alle 6 Sekunden. Gibt es keine Warnungen für den konfigurierten Landkreis, zeigt das Widget einen grünen „Alles in Ordnung"-Status.

## Größenverhalten

| Größe | Darstellung |
|-------|-------------|
| Klein (1×1) | Aktuellste Warnung kompakt (Headline + Schweregrad-Badge) |
| Mittel (2×1) | Warnung mit Sender-Name und Ereignistyp |
| Groß (2×2) | Ausführliche Ansicht: Headline, Ereignis, Sender, Zeitstempel |

## Konfiguration

### `config/app_config.json` (**ARS-Code Pflicht**)

```json
{
  "widgets": {
    "nina": {
      "ars": "08416000000",
      "refresh_seconds": 300
    }
  }
}
```

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `ars` | string | – | **Pflichtfeld.** Amtlicher Regionalschlüssel (ARS) des Landkreises |
| `refresh_seconds` | int | `300` | Aktualisierungsintervall in Sekunden |

> **Woher bekomme ich meinen ARS-Code?**
> Den 12-stelligen ARS findest du auf [nina.api.bund.dev](https://nina.api.bund.dev) oder über die offizielle NINA-API-Dokumentation. Beispiele:
> - Stuttgart: `08111000000`
> - München: `09162000000`
> - Berlin: `11000000000`
> - Hamburg: `02000000000`

## Aktivieren

1. ARS-Code in `app_config.json` unter `widgets.nina.ars` eintragen.
2. Shop öffnen (`E`) → **NinaWarningsWidget** in eine Zelle ziehen.
