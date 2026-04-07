# Nimrag Smart Mirror  
## Software Architecture Document (SAD)  
Version 0.1

---

## Revision History

| Date       | Version | Description                                      | Author              |
| ---------- | ------- | ------------------------------------------------ | ------------------- |
| 01/Dec/25  | 0.1     | Initial SAD-Auszug (Kap. 3, 6, 8, 11 ausgefüllt) | Nimrag Team (TINF24B5) |

---

## Table of Contents

1. Introduction  
   1.1 Purpose  
   1.2 Scope  
   1.3 Definitions, Acronyms and Abbreviations  
   1.4 References  
   1.5 Overview  

2. Architectural Representation  

3. Architectural Goals and Constraints  

4. Use-Case View  

5. Logical View  
   5.1 Overview  
   5.2 Architecturally Significant Design Packages  
   5.3 Use-Case Realizations  

6. Process View  

7. Deployment View  

8. Implementation View  
   8.1 Overview  
   8.2 Layers  

9. Data View (optional)  

10. Size and Performance  

11. Quality  

---

## 1. Introduction

> **Template:**  
> The introduction of the Software Architecture Document should provide an overview of the entire Software Architecture Document. It should include the purpose, scope, definitions, acronyms, abbreviations, references, and overview of the Software Architecture Document.

### 1.1 Purpose

This document provides a comprehensive architectural overview of the **Nimrag Smart Mirror** system, using a number of different architectural views to depict different aspects of the system. It is intended to capture and convey the significant architectural decisions which have been made on the system.

> **Template:**  
> This section defines the purpose of the Software Architecture Document, in the overall project documentation, and briefly describes the structure of the document. The specific audiences for the document should be identified, with an indication of how they are expected to use the document.

### 1.2 Scope

> **Template:**  
> A brief description of what the Software Architecture Document applies to; what is affected or influenced by this document.

### 1.3 Definitions, Acronyms and Abbreviations

> **Template:**  
> This subsection should provide the definitions of all terms, acronyms, and abbreviations required to properly interpret the Software Architecture Document. This information may be provided by reference to the project Glossary.

### 1.4 References

> **Template:**  
> This subsection should provide a complete list of all documents referenced elsewhere in the Software Architecture Document. Each document should be identified by title, report number (if applicable), date, and publishing organization. Specify the sources from which the references can be obtained. This information may be provided by reference to an appendix or to another document.

### 1.5 Overview

> **Template:**  
> This subsection should describe what the rest of the Software Architecture Document contains and explain how the Software Architecture Document is organized.

---

## 2. Architectural Representation

> **Template:**  
> This section describes what software architecture is for the current system, and how it is represented. Of the Use-Case, Logical, Process, Deployment, and Implementation Views, it enumerates the views that are necessary, and for each view, explains what types of model elements it contains.

---

## 3. Architectural Goals and Constraints

In diesem Abschnitt sind die zentralen Architekturziele und Randbedingungen des **Nimrag Smart Mirror** zusammengefasst. Die Inhalte basieren auf den bereits erarbeiteten Architekturentscheidungen und Taktiken (u. a. *Architekturentscheidungen-und-Entwurfsmuster-Nim.md* und SRS).

### 3.1 Architekturziele (Goals)

Die Architektur des Nimrag Smart Mirror verfolgt insbesondere folgende Ziele:

1. **Entkopplung & klare Schichtenbildung**  
   - Strikte Trennung von **Frontend (Vue 3 SPA)** und **Backend (FastAPI)** über klar definierte REST- und WebSocket-Schnittstellen.  
   - Ereignisbasierte Kommunikation (Event-Driven Architecture, Pub/Sub via MQTT/WebSockets), um Services voneinander zu entkoppeln.

2. **Erweiterbarkeit (Modifiability)**  
   - Neue Widgets (z. B. Wetter-, Kalender-, Musik- oder News-Widget) sollen über ein **Plugin-/Module-Pattern** hinzugefügt werden können, ohne den bestehenden Kern massiv anzupassen.  
   - Layouts und Konfigurationen (z. B. API-Keys, Widget-Positionen) sollen über externe Konfigurationsdateien (JSON/YAML) anpassbar sein.

