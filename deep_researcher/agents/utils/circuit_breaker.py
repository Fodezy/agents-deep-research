"""
Circuit breaker pattern for ValidationWrapper.
Prevents validation from impacting system stability when failure rates are high.
"""

import time
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
from collections import deque, defaultdict

from .observability import ObservabilityHandler


class CircuitState(Enum):
    """States of the circuit breaker"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Validation disabled due to failures
    HALF_OPEN = "half_open"  # Testing if validation has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 300  # Seconds before attempting recovery
    success_threshold: int = 3   # Successes needed to close from half-open
    window_size: int = 10       # Size of sliding window for failure tracking
    min_requests: int = 5       # Minimum requests before considering failure rate


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker monitoring"""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    total_requests: int = 0
    total_failures: int = 0
    total_bypasses: int = 0


class ValidationCircuitBreaker:
    """
    Circuit breaker for validation operations.
    Automatically disables validation when failure rates exceed thresholds.
    """
    
    def __init__(self, 
                 agent_name: str,
                 config: CircuitBreakerConfig = None,
                 observability: ObservabilityHandler = None):
        self.agent_name = agent_name
        self.config = config or CircuitBreakerConfig()
        self.observability = observability or ObservabilityHandler()
        
        self.metrics = CircuitMetrics()
        self.failure_window = deque(maxlen=self.config.window_size)
        self._last_half_open_attempt = 0
    
    def should_allow_validation(self) -> bool:
        """
        Determine if validation should be allowed based on circuit state.
        
        Returns:
            bool: True if validation should proceed, False to bypass
        """
        current_time = time.time()
        
        if self.metrics.state == CircuitState.CLOSED:
            # Normal operation - allow validation
            return True
        
        elif self.metrics.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if (current_time - self.metrics.last_failure_time) >= self.config.recovery_timeout:
                self._transition_to_half_open()
                return True
            else:
                # Still in failure state - bypass validation
                self._record_bypass()
                return False
        
        elif self.metrics.state == CircuitState.HALF_OPEN:
            # Allow limited testing
            return True
        
        return False
    
    def record_success(self):
        """Record a successful validation operation"""
        self.metrics.total_requests += 1
        
        if self.metrics.state == CircuitState.HALF_OPEN:
            self.metrics.success_count += 1
            if self.metrics.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        
        # Remove old failures from sliding window
        self._clean_failure_window()
        
        self.observability.increment(f'circuit_breaker.{self.agent_name}.success')
    
    def record_failure(self, error: str = None):
        """Record a failed validation operation"""
        current_time = time.time()
        
        self.metrics.total_requests += 1
        self.metrics.total_failures += 1
        self.metrics.failure_count += 1
        self.metrics.last_failure_time = current_time
        
        # Add to sliding window
        self.failure_window.append(current_time)
        
        # Check if we should open the circuit
        if (self.metrics.state == CircuitState.CLOSED and 
            self._should_open_circuit()):
            self._transition_to_open()
        
        elif self.metrics.state == CircuitState.HALF_OPEN:
            # Failed during recovery - back to open
            self._transition_to_open()
        
        self.observability.increment(f'circuit_breaker.{self.agent_name}.failure')
        if error:
            self.observability.increment(f'circuit_breaker.{self.agent_name}.failure.{self._classify_error(error)}')
    
    def get_status(self) -> Dict:
        """Get current circuit breaker status"""
        current_time = time.time()
        return {
            "agent_name": self.agent_name,
            "state": self.metrics.state.value,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "total_requests": self.metrics.total_requests,
            "total_failures": self.metrics.total_failures,
            "total_bypasses": self.metrics.total_bypasses,
            "failure_rate": self._calculate_failure_rate(),
            "time_since_last_failure": (
                current_time - self.metrics.last_failure_time 
                if self.metrics.last_failure_time else None
            ),
            "time_until_recovery": (
                max(0, self.config.recovery_timeout - (current_time - self.metrics.last_failure_time))
                if self.metrics.state == CircuitState.OPEN and self.metrics.last_failure_time else 0
            ),
            "window_failures": len(self.failure_window)
        }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        self.metrics = CircuitMetrics()
        self.failure_window.clear()
        self._last_half_open_attempt = 0
        self.observability.increment(f'circuit_breaker.{self.agent_name}.reset')
    
    def force_open(self, reason: str = "Manual override"):
        """Force circuit breaker to open state"""
        self._transition_to_open()
        self.observability.increment(f'circuit_breaker.{self.agent_name}.force_open')
        print(f"[CircuitBreaker] {self.agent_name} forced open: {reason}")
    
    def force_closed(self, reason: str = "Manual override"):
        """Force circuit breaker to closed state"""
        self._transition_to_closed()
        self.observability.increment(f'circuit_breaker.{self.agent_name}.force_closed')
        print(f"[CircuitBreaker] {self.agent_name} forced closed: {reason}")
    
    def _should_open_circuit(self) -> bool:
        """Determine if circuit should be opened based on failure rate"""
        # Need minimum requests to make a decision
        if self.metrics.total_requests < self.config.min_requests:
            return False
        
        # Check sliding window failure rate
        recent_failures = len(self.failure_window)
        if recent_failures >= self.config.failure_threshold:
            return True
        
        # Check overall failure rate if we have enough data
        if (self.metrics.total_requests >= self.config.window_size and
            self.metrics.failure_count >= self.config.failure_threshold):
            failure_rate = self._calculate_failure_rate()
            return failure_rate >= 0.5  # 50% failure rate threshold
        
        return False
    
    def _calculate_failure_rate(self) -> float:
        """Calculate current failure rate"""
        if self.metrics.total_requests == 0:
            return 0.0
        return self.metrics.total_failures / self.metrics.total_requests
    
    def _transition_to_open(self):
        """Transition to OPEN state"""
        if self.metrics.state != CircuitState.OPEN:
            print(f"[CircuitBreaker] {self.agent_name} opening - validation disabled")
            self.metrics.state = CircuitState.OPEN
            self.metrics.last_state_change = time.time()
            self.observability.increment(f'circuit_breaker.{self.agent_name}.state.open')
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        print(f"[CircuitBreaker] {self.agent_name} half-open - testing recovery")
        self.metrics.state = CircuitState.HALF_OPEN
        self.metrics.success_count = 0
        self.metrics.failure_count = 0
        self.metrics.last_state_change = time.time()
        self._last_half_open_attempt = time.time()
        self.observability.increment(f'circuit_breaker.{self.agent_name}.state.half_open')
    
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        print(f"[CircuitBreaker] {self.agent_name} closing - validation restored")
        self.metrics.state = CircuitState.CLOSED
        self.metrics.success_count = 0
        self.metrics.failure_count = 0
        self.metrics.last_state_change = time.time()
        self.failure_window.clear()
        self.observability.increment(f'circuit_breaker.{self.agent_name}.state.closed')
    
    def _clean_failure_window(self):
        """Remove old entries from failure window"""
        current_time = time.time()
        window_duration = 300  # 5 minutes
        
        while (self.failure_window and 
               current_time - self.failure_window[0] > window_duration):
            self.failure_window.popleft()
    
    def _record_bypass(self):
        """Record that validation was bypassed due to circuit breaker"""
        self.metrics.total_bypasses += 1
        self.observability.increment(f'circuit_breaker.{self.agent_name}.bypass')
    
    def _classify_error(self, error: str) -> str:
        """Classify error type for metrics"""
        error_lower = error.lower()
        if 'timeout' in error_lower:
            return 'timeout'
        elif 'json' in error_lower or 'parse' in error_lower:
            return 'parse_error'
        elif 'schema' in error_lower or 'validation' in error_lower:
            return 'validation_error'
        elif 'repair' in error_lower:
            return 'repair_failed'
        else:
            return 'unknown'


