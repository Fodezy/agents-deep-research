"""
Production metrics and observability for ValidationWrapper system.
Provides comprehensive monitoring, logging, and alerting capabilities.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import logging
from threading import Lock

# Setup structured logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationMetric:
    """Individual validation metric entry"""
    timestamp: datetime
    agent_name: str
    validation_result: str  # success, repair, fallback, error
    processing_time_ms: float
    error_type: Optional[str] = None
    repair_strategy: Optional[str] = None
    confidence: float = 1.0


@dataclass
class AgentMetrics:
    """Aggregated metrics for a specific agent"""
    agent_name: str
    total_validations: int = 0
    successful_validations: int = 0
    repair_attempts: int = 0
    successful_repairs: int = 0
    fallback_count: int = 0
    error_count: int = 0
    avg_processing_time_ms: float = 0.0
    p95_processing_time_ms: float = 0.0
    success_rate: float = 1.0
    repair_success_rate: float = 0.0
    recent_errors: List[str] = field(default_factory=list)
    processing_times: deque = field(default_factory=lambda: deque(maxlen=1000))


class ValidationMetricsCollector:
    """Production metrics collection and monitoring for ValidationWrapper system"""
    
    def __init__(self, max_history: int = 10000, alert_threshold: float = 0.95):
        self.max_history = max_history
        self.alert_threshold = alert_threshold
        self.metrics_history: deque = deque(maxlen=max_history)
        self.agent_metrics: Dict[str, AgentMetrics] = defaultdict(lambda: AgentMetrics(""))
        self.alert_callbacks: List[Callable] = []
        self._lock = Lock()
        
        # Performance tracking
        self.start_time = datetime.now()
        self.last_alert_time: Dict[str, datetime] = {}
        
        logger.info(f"ValidationMetricsCollector initialized - max_history={max_history}, alert_threshold={alert_threshold}")
    
    def record_validation(self, 
                         agent_name: str,
                         validation_result: str,
                         processing_time_ms: float,
                         error_type: Optional[str] = None,
                         repair_strategy: Optional[str] = None,
                         confidence: float = 1.0):
        """Record a validation event"""
        with self._lock:
            metric = ValidationMetric(
                timestamp=datetime.now(),
                agent_name=agent_name,
                validation_result=validation_result,
                processing_time_ms=processing_time_ms,
                error_type=error_type,
                repair_strategy=repair_strategy,
                confidence=confidence
            )
            
            self.metrics_history.append(metric)
            self._update_agent_metrics(metric)
            
            # Check for alerts
            self._check_alerts(agent_name)
    
    def _update_agent_metrics(self, metric: ValidationMetric):
        """Update aggregated agent metrics"""
        agent_metrics = self.agent_metrics[metric.agent_name]
        agent_metrics.agent_name = metric.agent_name
        agent_metrics.total_validations += 1
        agent_metrics.processing_times.append(metric.processing_time_ms)
        
        # Update counters based on validation result
        if metric.validation_result == "success":
            agent_metrics.successful_validations += 1
        elif metric.validation_result == "repair":
            agent_metrics.repair_attempts += 1
            if metric.confidence >= 0.7:  # Consider repair successful if confidence > 0.7
                agent_metrics.successful_repairs += 1
        elif metric.validation_result == "fallback":
            agent_metrics.fallback_count += 1
        elif metric.validation_result == "error":
            agent_metrics.error_count += 1
            if metric.error_type:
                agent_metrics.recent_errors.append(f"{metric.timestamp.isoformat()}: {metric.error_type}")
                if len(agent_metrics.recent_errors) > 10:
                    agent_metrics.recent_errors.pop(0)
        
        # Calculate derived metrics
        self._calculate_derived_metrics(agent_metrics)
    
    def _calculate_derived_metrics(self, agent_metrics: AgentMetrics):
        """Calculate derived metrics like success rates and percentiles"""
        if agent_metrics.total_validations > 0:
            # Success rate includes both direct success and successful repairs
            successes = agent_metrics.successful_validations + agent_metrics.successful_repairs
            agent_metrics.success_rate = successes / agent_metrics.total_validations
        
        if agent_metrics.repair_attempts > 0:
            agent_metrics.repair_success_rate = agent_metrics.successful_repairs / agent_metrics.repair_attempts
        
        if agent_metrics.processing_times:
            times = list(agent_metrics.processing_times)
            agent_metrics.avg_processing_time_ms = sum(times) / len(times)
            
            # Calculate P95
            if len(times) >= 20:  # Only calculate P95 if we have enough samples
                sorted_times = sorted(times)
                p95_index = int(0.95 * len(sorted_times))
                agent_metrics.p95_processing_time_ms = sorted_times[p95_index]
    
    def _check_alerts(self, agent_name: str):
        """Check if any alerts should be triggered"""
        agent_metrics = self.agent_metrics[agent_name]
        
        # Only check alerts if we have sufficient data
        if agent_metrics.total_validations < 10:
            return
        
        # Alert if success rate drops below threshold
        if agent_metrics.success_rate < self.alert_threshold:
            self._trigger_alert(
                agent_name=agent_name,
                alert_type="low_success_rate",
                message=f"Success rate {agent_metrics.success_rate:.2%} below threshold {self.alert_threshold:.2%}",
                severity="warning"
            )
        
        # Alert if average processing time is very high
        if agent_metrics.avg_processing_time_ms > 1000:  # > 1 second
            self._trigger_alert(
                agent_name=agent_name,
                alert_type="high_latency",
                message=f"Average processing time {agent_metrics.avg_processing_time_ms:.1f}ms is very high",
                severity="warning"
            )
        
        # Alert if too many recent errors
        if len(agent_metrics.recent_errors) > 5:
            self._trigger_alert(
                agent_name=agent_name,
                alert_type="high_error_rate",
                message=f"High error rate: {len(agent_metrics.recent_errors)} recent errors",
                severity="error"
            )
    
    def _trigger_alert(self, agent_name: str, alert_type: str, message: str, severity: str):
        """Trigger an alert (with rate limiting)"""
        alert_key = f"{agent_name}:{alert_type}"
        now = datetime.now()
        
        # Rate limit alerts (only trigger once per 5 minutes)
        if alert_key in self.last_alert_time:
            if now - self.last_alert_time[alert_key] < timedelta(minutes=5):
                return
        
        self.last_alert_time[alert_key] = now
        
        alert_data = {
            "timestamp": now.isoformat(),
            "agent_name": agent_name,
            "alert_type": alert_type,
            "message": message,
            "severity": severity
        }
        
        logger.warning(f"ValidationAlert [{severity.upper()}] {agent_name}: {message}")
        
        # Call registered alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for alerts"""
        self.alert_callbacks.append(callback)
        logger.info(f"Alert callback registered: {callback.__name__}")
    
    def get_agent_summary(self, agent_name: str) -> Dict[str, Any]:
        """Get comprehensive metrics summary for an agent"""
        if agent_name not in self.agent_metrics:
            return {"error": f"No metrics found for agent: {agent_name}"}
        
        metrics = self.agent_metrics[agent_name]
        return {
            "agent_name": agent_name,
            "total_validations": metrics.total_validations,
            "success_rate": metrics.success_rate,
            "repair_success_rate": metrics.repair_success_rate,
            "avg_processing_time_ms": metrics.avg_processing_time_ms,
            "p95_processing_time_ms": metrics.p95_processing_time_ms,
            "error_count": metrics.error_count,
            "fallback_count": metrics.fallback_count,
            "recent_errors": metrics.recent_errors[-3:] if metrics.recent_errors else [],
            "health_status": self._get_health_status(metrics)
        }
    
    def _get_health_status(self, metrics: AgentMetrics) -> str:
        """Determine overall health status for an agent"""
        if metrics.total_validations < 5:
            return "insufficient_data"
        
        if metrics.success_rate >= 0.95:
            if metrics.avg_processing_time_ms < 100:
                return "excellent"
            elif metrics.avg_processing_time_ms < 500:
                return "good"
            else:
                return "slow"
        elif metrics.success_rate >= 0.90:
            return "acceptable"
        elif metrics.success_rate >= 0.80:
            return "degraded"
        else:
            return "critical"
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get overall system metrics summary"""
        with self._lock:
            total_validations = sum(m.total_validations for m in self.agent_metrics.values())
            total_successful = sum(m.successful_validations + m.successful_repairs for m in self.agent_metrics.values())
            total_errors = sum(m.error_count for m in self.agent_metrics.values())
            
            uptime = datetime.now() - self.start_time
            
            agent_health = {}
            for name, metrics in self.agent_metrics.items():
                agent_health[name] = self._get_health_status(metrics)
            
            return {
                "uptime_hours": uptime.total_seconds() / 3600,
                "total_validations": total_validations,
                "system_success_rate": total_successful / total_validations if total_validations > 0 else 1.0,
                "total_errors": total_errors,
                "error_rate": total_errors / total_validations if total_validations > 0 else 0.0,
                "active_agents": len(self.agent_metrics),
                "agent_health": agent_health,
                "recent_activity": len([m for m in self.metrics_history if (datetime.now() - m.timestamp).total_seconds() < 300])
            }
    
    def export_metrics(self, format: str = "json", time_window_hours: int = 24) -> str:
        """Export metrics in various formats"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if format == "json":
            return json.dumps({
                "export_timestamp": datetime.now().isoformat(),
                "time_window_hours": time_window_hours,
                "system_summary": self.get_system_summary(),
                "agent_summaries": {name: self.get_agent_summary(name) for name in self.agent_metrics.keys()},
                "recent_metrics": [
                    {
                        "timestamp": m.timestamp.isoformat(),
                        "agent_name": m.agent_name,
                        "validation_result": m.validation_result,
                        "processing_time_ms": m.processing_time_ms,
                        "error_type": m.error_type,
                        "repair_strategy": m.repair_strategy,
                        "confidence": m.confidence
                    }
                    for m in recent_metrics[-100:]  # Last 100 events
                ]
            }, indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def reset_metrics(self, agent_name: Optional[str] = None):
        """Reset metrics (for testing or maintenance)"""
        with self._lock:
            if agent_name:
                if agent_name in self.agent_metrics:
                    del self.agent_metrics[agent_name]
                    logger.info(f"Reset metrics for agent: {agent_name}")
            else:
                self.metrics_history.clear()
                self.agent_metrics.clear()
                self.start_time = datetime.now()
                logger.info("Reset all metrics")


# Global metrics collector instance
_global_metrics = None


def get_metrics_collector() -> ValidationMetricsCollector:
    """Get the global metrics collector instance"""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = ValidationMetricsCollector()
    return _global_metrics


def record_validation_metric(agent_name: str,
                           validation_result: str,
                           processing_time_ms: float,
                           error_type: Optional[str] = None,
                           repair_strategy: Optional[str] = None,
                           confidence: float = 1.0):
    """Convenience function to record validation metrics"""
    collector = get_metrics_collector()
    collector.record_validation(
        agent_name=agent_name,
        validation_result=validation_result,
        processing_time_ms=processing_time_ms,
        error_type=error_type,
        repair_strategy=repair_strategy,
        confidence=confidence
    )


def setup_validation_monitoring():
    """Setup production monitoring and alerting"""
    collector = get_metrics_collector()
    
    # Setup basic alert callback that logs to structured format
    def log_alert(alert_data):
        logger.error(f"VALIDATION_ALERT: {json.dumps(alert_data)}")
    
    collector.add_alert_callback(log_alert)
    logger.info("Validation monitoring setup complete")
    
    return collector