# Refactoring Zusammenfassung – ModuleManager

**Branch:** `ModuleManagerRefactor`  
**Datum:** Juni 2026  
**Betroffene Datei:** `Frontend/nimrag-frontend/src/components/manager/ModuleManager.vue`

---

## Ausgangslage

`ModuleManager.vue` hatte vor dem Refactoring **172 Zeilen** mit stark gemischter Verantwortlichkeit:

- Widget-Lifecycle (Erzeugen und Aufräumen dynamisch gemounteter Vue-Apps pro Grid-Zelle)
- Keyboard-Handling (Edit-Modus-Steuerung per Tastatur)
- Shop-Verwaltungslogik (Öffnen/Schließen des Widget-Shops, Auswahl und Platzierung)

Alle drei Concerns lagen in einer einzigen Komponente, was Lesbarkeit, Testbarkeit und Wartbarkeit deutlich erschwert hat.

---

## Durchgeführte Änderungen

### Drei Composables ausgelagert

**`useWidgetManager.ts`**  
Kapselt das Erzeugen und Aufräumen dynamisch gemounteter Vue-Apps pro Grid-Zelle. Verwaltet die `widgetMap` (welches Widget in welcher Zelle sitzt), `occupiedCells` und localStorage-Persistenz. Stellt `insertWidgetIntoCell`, `moveWidgets` und `clearCell` als einzige Mutationspunkte bereit.

**`useEditMode.ts`**  
Verwaltet den Edit-Modus inklusive aller zugehörigen Keyboard-Events. Kapselt den Zustand `isEditMode` sowie das Registrieren und Entfernen der Keyboard-Listener. Außerhalb des Composable sind keine Keyboard-Bindings mehr in der Komponente nötig.

**`useModuleShop.ts`**  
Übernimmt die gesamte Shop-Verwaltungslogik: Shop öffnen/schließen, ausgewähltes Widget verfolgen, Platzierung im Grid auslösen. Die Komponente selbst muss keine Shop-internen Zustände mehr kennen.

### Ergebnis: ModuleManager.vue als reine Orchestrierungskomponente

`ModuleManager.vue` enthält nach dem Refactoring **keine Business-Logik mehr**. Die Datei beschränkt sich auf:
- Einbinden der drei Composables via `use*`
- Template-Verdrahtung (Props und Events zwischen GridBoard, CellSlot und ModuleShop)
- Keine direkten State-Mutationen

---

## Leitendes Prinzip: Single Responsibility

Jede der neuen Dateien hat genau eine klar abgegrenzte Aufgabe:

| Datei | Verantwortlichkeit |
|---|---|
| `useWidgetManager.ts` | Widget-Lifecycle und Grid-Persistenz |
| `useEditMode.ts` | Edit-Modus und Keyboard-Handling |
| `useModuleShop.ts` | Shop-Verwaltung und Widget-Auswahl |
| `ModuleManager.vue` | Orchestrierung und Template-Verdrahtung |

---

## Vorher / Nachher

| Metrik | Vorher | Nachher |
|---|---|---|
| Zeilen `ModuleManager.vue` | 172 | ~60 |
| Concerns pro Datei | 3 | 1 |
| Testbare Einheiten | 0 (alles in Komponente) | 3 Composables |
| Keyboard-Logik in Template | Ja | Nein |

---

## Auswirkungen auf Tests

Die ausgelagerten Composables sind nun isoliert testbar. Für `useModuleShop` und `useEditMode` wurden zugehörige Testdateien angelegt:

- `src/__tests__/composables/useModuleShop.test.ts`
- `src/__tests__/composables/useEditMode.test.ts`

Diese Tests können die Logik ohne ein gemountetes `ModuleManager.vue` prüfen, was schnellere und robustere Tests ermöglicht.
