<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# ich möchte in bestehendem repo (python backend  und vue frontend) mit einigen tausend zeilen code, jetzt graphify nutzen für visualisierung und insbesondere für coding agent für effizientere arbeit. außerdem will ich einrichtung nicht selbst machen sondern von copilot an sich machen lassen. entwickel dafür durch intesnive recherche gute strategie und vorgehen für copilot. ich habe bei anderem projekt nämlich erfahrung ghemacht dass einfach standard graph genereiren zu lassen, ziemlich schlechte qualität brachte (einzelne get funktionen als riesige knoten, völlig komisch und dumm benannte communities etc.)

Du solltest Graphify so einsetzen, dass Copilot immer zuerst eine „Karte“ deines Repos liest (GRAPH_REPORT + Communities) und erst dann einzelne Dateien anfasst – und zwar auf sauber gescoptem Code, nicht auf dem gesamten Wildwuchs.[^1_1][^1_2][^1_3][^1_4]

Unten ist ein konkretes Vorgehen, bei dem Copilot möglichst viel Setup übernimmt, du aber über ein paar gezielte Prompts die Qualität des Graphen steuerst.

***

## Zielbild

- Graphify baut aus deinem Python‑Backend und dem Vue‑Frontend einen Knowledge Graph (AST‑basiert, 20+ Sprachen), inkl. `graph.html`, `graph.json` und `GRAPH_REPORT.md` mit „god nodes“ und Community‑Analyse.[^1_5][^1_6][^1_2][^1_3][^1_1]
- Für GitHub Copilot gibt es eine Skill‑Integration (`graphify copilot install`) und für VS Code Copilot Chat eine Integration, die `.github/copilot-instructions.md` schreibt, damit Copilot den Graph immer als Kontext nutzt.[^1_7][^1_8][^1_1]
- Git‑Hooks oder `graphify --update` halten den Graph inkrementell aktuell, statt jedes Mal alles neu zu berechnen.[^1_9][^1_10][^1_1]

***

## Zielarchitektur im Repo

Bevor du Copilot losschickst, brauchst du eine grobe Zielstruktur, an der Graphify sich orientieren kann:

- Klare Top‑Level‑Ordner, z.B. `backend/` (FastAPI/Django/whatever), `frontend/` (Vue), `infra/`, `docs/`.
- Innerhalb von Backend/Frontend möglichst domain‑orientierte Pakete/Module, nicht nur technische Schichten.
- Ein bis zwei kurze Architektur‑Docs (`ARCHITECTURE.md` o.ä.) plus gute Modul‑Docstrings; Graphify extrahiert solche Rationale‑Nodes („warum“), was sowohl Community‑Labels als auch god‑nodes qualitativ verbessert.[^1_2][^1_3]

Das kannst du Copilot formulieren als:

> „Lies die Projektstruktur und schlage mir eine sinnvolle Top‑Level‑Gliederung (backend/frontend/etc.) und Architektur‑Notizdateien vor, die Graphify später als Rationale nutzen kann. Erstelle die Dateien selbst.“

***

## Schritt 1: Graphify + Copilot installieren (durch Copilot orchestriert)

**Was technisch passieren muss (Commands):**

- Graphify installieren: `pip install graphifyy`.[^1_11][^1_1][^1_5]
- Für GitHub Copilot CLI: `graphify copilot install` – das legt die Skill‑Definition in `~/.copilot/skills/graphify/SKILL.md` ab.[^1_12][^1_1][^1_7]
- Für VS Code Copilot Chat: `graphify vscode install` – das schreibt u.a. `.github/copilot-instructions.md` in dein Repo, sodass Copilot Chat automatisch angewiesen wird, `graphify-out/GRAPH_REPORT.md` als Architektur‑Kontext zu lesen.[^1_8][^1_1][^1_7]

**Wie du Copilot arbeiten lässt:**

1. Öffne das Repo in VS Code mit Copilot Chat.
2. Prompt (Beispiel, einmalig):
> „Du sollst für dieses Repo Graphify als Knowledge‑Graph‑Engine einrichten, damit du später beim Coding auf den Graph zugreifen kannst.
>  a) Erzeuge die nötigen Shell‑Befehle, um `graphifyy` zu installieren sowie `graphify copilot install` und `graphify vscode install` korrekt auszuführen.
>  b) Erkläre mir kurz, was die Befehle tun, ich führe sie dann in einem Terminal aus.“
3. Lass dir von Copilot die Befehle ausgeben, kontrolliere sie kurz und führe sie im Terminal aus.

Damit hast du die Skill‑Seite plus die Copilot‑Instruktionen eingerichtet, ohne selbst im Detail die Doku studieren zu müssen.

***

## Schritt 2: Gute `.graphifyignore` definieren

Schlechte Graph‑Qualität kommt oft daher, dass Graphify einfach alles scannt (node_modules, build‑Artefakte, generierte Files) und dann das Clustering mit Müll füttert – dann entstehen „komische Communities“ und riesige „node“‑Knoten.[^1_13][^1_7]

Graphify unterstützt `.graphifyignore` mit `.gitignore`‑Syntax; dort definierst du, was komplett außen vor bleiben soll.[^1_7]

**Empfohlene Start‑Konfiguration für dein Stack:**

Erzeuge (oder lass Copilot erzeugen) im Repo‑Root eine `.graphifyignore` mit z.B.:

```gitignore
# Build / Vendor
node_modules/
dist/
build/
.coverage/
.mypy_cache/

# Generierter Code
*.generated.py
*.js.map
*.d.ts

# Tool-/Agent-Metadaten
graphify-out/
AGENTS.md
CLAUDE.md
GEMINI.md
.gemini/
.opencode/
docs/translations/
```

Graphify liest diese Datei und ignoriert passende Pfade beim Erkennen/Extrahieren, solange du den Standard‑Pfad nutzt.[^1_7]

**Copilot‑Prompt dazu:**

> „Lies die Struktur dieses Repos (Python‑Backend + Vue‑Frontend) und schreib eine `.graphifyignore`, die alle offensichtlichen Build‑, Vendor‑ und generierten Dateien ausschließt. Erkläre kurz deine Entscheidungen.“

Damit bekommst du eine projektspezifische Ignorierliste, die du nur noch einmal reviewst.

*Hinweis:* In älteren Versionen gab es einen Bug, dass bestimmte Code‑Watch‑Pfade die Ignore‑Regeln nicht respektiert haben; das betrifft vor allem interne `watch()`‑Pfadvarianten.  Mit einem aktuellen Release bist du auf der sicheren Seite.[^1_13]

***

## Schritt 3: Erste Graph‑Builds scopen (Backend/Frontend getrennt)

