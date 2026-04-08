# Entry point for uvicorn when using the default "main:app" module name.
# This file re-exports the FastAPI application defined in app/backend/main.py.

from app.backend.main import app  # noqa: F401
