# Softwaremetriken – Nimrag Smart Mirror

**Referenz:** [GitHub Discussions #35](https://github.com/SebastianRieger/Software-Engineering/discussions/35)  
**Messzeitpunkt:** Sprint 5 / Woche 18  
**Werkzeuge:** radon (Backend), Vitest Coverage (Frontend), flake8

---

## Backend-Metriken

### Cyclomatic Complexity (radon cc)

Gemessen über `Backend/src` mit `radon cc -a -nb --min B`.

| Bewertung | Bedeutung |
|---|---|
| A | Einfach – kein nennenswertes Risiko |
| B | Mäßig komplex – gut wartbar |
| C | Leicht komplex – gelegentliche Überarbeitung sinnvoll |
| D–F | Hoch komplex – Refactoring empfohlen |

**CI-Gate:** Durchschnitt darf B nicht überschreiten.

Besonders komplexe Module:
- `src/services/gesture/` – Gesten-Klassifikation und Sequenz-Matcher sind inhärent komplex (viele Zweige für Gesten-Kandidaten, Confidence-Bewertung, Pose-Validierung)
- `src/services/weather.py` – Cache-Logik + Geocoding + Fallback-Pfade
- `src/api/api_v1/endpoints/` – Endpunkte selbst sind einfach; Komplexität liegt in Services

### Maintainability Index (radon mi)

Gemessen über `Backend/src` mit `radon mi -nb`.

- Scores zwischen 0 (nicht wartbar) und 100 (sehr gut wartbar)
- CI prüft, dass kein Modul unter den MI-Schwellwert fällt

### Linting (flake8)

- Konfiguration: `--max-line-length=120`, `--extend-ignore=E203,W503`
- Formattierungs-Gate: `black --check` sorgt für konsistenten Stil vor flake8

### Testabdeckung Backend

- Coverage-Report als XML aus `pytest --cov=src --cov-report=xml`
- Abgedeckte Module: API-Endpunkte, Services (Wetter, News, Konfiguration, Gesten, Interaktionen)
- Nicht abgedeckt (bewusst): GPIO-Hardware-Pfade, Spotify-OAuth-Flow, MediaPipe-Kamera-Input

---

## Frontend-Metriken

### Testabdeckung (Vitest Coverage)

Gemessen über `npm run test:coverage` in `Frontend/nimrag-frontend`.

Abgedeckte Bereiche:
- Composables: alle 14 ausgelagerten `use*.ts`-Dateien haben eigene Tests
- Services: alle 13 Service-Module sind getestet
- Komponenten: 10 Widget- und Manager-Komponenten

### TypeScript-Kompilierung

`npm run build` beinhaltet einen `tsc`-Schritt. Ein Build-Fehler bei TypeScript-Fehlern bricht die Pipeline ab. Das stellt sicher, dass keine ungetypten Zugriffe in Produktion gelangen.

### Dateigrößen (nach Vite-Build)

Vite bündelt und minimiert alle Assets. Das fertige `dist/`-Verzeichnis wird als CI-Artefakt gespeichert. Einzelne Chunk-Größen werden von Vite in der Build-Ausgabe gemeldet; Warnungen erscheinen ab 500 kB pro Chunk.

---

## Codequalität-Trends

| Maßnahme | Wirkung |
|---|---|
| ModuleManager-Refactoring (Branch `ModuleManagerRefactor`) | Komplexität in `ModuleManager.vue` von 172 auf ~60 Zeilen reduziert; drei eigenständige Composables mit je einer Verantwortlichkeit |
| `readonly(widgetMap)` im Composable | Verhindert externe State-Mutationen; verbessert Kapselung |
| `import.meta.glob` für Widget-Registry | Kein manuelles Registrieren neuer Widgets nötig; Fehlerquelle entfernt |
| localStorage-Try/Catch mit Dev-Logging | Stille Fehler werden im Dev-Modus sichtbar gemacht |

---

## Quality-Lauf lokal ausführen

```bash
# Vollständig
npm run quality

# Einzelne Teilbereiche
npm run quality:backend
npm run quality:frontend
npm run quality:duplication
npm run quality:aggregate
```

Berichte landen unter `reports/quality/`.
