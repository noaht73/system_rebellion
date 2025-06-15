import time
import logging
import asyncio
from typing import Callable, Any, Optional, Dict, Union
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"  # Normal operation - requests flow through
    OPEN = "OPEN"      # Circuit is open - requests are blocked
    HALF_OPEN = "HALF_OPEN"  # Testing if the service is back online


class WebSocketCircuitBreaker:
    """
    Sir Hawkington's Distinguished Circuit Breaker
    
    Prevents cascading failures when WebSocket connections fail repeatedly.
    Implements exponential backoff and automatic recovery.
    """
    
    def __init__(
        self, 
        name: str = "default",
        max_failures: int = 5, 
        reset_timeout: int = 60,
        half_open_max_trials: int = 3,
        exponential_backoff_factor: float = 2.0
    ):
        self.name = name
        self.failures = 0
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.half_open_max_trials = half_open_max_trials
        self.half_open_trials = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.exponential_backoff_factor = exponential_backoff_factor
        self.current_backoff = 1  # Initial backoff in seconds
        
        logger.info(f"Circuit Breaker '{name}' initialized with max_failures={max_failures}, reset_timeout={reset_timeout}s")
    
    def _calculate_backoff(self) -> float:
        """Calculate exponential backoff time based on failure count"""
        backoff = min(
            self.reset_timeout,  # Cap at reset_timeout
            self.current_backoff * (self.exponential_backoff_factor ** min(self.failures, 8))  # Prevent overflow
        )
        return backoff
    
    def get_wait_time(self) -> float:
        """Get the time to wait before next connection attempt"""
        if self.state == CircuitState.OPEN and self.last_failure_time:
            backoff = self._calculate_backoff()
            time_since_failure = time.time() - self.last_failure_time
            wait_time = max(0, backoff - time_since_failure)
            return wait_time
        return 0
    
    def record_success(self) -> None:
        """Record a successful connection"""
        prev_state = self.state
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_trials += 1
            
            if self.half_open_trials >= self.half_open_max_trials:
                # After enough successful trials in HALF_OPEN, we fully close the circuit
                self.reset()
                logger.info(f"Circuit Breaker '{self.name}' state: {prev_state.value} → {self.state.value} (after {self.half_open_trials} successful trials)")
        
        # If we're already CLOSED, just reset the failure count
        if self.state == CircuitState.CLOSED:
            self.failures = 0
            self.current_backoff = 1
    
    def record_failure(self) -> None:
        """Record a connection failure"""
        self.failures += 1
        self.last_failure_time = time.time()
        prev_state = self.state
        
        if self.state == CircuitState.HALF_OPEN:
            # If we fail during HALF_OPEN state, go back to OPEN with increased backoff
            self.state = CircuitState.OPEN
            self.half_open_trials = 0
            self.current_backoff *= self.exponential_backoff_factor
            logger.warning(f"Circuit Breaker '{self.name}' state: {prev_state.value} → {self.state.value} (failed during half-open trial)")
            
        elif self.failures >= self.max_failures and self.state == CircuitState.CLOSED:
            # Trip the circuit breaker after max failures
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit Breaker '{self.name}' state: {prev_state.value} → {self.state.value} (reached {self.failures} failures)")
    
    def reset(self) -> None:
        """Reset the circuit breaker to closed state"""
        prev_state = self.state
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.half_open_trials = 0
        self.current_backoff = 1
        logger.info(f"Circuit Breaker '{self.name}' state: {prev_state.value} → {self.state.value} (manual reset)")
    
    def can_attempt_connection(self) -> bool:
        """Check if a connection attempt is allowed"""
        if self.state == CircuitState.CLOSED:
            return True
            
        if self.state == CircuitState.OPEN:
            # Check if reset timeout has passed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self._calculate_backoff():
                # Transition to HALF_OPEN to test if the service is back
                self.state = CircuitState.HALF_OPEN
                self.half_open_trials = 0
                logger.info(f"Circuit Breaker '{self.name}' state: OPEN → HALF_OPEN (timeout expired, allowing test connection)")
                return True
            return False
            
        # In HALF_OPEN state, we allow connection attempts
        return True
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with circuit breaker protection
        
        Args:
            func: The async function to execute
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            ConnectionError: If the circuit is open
            Exception: Any exception raised by the function
        """
        if not self.can_attempt_connection():
            wait_time = self.get_wait_time()
            raise ConnectionError(
                f"Circuit '{self.name}' is open, back the fuck off for {wait_time:.2f} more seconds"
            )
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise


# Global registry of circuit breakers
_circuit_breakers: Dict[str, WebSocketCircuitBreaker] = {}

def get_circuit_breaker(name: str = "default", **kwargs) -> WebSocketCircuitBreaker:
    """Get or create a circuit breaker by name"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = WebSocketCircuitBreaker(name=name, **kwargs)
    return _circuit_breakers[name]

def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers (useful for testing)"""
    for breaker in _circuit_breakers.values():
        breaker.reset()


def reset_circuit_breaker(name: str = "default") -> None:
    """Reset a specific circuit breaker by name"""
    if name in _circuit_breakers:
        _circuit_breakers[name].reset()
    else:
        logger.warning(f"Circuit breaker '{name}' not found")
        raise ValueError(f"Circuit breaker '{name}' not found")