3. **Zuverlässigkeit & Ausfallsicherheit (Reliability)**  
   - Kritische Funktionen (Spracherkennung, Gestenerkennung, Hardware-Steuerung) laufen als getrennte Services/Prozesse, sodass ein Ausfall eines Dienstes nicht den gesamten Spiegel blockiert.  
   - Nutzung eines **Circuit Breaker** für externe APIs (z. B. Wetteranbieter), um bei Fehlern auf Cache- oder Fallback-Daten zurückzugreifen.

4. **Performance & Effizienz auf eingeschränkter Hardware**  
   - Der Spiegel läuft auf einem **Raspberry Pi** mit limitierten CPU- und RAM-Ressourcen.  
   - Durch **Lazy Loading**, Virtual DOM (Vue 3) und Caching werden nur die wirklich benötigten Komponenten gerendert und Daten so selten wie nötig abgerufen.

5. **Benutzererlebnis & Interaktivität (Usability)**  
   - Reaktive Visualisierung: Änderungen (z. B. neues Wetter, geänderte Lichtzustände) sollen zeitnah und ohne Reload sichtbar sein.  
   - Unterstützung verschiedener Eingabemethoden (Sprache, Geste, ggf. Touch) via **Strategy Pattern**.

### 3.2 Architekturbestimmende Entscheidungen (Architectural Drivers)

Aus den oben genannten Zielen ergeben sich folgende wesentliche Architekturentscheidungen:

- **Event-Driven Architecture / Pub-Sub**  
  - Nutzung von MQTT und WebSockets, um Zustandsänderungen zu propagieren, ohne dass Komponenten sich direkt kennen müssen.

- **Repository Pattern für Datenzugriff**  
  - Zentraler Zugriff auf externe APIs (Wetter, Kalender, etc.) und lokale Persistenz (SQLite) über Repository-Interfaces.

- **Circuit Breaker und Caching**  
  - Schutz vor langsamen oder fehlerhaften externen Diensten, insbesondere im Hinblick auf Nutzererlebnis und Verfügbarkeit.

- **Asynchrone Verarbeitung (Concurrency)**  
  - Parallele Ausführung von Sprach-/Gestenerkennung und Backend-Logik, damit das UI nicht blockiert.

### 3.3 Randbedingungen und Constraints

Wesentliche Randbedingungen, die die Architektur beeinflussen:

- **Hardware-Constraint**  
  - Raspberry Pi (ARM, begrenzter Speicher, keine dedizierte GPU für schwere KI-Modelle).  
  - Dauerbetrieb im Kiosk-Modus (Display an, geringe Latenz erforderlich).

- **Technologie-Stack**  
  - Frontend: **Vue 3**, TypeScript, Pinia.  
  - Backend: **FastAPI (Python)**, AsyncIO.  
  - Kommunikation: REST (HTTP), WebSockets, MQTT.  
  - Persistenz: SQLite (lokaler Cache), ggf. zusätzliche Key-Value-Caches.

- **Offline-Fähigkeit**  
  - Teile der Funktionalität (Zeit, Datum, grundlegende UI) müssen ohne Internet funktionieren; Wetter/Kalender müssen sinnvoll degradieren.

- **Entwicklungs- und Team-Constraints**  
  - Projekt entsteht im Rahmen einer Lehrveranstaltung (Software Engineering), daher Fokus auf nachvollziehbare Patterns und dokumentierte Architekturentscheidungen.  
  - Nutzung vorhandener Open-Source-Komponenten (z. B. Vosk für Spracherkennung).

---

## 4. Use-Case View

> **Template:**  
> This section lists use cases or scenarios from the use-case model if they represent some significant, central functionality of the final system, or if they have a large architectural coverage - they exercise many architectural elements, or if they stress or illustrate a specific, delicate point of the architecture.

---

## 5. Logical View

> **Template:**  
> This section describes the architecturally significant parts of the design model, such as its decomposition into subsystems and packages. And for each significant package, its decomposition into classes and class utilities. You should introduce architecturally significant classes and describe their responsibilities, as well as a few very important relationships, operations, and attributes.

### 5.1 Overview

> **Template:**  
> This subsection describes the overall decomposition of the design model in terms of its package hierarchy and layers.

### 5.2 Architecturally Significant Design Packages

