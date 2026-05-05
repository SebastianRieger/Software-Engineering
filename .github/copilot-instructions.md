## graphify

For any question about architecture, structure, ownership, or where code should be changed, start
with the Graphify report that matches the scope before searching raw files.

Scope selection:
- Backend or Python/FastAPI/gesture/calibration/config/runtime work: read `Backend/graphify-out/GRAPH_REPORT.md` first.
- Frontend or Vue/UI/layout/widget/realtime-client work: read `Frontend/nimrag-frontend/graphify-out/GRAPH_REPORT.md` first.
- Cross-cutting or unclear scope: read both scoped reports first; use `graphify-out/GRAPH_REPORT.md` only as a coarse combined inventory.

Working rules:
- Prefer god nodes, surprising connections, and community structure to choose the first files to open.
- Prefer `graphify path` first when you already know concrete symbols or boundaries.
- Use `graphify explain` only after checking that the symbol name is distinctive; near-name matches can drift onto siblings like error types.
- Use free-form `graphify query` only after you have picked anchor terms from the report; otherwise fuzzy starts can drift onto nearby symbols.
- Only skip the graph-first step when the user already anchored the task to a specific file, symbol, or failing test.

Freshness rules:
- For code-only refreshes, run `scripts/update_graphify_graphs.sh` from the repo root.
- If `.graphifyignore` changed, run `scripts/update_graphify_graphs.sh --clean`.
- The installed git hooks keep the repo-root graph current after commits, but the scoped backend and frontend graphs should still be refreshed with the script after larger refactors.
- For richer semantic rebuilds after docs/images/architecture-note changes, use `/graphify .`, `/graphify Backend`, or `/graphify Frontend/nimrag-frontend` in Copilot Chat.

Quality note:
- Community IDs may change after reclustering. Do not hard-code your own permanent community names in answers unless they are present in the current report.
