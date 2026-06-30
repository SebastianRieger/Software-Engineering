# Risk Management Table (RMMM) – Nimrag Smart Mirror

**Version:** 1.1  
**Datum:** Juni 2026  
**Team:** Sebastian, Jannik, Jan, Louis

---

## Legende

| Spalte | Bedeutung |
|---|---|
| **W** | Wahrscheinlichkeit (1 = niedrig, 3 = hoch) |
| **A** | Auswirkung (1 = gering, 3 = kritisch) |
| **Risiko** | W × A |
| **Status** | Offen / In Bearbeitung / Gemindert / Eingetreten |

---

## Risikotabelle

| ID | Risiko | Kategorie | W | A | Risiko | Maßnahme (Mitigation) | Monitoring | Status |
|---|---|---|---|---|---|---|---|---|
| R01 | Raspberry Pi Hardware-Ausfall | Hardware | 2 | 3 | **6** | Entwicklung auf Desktop möglich; Hardware erst für finale Validierung nötig; Ersatz-Pi bereithalten | Regelmäßige Hardware-Tests auf Zielplattform | Gemindert |
| R02 | API-Key läuft ab oder wird rate-limited (OpenWeatherMap, Twelve Data) | Extern | 2 | 2 | **4** | Free-Tier Limits kennen; Backend cached Antworten (600–1800 s); Fallback auf Stale-Cache | API-Dashboard überwachen; Cache-TTL anpassen | Gemindert |
| R03 | Spotify OAuth-Token verliert Gültigkeit | Extern | 2 | 1 | **2** | Token wird persistent gespeichert; Refresh-Flow implementiert | Manuelle Token-Erneuerung via `/spotify/login` | Gemindert |
| R04 | Python-Versionskompatibilität (3.14 vs. 3.11–3.13) | Technisch | 2 | 2 | **4** | Bootstrapper akzeptiert bewusst nur 3.11–3.13; Fehler wird klar kommuniziert | SMART_MIRROR_PYTHON-Variable als Fallback | Gemindert |
| R05 | MediaPipe / OpenCV inkompatibel auf ARM (Raspberry Pi) | Technisch | 2 | 3 | **6** | Plattform-Tests als Pflicht vor Release; Fallback: Gesten deaktivierbar | Validierungs-Checkliste in `GESTURE_VALIDATION.md` | In Bearbeitung |
| R06 | Kein HTTPS → Kamera-API blockiert im Browser | Technisch | 2 | 2 | **4** | Auf `localhost` greift Ausnahme; für produktiven Einsatz selbstsigniertes Zertifikat oder lokales HTTPS nötig | Kamera-Widget zeigt nicht-blockierenden Fehler-State | Gemindert |
| R07 | Scope Creep – immer mehr Widgets / Features ohne Priorisierung | Organisatorisch | 3 | 2 | **6** | Product Backlog priorisieren; neue Features erst nach Abschluss laufender Stories; Sprint-Ziele fixieren | Scrum Board wöchentlich reviewen | In Bearbeitung |
| R08 | Teamausfall / Verfügbarkeit einzelner Mitglieder | Organisatorisch | 2 | 2 | **4** | Wissenstransfer durch Code-Reviews und Doku; kein Einzelpunkt-Wissen | Regelmäßige Syncs; Bus-Faktor durch Pair-Programming reduzieren | Gemindert |
| R09 | Branch-Merge-Konflikte durch parallele Feature-Entwicklung | Technisch | 3 | 1 | **3** | Feature-Branches kurz halten; PR-Reviews als Gate; regelmäßiges Rebase auf `dev` | CI schlägt bei Konflikten fehl | Gemindert |
| R10 | Fehlende Authentifizierung in Produktion | Sicherheit | 1 | 3 | **3** | Als bekannte Einschränkung dokumentiert; kein öffentlicher Zugang geplant | Vor öffentlichem Betrieb JWT-Schutz aktivieren | Offen |
| R11 | aubio / native Build-Deps fehlen unter Windows | Technisch | 2 | 1 | **2** | Bootstrapper überspringt aubio auf Windows bewusst; Backend startet ohne Musical-Audio | Nutzer wird informiert; optionaler Pfad | Gemindert |
| R12 | Netzwerkausfall → externe APIs nicht erreichbar | Betrieb | 2 | 2 | **4** | Alle Widgets haben Stale-Cache-Fallback; `/system/external-apis/health` zeigt Status | Health-Endpunkt überwachen; Cache-TTLs dokumentieren | Gemindert |

---

## Risikomatrix

```
Auswirkung
  3 |  R10     R01 R05 |
  2 |  R03  R09  R02 R04 R06 R08 R12  R07 |
  1 |        R11  R09 |
    +--------------------
         1       2       3   Wahrscheinlichkeit
```

**Hohe Priorität (Risiko ≥ 6):** R01, R05, R07  
**Mittlere Priorität (Risiko 3–5):** R02, R04, R06, R08, R10, R12  
**Niedrige Priorität (Risiko ≤ 2):** R03, R09, R11

---

## Änderungshistorie

| Datum | Version | Änderung | Autor |
|---|---|---|---|
| Oktober 2025 | 1.0 | Initiale Risikoerfassung | Nimrag Team |
| Juni 2026 | 1.1 | Aktualisierung nach Sprint 5: R05 auf „In Bearbeitung" gesetzt, R03/R09 gemindert | Sebastian, Jannik |