> **Template:**  
> For each significant package, include a subsection with its name, its brief description, and a diagram with all significant classes and packages contained within the package. For each significant class in the package, include its name, brief description, and, optionally a description of some of its major responsibilities, operations and attributes.

### 5.3 Use-Case Realizations

> **Template:**  
> This section illustrates how the software actually works by giving a few selected use-case (or scenario) realizations, and explains how the various design model elements contribute to their functionality.

---

## 6. Process View

Dieser Abschnitt beschreibt, wie der Nimrag Smart Mirror in Prozesse und Threads zerlegt ist und wie diese Prozesse miteinander interagieren. Die Inhalte basieren auf den zuvor erarbeiteten Sequenzdiagrammen **„Sprachsteuerung“** und **„Wetter-Update mit Fallback“**.

### 6.1 Sprachsteuerung (Voice Command Flow)

**Ziel:** Verarbeitung eines Sprachbefehls („Spiegel, Licht an“) vom Mikrofon bis zur Ausführung der Aktion und Aktualisierung der UI.

**Beteiligte Prozesse/Komponenten:**

- **Benutzer / Mikrofon-Hardware** – erzeugt den Audio-Stream  
- **Vosk ASR Service (Python-Prozess)**  
  - Läuft als separater Service, nimmt Audio-Stream entgegen, führt Offline-Spracherkennung durch.  
- **Event Controller (im Backend)**  
  - Empfängt erkannte Befehle als Events.  
- **MQTT Broker**  
  - Verteilt Events an interessierte Hardware-/Backend-Komponenten.  
- **Hardware Controller (GPIO-Prozess)**  
  - Setzt z. B. das Licht über GPIO-Pins.  
- **WebSocket Manager & Vue-Frontend**  
  - Benachrichtigen die UI über Statusänderungen in Echtzeit.

**Ablauf (vereinfacht):**

1. Der Benutzer spricht einen Befehl in das Mikrofon.  
2. Der Mikrofon-Treiber streamt Audiodaten an den **Vosk-Service**.  
3. Vosk führt Spracherkennung durch und mappt den Text auf einen Intent (z. B. `LIGHT_ON`).  
4. Bei erkanntem Befehl sendet Vosk ein Event an den **Event Controller**.  
5. Der Event Controller publiziert das Event auf einem MQTT-Topic (`nimrag/voice/command`) und triggert ggf. eine Aktion im Hardware Controller.  
6. Der Hardware Controller schaltet das entsprechende Gerät (z. B. Licht) und publiziert den neuen Zustand (`nimrag/status/light`).  
7. Über MQTT/WebSockets wird die Statusänderung an das Frontend propagiert; die Vue-Anwendung aktualisiert das entsprechende Widget.

   **Sequenzdiagramm**
   
 <img width="4726" height="1936" alt="Sequenzdiagramm_Sprachbefehl" src="https://github.com/user-attachments/assets/ca49a041-b6b8-4dae-9994-3246fcb776cf" />

### 6.2 Wetter-Widget Aktualisierung mit Circuit Breaker

**Ziel:**  
Periodische Aktualisierung des Wetter-Widgets mit Fallback über Cache und Circuit Breaker, um externe API-Ausfälle abzufangen.

**Beteiligte Prozesse/Komponenten:**

- **Vue-Frontend (Weather Widget)**  
  - Initiiert regelmäßig Requests (z. B. alle 15 Minuten).

- **FastAPI Endpoint**  
  - Entgegennahme der HTTP-Requests vom Frontend.

- **Weather Repository (im Backend)**  
  - Kapselt Zugriff auf Cache und externe Wetter-API.

- **Lokaler Cache (SQLite/Key-Value-Store)**  
  - Speichert zuletzt erfolgreiche Wetterdaten mit Timestamp.

- **Externe Wetter-API (z. B. OpenWeatherMap)**  
  - Liefert aktuelle Wetterdaten (wenn erreichbar).

- **Circuit Breaker-Mechanismus**  
  - Verhindert wiederholte langsame/fehlerhafte Requests.

**Ablauf (vereinfacht):**

