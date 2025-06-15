"""
System Rebellion Resilience Strategies
--------------------------------------

A comprehensive set of resilience strategies to make the System Rebellion
application more robust and reliable.

Includes:
- Circuit Breaker: Prevents cascading failures from WebSocket connections
- Backpressure Handling: Manages data flow to prevent overwhelming the system
- Autonomous Error Recovery: Self-healing mechanisms for common errors
- Metric Transformation: Real-time data processing with NumPy
"""

from app.core.resilience.circuit_breaker import (
    WebSocketCircuitBreaker,
    get_circuit_breaker,
    reset_all_circuit_breakers,
    reset_circuit_breaker,
    CircuitState
)

from app.core.resilience.backpressure import (
    BackpressureHandler,
    get_backpressure_handler
)

from app.core.resilience.error_recovery import (
    AutonomousErrorRecovery,
    RecoveryAction,
    RecoveryStrategy,
    ErrorSeverity,
    ErrorContext,
    with_error_recovery,
    error_recovery
)

from app.core.resilience.metric_transformer import (
    MetricTransformer,
    get_metric_transformer
)

__all__ = [
    'WebSocketCircuitBreaker',
    'get_circuit_breaker',
    'reset_all_circuit_breakers',
    'reset_circuit_breaker',
    'CircuitState',
    'BackpressureHandler',
    'get_backpressure_handler',
    'AutonomousErrorRecovery',
    'RecoveryAction',
    'RecoveryStrategy',
    'ErrorSeverity',
    'ErrorContext',
    'with_error_recovery',
    'error_recovery',
    'MetricTransformer',
    'get_metric_transformer'
]
