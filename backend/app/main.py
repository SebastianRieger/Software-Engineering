from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from .api.v1 import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Nimrag Backend", version="0.1.0")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

        @app.get("/", response_class=HTMLResponse)
        async def root_ui():
                """Simple HTML page to verify the backend is running."""
                return """
                <!doctype html>
                <html>
                    <head>
                        <meta charset=\"utf-8\" />
                        <title>Nimrag Backend</title>
                        <style>
                            body { font-family: system-ui, -apple-system, Roboto, 'Segoe UI', Arial; padding: 2rem; }
                            .card { max-width: 640px; margin: 2rem auto; padding: 1.5rem; border: 1px solid #e1e1e1; border-radius: 8px; }
                            a.button { display: inline-block; padding: 0.5rem 1rem; background: #0066ff; color: white; text-decoration: none; border-radius: 4px; }
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <h1>Nimrag Backend</h1>
                            <p>Status: <strong>running</strong></p>
                            <p>Quick links:</p>
                            <ul>
                                <li><a class="button" href="/healthz">/healthz</a></li>
                                <li><a class="button" href="/api/v1">/api/v1 (API root)</a></li>
                            </ul>
                            <p>Run the FastAPI server with <code>uvicorn app.main:app --reload</code> and open this page at <code>http://localhost:8000/</code>.</p>
                        </div>
                    </body>
                </html>
                """

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
