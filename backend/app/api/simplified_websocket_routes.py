from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from app.websockets import WebSocketManager, websocket_manager
from jose import jwt, JWTError
from app.api.websocket_auth import get_user_from_token
from app.services.metrics.simplified_metrics_service import SimplifiedMetricsService
from app.core.config import settings
from app.models.user import User
from app.core.resilience import (
    WebSocketCircuitBreaker, 
    get_circuit_breaker,
    BackpressureHandler,
    get_backpressure_handler,
    RecoveryAction,
    RecoveryStrategy,
    error_recovery
)
import asyncio
import json
import logging
import socket
import platform
import psutil
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.api import deps

logger = logging.getLogger('simplified_metrics_websocket')

# Declare globals for resilience components, to be initialized on app startup
metrics_circuit_breaker: Optional[WebSocketCircuitBreaker] = None
metrics_backpressure: Optional[BackpressureHandler] = None

def initialize_resilience_components():
    """Initializes resilience components for the WebSocket service."""
    global circuit_breaker, backpressure_handler
    
    circuit_breaker = get_circuit_breaker(
        name="simplified_metrics_websocket", 
        max_failures=3,
        reset_timeout=30,
        exponential_backoff_factor=1.5
    )

    backpressure_handler = get_backpressure_handler(
        name="simplified_metrics_backpressure",
        max_buffer_size=100,
        sampling_strategy="latest"
    )

    error_recovery.register_strategy(
        component="websocket",
        error_type="WebSocketDisconnect",
        recovery_action=RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_retries=3,
            retry_delay=2.0,
            exponential_backoff=True
        )
    )

    error_recovery.register_strategy(
        component="websocket",
        error_type="ConnectionError",
        recovery_action=RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            max_retries=5,
            retry_delay=1.0,
            exponential_backoff=True
        )
    )

    error_recovery.register_strategy(
        component="metrics",
        error_type="*",  # Any error in metrics collection
        recovery_action=RecoveryAction(
            strategy=RecoveryStrategy.FALLBACK,
            fallback_function=lambda ctx, *args, **kwargs: {
                "error": True,
                "error_type": "metrics_collection_failed",
                "message": f"Failed to collect metrics: {ctx.get('error', 'Unknown error')}",
                "timestamp": datetime.now().isoformat(),
                "retry_available": True
            }
        )
    )

async def get_system_info() -> Dict[str, Any]:
    """
    Retrieve basic system information for the client.
    """
    try:
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True),
            "total_memory": psutil.virtual_memory().total,
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "python_version": platform.python_version()
        }
    except Exception as error:
        logger.error(f"Error retrieving system information: {error}")
        return {
            "error": True,
            "message": "Failed to retrieve system information"
        }

router = APIRouter()

@router.websocket("/ws/system-metrics/{client_id}")
async def system_metrics_socket(
    websocket: WebSocket,
    client_id: str,
    current_user: User = Depends(get_user_from_token)
):
    """
    Sir Hawkington's Simplified System Metrics WebSocket

    Authenticates via token in query parameter and streams system metrics.
    """
    if not current_user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    await websocket_manager.connect(websocket)
    logger.info(f"Accepted WebSocket connection for user '{current_user.username}' with client ID '{client_id}'")

    try:
        # Send connection established message
        await websocket.send_json({
            "type": "connection_established",
            "message": f"Welcome, {current_user.username}! You are authenticated.",
            "client_id": client_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Send initial system info
        system_info = await get_system_info()
        await websocket.send_json({
            "type": "system_info",
            "data": system_info
        })

        metrics_service = await SimplifiedMetricsService.get_instance()
        update_interval_seconds = 1.0

        while True:
            loop_start_time = time.time()

            # Ensure resilience components are initialized
            if not metrics_circuit_breaker or not metrics_backpressure:
                logger.error("Resilience components not initialized.")
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                break

            # Check circuit breaker
            if not metrics_circuit_breaker.can_attempt_connection():
                wait_duration = metrics_circuit_breaker.get_wait_time()
                logger.warning(f"Circuit breaker open for {client_id}, waiting {wait_duration:.2f} seconds.")
                await websocket.send_json({
                    "type": "circuit_breaker",
                    "payload": {
                        "status": "open",
                        "message": f"Service cooling down for {wait_duration:.2f} seconds",
                        "retry_after": wait_duration
                    }
                })
                await asyncio.sleep(min(wait_duration, update_interval_seconds))
                continue

            # Retrieve and send metrics
            try:
                metrics_data = await metrics_service.get_metrics()
                await websocket.send_json(metrics_data)
                metrics_circuit_breaker.record_success()
            except Exception as error:
                logger.error(f"Error retrieving metrics for {client_id}: {error}", exc_info=True)
                metrics_circuit_breaker.record_failure()

            # Handle incoming pings
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                message_data = json.loads(message)
                if message_data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass  # No incoming message
            except (json.JSONDecodeError, WebSocketDisconnect):
                break

            # Maintain update interval
            elapsed_time = time.time() - loop_start_time
            await asyncio.sleep(max(0, update_interval_seconds - elapsed_time))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user '{current_user.username}' with client ID '{client_id}'")
    except Exception as error:
        logger.error(f"Unexpected error in WebSocket for {client_id}: {error}", exc_info=True)
    finally:
        await websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket cleaned up for client ID '{client_id}'")
