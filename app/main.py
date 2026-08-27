from fastapi import FastAPI

from app.api import router
from app.config import get_settings


# Application factory function to create and configure the FastAPI app
def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Evently API",
        version=settings.app_version,
        summary="Minimal form intake service",
    )
    app.include_router(router)
    return app


# Main application instance
app = create_app()