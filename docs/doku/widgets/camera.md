# CameraWidget

**Dateiname:** `CameraWidget.vue`

## Was es macht

Zeigt den Live-Feed einer angeschlossenen Kamera direkt im Widget an. Nutzt die Browser-API (`getUserMedia`). Mehrere Kameras werden automatisch erkannt; die zuletzt gewählte wird in `localStorage` gespeichert.

## Größenverhalten

Das Widget skaliert das Kamerabild auf die volle Zellgröße (`object-fit: cover`). Es gibt keine separaten Layouts – die Kamera füllt immer den gesamten verfügbaren Platz.

## Konfiguration

Kein API-Key nötig.

### `config/app_config.json` (optional)

```json
{
  "widgets": {
    "camera": {
      "preferred_device_id": null,
      "preferred_device_label": null
    }
  }
}
```

| Feld | Typ | Standard | Beschreibung |
|------|-----|----------|--------------|
| `preferred_device_id` | string \| null | `null` | Hardware-ID der bevorzugten Kamera (aus `enumerateDevices`) |
| `preferred_device_label` | string \| null | `null` | Anzeigename der bevorzugten Kamera |

> Die `device_id` kann im Browser über `navigator.mediaDevices.enumerateDevices()` ermittelt werden. In der Regel reicht es, die Kamera einmal im Widget auszuwählen – die Auswahl wird automatisch in `localStorage` gespeichert.

## Aktivieren

Shop öffnen (`E`) → **CameraWidget** in eine Zelle ziehen. Browser fragt einmalig nach Kamera-Berechtigung.
