| Quality attribute | Refinement               | Quality attribute scenarios                                                                 | Business value | Technical risk |
|-------------------|--------------------------|----------------------------------------------------------------------------------------------|----------------|-----------------|
| Performance       | Rendering time           | Beim Einfügen eines Widgets soll das Rendering unter 300 ms bleiben, auch auf einem Raspberry Pi. | H              | M               |
| Performance       | Startup time             | Beim Einschalten des Spiegels ist die UI innerhalb von 30 Sekunden betriebsbereit.           | H              | M               |
| Efficiency / Performance | Energy saving | Wenn 5 Minuten lang keine Nutzerinteraktion oder Bewegung erkannt wird, schaltet der Spiegel in den Energiesparmodus, ohne die Funktionsfähigkeit zu verlieren. | M | M |
| Modifiability     | Module extensibility     | Neue Widgets können ohne Änderungen am Core hinzugefügt werden; Integrationsaufwand < 2h.     | H              | M               |
| Usability         | Learnability & clarity   | Nutzer können sich innerhalb von 10 Sekunden visuell im Spiegel orientieren.                  | M              | L               |
| Availability      | Recovery & stability     | Bei API-Ausfällen (Wetter, Kalender) zeigt das System fallback-Daten an, ohne dass die UI einfriert. | M         | M               |
| Interoperability  | External data integration | Externe APIs (Wetter, Kalender) liefern Daten, die korrekt interpretiert und angezeigt werden (<5s Response). | M | M               |
| Security          | Integrity                | Module dürfen nur über definierte Schnittstellen kommunizieren.                               | H              | M               |
