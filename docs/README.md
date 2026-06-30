# Nimrag – Dokumentationsübersicht

Alle Dokumente liegen in thematischen Unterordnern. Diese Datei ist der einzige Einstiegspunkt.

---

## Schnellzugriff

| Was suche ich? | Wo? |
|---|---|
| Projekt starten / Setup | [project/GETTING_STARTED.md](project/GETTING_STARTED.md) |
| Repository & Scrum Board Links | [project/Links.md](project/Links.md) |
| Anforderungen (SRS) | [SRS/](SRS/) |
| Softwarearchitektur (SAD) | [architecture/SAD.md](architecture/SAD.md) |
| Qualitätsbericht (Übersicht) | [quality/Qualitaetsbericht.md](quality/Qualitaetsbericht.md) |
| Widget-Dokumentation | [doku/](doku/) |
| Präsentation (PDF) | [presentation/](presentation/) |

---

## Ordnerstruktur

### [architecture/](architecture/)
Architekturentscheidungen und technische Grundlagen.

| Datei | Inhalt |
|---|---|
| [SAD.md](architecture/SAD.md) | Software Architecture Document (RUP) |
| [Architekturentscheidungen und Entwurfsmuster – Nim.md](architecture/Architekturentscheidungen%20und%20Entwurfsmuster%20%E2%80%93%20Nim.md) | Begründungen für alle Architekturentscheidungen |
| [ASR.md](architecture/ASR.md) | Architecturally Significant Requirements |
| [Utility Tree für das Nimrag Smart Mirror Projekt.md](architecture/Utility%20Tree%20f%C3%BCr%20das%20Nimrag%20Smart%20Mirror%20Projekt.md) | Qualitätsattribute und Utility Tree |

---

### [quality/](quality/)
Alle Qualitätssicherungsmaßnahmen des Projekts.

| Datei | Inhalt |
|---|---|
| [Qualitaetsbericht.md](quality/Qualitaetsbericht.md) | Gesamtüberblick Qualität (Einstieg) |
| [Test-Report.md](quality/Test-Report.md) | Alle Backend- und Frontend-Tests (53 Dateien) |
| [Softwaremetriken.md](quality/Softwaremetriken.md) | radon, flake8, TypeScript, Coverage |
| [CICD-Setup.md](quality/CICD-Setup.md) | GitHub Actions Pipeline (6 Jobs) |
| [Refactoring-Zusammenfassung.md](quality/Refactoring-Zusammenfassung.md) | ModuleManager → 3 Composables |
| [technical-review-bericht.md](quality/technical-review-bericht.md) | Technical Review vom 26.05.2025 |

---

### [project/](project/)
Projektdokumentation, Planung und Einstieg.

| Datei | Inhalt |
|---|---|
| [GETTING_STARTED.md](project/GETTING_STARTED.md) | Setup-Anleitung inkl. aller Widget-Env-Variablen |
| [Projektretrospektive.md](project/Projektretrospektive.md) | Was gut/schlecht lief, Features Woche 18 |
| [RMMM.md](project/RMMM.md) | Risk Management Table (12 Risiken) |
| [Links.md](project/Links.md) | Repository, Scrum Board, Discussions |

---

### [diagram-docs/](diagram-docs/)
Markdown-Dokumente mit Mermaid-Diagrammen. Bild-Dateien (PNG etc.) liegen separat in [Diagramme/](Diagramme/).

| Datei | Inhalt |
|---|---|
| [6_Sequenzdiagramme_Komponentenebene.md](diagram-docs/6_Sequenzdiagramme_Komponentenebene.md) | 5 Sequenzdiagramme (Wetter, Gesten, LED, MQTT, WebSocket) |
| [8_Komponenten_und_Paketdiagramme.md](diagram-docs/8_Komponenten_und_Paketdiagramme.md) | Komponenten- und Paketdiagramme |
| [UML_Klassendiagramme.md](diagram-docs/UML_Klassendiagramme.md) | Klassendiagramme |
| [Zusaetzliche_Architektur_Diagramme.md](diagram-docs/Zusaetzliche_Architektur_Diagramme.md) | Deployment, DFD, ER, State Machines, User Journey |
| [Mermaid_Diagramme_Index.md](diagram-docs/Mermaid_Diagramme_Index.md) | Master-Index aller 16 Diagramme |
| [README_Diagramme.md](diagram-docs/README_Diagramme.md) | Cheat Sheet & Quick Reference |
| [DELIVERABLES_Diagramme.md](diagram-docs/DELIVERABLES_Diagramme.md) | Deliverables-Übersicht |
| [00_START_HERE.md](diagram-docs/00_START_HERE.md) | Einstieg in die Diagramm-Dokumentation |

### [Diagramme/](Diagramme/)
Bild-Dateien (PNG, SVG) die von den Markdown-Docs referenziert werden.

---

### [SRS/](SRS/)
Software Requirements Specification (RUP).

Enthält das vollständige SRS-Dokument (`SRS Nimrag.md`, v1.2) und zugehörige Anhänge.

---

### [UCRS/](UCRS/)
Use Case Requirement Specifications.

---

### [doku/](doku/)
Widget-Dokumentation und technische Referenz.

| Datei / Ordner | Inhalt |
|---|---|
| [widgets/](doku/widgets/) | Dokumentation aller Widgets (Wetter, Uhr, News, Markt, …) |
| [market-widget.md](doku/market-widget.md) | Markt-Widget Spezifikation |
| [configdocu.md](doku/configdocu.md) | Konfigurationsdokumentation |

---

### [Event-driven architecture/](Event-driven%20architecture/)
Dokumentation zur Event-Driven Architecture des Systems (EDA, MQTT, WebSocket-Flows).

---

### [presentation/](presentation/)
Präsentationsunterlagen.

| Datei | Inhalt |
|---|---|
| `Nimrag Smart Mirror · Projektpräsentation (1).pdf` | Projektpräsentation (Folien) |

---

### [License/](License/)
Lizenzinformationen des Projekts.
