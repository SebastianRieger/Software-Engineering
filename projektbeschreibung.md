# Smart Mirror – Projekt „Nimrag"

## Software-Entscheidung

Das Team hat sich für eine **vollständig eigene Software-Lösung** entschieden (keine MagicMirror²-Basis), um maximale Flexibilität und eigene Architekturentscheidungen zu ermöglichen.

**Eigene Software – Umgesetzte Architektur:**
- **Frontend:** Vue 3 + TypeScript + Vite (Grid-basiertes Widget-System mit Drag & Drop)
- **Backend:** Python 3.12 + FastAPI + uvicorn (REST-API + WebSocket-Realtime-Hub)
- **Kommunikation:** Event-driven Architecture via WebSocket (`/ws`)
- **Gestensteuerung:** MediaPipe Hand Landmarker (Offline-Modell)
- **Sprachsteuerung:** Whisper-basierter Audio-Service
- **Datenbank:** SQLite via SQLAlchemy

Läuft als Webanwendung im Browser – nicht an Raspberry-Pi-Hardware gebunden und auf jeder Plattform erreichbar.

---

## Beispiel eines fertigen Smart Mirrors

![Smart Mirror Beispiel](pics/smart-mirror-example.png)

**Features des gezeigten Smart Mirrors:**
- Kalenderansicht mit anstehenden Terminen
- Aktuelle Uhrzeit und Datum
- Wetterinformationen mit mehrtägiger Vorhersage
- Mondphasen-Anzeige
- Eleganter dunkler Rahmen
- Klare, gut lesbare Benutzeroberfläche

---

## Allgemeines Layout

![Layout Übersicht](pics/Layout.png)

---

## Umgesetzte Module & Features

### Implementierte Widgets

| Widget | API-Key | Beschreibung |
|---|---|---|
| **Uhr** | Nein | Analog/Digital umschaltbar |
| **Wetter** | OpenWeatherMap | Aktuelle Bedingungen & Vorhersage |
| **News (Tagesschau)** | Nein | Nachrichten nach Ressort & Region |
| **Markt** | Twelve Data | Aktien- und Kryptokurse |
| **Spotify** | Spotify OAuth | Aktuelle Wiedergabe & Steuerung |
| **NINA-Warnungen** | Nein (ARS-Code) | Amtliche Katastrophenschutzmeldungen |
| **Kamera** | Nein | Live-Webcam-Preview |
| **Zufälliges Meme** | Nein | Zufälliges Bild aus dem Meme-Pool |
| **Nutzlose Fakten** | Nein | Täglicher Fun-Fact |
| **Frage des Tages** | Nein | Tägliche Trivia-Frage |
| **Corporate Bullshit** | Nein | Stündlich generierter Corporate-Satz |

### Steuerungsarten

- **Gestensteuerung** – MediaPipe-basierte Handerkennung (Wischen, Pinch, Push)
- **Sprachsteuerung** – Whisper-basierter Audio-Service
- **Web-Interface** – Grid-Editor mit Drag & Drop, Größenanpassung, LocalStorage-Persistenz
- **Smartphone-Konfiguration** – Einstellungen über das Web-Frontend erreichbar

### Frontend-Architektur

- Grid-basiertes Widget-System (GridBoard, ModuleManager, ModuleShop)
- Widget-Shop per `E`-Taste öffnbar
- Widgets per Drag & Drop platzierbar und in der Größe skalierbar
- Widget-Zustände und -Positionen werden per LocalStorage gespeichert

---

## Mockups

**Mockup 1 – Grundlayout:**
![Mockup 1](pics/Mockup1.jpg)

**Mockup 2 – Mit Beispielen:**
![Mockup 2](pics/Mockup2.jpg)

**Aktuelles Frontend:**

![Frontend](pics/Frontend.png)