Statt direkt das ganze Repo zu graphen (was oft zu Rauschen führt), würde ich Copilot explizit anweisen, zuerst Teilbäume zu verarbeiten:

- Backend:
    - Befehl: `graphify . --out graphify-out-backend --code-only` im `backend/`‑Ordner (oder `graphify backend --code-only`, je nach Layout).[^1_14]
    - `--code-only` sorgt dafür, dass zunächst nur Code, nicht auch heterogene Docs/Images, verarbeitet werden (du kannst später eine zweite Runde mit multimodalen Inputs machen).[^1_14]
- Frontend:
    - Befehl: analog in `frontend/` -> `graphify-out-frontend`.

Graphify erzeugt jeweils:

- `graph.html` – interaktive Visualisierung mit Community‑Filter.[^1_6][^1_1][^1_5][^1_7]
- `GRAPH_REPORT.md` – mit god nodes (höchste Degree), Community‑Liste, „surprising connections“ und vorgeschlagenen Fragen.[^1_3][^1_1][^1_2]
- `graph.json` – persistenter Graph für spätere Queries.[^1_4][^1_1][^1_7]

**Prompt für Copilot:**

> „Erzeuge für dieses Repo zwei separate Graphify‑Runs: einen für `backend/` und einen für `frontend/`.
>  Nutze `--code-only` und sinnvolle `--out`‑Verzeichnisse.
>  Gib mir die genauen Shell‑Befehle und beschreibe kurz, wie ich anschließend `graph.html` und `GRAPH_REPORT.md` finde.“

Führe dann nur die Befehle aus. Danach kannst du Copilot bitten, `GRAPH_REPORT.md` zu öffnen und zu analysieren.

***

## Schritt 4: Copilot so konfigurieren, dass er den Graph nutzt

Nach `graphify vscode install` hat dein Repo eine `.github/copilot-instructions.md`, in der festgehalten ist, dass Copilot Chat vor Architekturfragen `graphify-out/GRAPH_REPORT.md` lesen soll, sofern vorhanden.[^1_1][^1_8][^1_7]

Für dein Multi‑Graph‑Setup (separates Backend/Frontend‑Out) kannst du Copilot bitten, diese Datei anzupassen:

- Füge Regeln hinzu wie:
    - „Für Backend‑bezogene Fragen konsultiere zuerst `graphify-out-backend/GRAPH_REPORT.md`.
    - Für Frontend‑Fragen konsultiere `graphify-out-frontend/GRAPH_REPORT.md`.
    - Nutze die dort genannten god nodes und Communities, um relevante Dateien/Module zu wählen, bevor du Code änderst.“

Prompt dazu:

> „Öffne `.github/copilot-instructions.md` und erweitere sie so, dass du für Backend‑Fragen immer `graphify-out-backend/GRAPH_REPORT.md` und für Frontend‑Fragen `graphify-out-frontend/GRAPH_REPORT.md` als primären Kontext nutzt. Formuliere die Regeln klar und kurz.“

Damit zwingst du Copilot, sich strukturell zu orientieren (Graph → god nodes → Dateien) statt wahllos den Workspace zu durchsuchen.[^1_3][^1_4][^1_1]

***

## Schritt 5: Arbeits‑Playbooks für den Coding‑Agent

Damit Graphify nicht nur „schöne Bilder“ liefert, sondern deinen Alltag mit Copilot verbessert, brauchst du wiederverwendbare Prompt‑Patterns. Beispiele:

### 5.1 Feature‑Implementierung

> „Nutze zuerst die Graphify‑Reports für Backend und Frontend:
>  – Identifiziere die relevanten Communities und god nodes für *[Featurebeschreibung]*.
>  – Liste mir die 5–10 relevantesten Module/Komponenten mit Begründung aus dem Graph.
>  – Erstelle danach einen Schritt‑Plan für die Implementierung und schlage konkrete Code‑Änderungen vor.“

So zwingst du Copilot, den Graph explizit in den Workflow zu integrieren („erst Karte lesen, dann Code ändern“).

### 5.2 Refactorings / große Knoten

Wenn du merkst, dass Graphify einzelne GET‑Handler o.ä. als riesige Knoten markiert:

> „Analysiere anhand des Graphify‑Graphs die Knoten mit höchster Degree und deren Communities.
>  Erkläre mir, welche Funktionen/Module im Backend übermäßig viele Abhängigkeiten haben (god nodes) und schlage Refactorings vor, um sie in sinnvollere Submodule zu zerlegen. Nutze konkrete Code‑Beispiele.“

Graphify liefert dafür explizit die god nodes und „surprising connections“, die Copilot aus `GRAPH_REPORT.md` herauslesen kann.[^1_2][^1_3]

### 5.3 Onboarding / Architekturfragen

> „Du kennst den Graphify‑Graph dieses Repos.
>  Erkläre mir die Architektur des Backends in 10 Sätzen, gruppiert nach Communities, und nenne für jede Community ihre wichtigsten god nodes und Dateien.“

Das ist im Prinzip ein „Struktur‑Query“ über den Graphen und gibt dir eine sehr viel bessere Übersicht als reine Textsuche.

***

## Schritt 6: Qualität von Communities und Labels verbessern

Graphify clustert mit der Leiden‑Methode (bzw. verwandten Verfahren) und weist jedem Knoten eine `community`‑ID zu; daraus generiert der Report benannte Communities und god nodes.[^1_15][^1_2][^1_3]

Wenn du schlechte Community‑Namen und seltsame Gruppierungen hattest, kannst du gezielt nachsteuern:

- **Noise raus**: iteriere mit Copilot über `.graphifyignore`, wenn du im `GRAPH_REPORT.md` siehst, dass z.B. Testordner, generierte Clients oder Legacy‑Ordner eigene große Communities bilden. Lass Copilot dir konkrete Ignore‑Einträge vorschlagen.[^1_13][^1_7]
- **Semantische Namen fördern**:
    - Schreib kurze, prägnante Modul‑Docstrings und Kommentare mit klaren Stichwörtern; Graphify extrahiert nicht nur Funktionsnamen, sondern auch solche Rationale‑Snippets als „rationale_for“‑Nodes, was die Community‑Interpretation verbessert.[^1_3]
    - Benenne Ordner/Dateien nach Domain (z.B. `billing/`, `user_profile/`) statt rein nach Technik.
- **Wiki/Labels optional nutzen**: in neueren Versionen kann Graphify zusätzlich Wiki‑Artikel und Label‑Artefakte generieren, die Community‑Labels persistieren; das hilft, wenn du nachträglich menschenlesbare Namen pflegen willst.[^1_16][^1_17][^1_9]

