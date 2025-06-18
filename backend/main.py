from fastapi import FastAPI, Response
from contextlib import asynccontextmanager
import logging
import secrets
import uvicorn

from app.core.database import init_models, log_registered_models
from app.core.middleware import setup_middleware
from app.api import router as api_router
from app.api import simplified_websocket_routes
from app.services.metrics.simplified_metrics_service import initialize_metrics_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import all models to ensure they are registered with SQLAlchemy
from app.models import *  # noqa

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting up System Rebellion application...")
    try:
        # Log registered models for debugging
        log_registered_models()
        # Initialize models (create tables)
        await init_models()
        logger.info("Database initialization successful")

        # Initialize WebSocket resilience components
        simplified_websocket_routes.initialize_resilience_components()

        # Force initialization of the metrics service to ensure it's ready
        await initialize_metrics_service()
    except Exception as e:
        logger.error(f"Failed to initialize database during startup: {str(e)}")
        # In a real app, you might want to exit or handle this more gracefully
        # For now, we let it raise, which will stop the server from starting.
        raise
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down System Rebellion application...")

def create_application() -> FastAPI:
    app = FastAPI(
        title="System Rebellion",
        description="Quantum Optimization Platform",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # Setup all middleware (CORS, etc.)
    setup_middleware(app)

    # CSRF token endpoint - kept here for stability until moved to auth router
    @app.get("/api/auth/csrf_token")
    async def get_csrf_token(response: Response):
        """Generate a new CSRF token and set it as a cookie and in headers"""
        csrf_token = secrets.token_urlsafe(32)
        response.set_cookie(
            key="csrftoken",
            value=csrf_token,
            httponly=False,
            secure=False, # Set to True in production with HTTPS
            samesite="lax",
            max_age=3600, # 1 hour
            path="/"
        )
        response.headers["X-CSRFToken"] = csrf_token
        return {"csrf_token": csrf_token}

    # Include the main API router
    # This single line replaces all the previous app.include_router calls
    app.include_router(api_router, prefix="/api")

    # Include the WebSocket router at the root level
    app.include_router(simplified_websocket_routes.router)

    return app

# Create the app instance
app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", # Changed to 0.0.0.0 to be accessible
        port=8000,
        reload=True,
        log_level="debug" # Changed to info for cleaner logs, can be debug if needed
    )