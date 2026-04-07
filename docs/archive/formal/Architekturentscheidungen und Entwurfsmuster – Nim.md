# Architekturentscheidungen und Entwurfsmuster – Nimrag Smart Mirror

## Performance-Taktiken \& deren Umsetzung

**Control Resource Demand** nutzt das **Repository Pattern** für zentralen Datenzugriff – APIs, Cache und Fallback-Daten werden durch eine Schicht verwaltet. API-Requests werden automatisch begrenzt; bei Überschreitung erfolgt Fallback. In einer event-getriebenen Architektur werden Rate-Limiting-Events emittiert, die Datenquellen drosseln.

**Reduce Overhead** durch Vue 3 Virtual DOM und Lazy Loading – nur aktive Widgets werden gerendert. **Bound Execution Times** implementiert der **Circuit Breaker Pattern**: Bei API-Timeouts (5s Standard) werden Anfragen blockiert und gecachte Daten genutzt. Ein Watchdog überwacht Sprach-/Gestenerkennung mit konfigurierbaren Timeouts.

**Introduce Concurrency** nutzt FastAPI mit AsyncIO. Sprach- und Gestenerkennung laufen parallel; WebSockets ermöglichen Echtzeit-Updates ohne Polling. Events werden asynchron zwischen Services propagiert.

**Maintain Multiple Copies of Data:** Der **Caching-Strategy Pattern** speichert Wetter-, Kalender- und Konfigurationsdaten lokal in SQLite als Fallback bei Netzwerkausfällen.

## Verfügbarkeits- und Fehlerbehandlungs-Taktiken

**Detect Faults** durch Health-Checks und Heartbeats. Das **Observer Pattern** benachrichtigt die UI sofort bei Statusänderungen – ideal für das Pub/Sub-Modell event-getriebener Systeme.

**Recover from Faults** implementiert Retry mit Exponential Backoff und Graceful Degradation. Das **Strategy Pattern** ermöglicht alternative Interaktionsmethoden: Bei Ausfall der Spracherkennung wird zur Touch-Bedienung gewechselt. Das **Circuit Breaker Pattern** verhindert Überbelastung durch fehlerhafte externe Services.

**Prevent Faults** durch Input-Validierung, TypeScript-Typsicherheit und das **Command Pattern** für sichere Operationen.

## Modifiabilität und Wartbarkeit

**Reduce Coupling** durch komponenten-basierte Architektur. Jedes Widget ist eine eigenständige Vue-Komponente; REST-APIs und MQTT agieren als Vermittler. Events entkoppeln Services vollständig – keine direkten Abhängigkeiten zwischen Komponenten.

**Increase Cohesion** folgt dem Single Responsibility Principle. Das **Facade Pattern** kapselt komplexe Logik. **Defer Binding** nutzt externe Konfigurationsdateien; die **Plugin-Architektur** mit **Factory Pattern** ermöglicht dynamisches Laden von Widgets ohne Code-Änderungen.

## Benutzerfreundlichkeit

**Support User Initiative** bietet Abbruch-Möglichkeiten und Undo-/Redo-Funktionen durch das **Command Pattern**.

**Support System Initiative** nutzt das **Observer Pattern** für proaktive Benachrichtigungen – Warnungen bei Regen, kontextbewusste Tipps, personalisierte Grüße.

## Sicherheit

**Resist Attacks** durch JWT-Authentifizierung, rollenbasierte Zugriffskontrolle und das **Decorator Pattern** für Datenvaldierung. TLS schützt externe Verbindungen.

**Detect Attacks** via Rate Limiting und das **Audit-Logging-Pattern** für alle sicherheitsrelevanten Ereignisse.

**React to Attacks:** Sofortiges Token-Entzug; das **Account Lockout Pattern** sperrt Accounts nach mehrfachen Fehlversuchen temporär.

## Testbarkeit

**Control and Observe System State** durch das **Mock-Object Pattern**. Externe APIs werden durch Mock-Services ersetzt. Das **Dependency Injection Pattern** ermöglicht einfaches Austausch von echten und Test-Objekten.

**Limit Complexity:** Max. 3 Komponenten-Verschachtelungs-Ebenen, Funktionen unter 50 Zeilen. Das **Strategy Pattern** testet verschiedene Algorithmen ohne Code-Duplikation.

## Zentrale Entwurfsmuster

Repository Pattern · Observer Pattern · Factory Pattern · Strategy Pattern · Circuit Breaker Pattern · Dependency Injection · Command Pattern · Facade Pattern · Plugin-Architektur · Decorator Pattern · Pub/Sub Pattern (Events) · Event Sourcing

## Fazit

Die Architektur balanciert pragmatisch zwischen Performance, Zuverlässigkeit, Wartbarkeit und Benutzerfreundlichkeit. Event-Driven Architecture ergänzt diese Taktiken durch Entkopplung und asynchrone Kommunikation. Die konsequente Anwendung bewährter Patterns schafft ein robustes, erweiterbares System ohne Über-Engineering – das Team kann iterativ Features hinzufügen bei maximaler Code-Qualität.