Prompt‑Pattern für Copilot:

> „Öffne `graphify-out-backend/GRAPH_REPORT.md` und identifiziere Communities mit schlechten Namen oder offensichtlich gemischten Inhalten.
>  Schlage mir Änderungen (Renames, Docstrings, `.graphifyignore`‑Einträge) vor, um die Struktur beim nächsten Graphify‑Run zu verbessern.“

***

## Schritt 7: Graph aktuell halten

Damit Copilot langfristig von Graphify profitiert, muss der Graph ohne großen Aufwand aktuell bleiben.

**Option A – Git‑Hook (automatisch):**

- Graphify besitzt einen Befehl `graphify hook install`, der `post-commit`‑Hooks installiert und nach passenden Code‑Commits automatisch einen inkrementellen Rebuild startet.[^1_10][^1_18][^1_1]
- Es gab Fälle, in denen bestimmte Dateiendungen (.tsx/.jsx etc.) im Hook‑Allowlist gefehlt haben und deshalb kein Rebuild ausgelöst wurde; prüfe deine Graphify‑Version und ggf. die Hook‑Skripte kurz.[^1_18]

Prompt:

> „Installiere bitte für dieses Repo die Graphify‑post‑commit‑Hooks (`graphify hook install`) und erkläre mir, welche Dateitypen aktuell den Rebuild triggern. Schlage Anpassungen vor, falls `.vue` oder andere relevante Endungen fehlen.“

**Option B – Manuelles Update (kontrolliert):**

- Du kannst auch bewusst nur z.B. einmal am Tag oder vor größeren Sessions `graphify --update` aufrufen, was den bestehenden Graph auf Basis der Cache‑Informationen inkrementell aktualisiert.[^1_9][^1_10][^1_1]
- Lass dir von Copilot einen einfachen `make graph`‑ oder `npm run graph`‑Task bauen, der `graphify --update` für Backend/Frontend anstößt.

***

## Fazit

Kern der Strategie ist: Du benutzt Copilot als „Orchestrator“ für Graphify‑Installation, `.graphifyignore`‑Design und Copilot‑Instruktionen, während Graphify das strukturelle Gedächtnis deines Repos bildet (GRAPH_REPORT, Communities, god nodes).[^1_4][^1_1][^1_2][^1_7][^1_3]

Wenn du möchtest, kann ich dir als nächsten Schritt ganz konkret:

- einen Beispiel‑Prompt für Copilot Chat schreiben, den du 1:1 in deinem Repo verwenden kannst („hier ist dein dauerhafter Arbeitsmodus mit Graphify“), oder
- eine `.graphifyignore`‑Startversion speziell für deine Ordnerstruktur (wenn du grob sagst, wie dein Backend/Frontend aktuell aufgebaut ist).
<span style="display:none">[^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_38][^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51]</span>

<div align="center">⁂</div>

[^1_1]: https://github.com/safishamsi/graphify

[^1_2]: https://github.com/safishamsi/graphify/blob/v4/ARCHITECTURE.md

[^1_3]: https://libraries.io/pypi/graphify-leo

[^1_4]: https://github.com/safishamsi/graphify/blob/v4/README.md

[^1_5]: https://graphifylabs.ai

[^1_6]: https://www.youtube.com/watch?v=eYHpKFfhK2A

[^1_7]: https://libraries.io/pypi/graphifyy

[^1_8]: https://newreleases.io/project/github/safishamsi/graphify/release/v0.4.15

[^1_9]: https://github.com/safishamsi/graphify/blob/v4/CHANGELOG.md

[^1_10]: https://www.youtube.com/watch?v=BkHps04qGgc

[^1_11]: https://www.reddit.com/r/ArtificialInteligence/comments/1sfaby2/i_built_graphify_after_karpathys_raw_folder_post/

[^1_12]: https://libraries.io/npm/graphifyy

[^1_13]: https://github.com/safishamsi/graphify/issues/188

[^1_14]: https://lib.rs/crates/graphify-security

[^1_15]: https://docs.rs/graphify-cluster/latest/graphify_cluster/

[^1_16]: https://github.com/safishamsi/graphify/issues/229

[^1_17]: https://sourceforge.net/projects/graphify.mirror/files/v0.4.14/

[^1_18]: https://github.com/safishamsi/graphify/issues/222

[^1_19]: https://www.youtube.com/watch?v=GOfpB5Mquss

[^1_20]: https://github.com/CoffeeVampir3/Graphify/blob/main/Readme.md

[^1_21]: https://www.reddit.com/r/GithubCopilot/comments/1supxer/codegraph_helping_copilot_see_structure_not_just/

[^1_22]: https://github.com/CoffeeVampir3/Graphify/

[^1_23]: https://github.com/safishamsi/graphify/issues/425

[^1_24]: https://gist.github.com/ashokvarmamatta/344a642e8b5bd286be605a8f439c3848

[^1_25]: https://github.com/Graphitti/graphify

[^1_26]: https://github.com/safishamsi/graphify/blob/v5/README.md

[^1_27]: https://skillsllm.com/skill/graphify

[^1_28]: https://gitgems.app/repo/safishamsi/graphify

[^1_29]: https://corti.com/graphify-bringing-knowledge-graphs-to-ai-assisted-engineering/

[^1_30]: https://github.com/Bogdanp/dramatiq/issues/594

[^1_31]: https://libraries.io/pypi/graphifyyy

[^1_32]: https://www.youtube.com/watch?v=EKbQ5sajVxA

[^1_33]: https://forum.obsidian.md/t/excluding-including-folders-in-graph-view/15213

[^1_34]: https://jfrog.com/help/r/how-to-use-include-exclude-patterns

[^1_35]: https://github.com/safishamsi/graphify/blob/v4/.gitignore

[^1_36]: https://memgraph.com/docs/advanced-algorithms/available-algorithms/leiden_community_detection

[^1_37]: https://i11www.iti.kit.edu/_media/teaching/theses/ba-nguyen-21.pdf

[^1_38]: https://libraries.io/pypi/codegraph-tools

[^1_39]: https://arxiv.org/html/2405.11658v4

[^1_40]: https://openclawapi.org/es/blog/2026-04-12-graphify-knowledge-graph

[^1_41]: https://developer.nvidia.com/blog/how-to-accelerate-community-detection-in-python-using-gpu-powered-leiden/

[^1_42]: https://openclawapi.org/ru/blog/2026-04-12-graphify-knowledge-graph

[^1_43]: https://github.com/safishamsi/graphify/issues/37

[^1_44]: https://github.com/safishamsi/graphify/issues/140