1. Das Wetter-Widget ruft periodisch `GET /api/v1/weather` auf.  
2. Der FastAPI-Endpoint delegiert an das `Weather Repository` (`getWeatherData()`).  
3. Das Repository prüft, ob der Cache noch gültig ist (z. B. Daten jünger als 10–15 Minuten).  
   - **Wenn ja:** Rückgabe der gecachten Daten.  
4. Wenn der Cache abgelaufen ist, prüft das Repository den Zustand des Circuit Breakers:

   - **Closed (Normalfall):**  
     - Anfrage an die externe Wetter-API.  
     - Bei Erfolg: Daten speichern, Cache aktualisieren, Erfolgszähler zurücksetzen.  
     - Bei Fehler/Timeout: Fehlerzähler erhöhen, Circuit Breaker ggf. öffnen, Fallback auf Cache-Daten.

   - **Open (Fehlerzustand):**  
     - Kein externer Request, sofortiger Fallback auf Cache-Daten oder Fehlerstatus.

5. Das Repository gibt ein konsolidiertes Wetter-Modell an den FastAPI-Endpoint zurück.  
6. Der Endpoint liefert eine JSON-Antwort an die Vue-Anwendung, die das Weather Widget aktualisiert.
 
## 7. Deployment View

> **Template:**  
> This section describes one or more physical network (hardware) configurations on which the software is deployed and run. It is a view of the Deployment Model. At a minimum for each configuration it should indicate the physical nodes (computers, CPUs) that execute the software, and their interconnections (bus, LAN, point-to-point, and so on.) Also include a mapping of the processes of the Process View onto the physical nodes.

---

## 8. Implementation View

Dieser Abschnitt beschreibt die Struktur des Implementierungsmodells des **Nimrag Smart Mirror**, insbesondere die Layer und Subsysteme. Basis ist die bereits erstellte Komponenten-/Layer-Architektur (Vue 3 Frontend, FastAPI Backend, Infrastruktur-Services).

### 8.1 Overview

Die Implementierung folgt einer klaren Schichtenarchitektur:

#### Presentation Layer (Client)

- **Vue 3 Single Page Application (SPA)** im Kiosk-Modus.  
- **Widget Store (Pinia)** als zentraler State-Container.  
- **WebSocket-Client** für Echtzeit-Updates von Backend-Events.

#### Application Layer (Server)

- **FastAPI Gateway**  
  - Stellt REST-API-Endpunkte zur Verfügung (z. B. `/api/v1/weather`, `/api/v1/calendar`).  
  - Verwaltet WebSocket-Verbindungen.

- **Event Bus / Controller**  
  - Nimmt Events von Sprach-/Gesten-Services entgegen, mappt sie auf Domänenaktionen.

- **WebSocket Manager**  
  - Pusht relevante Events an verbundene Frontends.

#### Domain & Infrastructure Layer

- **Voice Service (Vosk)** – Offline-Spracherkennung.  
- **Gesture Service (z. B. MediaPipe)** – Gestenerkennung (optional).  
- **Hardware Controller (GPIO)** – Ansteuerung von LEDs, Relais, Sensoren.  
- **Data Repository** – kapselt Datenzugriff auf externe APIs und lokale Persistenz (Repository Pattern).

#### Persistence & External

- **SQLite DB / lokaler Cache**  
  - Speichert Wetter-, Kalender- und Konfigurationsdaten.

- **MQTT Broker (z. B. Mosquitto)**  
  - Verteilt Nachrichten zwischen Services (Pub/Sub).

- **Externe APIs (Cloud)**  
  - Wetter, Kalender, weitere Integrationen.

**Komponenten und Layer Übersicht**

 <img width="4557" height="3422" alt="graph_Layer_ausfuhrlich" src="https://github.com/user-attachments/assets/3c92608e-1db3-4b91-9f8c-58d56344561e" />
<img width="6038" height="3387" alt="Komponenten_Graph" src="https://github.com/user-attachments/assets/02fe2f20-744a-4daa-a4a8-f4bf9858eff9" />

### 8.2 Layers

#### Presentation Layer

- Enthält die Vue-3-Komponenten, Layout-Logik und Widgets.  
- Kommuniziert ausschließlich über REST/WebSockets mit dem Backend.  
- Nutzt Pinia-Stores als zentrales State-Management.

#### Application Layer

