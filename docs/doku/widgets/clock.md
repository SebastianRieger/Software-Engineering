# ClockWidget

**Dateiname:** `ClockWidget.vue`

## Was es macht

Zeigt die aktuelle Uhrzeit an. Unterstützt zwei Modi:

- **Digital** – große numerische Zeitanzeige (standard `toLocaleTimeString`)
- **Analog** – klassisches Zifferblatt via `AnalogClock`-Komponente

Der Modus lässt sich über die Taste `A` oder eine entsprechende Geste umschalten (`useClockWidgetMode`-Composable, wird global gespeichert).

## Größenverhalten

| Größe | Verhalten |
|-------|-----------|
| Klein (1×1) | Kleine Uhrzeit / kleines Zifferblatt |
| Mittel (2×1) | Mittlere Darstellung |
| Groß (2×2) | Große Uhrzeit / großes Zifferblatt |

Die Schriftgröße bzw. der Zifferblatt-Durchmesser skaliert automatisch mit der Cell-Size (`4rem` → `6rem` → `8rem`).

## Konfiguration

Keine Einträge in `app_config.json` nötig.

## Aktivieren

Shop öffnen (`E`) → **ClockWidget** in eine Zelle ziehen.
