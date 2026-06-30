# Projektretrospektive – Nimrag Smart Mirror

**Zeitraum:** Woche 18 | **Format:** Team-Retro (alle Mitglieder)

---

## Zusammenfassung

Am Ende von Sprint 5 / Woche 18 hielt das Nimrag-Team eine strukturierte Retrospektive ab. Die folgende Zusammenfassung fasst die wichtigsten Punkte aus der gemeinsamen Runde zusammen.

---

## Was gut lief

| Thema | Beschreibung |
|---|---|
| **Teamstruktur** | Aufgabenverteilung war klar und funktionierte gut über die gesamte Projektlaufzeit |
| **Projektvision** | Einheitliches Verständnis der Ziele im Team – kein nennenswerter Richtungsstreit |
| **Automatisierung** | `npm run setup` vereinfachte das Onboarding und die lokale Entwicklung erheblich |
| **Plattformkompatibilität** | Linux- und Windows-Support funktionierte ohne separate Konfigurationen |

---

## Was schlecht lief

| Thema | Beschreibung |
|---|---|
| **Motivation** | Phasenweises Arbeiten führte zu unregelmäßiger Beteiligung einzelner Mitglieder |
| **Teamkonstellation** | Gegen Ende wurde die Zusammenarbeit schwieriger (Verfügbarkeiten, Prioritäten) |
| **Code-Planung** | Zu Beginn fehlte eine ausreichende Vorplanung, was späteres Refactoring nötig machte |
| **Branch-Regeln** | Branch-Protection-Regeln wurden erst nachträglich eingeführt; frühere Einführung hätte Konflikte verhindert |

---

## Was wir uns vornehmen

- **Branch-Regeln von Anfang an festlegen** – Protection Rules und Review-Pflicht direkt bei Projektstart konfigurieren
- **Kleinere Pull Requests und Tasks** – Große Features in kleinere, reviewbare Einheiten aufteilen
- **Meetings kürzer und strukturierter halten** – Klare Agenda, Timeboxing, Ergebnisse direkt festhalten
- **Offene Stories aus dem letzten Sprint priorisieren** – Kein Carry-over-Aufbau durch konsequente Sprint-Abschlüsse
- **Regelmäßige Syncs einplanen** – Kurze, wöchentliche Check-ins statt langer, seltener Meetings

---

## Ergebnisse Woche 18

In der letzten Projektwoche wurden noch folgende Features fertiggestellt und eingebaut:

| Feature | Beschreibung |
|---|---|
| **LocalStorage-Persistenz** | Widget-Layout wird browserübergreifend gespeichert und bei Reload wiederhergestellt |
| **Pi Image** | Raspberry Pi Image in der finalen Validierungs- und Testphase abgeschlossen |
| **Neue Tests** | Zusätzliche Frontend- und Backend-Tests für neu hinzugekommene Features |
| **Clock-Widget Redesign** | Nutzer können jetzt zwischen analoger und digitaler Uhr wechseln |
| **Adaptiver Widget-Shop** | Shop-Layout passt sich dynamisch an die Bildschirmgröße des Nutzers an |

---

## Fazit

Das Projekt hat sein Kernziel erreicht: ein funktionaler Smart Mirror mit modularem Widget-System, Gestensteuerung, Echtzeit-Backend und Raspberry Pi-Integration. Die Retrospektive zeigt, dass die technische Basis solide ist, während organisatorische Prozesse (Planung, Branch-Workflows, Sprint-Disziplin) in einem Folgeprojekt früher etabliert werden sollten.
