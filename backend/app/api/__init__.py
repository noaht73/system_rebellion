from fastapi import APIRouter

# Import all endpoint routers
from app.api.endpoints import (
    alerts, auth, auto_tuner, configuration, health, optimization, system_logs, users
)
from app.api import simplified_websocket_routes

# Create the main API router, which will be included by the FastAPI app
router = APIRouter()

# Include all endpoint routers with their respective prefixes and tags
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(optimization.router, prefix="/optimization-profiles", tags=["Optimization"])
router.include_router(configuration.router, prefix="/system-configurations", tags=["Configuration"])
router.include_router(alerts.router, prefix="/system-alerts", tags=["Alerts"])
router.include_router(auto_tuner.router, prefix="/auto-tuner", tags=["Auto-Tuner"])
router.include_router(system_logs.router, prefix="/system-logs", tags=["System Logs"])
router.include_router(health.router, prefix="/health-check", tags=["Health"])

# Include other API-level routes
router.include_router(simplified_websocket_routes.router, prefix="/metrics", tags=["Metrics"])