- Implementiert die REST-API und die WebSocket-Endpunkte mit FastAPI.  
- Enthält die Request-Handler, Validierung und Mapping auf Domänenaktionen.

#### Domain & Infrastructure Layer

- Beinhaltet die eigentliche Geschäftslogik, die Repository-Klassen und die Integrationslogik zu Hardware und externen Diensten.  
- Realisiert Performance- und Verfügbarkeits-Taktiken (Caching, Circuit Breaker, Retry-Strategien etc.).

#### Persistence & External Layer

- Zuständig für Speicherung (SQLite) und Kommunikation mit 3rd-Party-Services (z. B. Wetter-API).  
- Implementiert Schnittstellen, die im Repository verwendet werden, sodass konkrete Implementierungen austauschbar sind (z. B. Mock vs. echte API).

---

## 9. Data View (optional)

> **Template:**  
> A description of the persistent data storage perspective of the system. This section is optional if there is little or no persistent data, or the translation between the Design Model and the Data Model is trivial.

---

## 10. Size and Performance

> **Template:**  
> A description of the major dimensioning characteristics of the software that impact the architecture, as well as the target performance constraints.

---

## 11. Quality

In diesem Abschnitt wird beschrieben, wie die gewählte Architektur die nicht-funktionalen Qualitätsanforderungen des **Nimrag Smart Mirror** adressiert. Die Inhalte basieren auf den zuvor ausgearbeiteten Architekturtaktiken.

### 11.1 Performance & Effizienz

**Taktik: Control Resource Demand**

- Implementierung über das **Repository Pattern**:  
  - Alle API-Requests (z. B. Wetter, Kalender) laufen über zentrale Repository-Klassen.  
  - Rate-Limiting: Externe Anfragen werden begrenzt (Zeitfenster, Max-Requests), um API-Limits nicht zu reißen.

**Taktik: Reduce Overhead**

- Das **Vue 3 Virtual DOM** rendert nur geänderte Teile des UI.  
- **Lazy Loading**: Widgets und Module werden erst nach Bedarf geladen (Code-Splitting), um initiale Ladezeit und Speicherverbrauch zu reduzieren.

**Taktik: Introduce Concurrency**

- **FastAPI + AsyncIO** ermöglichen parallele Verarbeitung von Requests und Hintergrundjobs.  
- Sprach- und Gestenerkennung können in separaten Threads/Prozessen laufen, wodurch die UI-Interaktion nicht blockiert wird.

### 11.2 Verfügbarkeit (Availability)

**Taktik: Recover from Faults**

- Verwendung des **Circuit Breaker Patterns** für externe Dienste:  
  - Bei wiederholten Fehlern/Timeouts werden externe Requests temporär unterbunden.  
  - Fallback auf gecachte Daten; das System zeigt weiterhin nutzbare Informationen an (Graceful Degradation).

**Taktik: Detect Faults**

- Health-Checks und einfache Watchdogs für Sensor-/Service-Prozesse (z. B. Voice Service, MQTT-Verbindung).  
- Logging von Fehlerzuständen, um Probleme früh zu erkennen.

### 11.3 Modifiability (Wartbarkeit & Erweiterbarkeit)

**Taktik: Reduce Coupling**

- Ereignisbasierte Kommunikation (Events, MQTT-Topics, WebSocket-Events), statt harter Abhängigkeiten zwischen Komponenten.  
- Widgets kennen nur Datenmodelle und Events, nicht die dahinter liegenden Services oder Hardware.

**Taktik: Defer Binding**

- Konfiguration (z. B. API-Keys, Widget-Layout, Aktivierung einzelner Features) liegt in externen Konfigurationsdateien (JSON/YAML).  
- Änderungen erfordern idealerweise keinen Code-Change, sondern nur Konfigurationsanpassungen.

### 11.4 Testbarkeit

**Taktik: Mocking & Dependency Injection**

- Repositories und Services werden über Schnittstellen abstrahiert, sodass sie in Tests durch Mocks ersetzt werden können (z. B. Fake-Wetterservice).  
- Durch klare Trennung von Frontend/Backend und Infrastruktur lassen sich einzelne Teile isoliert testen (Unit-Tests) sowie End-to-End-Tests über definierte APIs durchführen.