[^1_45]: https://www.youtube.com/watch?v=wxaxlIlN7BA

[^1_46]: https://www.datacamp.com/tutorial/git-hooks-complete-guide

[^1_47]: https://lib.rs/crates/graphify-analyze

[^1_48]: https://stackoverflow.com/questions/49912695/git-pre-and-post-commit-hooks-not-running

[^1_49]: https://github.com/microsoft/vscode-docs/blob/main/docs/copilot/getting-started-chat.md

[^1_50]: https://courses.csail.mit.edu/6.S194/13/lessons/03-git/adding-custom-hooks-to-git.html

[^1_51]: https://code.visualstudio.com/docs/copilot/setup


---

# Graphify – dichte Referenz für Coding‑Agent / Copilot

*(Ziel: Dieses Dokument als Kontext für Copilot/Coding‑Agent. Fokus: Fortgeschrittene Nutzung, keine Basic‑Erklärungen.)*

***

## 1. Grundmodell von Graphify

- Rolle: Knowledge‑Graph‑Engine für beliebige Ordner (Code, Docs, Bilder, Audio/Video). Einmal bauen, dann inkrementell wachsen lassen.[^2_1][^2_2][^2_3]
- Parser: AST‑Pass für ~20 Sprachen via tree‑sitter (Python, JS/TS, Go, Rust, Java, C/C++, C\#, Kotlin, Scala, PHP, Swift, Ruby, Lua, Zig, PowerShell, Elixir, Objective‑C, Julia, Verilog, SystemVerilog, Vue, Svelte, Dart).[^2_2][^2_3]
- Semantik: LLM‑Subagenten extrahieren Konzepte/Beziehungen/Rationales aus Text, PDFs, Bildern, Audio/Video; Whisper‑Transkription lokal, Domain‑Prompt aus god nodes.[^2_2][^2_3]
- Community‑Detection: Leiden, topologiebasiert (keine Embeddings); semantische Kanten `semantically_similar_to` fließen in das Community‑Clustering ein.[^2_2][^2_4][^2_5]
- Vertrauen: Kanten‑Label `confidence ∈ {EXTRACTED, INFERRED, AMBIGUOUS}` + `confidence_score` 0–1.[^2_2][^2_3]

***

## 2. Artefakte und Verzeichnisstruktur

Standard‑Output (pro Run oder Corpus):[^2_2][^2_3]

```text
graphify-out/
  graph.json         # persistenter Graph
  GRAPH_REPORT.md    # Analyse für Agent
  graph.html         # interaktive Visualisierung
  cache/             # SHA256-basierte AST/semantik-Caches
  transcripts/       # optional, Audio/Video-Transkripte
```

- `graph.json` (NetworkX‑Export):
    - `nodes[]`: `id`, `label`, `source_file`, `source_location`, `community`, evtl. Node‑Typ (Klasse, Funktion, Konzept, rationale‑Snippet).[^2_3]
    - `edges[]`: `source`, `target`, `relation` (z.B. `imports`, `calls`, `semantically_similar_to`), `confidence`, `confidence_score`.[^2_3]
- `GRAPH_REPORT.md`:
    - God nodes (hohe Degree / Betweenness, Blast‑Radius‑Träger).[^2_1][^2_3]
    - Surprising connections (clusterübergreifende Kanten mit Erklärung).[^2_3]
    - Suggested questions (4–5 „Graph‑typische“ Fragen).[^2_3]
    - Design rationale (aus `NOTE/WHY/HACK`‑Kommentaren, Docstrings).[^2_3]
- `graph.html`: vis.js‑basierte Ansicht, Suche, Community‑Filter, Show/Hide‑All.[^2_2][^2_3]

***

## 3. Installation / Plattform‑Layer (für Agent)

### 3.1 Paket und CLI

- PyPI‑Name: `graphifyy` (mit doppeltem y). CLI‑Binary: `graphify`.[^2_6][^2_3]
- Empfohlen: isoliert per `pipx install graphifyy` ausführen, falls Pfad/venv‑Probleme.[^2_3]


### 3.2 Skill‑/IDE‑Integration

- Genereller Flow:[^2_2][^2_3]
    - `pip install graphifyy`
    - `graphify install --platform <PLATFORM>`
- Beispiele Plattform‑Switches:[^2_2][^2_3]
    - `graphify install` (Default: Claude Code)
    - `graphify install --platform codex|opencode|claw|aider|droid|trae|cursor|gemini|windows`

Plattformspezifisches Verhalten:[^2_2][^2_3]

- **Claude Code** `graphify claude install`
    - Schreibt Regeln in `CLAUDE.md` → „erst GRAPH_REPORT lesen“.[^2_3]
    - Installiert PreToolUse‑Hook in `settings.json`: intercept für grep/rg/find/fd‑ähnliche Kommandos; injiziert „Graphify‑Hinweis“ vor Tools.[^2_2][^2_3]
- **Cursor** `graphify cursor install`
    - Erstellt `.cursor/rules/graphify.mdc` mit `alwaysApply: true`.[^2_3]
- **OpenClaw / Aider / Trae**
    - `graphify claw|aider|trae install` → schreibt Instruktionen in `AGENTS.md` (Graph‑Report priorisieren).[^2_3]
- Uninstall‑Symmetrie: `graphify <platform> uninstall`, `graphify hook uninstall`.[^2_3]

***

## 4. Build‑Modi und Flags (Corpus‑Erstellung)

### 4.1 Basis‑Aufrufe

- General:
    - `/graphify .` in Skill‑fähigem IDE/Agent.[^2_2][^2_3]
    - `graphify .` direkt als CLI.[^2_2][^2_1]
- Scoping:
    - `graphify ./src`
    - `graphify ./src --no-viz` (kein HTML, schneller, reiner AST/LLM + JSON/Report).[^2_3]
    - `graphify ./src --mode deep` (aggressivere semantische Extraktion, mehr INFERRED/AMBIGUOUS‑Kanten, höherer Tokenverbrauch).[^2_3]


### 4.2 Incrementalität

- `--update` (inkrementell):
    - Nutzt Cache‑Hashes; nur geänderte Dateien werden erneut geparst + semantisch extrahiert.[^2_3]
    - Shrink‑Guard: Graph wird nicht mit kleineren JSON‑Schnappschüssen überschrieben; `to_json()` verweigert Shrink → keine stillen Graph‑Verluste.[^2_2]
- `--watch`:
    - Live AST‑Rebuild beim Speichern (LLM‑frei, nur Code).[^2_1][^2_3]
    - Für Docs/Bilder: Hinweis, manuell `--update` auszuführen.[^2_3]


### 4.3 Git‑Hooks

- `graphify hook install`:[^2_3][^2_7]
    - Installiert `post-commit` und `post-checkout` in `.git/hooks/`.
    - Jeder Commit/Branch‑Wechsel triggert Rebuild (inkrementell über Cache).
    - Fehler in Rebuild (Parse, LLM‑Timeout etc.) → non‑zero exit → Git‑Op wird abgebrochen (keine stillen Inkonsistenzen).[^2_3]
- `graphify hook status`, `graphify hook uninstall`.[^2_3]
- Bekannte Stolpersteine: Dateiendungs‑Allowlist in Hooks (.tsx/.jsx/.vue u.a.) muss ggf. angepasst werden, je nach Version.[^2_7]


### 4.4 Clone und Multi‑Repo

- `graphify clone <github-url> [--branch BR] [--out DIR]`:[^2_2]

```
- Clont nach `~/.graphify/repos/<owner>/<repo>`, reuses clone mit `git pull` bei Folgeaufrufen.  
```

    - Führt vollständigen Graphify‑Pipeline‑Run auf Clone aus (inkl. `graphify-out/`).
- `graphify merge-graphs g1.json g2.json ...`:[^2_2]
    - Merget mehrere `graph.json` in einen Cross‑Repo‑Graph, taggt Nodes mit Source‑Repo.
    - Unterstützt Team‑/Monorepo‑Szenarien, Dependency‑Landkarte über Projekte.

***

## 5. Query‑Befehle (Graph‑Abfragen)

### 5.1 `graphify query`

Semantische Query auf `graph.json`:[^2_3]

```bash
graphify query "what connects Attention to the optimizer?"
graphify query "show the auth flow" --budget 1500
graphify query "what connects DigestAuth to Response?" --dfs
graphify query "... " --graph path/to/another-graph.json
```

- Default: random walk / sampling‑basierte Traversal entlang relevanter Kanten.
- `--budget <TOKENS>`: Begrenzung des Text‑Outputs für LLM‑Kontext.[^2_3]
- `--dfs`: deterministische Tiefensuche statt Sampling; sinnvoll für „vollständige Pfade“.[^2_3]
- `--graph` zum expliziten Setzen eines alternativen Graph‑Files (Multi‑Graph‑Setups).[^2_3]

Output idealerweise direkt in Agent‑Prompt einbetten:

> „Use this graph query output to answer. Prefer graph structure over guessing; cite source files.“[^2_3]

### 5.2 `graphify path`

Shortest‑/relevanter Pfad zwischen zwei Node‑IDs:[^2_3]

```bash
graphify path "DigestAuth" "Response"
```

- Nutzt Graph‑Topologie (Import/Call/Semantik‑Kanten).
- Gut für „End‑to‑End‑Flows“ (Request → Handler → DB) oder „Blast‑Radius“‑Analysen (God node → betroffene Module).


### 5.3 `graphify explain`

Node‑Kontext:[^2_3]

```bash
graphify explain "SwinTransformer"
```

- Gibt Community, Nachbarn, Kanten‑Typen, Source‑Files, Rationale‑Snippets.
- Eignet sich, um LLM auf „je Node“‑Kontext zu fokussieren, bevor Code geändert wird.

***

## 6. Dateitypen, Extras und `.graphifyignore`

### 6.1 Unterstützte Typen (Auszug)[^2_2][^2_3]

- Code: `.py .ts .js .go .rs .java .c .cpp .rb .cs .kt .scala .php .swift .lua .zig .ps1 .ex .m .jl`
- Docs: `.md .txt .rst`
- Bilder: `.png .jpg .webp`
- PDFs: `.pdf` (mit `pip install graphifyy[pdf]`)
- Audio/Video: `.mp4 .mp3 .wav` + YouTube‑URLs (über yt‑dlp → Audio → Whisper; `pip install 'graphifyy[video]'`).[^2_3][^2_2]


### 6.2 Ignore‑Regeln

- `.graphifyignore` am Repo‑Root, Syntax ≈ `.gitignore`. Gilt auch, wenn `graphify` in Subordnern läuft.[^2_2][^2_3]
- Typische Einträge:

```gitignore
node_modules/
dist/
build/
*.generated.py
graphify-out/
```

- Fehlerbild „zu wenige Nodes“ → meist zu aggressive Ignore‑Pattern; Diagnose via `graphify ./src --no-viz` + Check der gelesenen Dateien.[^2_3]


### 6.3 Extras / Optional‑Dependencies

- `[video]`: Whisper + yt‑dlp für AV‑Transkription.[^2_3]
- `[pdf]`: PDF‑Parsing.[^2_3]
- `[watch]`: `watchdog` für `--watch`‑Modus.[^2_3]

***

## 7. Graph‑Konsistenz, Caches und Fortgeschrittenes

### 7.1 Cache‑Layout

- AST‑ und Semantik‑Cache in getrennten Subdirs (`cache/ast/`, `cache/semantic/`); verhindert Überschreiben bei gemischten Corpora (Code + Docs).[^2_2]
- Cache‑Invalidierung:
    - Komplett: `rm -rf graphify-out/cache` + Full‑Run.[^2_3]
    - Partiell: gezielte Cache‑Datei löschen, dann `--update`.[^2_3]


### 7.2 Safety / Konsistenz‑Guards

- Shrink‑Guard: keine Überschreibung von `graph.json` durch kleinere Graphen bei partiellen Updates.[^2_2]
- Desync‑Guard: `graphify update` schreibt `GRAPH_REPORT.md`/`graph.html` nur bei erfolgreichem JSON‑Write.[^2_2]
- Node‑ID‑Kollisionen: Dateien gleichen Namens in unterschiedlichen Ordnern erhalten eindeutig prefixed IDs (inkl. Parent‑Dir).[^2_2]


### 7.3 Deduplikation / Merge‑API (Python‑Lib)

- `build_merge()`:
    - Lädt existierenden Graph, merged neue Chunks, optional Prune gelöschter Dateien, respektiert Shrink‑Guard.[^2_2]
- `deduplicate_by_label()`:
    - Collapst Nodes mit gleichen normalisierten Labels (z.B. aus parallelen Subagents).[^2_2]

***

## 8. Fortgeschrittene Integrationen

### 8.1 MCP‑Server

- Start:

```bash
python -m graphify.serve graphify-out/graph.json
```

- Bietet MCP‑Tools:[^2_3]
    - `query_graph` (Subgraph für Fragen)
    - `get_node`
    - `get_neighbors`
    - `shortest_path`
- Einsatz: AI‑Agent spricht direkt über MCP mit Graph, ohne CLI‑Zwischenschritt.


### 8.2 Neo4j‑Export

- Generiere Cypher‑Script:[^2_3]

```bash
/graphify ./src --neo4j
```

- Direkt‑Push:[^2_3]

```bash
/graphify ./src --neo4j-push bolt://localhost:7687
```

- Für tiefe Graph‑Analytics (Cypher‑Queries, zentrale Knoten, eigene Community‑Algorithmen).


### 8.3 Wiki‑Export

- Befehl:[^2_3]

```bash
/graphify ./src --wiki
```

- Output: `graphify-out/wiki/index.md` + Markdown‑Artikel pro Community und god node.
- Ziel: agent‑freundliche, navigierbare Wissensbasis (Filesystem‑RAG).

***

## 9. Best Practices für Agent‑Nutzung

*(Stichworte, damit Copilot/Agent sinnvoll mit Graphify umgeht.)*

- Vor jeder größeren Änderung:
    - `GRAPH_REPORT.md` lesen → Communities + god nodes bestimmen.[^2_2][^2_3]
    - Relevante Communities/Nodes per `graphify query`/`path` einengen.
- Für Features/Refactorings:
    - „Erst Graph, dann Code“: Query‑Output als primären Kontext nutzen, Files daraus gezielt öffnen.
- Blast‑Radius‑Analyse:
    - God node aus Report → `graphify path`/`query` → Liste der betroffenen Module/Services.
- Onboarding:
    - Nur `GRAPH_REPORT.md` + `graph.html` + 1–2 Queries lesen, nicht das gesamte Repo.
- Pflege:
    - Hooks/`--update` sauber halten, `.graphifyignore` iterativ verbessern; keine generierten/Build‑Ordner erlauben, um Community‑Rauschen zu reduzieren.[^2_2][^2_8][^2_3]

***

Wenn du willst, formuliere ich daraus im nächsten Schritt eine knappe `.github/copilot-instructions.md`, speziell zugeschnitten auf dein Repo (Backend/Frontend getrennt), die Copilot zwingt, Graphify‑Artefakte immer zuerst zu nutzen.

<div align="center">⁂</div>

[^2_1]: https://graphifylabs.ai

[^2_2]: https://skillsllm.com/skill/graphify

[^2_3]: https://openclawapi.org/es/blog/2026-04-12-graphify-knowledge-graph

[^2_4]: https://github.com/safishamsi/graphify/blob/v4/ARCHITECTURE.md

[^2_5]: https://libraries.io/pypi/graphify-leo

[^2_6]: https://libraries.io/pypi/graphifyy

[^2_7]: https://github.com/safishamsi/graphify/issues/222

[^2_8]: https://github.com/safishamsi/graphify/issues/188


---

## Ziel dieses Abschnitts

Zweck: Agent soll eigenständig Graphify installieren, konfigurieren, ausführen und den ersten Graph so bauen, dass er logisch, balanciert und repo‑spezifisch ist (kein Rauschen, keine falschen Communities).[^3_1][^3_2][^3_3]

***

## 1. Installations‑Wissen für den Agent

- Official package: `graphifyy` (PyPI, double‑y); CLI‑Befehl: `graphify`.[^3_2][^3_4][^3_1]
- Python‑Version: ≥ 3.10.[^3_3]
- Installation bevorzugt über Tool‑Runner, um PATH‑Probleme zu vermeiden:
    - `uv tool install graphifyy` **oder** `pipx install graphifyy` → `graphify` landet automatisch im PATH.[^3_1][^3_2]
    - Fallback: `pip install graphifyy` + PATH‑Ergänzung (`~/.local/bin` Linux, `~/Library/Python/3.x/bin` Mac) oder `python -m graphify` nutzen.[^3_2][^3_1]

**Agent‑Ziel:**

- Prüfe, ob `graphify` im PATH ist; wenn nicht, installiere mit `uv tool install graphifyy` oder `pipx install graphifyy`.[^3_4][^3_1][^3_2]
- Verifiziere Version ≥ 0.6.3, um god_node‑Fixes und semantische Node‑Preservation zu bekommen (`graphify --version`).[^3_5][^3_6]

***

## 2. Plattform‑Integration (für Copilot / Agent)

- Plattform‑Install allgemein:[^3_1][^3_2]
    - `graphify install` (Claude Code, Linux/Mac; Windows auto‑detect).[^3_2][^3_1]
    - `graphify install --platform copilot` (GitHub Copilot CLI).[^3_1][^3_2]
    - `graphify vscode install` (VS Code Copilot Chat, schreibt `.github/copilot-instructions.md`).[^3_2][^3_1]
    - Weitere Plattformen: `graphify <platform> install` (codex, opencode, claw, droid, trae, gemini, hermes, kiro, pi, antigravity, cursor etc.).[^3_7][^3_1][^3_2]

**Agent‑Ziel:**

- Erkenne aktive Plattform (z.B. Copilot CLI + VS Code Copilot Chat) und führe passende `graphify <platform> install`‑Befehle aus.[^3_8][^3_1][^3_2]
- Prüfe, ob `.github/copilot-instructions.md` existiert und erweitere sie später um repo‑spezifische Graph‑Nutzungsregeln.[^3_1][^3_2]

***

## 3. Preflight‑Checks im Repo

- Voraussetzungen vor erstem Run:[^3_9][^3_3]
    - Root‑Ordner definieren (Projekt‑Root, nicht Home‑Verzeichnis).
    - Grobe Domain‑Ordner (z.B. `backend/`, `frontend/`, `infra/`, `docs/`).
    - Optional: vorhandene Architektur‑Dokumente (`ARCHITECTURE.md`, `README`s), die später zusätzliche Rationale‑Nodes liefern.

**Agent‑Ziel:**

- Ermittele Projekt‑Root anhand Git‑Root (`git rev-parse --show-toplevel`) oder klarer Marker.[^3_3]
- Erkenne Hauptordner (Code vs. Build/Artefakte) mit heuristischer Analyse der Struktur vor dem ersten `graphify`‑Run.[^3_3]

***

## 4. .graphifyignore‑Strategie (entscheidend für Graph‑Qualität)

### 4.1 Semantik von `.graphifyignore`

- Datei im Projekt‑Root, gleiche Syntax wie `.gitignore`, inkl. Negation `!pattern`.[^3_9][^3_2][^3_1]
- Muster gelten auch, wenn `graphify` auf Subordner (`./raw`, `./src`) ausgeführt wird (Fix für frühere Bugs mit Parent‑Ignore und relativen Pfaden).[^3_10][^3_9]
- Dateien, die auf `.graphifyignore` matchen, werden nicht in Detection/Extraction aufgenommen (kein AST, keine semantischen Kanten).[^3_2][^3_1]


### 4.2 Was explizit ausgeschlossen werden soll

**Immer ignorieren:**[^3_9][^3_3][^3_1]

- Build‑ und Vendor‑Dirs: `node_modules/`, `dist/`, `build/`, `.next/`, `out/`, `.venv/`, `env/`, `.mypy_cache/`, `.pytest_cache/`.
- Generated Code: `*.generated.*`, `.openapi-client/`, `*/__generated__/*`, Protobuf‑/gRPC‑Artefakte.
- Große Binärartefakte, die nicht relevant sind: `*.zip`, `*.tar`, `*.whl`.
- Graphify‑Outputs selbst: `graphify-out*/` (wenn mehrere Out‑Verzeichnisse).

**Falls vorhanden ignorieren:**

- Legacy‑Code‑Ordner, die nicht mehr produktiv sind und Communities verzerren (z.B. `legacy/`, `old/`).
- Test‑Fixtures mit massenhaft, aber trivialen Strukturen (`tests/fixtures/large/*`).


### 4.3 Was nicht ignoriert werden darf

- Kern‑Code‑Verzeichnisse für Backend/Frontend.
- Domain‑Docs (Architektur‑README, ADRs, Spezifikationen), sofern semantisch relevant.
- SQL‑Schemas, Migrations, Config‑Dateien mit Domain‑Semantik (z.B. `alembic/versions`, `prisma/schema.prisma`) – liefern Schema‑Nodes.

**Agent‑Ziel:**

- Erstelle/aktualisiere `.graphifyignore` anhand realer Projektstruktur.
- Prüfe nach erstem Run, ob `graph.json` zu wenige Nodes enthält (Hinweis auf zu aggressive Ignore‑Regeln) und passe Patterns an.[^3_3][^3_9]
- Beachte Issue 495: wenn `graphify` in Subdir läuft, trotzdem `.graphifyignore` im Root beachten (aktuelle Versionen fixen das; älterer Code kann Bug haben).[^3_10][^3_9]

***

## 5. Plan für ersten Graph‑Build (Scoping, um „schlechte Graphen“ zu vermeiden)

### 5.1 Grundprinzip

- Erst klein und fokussiert graphen, dann schrittweise Umfang erhöhen.[^3_11][^3_3]
- Zuerst Code‑Schicht (AST‑Pass, zero tokens), später Docs/AV hinzufügen.[^3_8][^3_11][^3_1]


### 5.2 Konkrete Schrittfolge

1. **Dry‑Run‑Scope bestimmen**
    - Backend‑Subgraph: `graphify backend --no-viz` (oder `graphify ./backend --no-viz`).[^3_3][^3_1][^3_2]
    - Frontend‑Subgraph: `graphify frontend --no-viz`.
    - Option `--no-viz` spart Zeit, erzeugt `graph.json` + `GRAPH_REPORT.md` ohne HTML; erst später `graph.html` nötig.[^3_1][^3_3]
2. **Code‑Only‑Phase**
    - Falls Version/Flags existieren: Code‑fokussierter Modus (ohne AV/PDF) verwenden, um initiale Topologie sauber zu halten.[^3_3][^3_1]
    - Erst nach stabiler Topologie AV/PDF/Docs hinzufügen, um semantische Kanten zu ergänzen.
3. **Review‑Phase**
    - Agent liest `GRAPH_REPORT.md` vom Backend‑ und Frontend‑Run, prüft Communities, god nodes, surprising connections.[^3_12][^3_13]
    - Bei Rauschen (z.B. große Communities aus Testcode, generierten Clients) → `.graphifyignore` verschärfen, ggf. Domain‑Ordner umstrukturieren.
4. **Full‑Project‑Graph**
    - Nach Stabilisierung: `graphify .` im Projekt‑Root, um gesamtes Repo in `graphify-out/` zu erfassen (inkl. Docs, falls gewünscht).[^3_2][^3_1][^3_3]

**Agent‑Ziel:**

- Kein „full repo“‑Run ohne vorheriges Teil‑Scoping und `.graphifyignore`‑Feintuning.
- Fokus auf Domain‑Code, nicht auf Build/Tests, bis erste Topologie plausibel ist.

***

## 6. Qualitätssicherung: Erkennung und Vermeidung schlechter Graphen

### 6.1 Typische Fehlbilder

1. **Riesige god nodes in trivialen Helpern**
    - Ursache: generische Funktionsnamen, INFERRED‑Kanten, rationale‑Node‑Leakage.[^3_6][^3_5]
    - Fix in v0.6.3+: INFERRED‑`calls` ignorieren Call‑Targets mit >2 möglichen Resolutions (z.B. globale `log`, `execute`, `find`), um künstliche Hubs zu vermeiden.[^3_6]
    - Fix in v0.6.6+: rationale‑Nodes werden nicht mehr als „echte“ Semantik‑Knoten in Cross‑File‑Resolution eingespeist.[^3_5]
2. **Unlogische Communities (Tests, Build, Legacy gemischt mit Domain)**
    - Ursache: Build/Tests/Legacy nicht ignoriert; Community‑Detection findet Struktur, aber nicht die gewünschte Domainstruktur.[^3_13][^3_14]
    - Lösung: `.graphifyignore` verschärfen; Domain‑Ordner konsolidieren; ggf. mehrere Graphs (per Subfolder‑Runs oder `merge-graphs`) statt Monolith.
3. **Unbalancierter Graph (viel Docs, wenig Code oder umgekehrt)**
    - Ursache: Falsche Auswahl von Input‑Dateien (nur Docs oder nur Teil des Codes).
    - Lösung: Sicherstellen, dass Core‑Codepfade + wichtigste Architektur‑Docs immer gemeinsam im ersten Full‑Graph enthalten sind.

### 6.2 Explizite Checks, die Agent durchführen soll

- Node‑Count pro Typ:
    - Prüfe in `graph.json` Anzahl Code‑Nodes vs. semantische Nodes; krasse Unterrepräsentation von Code → `.graphifyignore` zu aggressiv.[^3_14][^3_13]
- God‑Node‑Liste aus `GRAPH_REPORT.md`:[^3_12][^3_13]
    - Verifiziere, dass Top‑10‑god nodes echte Domain‑Abstraktionen sind (Services, zentrale Klassen, nicht Utility‑Funktionen).
    - Bei 3+ Utility‑god nodes → Refactoring‑Plan vorschlagen oder `.graphifyignore`/Ordnerstruktur anpassen.
- Community‑Cohesion und Labels:[^3_13][^3_14][^3_12]
    - Communities mit schwacher Kohäsion und vielen unterschiedlichen Domänen → Kandidat für bessere Ordnerstruktur oder weitere Excludes.

**Agent‑Ziel:**

- Nach erstem Graph: automatisierter Checklauf, der `GRAPH_REPORT.md` und `graph.json` auswertet und Fehlbilder markiert; erst danach Graph für Coding‑Kontext freigeben.

***

## 7. Incrementalität und Hooks, ohne Graph zu „zerstören“

### 7.1 `graphify update`

- Zweck: inkrementelle Aktualisierung, basierend auf Cache; nur geänderte Dateien werden neu verarbeitet.[^3_1][^3_3]
- Bugfix in neueren Versionen: semantische Nodes (INFERRED/AMBIGUOUS) bleiben bei Update erhalten; früher konnten sie verschwinden.[^3_6]


### 7.2 Git‑Hooks

- `graphify hook install`: installiert `post-commit` und `post-checkout` im Git‑Repo, die `graphify update` im Hintergrund ausführen.[^3_6][^3_2][^3_1]
- Fixes in v0.6.3: Hooks laufen detached (`nohup & disown`), blockieren Commit nicht; Logs unter `~/.cache/graphify-rebuild.log`.[^3_6]
- Best Practice:
    - Hooks erst nach stabiler erster Graph‑Version installieren.
    - Falls Build‑Zeit kritisch ist, Hooks nur für bestimmte Branches/Teams aktivieren.

**Agent‑Ziel:**

- Verwende `graphify update` + Hooks ausschließlich nach initialer Validierung des Graphen.
- Verhindere „Graph‑Shrink“ (kleinere Snapshot‑Graphen) durch Verlassen der Standard‑Guardrails; nicht manuell `graph.json` überschreiben.[^3_6][^3_1]

***

## 8. Anpassung an konkret vorhandene Repo‑Struktur

**Heuristik, die Agent vor Erstkonfiguration anwenden soll:**[^3_9][^3_3]

1. Verzeichnisanalyse:
    - Identifiziere Ordner mit hohem Anteil an `.py`, `.js`, `.ts`, `.vue`, `.rs` etc. → Code‑Kandidaten.
    - Identifiziere Ordner mit Build/Artefakten (`dist`, `build`, `node_modules`, `coverage`) → Default‑Exclude.
2. Role‑Tagging:
    - Markiere `backend` / `api` / `server` / `core` als Backend‑Zone.
    - Markiere `frontend` / `web` / `client` / `app` als Frontend‑Zone.
3. Mapping auf Graphify‑Runs:
    - Erzeuge zunächst zwei Out‑Dirs: `graphify-out-backend/`, `graphify-out-frontend/` mit getrennten `graphify`‑Runs.[^3_3]
    - Optional: späterer Merge via `merge-graphs` in einen Projekt‑Wide‑Graph.
4. Copilot‑Instruktionen anpassen:
    - In `.github/copilot-instructions.md` definieren:
        - Backend‑Fragen → `graphify-out-backend/GRAPH_REPORT.md` + `graphify query` auf Backend‑Graph.
        - Frontend‑Fragen → `graphify-out-frontend/GRAPH_REPORT.md`.

**Agent‑Ziel:**

- Verwende Strukturheuristik, um initiale Scopes und `.graphifyignore` repo‑spezifisch zu generieren; vermeide One‑Size‑Fits‑All‑Graph.

***

## 9. Minimaler Setup‑Plan, den Agent autonom umsetzen soll

**In Reihenfolge, ohne Erklärtexte:**

1. Prüfe `graphify` / `graphifyy` Installation, installiere falls nötig, verifiziere Version ≥ 0.6.3.[^3_5][^3_2][^3_6][^3_1]
2. Erkenne Projekt‑Root; lies bestehende `.gitignore`, generiere `.graphifyignore` mit sinnvollen Excludes; validiere gegen Struktur.[^3_9][^3_2][^3_1][^3_3]
3. Installiere Plattform‑Integration (`graphify copilot install`, `graphify vscode install` o.ä.).[^3_8][^3_2][^3_1]
4. Erstelle zwei erste Teil‑Graphs (Backend, Frontend) mit `--no-viz`, Code‑fokussiert.[^3_3]
5. Analysiere `graph.json` + `GRAPH_REPORT.md` für god nodes, Communities, Node‑Counts; passe `.graphifyignore` und ggf. Ordnerstruktur an.[^3_14][^3_12][^3_13][^3_6]
6. Baue Full‑Graph (`graphify .` → `graphify-out/`), inkl. HTML.[^3_2][^3_1][^3_3]
7. Aktualisiere `.github/copilot-instructions.md`, sodass jede Coding‑Session Graph‑Artefakte zuerst nutzt.[^3_1][^3_2]
8. Aktiviere `graphify hook install` + nutze `graphify update` für inkrementelle Aktualisierungen.[^3_6][^3_2][^3_1]

Damit hat der Agent alle nötigen Informationen, um Graphify repo‑spezifisch sauber aufzusetzen und einen logisch balancierten Graphen zu erzeugen, ohne „falsche“ Knoten/Communities durch Noise‑Dateien.
<span style="display:none">[^3_15]</span>

<div align="center">⁂</div>

[^3_1]: https://skillsllm.com/skill/graphify

[^3_2]: https://github.com/safishamsi/graphify

[^3_3]: https://ai-chain.tw/en/blog/gitnexus-graphify-ai-coding-workflow-guide/

[^3_4]: https://www.piwheels.org/project/graphifyy/

[^3_5]: https://newreleases.io/project/github/safishamsi/graphify/release/v0.6.6

[^3_6]: https://newreleases.io/project/github/safishamsi/graphify/release/v0.6.3

[^3_7]: https://newreleases.io/project/github/safishamsi/graphify/release/v0.3.0

[^3_8]: https://www.youtube.com/watch?v=BkHps04qGgc

[^3_9]: https://www.linkedin.com/pulse/claude-code-graphify-stop-paying-same-knowledge-twice-hubmann-0adnf

[^3_10]: https://github.com/safishamsi/graphify/issues/495

[^3_11]: https://www.youtube.com/watch?v=WNru_PFycT8

[^3_12]: https://zenn.dev/michy/articles/0fe69223a7b063

[^3_13]: https://libraries.io/go/github.com%2Ftechinpark%2Fgraphify-go

[^3_14]: https://docs.rs/graphify-analyze/latest/graphify_analyze/

[^3_15]: https://www.reddit.com/r/ClaudeAI/comments/1t18eeh/i_built_graphify_26_days_450k_downloads_40k_stars/

