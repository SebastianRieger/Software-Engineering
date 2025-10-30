# Nimrag Backend (scaffold)

Dieses Verzeichnis enthält ein Starter-Scaffold für das FastAPI-Backend des Nimrag Smart Mirror.

Beachten: Python 3.12 verwenden, da media pipe inkompatibel mit 13.

venv und installation requirements mit "activateback" (funktioniert nur auf meinem system!!)

Quick start (lokal, mit Docker):

```sh
# Build & run
docker compose up --build

# Open http://localhost:8000/docs for API docs
```

Entwicklungs-Highlights:
- FastAPI app in `app/main.py`
- API-Router unter `/api/v1`
- Beispielendpoints: `/api/v1/weather`, `/api/v1/system/status`, `/api/v1/led/control`
- Dockerfile + docker-compose
