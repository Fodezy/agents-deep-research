import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

class ObservabilityHandler:
    """
    In-memory observability for validation and repair metrics.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, Dict[frozenset, int]] = defaultdict(lambda: defaultdict(int))
        self._timers: Dict[str, float] = {}
        self._failures: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5))

    def increment(self, counter_name: str, tags: Optional[Dict[str, Any]] = None) -> None:
        key = frozenset((tags or {}).items())
        with self._lock:
            self._counters[counter_name][key] += 1

    def record_time(self, timer_name: str, duration_ms: float) -> None:
        with self._lock:
            self._timers[timer_name] = duration_ms

    def log_validation_failure(self, agent_name: str, error_type: str, details: Dict[str, Any]) -> None:
        record = {
            "timestamp": time.time(),
            "error_type": error_type,
            "details": details,
        }
        with self._lock:
            self._failures[agent_name].append(record)

    def get_metrics_summary(self) -> Dict[str, Any]:
        with self._lock:
            # flatten counters: sum across all tag-keys
            counters = {name: sum(tag_map.values()) for name, tag_map in self._counters.items()}
            timers   = dict(self._timers)
            failures = {agent: list(deque_obj) for agent, deque_obj in self._failures.items()}
        return {
            "counters": counters,
            "timers_ms": timers,
            "failures": failures,
        }

    def reset_metrics(self) -> None:
        with self._lock:
            self._counters.clear()
            self._timers.clear()
            self._failures.clear()
