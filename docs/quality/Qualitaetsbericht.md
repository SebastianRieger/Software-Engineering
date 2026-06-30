# Qualitätsbericht – Nimrag Smart Mirror

**Version:** 1.0  
**Datum:** Juni 2026  
**Team:** Sebastian, Jannik, Jan, Louis

---

## 1. Überblick

Dieser Qualitätsbericht fasst alle qualitätssichernden Maßnahmen des Projekts Nimrag Smart Mirror zusammen. Er referenziert die detaillierten Einzeldokumente und gibt einen Gesamtüberblick über den Qualitätsstand am Ende des Projekts.

---

## 2. Testabdeckung

Das Projekt verfügt über eine umfangreiche automatisierte Testbasis.

| Bereich | Testdateien | Werkzeug |
|---|---|---|
| Backend (Python) | 16 | pytest + pytest-cov |
| Frontend (TypeScript/Vue) | 37 | Vitest |

### Backend

Getestet werden: Wetter-Endpunkte und Cache, Tagesschau-Proxy, Konfigurationsendpunkte, externer API-Healthcheck, Gesten-Session-Management, Gesten-Klassifikation und Sequenz-Analyse, LED-Service, Kalibrierung, Voice- und Audio-Service.

### Frontend

Getestet werden: alle 14 ausgelagerten Composables, 10 Widget- und Manager-Komponenten sowie 13 Service-Module.

**Vollständige Details:** [Test-Report.md](./Test-Report.md)

---

## 3. CI/CD-Pipeline

Die gesamte Qualitätsprüfung ist in GitHub Actions automatisiert. Die Pipeline besteht aus 6 Jobs:

1. **Backend Lint** – black + flake8
2. **Backend Tests** – pytest mit Coverage
3. **Frontend Tests** – Vitest mit Coverage
4. **Frontend Build** – TypeScript + Vite
5. **Quality Gates** – radon CC und MI
6. **Deploy** – Release-Artefakt (nur auf `main`)

Jeder Pull Request auf `main` oder `dev` muss alle Jobs erfolgreich durchlaufen.

**Vollständige Details:** [CICD-Setup.md](./CICD-Setup.md)

---

## 4. Softwaremetriken

| Metrik | Werkzeug | CI-Gate |
|---|---|---|
| Cyclomatic Complexity | radon cc | Durchschnitt ≤ B |
| Maintainability Index | radon mi | Kein Modul unter Schwelle |
| Formatierung Backend | black | Kein unformatierter Code |
| Stil-Check Backend | flake8 | Keine ungenutzten Imports, keine langen Zeilen (>120) |
| TypeScript-Korrektheit | tsc | Build muss fehlerfrei kompilieren |

**Vollständige Details:** [Softwaremetriken.md](./Softwaremetriken.md)

---

## 5. Refactoring

Im Laufe des Projekts wurde `ModuleManager.vue` nach Clean-Code-Prinzipien überarbeitet. Die Datei war mit 172 Zeilen und drei gemischten Verantwortlichkeiten schwer lesbar und nicht einzeln testbar.

**Ergebnis:** Drei eigenständige Composables (`useWidgetManager.ts`, `useEditMode.ts`, `useModuleShop.ts`) mit je einer klar abgegrenzten Aufgabe. `ModuleManager.vue` selbst ist nun eine reine Orchestrierungskomponente.

**Vollständige Details:** [Refactoring-Zusammenfassung.md](./Refactoring-Zusammenfassung.md)

---

## 6. Technical Review

Am 26.05.2025 fand ein strukturierter Technical Review des Frontend-Widget-Management-Systems statt. Reviewed wurden `useWidgetManager.ts`, `widgetRegistry.ts`, `GridBoard.vue` und `useWidgetManager.test.ts`.

**Stärken:** Singleton-Pattern korrekt umgesetzt, `markRaw()` verhindert Proxy-Overhead, `import.meta.glob` für automatische Registry, robuste localStorage-Fehlerbehandlung, vollständige Edge-Case-Tests.

**Festgestellte Mängel (alle mittlere/niedrige Priorität):**
- Magische Zahl `16` für Zellenanzahl → als Konstante extrahieren
- Mix aus Tailwind und Inline-Styles → in `<style scoped>` auslagern
- Stille `catch`-Blöcke → Dev-Logging ergänzen
- `widgetMap` direkt exponiert → `readonly()` zurückgeben

**Vollständige Details:** [technical-review-bericht.md](./technical-review-bericht.md)

---

## 7. Bekannte Qualitätslücken

| Bereich | Lücke | Bewertung |
|---|---|---|
| Kamera-Tests | `getUserMedia` nicht in JSDOM testbar | Akzeptiert – nur E2E lösbar |
| GPIO/LED | Nur gemockt in CI | Akzeptiert – Hardware-abhängig |
| Spotify OAuth | OAuth-Flow nicht automatisiert | Akzeptiert – erfordert externe Sandbox |
| SonarCloud | Vorbereitet aber noch nicht aktiviert | Offen |
| Authentifizierung | Kein JWT-Schutz in Produktion aktiv | Bekannte Einschränkung |

---

## 8. Fazit

Die Codequalität des Projekts ist für einen Hochschul-Prototyp auf einem hohen Niveau. Die CI/CD-Pipeline stellt sicher, dass kein ungeprüfter oder unformatierter Code auf `main` landet. Die Testbasis deckt die wichtigsten Pfade sowohl im Backend als auch im Frontend ab. Das Refactoring des ModuleManagers verbesserte die Wartbarkeit des zentralen Frontend-Kerns deutlich.
