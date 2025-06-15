from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from app.websockets import WebSocketManager, websocket_manager
from jose import jwt, JWTError
from app.api.websocket_auth import authenticate_websocket
from app.services.metrics.simplified_metrics_service import SimplifiedMetricsService
from app.core.config import settings
from app.models.user import User
from app.core.database import get_db
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
import socket
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Initialize resilience components
metrics_circuit_breaker = get_circuit_breaker(
    name="simplified_metrics_websocket", 
    max_failures=3,
    reset_timeout=30,
    exponential_backoff_factor=1.5
)

metrics_backpressure = get_backpressure_handler(
    name="simplified_metrics_backpressure",
    max_buffer_size=100,
    sampling_strategy="latest"
)

# Register recovery strategies
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

# For metrics errors - return ERROR state, not fake data
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

async def get_system_info():
    """
    Get basic system information for the client
    """
    try:
        # Get the metrics service instance
        metrics_service = await SimplifiedMetricsService.get_instance()
        
        # Get all metrics to extract system info
        metrics = await metrics_service.get_metrics()
        
        # Extract system info from the metrics
        system_info = metrics.get('system_info', {})
        
        # Add hostname if not present
        if 'hostname' not in system_info:
            system_info['hostname'] = socket.gethostname()
            
        return system_info
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {
            "hostname": socket.gethostname(),
            "error": str(e)
        }

router = APIRouter()

