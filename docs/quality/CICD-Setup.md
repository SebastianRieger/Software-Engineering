# CI/CD Setup – Nimrag Smart Mirror

**Workflow-Datei:** `.github/workflows/ci-cd.yml`  
**Ergänzend:** `.github/workflows/github-pages-deploy.yml`

---

## Überblick

Die CI/CD-Pipeline läuft auf GitHub Actions und wird bei jedem Push oder Pull Request auf `main` und `dev` ausgelöst. Ein manueller Trigger (`workflow_dispatch`) ist ebenfalls konfiguriert.

```
Trigger:
  push      → main, dev
  pull_request → main, dev
  workflow_dispatch (manuell)
```

Concurrent Runs auf demselben Branch werden automatisch abgebrochen (`cancel-in-progress: true`), um veraltete Läufe nicht zu blockieren.

---

## Pipeline-Übersicht

```
lint-backend ──┐
               ├──→ quality-gates ──→ deploy (nur main)
test-backend ──┤
test-frontend ─┤
               └──→ build-frontend ──┘
```

---

## Job 1 – Backend Lint & Format

**Name:** `lint-backend`  
**Runner:** `ubuntu-latest` | **Timeout:** 10 min

Prüft Code-Stil und Fehler ohne vollständige Abhängigkeitsinstallation:

| Tool | Aufgabe |
|---|---|
| `black --check` | Einheitliche Formatierung (PEP 8 kompatibel) |
| `flake8` | Style- und Fehlerpruefung, max. Zeilenlänge 120 |

Schlägt ein Lint-Job fehl, blockiert er den gesamten `quality-gates`-Job.

---

## Job 2 – Backend Tests & Coverage

**Name:** `test-backend`  
**Runner:** `ubuntu-latest` | **Timeout:** 20 min  
**Python:** 3.12

```bash
pytest tests/ -v \
  --cov=src \
  --cov-report=xml:coverage.xml \
  --cov-report=term-missing
```

- Tests laufen gegen eine SQLite In-Memory-Datenbank (`ci_test.db`)
- Coverage-Report (`coverage.xml`) wird als Artefakt hochgeladen und steht 14 Tage bereit
- Alle 16 Backend-Testdateien (Wetter, Gesten, News, Konfiguration, …) werden ausgeführt

---

## Job 3 – Frontend Tests & Coverage

**Name:** `test-frontend`  
**Runner:** `ubuntu-latest`  
**Node:** 20

```bash
cd Frontend/nimrag-frontend
npm ci
npm run test:coverage
```

- Verwendet **Vitest** als Test-Runner
- Coverage-Report landet unter `coverage/` und wird als Artefakt hochgeladen (14 Tage)
- Alle 37 Frontend-Testdateien (Composables, Components, Services) werden ausgeführt

---

## Job 4 – Frontend Build

**Name:** `build-frontend`  
**Abhängigkeit:** `test-frontend` muss erfolgreich sein

```bash
cd Frontend/nimrag-frontend
npm ci
npm run build   # tsc + vite
```

- TypeScript-Kompilierung und Vite-Build in einem Schritt
- Das fertige `dist/`-Verzeichnis wird als Artefakt `frontend-dist` hochgeladen (30 Tage)

---

## Job 5 – Quality Gates

**Name:** `quality-gates`  
**Abhängigkeiten:** `lint-backend`, `test-backend`, `test-frontend`

```bash
radon cc Backend/src -a -nb --min B   # Cyclomatic Complexity ≤ B (durchschnittlich)
radon mi Backend/src -nb              # Maintainability Index
```

- **Cyclomatic Complexity:** Warnung ab Durchschnitt > B (≙ mäßig komplex)
- **Maintainability Index:** Überprüfung auf Modul-Ebene
- SonarCloud-Integration ist vorbereitet (auskommentiert), kann durch Hinterlegen eines `SONAR_TOKEN`-Secrets aktiviert werden

---

## Job 6 – Deploy

**Name:** `deploy`  
**Abhängigkeiten:** alle vorherigen Jobs  
**Bedingung:** Nur bei `push` auf `main`

1. Frontend-Dist-Artefakt herunterladen
2. Release-Tarball erzeugen: `nimrag-frontend-<git-sha>.tar.gz`
3. Bundle + Coverage-Report als Release-Artefakt hochladen (90 Tage)

Ein SSH-Deployment auf den Raspberry Pi (via `appleboy/ssh-action`) ist vorbereitet und auskommentiert. Benötigte Secrets: `SSH_PRIVATE_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`.

---

## Verwendete Umgebungsvariablen (CI)

| Variable | Wert |
|---|---|
| `PYTHON_VERSION` | `3.12` |
| `NODE_VERSION` | `20` |
| `DATABASE_URL` | `sqlite:///./ci_test.db` |
| `SECRET_KEY` | `ci-test-secret-key` |

Produktions-Secrets (API-Keys, SSH) werden als GitHub Secrets hinterlegt und nicht im Code gespeichert.

---

## Lokale Qualitätsprüfung

Das Repository enthält zusätzlich ein `npm run quality`-Skript für den lokalen Einsatz:

```bash
npm run quality            # alles
npm run quality:backend    # nur Backend (Lint + Tests + Radon)
npm run quality:frontend   # nur Frontend (Tests + Build)
npm run quality:duplication
npm run quality:aggregate
```

Artefakte landen unter `reports/quality/`.
