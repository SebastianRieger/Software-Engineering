---
marp: true
theme: default
paginate: true
footer: "Nimrag Smart Mirror · Software Engineering 2026"
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

  section {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    font-size: 1.05rem;
    color: #1a1a2e;
    padding: 40px 60px;
  }

  h1 { color: #1a1a2e; font-size: 2rem; font-weight: 700; margin-bottom: 0.3em; }
  h2 { color: #5b21b6; font-size: 1.5rem; font-weight: 600;
       border-bottom: 2px solid #5b21b6; padding-bottom: 6px; margin-bottom: 0.6em; }
  h3 { color: #374151; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.3em; }

  section.lead {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 60%, #24243e 100%);
    color: #f1f5f9; text-align: center; justify-content: center;
  }
  section.lead h1 { color: #c4b5fd; font-size: 2.6rem; }
  section.lead h2 { color: #e2e8f0; border: none; font-weight: 300; font-size: 1.3rem; }
  section.lead p { color: #94a3b8; }
  section.lead footer { color: #475569; }

  table { font-size: 0.8em; width: 100%; border-collapse: collapse; }
  th { background: #1a1a2e; color: #fff; padding: 8px 12px; text-align: left; }
  td { padding: 7px 12px; border-bottom: 1px solid #e2e8f0; }
  tr:nth-child(even) td { background: #f8fafc; }

  .zwei-spalten {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 32px; align-items: start;
  }
  .zwei-bilder {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 20px; align-items: center;
  }
  .drei-bilder {
    display: grid; grid-template-columns: 1fr 1fr 1fr;
    gap: 16px; align-items: center;
  }
  .zwei-bilder img, .drei-bilder img { width: 100%; border-radius: 6px; }
  .bildtitel { text-align: center; font-size: 0.75em; color: #64748b;
               margin-top: 6px; font-style: italic; }

  .highlight {
    background: #ede9fe; border-left: 4px solid #7c3aed;
    padding: 10px 16px; border-radius: 0 6px 6px 0; margin: 8px 0;
  }
  .karte {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 16px 20px;
  }
  footer { font-size: 0.7em; color: #94a3b8; }
---

<!-- _class: lead -->

# Nimrag Smart Mirror

## Intelligenter Spiegel mit berührungsloser Gestensteuerung

<br/>

Software Engineering Projekt · 2026

---

# Agenda

<div class="zwei-spalten">
<div>

**1 ·** Produktvision

<br/>

**2 ·** User Experience
- Das Widget- und Gridsystem
- Gestensteuerung

<br/>

**3 ·** Technische Umsetzung
- Systemarchitektur & Design
- Backend & Gestensubsystem
- Frontend-Architektur

</div>
<div>

**4 ·** Hardware

<br/>

**5 ·** Qualität & CI/CD

<br/>

**6 ·** Projektmanagement

<br/>

**7 ·** Ausblick & Live-Demo

</div>
</div>

---

# 1 · Produktvision — Was ist Nimrag?

<div class="zwei-spalten">
<div>

### Das Projekt

Nimrag ist ein Smart Mirror: ein halbdurchlässiger Spiegel mit dahinterliegendem Display, der Informationen als Overlay darstellt.

**Kernfunktionen:**
- Anzeige von Alltagsinformationen (Wetter, Uhrzeit, Nachrichten, Warnungen)
- Berührungslose Steuerung über Kamera-basierte Gestensteuerung
- Modulares Widget-System für flexible Inhalte

**Technischer Ansatz:**
- Eigenentwicklung: Frontend (Vue.js) + Backend (FastAPI)
- Hardware: Raspberry Pi · Kamera · Zwei-Wege-Spiegel
- Automatisierte Build- und Deployment-Pipeline

</div>
<div>

### Projektziel

Entwicklung eines funktionsfähigen Prototyps mit:

- Konfigurierbarem Widget-Grid
- Zuverlässiger berührungsloser Gestensteuerung
- Getesteter und dokumentierter Codebasis
- Deployment auf dedizierter Hardware

</div>
</div>

<!--
Einleitung: sachlich und akademisch halten — keine Werbung.
-->

---

<!-- _class: lead -->

# 2 · User Experience

## Das Widget- und Gridsystem & Gestensteuerung

---

## 2.1 · Das Widget- und Gridsystem

<div class="zwei-spalten">
<div>

### Das Grid

- Widgets frei auf dem Grid positionierbar
- Mehrere Widgets gleichzeitig sichtbar
- Widgets verschiebbar, skalierbar, löschbar
- Änderungen werden persistiert

### Verfügbare Widgets

- Wetter · Uhrzeit · Nachrichten (Tagesschau)
- NINA-Katastrophenwarnungen · Börsenkurse
- Kamera-Vorschau · Frage des Tages
- Useless Fact · Corporate Bullshit of the Hour
- Zufalls-Meme · Animiertes GIF

</div>
<div>

![](screenshots/ui_cursor.png)
<p class="bildtitel">Live-Ansicht — aktiver Cursor auf dem Widget-Grid</p>

</div>
</div>

<!--
Hier erklärt Sebastian das Grid-System im Detail.
Screenshot zeigt die reale App mit aktivem Cursor (weißer Punkt).
-->

---

<!-- _class: lead -->

# 2.2 · Gestensteuerung

## Berührungslose Bedienung für den Alltag

---

## Warum keine Maus — warum Gesten?

<div class="zwei-spalten">
<div>

**Das Problem:**

- Wandmontiert → keine Tastatur oder Maus in Reichweite
- Kontext: Badezimmer, Flur, Küche → Hygiene, nasse Hände

</div>
<div>

**Die Lösung:**

- Kamera erkennt Handbewegungen vor dem Spiegel
- Komplett **berührungslos** aus 50–80 cm Abstand
- Keine Hardware-Eingabegeräte notwendig
- Ergänzung: Sprachsteuerung *(in Entwicklung)*

</div>
</div>

<div class="highlight">

Gestensteuerung ist kein Add-on — sie ist die einzig sinnvolle Eingabemethode für einen wandmontierten Spiegel.

</div>

<!--
Warum-Folie knapp halten, 30-45 Sek.
-->

---

## Die vier Eingabemethoden

<div class="zwei-spalten">
<div>

**↔ Wischen** *(Swipe)*
Offene Handfläche horizontal wischen
→ Navigiert zum nächsten / vorherigen Widget

<br/>

**⭕ Kreis**
Kreisbewegung beschreiben, Hand am Ende öffnen
→ Bestätigt eine Aktion / öffnet Menü

</div>
<div>

**🖱 Cursor + Halten**
Zeigefinger bewegt den Cursor — 1 Sekunde auf einem Button halten
→ Löst Klick aus (Löschen, Größe ändern, Menü)

<br/>

**✊ Pinch-to-Move**
Daumen + Zeigefinger zusammen = Widget greifen
Hand bewegen = Widget folgt, Finger öffnen = ablegen
→ Drag & Drop für das Widget-Grid

</div>
</div>

<br/>

> *Frühere Ansätze wie Push-Klick-Gesten oder Zwei-Hand-Zoom wurden verworfen — Cursor-Hold löst dasselbe eleganter.*

---

## Gesten nach Kontext

<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:0.9em">
<div class="karte">

**📷 Kamera-Vorschau** *(Startbildschirm)*

Beim Start zeigt die App die Kamera-Vorschau im Vollbild.

↔ Wischen nach links — zum Widget-Grid wechseln

</div>
<div class="karte">

**🏠 Widget-Grid (Normalmodus)**

⭕ Kreis — Edit-Modus aktivieren

🖱 Cursor halten — Buttons & Menüs klicken

</div>
<div class="karte">

**✏️ Edit-Modus**

✊ Pinch — Widget greifen & verschieben

✊ Pinch auf leerem Feld — Widget-Shop öffnen

🖱 Cursor halten — Widget löschen · Größe ändern

⭕ Kreis — Edit-Modus beenden

</div>
<div class="karte">

**🛒 Widget-Shop**

↔ Wischen — Widgets durchblättern

🖱 Cursor halten — Widget auswählen & hinzufügen

</div>
</div>

<!--
Kontext-basierte Darstellung statt leerer Tabellen-Zellen.
Kreis ist ausschließlich für Edit-Modus ein/aus.
-->

---

## Gestensteuerung — Ablauf

![center w:900](diagrams/gest_ablauf.png)

<!--
Kamera → Erkennung → Cursor als Interface-Punkt → vier mögliche Aktionen → Frontend
-->

---

## Pinch-to-Move — Schritt für Schritt

<br/>

![center w:820](diagrams/pinch_move.png)

<!--
Automatische Tausch-Logik betonen: kein "kein Platz"-Fehler, sondern intelligentes Swap.
-->

---

## Pinch-to-Move — live in Aktion

<div class="zwei-bilder">
<div>

![](screenshots/clock_verschieben.png)
<p class="bildtitel">Widget wird mit Pinch gegriffen und verschoben</p>

</div>
<div>

![](screenshots/clock_getauscht.png)
<p class="bildtitel">Clock- und Wetter-Widget haben automatisch die Plätze getauscht</p>

</div>
</div>

<!--
Die zwei Screenshots zusammen zeigen den Swap-Prozess in Aktion.
Linkes Bild: Widget wird per Pinch-Geste bewegt (CLOCKWIDGET-Label sichtbar).
Rechtes Bild: Nach dem Ablegen haben beide Widgets die Plätze getauscht.
-->

---

<!-- _class: lead -->

# 3 · Technische Umsetzung

## Architektur, Design-Entscheidungen & Implementierung

---

## 3.1 · System-Architektur — Überblick

![center w:980](diagrams/architektur.png)

<!--
Web-APIs (Wetter, News etc.) werden vom Backend abgefragt, nicht direkt vom Frontend.
Raspberry Pi ist die Hardware-Plattform, die alles hostet.
-->

---

## 3.1 · Zentrale Design-Entscheidungen

<div class="zwei-spalten">
<div>

### Modularer Monolith

Alle Backend-Services laufen **in einem Prozess** — keine Microservices.

- Kein Netzwerk-Overhead zwischen Services
- Ein einziges Deployment auf dem Raspberry Pi
- Klare Layer-Grenzen trotzdem vorhanden: `API → Services → Repositories → DB`
- Richtige Wahl für 3-köpfiges Team und diesen Projekt-Scope

</div>
<div>

### Event-System via WebSocket

Ein einziger `/ws`-Endpunkt für alle Echtzeit-Events:

- Erkannte Geste → Frontend
- UI-Aktionen (Widget wechseln, greifen, ablegen)

### Frontend: Composable & Registry

Jedes Widget ist eigenständig registriert — neue Widgets lassen sich **ohne Änderung am Core-System** hinzufügen.

</div>
</div>

---

## Tech-Stack auf einen Blick

| Bereich | Technologie | Einsatz |
|---------|-------------|---------|
| Backend-Framework | FastAPI · Python 3.12 | REST-API + WebSocket |
| Hand-Tracking | MediaPipe (Google) | 21 Landmarks pro Hand |
| Datenbank | SQLite | Konfiguration, Cache, Sessions |
| Konfiguration | Pydantic BaseSettings | 150+ typsichere Parameter |
| Realtime | asyncio · WebSocket | Event-Broadcasting |
| Frontend | Vue.js · Vite · Tailwind CSS | Widget-Grid, Cursor-Overlay |
| Hardware-Plattform | Raspberry Pi | Kamera + Hosting |

---

<!-- _class: lead -->

# 3.2 · Backend

## Architektur & Gestensubsystem

---

## Backend — Schichtarchitektur

![center w:680](diagrams/backend_layers.png)

<div class="highlight">

**Datenfluss:** Kamera → Gesture-Service → Input-Orchestrator → WebSocket → Frontend

</div>

<!--
Schichten kurz von oben nach unten erklären.
Input-Orchestrator: Mapping-Layer "Gesture X → UI-Aktion Y".
-->

---

## Gestensubsystem — Aufbau & Verantwortlichkeiten

![center w:980](diagrams/gesture_subsystem.png)

**Klare Ownership:** `detection.py` klassifiziert — `runtime.py` orchestriert nur. Keine gemischten Verantwortlichkeiten.

<!--
detection.py: EINZIGER Ort, der entscheidet welche Geste es ist.
contracts.py = Single Source of Truth: jede Geste hat genau einen Contract.
-->

---

## MediaPipe Hand-Tracking — so sieht das System die Hand

<div class="drei-bilder">
<div>

![](screenshots/hand_faust.png)
<p class="bildtitel">Faust — Startpose für die Kreis-Geste</p>

</div>
<div>

![](screenshots/hand_pinch.png)
<p class="bildtitel">Pinch — Daumen + Zeigefinger zusammen</p>

</div>
<div>

![](screenshots/hand_palm.png)
<p class="bildtitel">Offene Handfläche — Startpose für Wischen</p>

</div>
</div>

<br/>

MediaPipe erkennt **21 Landmarks** pro Hand in Echtzeit — Basis für alle Gesten-Klassifikationen.

<!--
Zeigen, was das System "sieht": 21 Punkte auf der Hand.
Weiße Punkte = Palm-Landmarks, blaue Punkte = Finger-Joints.
-->

---

## 3.3 · Frontend-Architektur

<div class="zwei-spalten">
<div>

### Aufbau: Vue 3 + TypeScript

Klare Schichttrennung — jede Schicht hat eine Verantwortung:

- **Komponenten** — Darstellung (UI)
- **Composables** (`use...`) — Geschäftslogik, wiederverwendbar, testbar
- **Services** — Datenzugriff & externe APIs

**Grid & Layout:** 4×4 Grid-System · Drag & Drop · variable Widget-Größen · automatische Layout-Speicherung

</div>
<div>

### Composables — Logik aus der UI ausgelagert

Logik in eigenständigen `use...`-Dateien:
- `useWidgetManager` — Widget-Zustand & Positionen
- `useHandTracking` — Gesten-Events vom Backend
- `useModuleShop` — Widget-Bibliothek

**Vorteil:** Schlanke Komponenten · Zustände zentral verwaltet · einfacher zu testen

</div>
</div>

<!--
Folie 1: Architektur-Überblick + Composables als Kern-Prinzip.
Grid-Info kurz erwähnen, Screenshot haben das schon gezeigt.
-->

---

## 3.3 · Das Widget-System — Erweiterbarkeit by Design

<div class="zwei-spalten">
<div>

### Registry Pattern + Factory

```ts
// widgetRegistry.ts
const modules = import.meta.glob(
  '../components/widgets/*.vue',
  { eager: true }
)
```

Widgets werden **automatisch erkannt** — kein manuelles Eintragen nötig. `getWidgetComponent(name)` lädt die passende Komponente dynamisch.

Singleton-Zustand in `useWidgetManager` stellt sicher, dass alle Komponenten dasselbe Widget-Layout sehen.

</div>
<div>

### Neues Widget in 3 Schritten

```
1. Neue .vue-Datei anlegen
2. Template + Logik + Styling implementieren
3. Im Widget-Ordner speichern
```

**Fertig.** Das System erkennt und registriert das Widget automatisch — ohne Änderung am Core.

<div class="highlight">

Der Smart Mirror ist dadurch flexibel erweiterbar: jede neue Funktion ist ein eigenständiges Modul.

</div>

</div>
</div>

<!--
Folie 2: Registry + Factory zusammen, Widget-Erstellung als praktischer Payoff.
Das ist die konkrete Konsequenz aller Architektur-Entscheidungen.
-->

---

# 4 · Hardware — Image-Build-Pipeline

<br/>

![center w:1100](diagrams/hardware_pipeline.png)

<br/>

<div class="zwei-spalten">
<div>

**Vom Code zum fertigen Spiegel-Image**

Eine einzige YAML-Datei treibt den gesamten Build und erzeugt ein einzelnes `.img`-File — direkt auf SD-Karte flashbar.

**First-Boot-Setup** führt beim ersten Hochfahren aus:
- `npm install` + `pip install`
- Datenbankmigrationen
- Systemd-Services aktivieren

</div>
<div>

**Hardware-Komponenten**

- Raspberry Pi (Herzstück)
- Zwei-Wege-Spiegel + Display + Rahmen
- USB-Kamera für Gestensteuerung
- LED-Strip (TP-Link Tapo + MOSFET)

</div>
</div>

<!--
Jannik erklärt den Hardware-Aufbau und die Build-Pipeline.
Das Image läuft direkt auf dem Pi — kein manuelles Setup nötig.
-->

---

# 5 · Qualität — Tests & CI/CD

<div class="zwei-spalten">
<div>

### Automatisierte Tests

- **pytest** mit Coverage-Report (`coverage.xml`)
- Backend-Tests: Endpunkte, Services, Repositories
- Linting: **black** (Formatierung) + **flake8** (Stil & Fehler)
- Alle Tests laufen isoliert mit Test-SQLite-Datenbank

</div>
<div>

### CI/CD Pipeline (GitHub Actions)

```
Push / Pull Request
    ↓
① Lint & Format-Check
② Backend Tests + Coverage
③ Frontend Build
④ Quality Gates
    ↓ (nur main-Branch)
⑤ Deploy-Artefakt
```

</div>
</div>

<div class="highlight">

Pipeline blockiert Merges bei fehlgeschlagenen Tests oder Lint-Fehlern — Qualitätssicherung ist verpflichtend, nicht optional.

</div>

---

# 6 · Projektmanagement

<div class="zwei-spalten">
<div>

### Vorgehen

- Agile Entwicklung in Sprints
- Feature-Branches + Pull Requests
- Code Reviews vor Merges in `dev` und `main`
- `main` = stabile Version, `dev` = Integration

</div>
<div>

### Aufgabenverteilung

| Bereich | Verantwortung |
|---------|--------------|
| Backend & Gestensteuerung | Louis |
| Frontend & Widget-UI | Sebastian |
| Hardware | Jannik |
| Gemeinsam | Architektur, Reviews |

</div>
</div>

---

# 7 · Ausblick & nächste Schritte

<div class="zwei-spalten">
<div>

### Offen / In Entwicklung

- Sprachsteuerung (Deutsch) — Integration fast abgeschlossen
- Kalibrierung der Gesten per Nutzer-Profil
- Deployment-Pipeline für Raspberry Pi finalisieren
- LED-Steuerung via Smart-Home-Integration

</div>
<div>

### Mögliche Erweiterungen

- Weitere Widget-Typen (Kalender, Smart-Home)
- Nutzerprofile & Personalisierung
- Verbesserte Gestengenauigkeit via DTW-Kalibrierung
- Mobile Companion-App

</div>
</div>

<br/>

<div class="highlight">

**Jetzt zeigen wir das System live — alle Gesten in Aktion.**

</div>

---

<!-- _class: lead -->

# Live-Demo

## Nimrag in Aktion

<br/>

*Swipe · Circle · Pinch-to-Move · Cursor-Hold*

<br/>

---

<!-- _class: lead -->

# Danke für eure Aufmerksamkeit

## Fragen?

<br/>

*Nimrag Smart Mirror · Software Engineering 2026*
