# Teststrategie für den Smart‑Spiegel (Nimrag)
Dokumentation & Grundlage für einen Blogeintrag

## 1. Überblick
Um die Qualität unseres Smart‑Spiegel‑Projekts **Nimrag** sicherzustellen, setzen wir auf eine klar definierte Teststrategie. Diese umfasst verschiedene Testarten, moderne Testwerkzeuge und eine strikte Integration in unsere CI/CD‑Pipeline. Ziel ist es, Stabilität, Wartbarkeit und Zuverlässigkeit des Systems langfristig zu gewährleisten.

---

## 2. Eingesetzte Testarten

### **Unit Tests**
- Testen einzelne Funktionen oder Module isoliert.
- Beispiele:
  - Vue‑Komponentenlogik und Composables
  - Hilfsfunktionen im Frontend
  - API‑Dienste (Weather, LED, MQTT)
  - Authentifizierungs‑ und GPIO‑Funktionen

### **Integrationstests**
- Prüfen das Zusammenspiel mehrerer Module.
- Beispiele:
  - Frontend ↔ FastAPI‑Backend
  - LED‑Steuerung ↔ Hardware‑Abstraktionen (gpiozero)
  - Weather‑Service ↔ externe APIs
  - MQTT‑Kommunikation zwischen Komponenten

### **End‑to‑End‑Tests (E2E)**
- Simulieren echte Nutzerinteraktionen auf dem Raspberry Pi.
- Beispiele:
  - Boot‑Prozess des Smart‑Spiegels
  - Laden der Widgets (Wetter, Musik, Konfiguration)
  - Gesten‑ und Voice‑Control
  - Offline‑Modus und Fallback‑Mechanismen

### **API‑Tests**
- Stellen sicher, dass FastAPI‑Endpoints korrekt funktionieren.
- Beispiele:
  - Response‑Struktur der Weather‑ und Config‑Endpoints
  - LED‑Steuerung über API
  - Authentifizierung und Autorisierung
  - Fehlercodes und Timeout‑Handling

---

## 3. Zielwert für die Testabdeckung

Wir definieren einen Zielwert von **70–80% Testabdeckung**.

### **Warum dieser Wert?**
- Der Smart‑Spiegel ist ein **modernes IoT‑Produkt**, aber **nicht sicherheitskritisch**.
- 100% Coverage ist weder realistisch noch sinnvoll.
- 70–80% bietet ein gutes Verhältnis aus Aufwand und Nutzen.

### **Wichtiger als die Zahl: Die richtigen Bereiche**
Folgende Bereiche müssen besonders gut abgedeckt sein:

- **Vue‑Komponenten und UI‑Logik** (Frontend)
- **Netzwerk‑Funktionen** (API‑Kommunikation, MQTT)
- **Weather‑ und LED‑Services** (kritische Hardware‑Integration)
- **Fehlerbehandlung**
  - Offline‑Modus ohne Internet
  - API‑Timeouts und Fallback‑Mechanismen
  - Raspberry Pi Boot‑Fehler
- **Start‑/Boot‑Prozess des Raspberry Pi**

---

## 4. Automatische Testwerkzeuge

### **Frontend** (Vue 3 + TypeScript)
- **Vitest**
  - Schnelle Unit‑ und Integrationstests
  - Bereits in `vitest.config.ts` konfiguriert mit 80% Coverage‑Threshold
- **Vue Test Utils**
  - Realistische Komponententests für Vue 3 Single‑File Components
- **Testing Library (Vue)**
  - Fokus auf echtes User‑Verhalten statt Implementierungsdetails
- **MSW (Mock Service Worker)** *(geplant)*
  - API‑Mocks ohne echten FastAPI‑Server
  - Ideal für Offline‑ und Fehlerfall‑Tests

### **Backend** (Python + FastAPI)
- **pytest**
  - Stabil, schnell und flexibel
  - Ideal für API‑ und Logiktests
- **pytest‑asyncio**
  - Support für async/await in Tests (wichtig für FastAPI)
- **TestClient (FastAPI)**
  - Echte HTTP‑ähnliche Tests ohne Server‑Overhead
- **Mock Services**
  - Mocks für LED‑Service, Weather‑Service und MQTT (siehe `conftest.py`)

---

## 5. Verwaltung der Testfälle

Unsere Tests sind vollständig in die **CI/CD‑Pipeline** integriert.

- Jeder Commit löst automatisch alle Tests (Frontend + Backend) aus.
- Ein Merge in den `dev`‑Branch ist **nur möglich, wenn alle Tests erfolgreich sind**.
- Fehlgeschlagene Tests blockieren den Merge.
- Coverage‑Berichte werden nach jedem Testlauf generiert.
- Dadurch gelangen keine instabilen Änderungen in die Hauptentwicklungslinie.

---

## 6. Fazit

Unsere Teststrategie stellt sicher, dass **Nimrag** zuverlässig, wartbar und stabil bleibt.
Durch die Kombination aus Unit‑, Integrations‑, API‑ und E2E‑Tests, modernen Werkzeugen und einer strikten CI‑Integration schaffen wir eine solide Grundlage für ein professionelles IoT‑Produkt.
