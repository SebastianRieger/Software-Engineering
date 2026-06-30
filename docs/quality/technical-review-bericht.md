# Technical Review Bericht

**Datum:** 26.05.2025 | **Zeit:** 14:00 bis 15:30 Uhr | **Ort:** Discord-Sprachanruf

---

## Teilnehmer

| Name | Rolle |
|---|---|
| Sebastian | Moderator |
| Jannik | Protokollant |
| Louis | Reviewer |
| Justin | Externer Reviewer (Betception) |

---

## Ziel und Fokus

Reviewed wurde das **Frontend-Widget-Management-System** (`useWidgetManager.ts`, `widgetRegistry.ts`, `GridBoard.vue`, `useWidgetManager.test.ts`).

**Begründung der Auswahl:** Diese vier Dateien bilden ein vollständiges Feature, von der Datenhaltung über die Registry bis zur UI. Das Modul ist das Kernelement des Dashboards, nutzt moderne Vue-3-Patterns und hat vorhandene Testabdeckung, womit es gut reviewbar und lehrreich für das gesamte Team ist.

---

## Komponenten & Kriterien

| Komponente | Kriterien |
|---|---|
| `useWidgetManager.ts` | Codequalität, Wartbarkeit, Korrektheit, Typsicherheit |
| `widgetRegistry.ts` | Codequalität, Wartbarkeit |
| `GridBoard.vue` | Codequalität, Performance |
| `useWidgetManager.test.ts` | Testqualität, Abdeckung |

---

## Methodik

**Strukturierter Walkthrough:** Der Moderator führte die Gruppe Datei für Datei durch den Code (Registry, Composable, Tests, UI). Reviewer äußerten Anmerkungen live, der Protokollant hielt diese fest. Abschließend wurden die Punkte gemeinsam priorisiert.

---

## Ergebnisse

### Stärken

- **Singleton-Pattern**: Modul-Level-State in `useWidgetManager` korrekt umgesetzt, sodass alle Aufrufer denselben Zustand teilen ohne Pinia/Vuex.
- **`markRaw()`**: Komponenten-Objekte werden korrekt aus Vues Reaktivitätssystem ausgeschlossen, was Overhead und potenzielle Proxy-Fehler verhindert.
- **Bidirektionale Registry**: `import.meta.glob` registriert neue Widgets automatisch beim Ablegen einer `.vue`-Datei; keine manuelle Konfiguration nötig.
- **Graceful Degradation**: Beide localStorage-Operationen sind in `try/catch` gekapselt, sodass kein Absturz bei privaten Fenstern oder vollem Quota auftritt.
- **Testabdeckung**: Alle Edge Cases von `moveWidgets` (leer/belegt, beide leer, Swap) sind explizit getestet.
- **Event-Kommunikation**: `GridBoard.vue` mutiert den Zustand nicht direkt, sondern emittiert typisierte Events nach oben.

### Mängel & Maßnahmen

**1. Magische Zahl `16` für Zellenanzahl in `GridBoard.vue` Zeile 21 | Priorität: Mittel**

Die Anzahl der Grid-Zellen ist als Literal `16` hardcodiert. Wenn das Layout geändert wird (z. B. 5x5), muss dieser Wert manuell gefunden und angepasst werden, was fehleranfällig ist, da der Zusammenhang mit den CSS-Grid-Definitionen nicht offensichtlich ist.
**Maßnahme:** Konstante `const GRID_CELL_COUNT = 16` auf Modulebene extrahieren, die sowohl im `onMounted`-Loop als auch in den Style-Definitionen referenziert wird.

**2. Mix aus Tailwind-Klassen und Inline-Styles in `GridBoard.vue` Zeilen 91 bis 97 | Priorität: Niedrig**

Das Grid-Container-Element verwendet gleichzeitig Tailwind-Utility-Klassen (`bg-neutral-900`, `p-4`) und ein `style`-Attribut für Layout-Properties (`grid-template-columns`, `width`, `height`). Dieser Mix erschwert das Lesen und Anpassen des Layouts, da man an zwei Stellen suchen muss.
**Maßnahme:** Layout-Properties in den `<style scoped>`-Block auslagern, sodass alle Styles an einer Stelle stehen.

**3. Stille Fehler in `saveToStorage` ohne Logging in `useWidgetManager.ts` Zeile 46 | Priorität: Niedrig**

Der `catch`-Block schluckt alle Fehler kommentarlos. Im Entwicklungsbetrieb ist das problematisch: schlägt ein localStorage-Schreibvorgang fehl (z. B. wegen Quota-Überschreitung), gibt es keinerlei Hinweis und der Zustandsverlust nach einem Reload ist schwer zu debuggen.
**Maßnahme:** Im Dev-Modus eine Warnung ausgeben: `if (import.meta.env.DEV) console.warn('[useWidgetManager] localStorage write failed:', e)`

**4. `widgetMap` direkt exponiert in `useWidgetManager.ts` Zeile 84 | Priorität: Niedrig**

Das `widgetMap`-Ref wird direkt aus dem Composable zurückgegeben, d. h. jede Komponente kann `widgetMap.value = {}` schreiben und dabei den `watch`-basierten Persistenz-Mechanismus umgehen. Das untergräbt die Kapselung des Composable.
**Maßnahme:** `readonly(widgetMap)` zurückgeben, sodass Mutationen nur über die vorgesehenen Funktionen (`insertWidgetIntoCell`, `moveWidgets`, `clearCell`) möglich sind.

### Gelernte Best Practices

- Modul-Level-Composables als leichtgewichtige Alternative zu Pinia für globalen State
- `import.meta.glob` für automatische Komponentenregistrierung ohne manuelle Registry
- Edge-Case-Tests bei State-Mutationen sind wichtiger als reine Happypath-Tests