@router.websocket("/ws/system-metrics")
async def system_metrics_socket(websocket: WebSocket):
    """
    Sir Hawkington's Simplified System Metrics WebSocket
    
    Robust authentication with connection-first flow for System Rebellion!
    """
    # Generate a unique client ID
    client_id = f"client_{id(websocket)}"
    connection_active = False
    db = None
    
    try:
        # Accept the connection FIRST (website connection before auth)
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for {client_id}")
        print(f"WebSocket connection accepted for {client_id}")
        connection_active = True
        
        # Register the connection with the WebSocket manager
        await websocket_manager.connect(websocket)
        
        # Send connection established message and request authentication
        await websocket.send_json({
            "type": "connection_established",
            "message": "Sir Hawkington welcomes you! Please provide authentication.",
            "client_id": client_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        print(f"Sent connection established message to {client_id}")
        
        # Wait for authentication message from frontend
        try:
            logger.info(f"Waiting for auth message from {client_id}...")
            auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
            logger.info(f"Received auth message from {client_id}: {auth_message}")
            print(f"Received auth message from {client_id}: {auth_message}")
            
            if auth_message.get("type") != "auth":
                logger.error(f"Expected auth message, got: {auth_message.get('type', 'unknown')}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Expected authentication message",
                    "code": "auth_required"
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            # Extract token from auth message
            token = auth_message.get("token", "")
            logger.info(f"Extracted token from {client_id}: {token[:20]}..." if token else f"No token in message from {client_id}")
            print(f"Extracted token from {client_id}: {token[:20]}..." if token else f"No token in message from {client_id}")
            
            if not token:
                logger.error(f"No token provided in auth message from {client_id}")
                await websocket.send_json({
                    "type": "error",
                    "message": "No authentication token provided",
                    "code": "no_token"
                })
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            
            # Remove Bearer prefix if present
            token = token.replace("Bearer ", "").strip()
            logger.info(f"Cleaned token from {client_id}: {token[:20]}...")
            print(f"Cleaned token from {client_id}: {token[:20]}...")
            
            # Store token in query params for authenticate_websocket function
            websocket.query_params = {"token": token}
            logger.info(f"Token stored in query params for {client_id}")
            print(f"Token stored in query params for {client_id}")
            
        except asyncio.TimeoutError:
            logger.error(f"Authentication timeout for {client_id}")
            await websocket.send_json({
                "type": "error",
                "message": "Authentication timeout",
                "code": "auth_timeout"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        except Exception as e:
            logger.error(f"Error receiving auth message from {client_id}: {str(e)} - Type: {type(e).__name__}")
            logger.error(f"Full exception details: {repr(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Authentication error",
                "code": "auth_error"
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # Now authenticate the user (using existing robust system)
        user = await authenticate_websocket(websocket)
        if not user:
            logger.warning(f"Authentication failed for {client_id}")
            await websocket.send_json({
                "type": "auth_failed",
                "message": "Authentication required for System Rebellion access",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        logger.info(f"WebSocket authenticated for user {user.username} ({client_id})")
        print(f"WebSocket authenticated for user {user.username} ({client_id})")
        
        # Get database session
        db = next(get_db())
        print(f"Got database session for {client_id}")
        
        # Send initial system info
        system_info = await get_system_info()
        await websocket.send_json({
            "type": "system_info",
            "data": system_info,
            "message": "Sir Hawkington welcomes you to the System Metrics WebSocket!"
        })
        print(f"Sent system info to {client_id}")
        
        # Initialize metrics service
        metrics_service = await SimplifiedMetricsService.get_instance()
        print(f"Got metrics service instance for {client_id}")
        
        # Set default update interval
        update_interval = 1.0  # seconds
        print(f"Set update interval to {update_interval} seconds")
        
        # Main WebSocket loop
        while True:
            try:
                # Record the start time of this loop iteration
                loop_start_time = time.time()
                print(f"Starting loop iteration for {client_id}")
                
                # Check if circuit breaker is open
                if metrics_circuit_breaker.is_open():
                    wait_time = metrics_circuit_breaker.get_wait_time()
                    logger.warning(f"Circuit breaker open for {client_id}, waiting {wait_time}s")
                    await websocket.send_json({
                        "type": "circuit_breaker",
                        "status": "open",
                        "message": f"Too many errors, service cooling down for {wait_time}s",
                        "retry_after": wait_time
                    })
                    await asyncio.sleep(min(wait_time, update_interval))
                    continue
                
                # Get metrics with backpressure handling
                metrics = await metrics_backpressure.handle(
                    metrics_service.get_metrics
                )
                print(f"Got metrics for {client_id}")
                
                # If metrics collection was successful, reset circuit breaker
                metrics_circuit_breaker.record_success()
                print(f"Metrics collection successful for {client_id}, resetting circuit breaker")
                
                # Send metrics to client
                await websocket.send_json({
                    "type": "metrics_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": metrics
                })
                print(f"Sent metrics to {client_id}")
                
                # Check for client messages with a timeout
                try:
                    # Wait for a message with a timeout shorter than the update interval
                    message_timeout = min(0.5, update_interval / 2)
                    message = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=message_timeout
                    )
                    print(f"Received message from {client_id}: {message}")
                    
                    # Process client message
                    try:
                        msg = json.loads(message)
                        msg_type = msg.get("type", "")
                        msg_data = msg.get("data", {})
                        
                        if msg_type == "ping":
                            await websocket.send_json({
                                "type": "pong", 
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                        elif msg_type == "set_interval":
                            # Client requesting to change the update interval (1-10 seconds)
                            new_interval = max(1.0, min(10.0, float(msg_data.get("interval", 1.0))))
                            update_interval = new_interval
                            logger.info(f"Client {client_id} set update interval to {update_interval}s")
                            
                            await websocket.send_json({
                                "type": "interval_update", 
                                "interval": update_interval,
                                "message": f"Update interval set to {update_interval} seconds"
                            })
                        elif msg_type == "request_system_info":
                            # Send system info on demand
                            system_info = await get_system_info()
                            await websocket.send_json({
                                "type": "system_info",
                                "data": system_info
                            })
                        elif msg_type == "reset_circuit_breaker":
                            # Reset all circuit breakers
                            metrics_circuit_breaker.reset()  # Reset the main circuit breaker
                            
                            # Also reset individual service circuit breakers
                            metrics_service = await SimplifiedMetricsService.get_instance()
                            await metrics_service.reset_circuit_breakers()
                            
                            await websocket.send_json({
                                "type": "circuit_breaker_reset",
                                "message": "All circuit breakers have been reset"
                            })
                    except json.JSONDecodeError:
                        logger.warning(f"Received non-JSON message from client {client_id}")
                    except Exception as e:
                        logger.error(f"Error processing message from client {client_id}: {str(e)}")
                except asyncio.TimeoutError:
                    # No message received, continue with the loop
                    pass
                
                # Calculate how long to sleep to maintain the desired update interval
                elapsed = time.time() - loop_start_time
                sleep_time = max(0.1, update_interval - elapsed)
                print(f"Sleeping for {sleep_time} seconds to maintain update interval for {client_id}")
                await asyncio.sleep(sleep_time)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket for {client_id} disconnected by client")
                print(f"WebSocket for {client_id} disconnected by client")
                break
                
            except Exception as e:
                logger.error(f"Unhandled WebSocket error: {str(e)}")
                print(f"Unhandled WebSocket error: {str(e)}")
                try:
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Sir Hawkington encountered an error: {str(e)}",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                except:
                    pass
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket for {client_id} disconnected during setup")
        print(f"WebSocket for {client_id} disconnected during setup")
        metrics_circuit_breaker.record_failure()
    except Exception as e:
        logger.error(f"WebSocket error during setup for {client_id}: {str(e)}", exc_info=True)
        print(f"WebSocket error during setup for {client_id}: {str(e)}")
        metrics_circuit_breaker.record_failure()
        # Try to send error message if possible
        try:
            await websocket.send_json({
                "type": "connection_error",
                "message": f"Sir Hawkington regrets to inform you of a connection error: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_after": metrics_circuit_breaker.get_wait_time()
            })
        except:
            pass
    finally:
        # Clean up connection if it was established
        if connection_active:
            await websocket_manager.disconnect(websocket)
            logger.info(f"WebSocket disconnected and cleaned for {client_id}")
            print(f"WebSocket disconnected and cleaned for {client_id}")
        
        # Close database session if it was opened
        if db:
            db.close()
            logger.debug(f"Database session closed for {client_id}")
            print(f"Database session closed for {client_id}")