class CircuitBreakerRegistry:
    """
    Registry for managing circuit breakers across multiple agents.
    Provides centralized monitoring and control.
    """
    
    def __init__(self, observability: ObservabilityHandler = None):
        self.observability = observability or ObservabilityHandler()
        self._breakers: Dict[str, ValidationCircuitBreaker] = {}
        self._global_config = CircuitBreakerConfig()
    
    def get_breaker(self, agent_name: str, 
                   config: CircuitBreakerConfig = None) -> ValidationCircuitBreaker:
        """Get or create circuit breaker for agent"""
        if agent_name not in self._breakers:
            self._breakers[agent_name] = ValidationCircuitBreaker(
                agent_name=agent_name,
                config=config or self._global_config,
                observability=self.observability
            )
        return self._breakers[agent_name]
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get status of all circuit breakers"""
        return {
            name: breaker.get_status() 
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self._breakers.values():
            breaker.reset()
        self.observability.increment('circuit_breaker.registry.reset_all')
    
    def force_open_all(self, reason: str = "Emergency shutdown"):
        """Force all circuit breakers to open"""
        for breaker in self._breakers.values():
            breaker.force_open(reason)
        self.observability.increment('circuit_breaker.registry.force_open_all')
    
    def force_closed_all(self, reason: str = "Manual recovery"):
        """Force all circuit breakers to closed"""
        for breaker in self._breakers.values():
            breaker.force_closed(reason)
        self.observability.increment('circuit_breaker.registry.force_closed_all')
    
    def get_global_health(self) -> Dict:
        """Get overall health status of validation system"""
        statuses = self.get_all_status()
        
        total_agents = len(statuses)
        open_agents = sum(1 for status in statuses.values() if status['state'] == 'open')
        half_open_agents = sum(1 for status in statuses.values() if status['state'] == 'half_open')
        
        overall_failure_rate = (
            sum(status['total_failures'] for status in statuses.values()) /
            max(1, sum(status['total_requests'] for status in statuses.values()))
        )
        
        return {
            "total_agents": total_agents,
            "healthy_agents": total_agents - open_agents - half_open_agents,
            "degraded_agents": half_open_agents,
            "failed_agents": open_agents,
            "overall_failure_rate": overall_failure_rate,
            "validation_available": open_agents < total_agents,
            "system_health": (
                "healthy" if open_agents == 0 else
                "degraded" if open_agents < total_agents / 2 else
                "critical"
            )
        }


# Global registry instance
_circuit_breaker_registry = None

def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry"""
    global _circuit_breaker_registry
    if _circuit_breaker_registry is None:
        _circuit_breaker_registry = CircuitBreakerRegistry()
    return _circuit_breaker_registry