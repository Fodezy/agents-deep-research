"""
Enhanced logging configuration for ValidationWrapper system.
Provides structured logging, performance tracking, and debugging capabilities.
"""

import logging
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager
from functools import wraps


class ValidationLogger:
    """Enhanced logger for validation operations with structured output"""
    
    def __init__(self, name: str = "ValidationWrapper"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Setup structured logging format
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = StructuredFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_validation_start(self, agent_name: str, input_preview: str):
        """Log start of validation operation"""
        self.logger.info("validation_start", extra={
            "agent_name": agent_name,
            "input_preview": input_preview[:100] + "..." if len(input_preview) > 100 else input_preview,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_validation_success(self, agent_name: str, processing_time_ms: float, confidence: float):
        """Log successful validation"""
        self.logger.info("validation_success", extra={
            "agent_name": agent_name,
            "processing_time_ms": processing_time_ms,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_validation_repair(self, agent_name: str, error_type: str, repair_strategy: str, 
                            processing_time_ms: float, success: bool, confidence: float):
        """Log validation repair attempt"""
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, "validation_repair", extra={
            "agent_name": agent_name,
            "error_type": error_type,
            "repair_strategy": repair_strategy,
            "processing_time_ms": processing_time_ms,
            "repair_success": success,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_validation_fallback(self, agent_name: str, reason: str, processing_time_ms: float):
        """Log fallback to legacy processing"""
        self.logger.warning("validation_fallback", extra={
            "agent_name": agent_name,
            "reason": reason,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_validation_error(self, agent_name: str, error_type: str, error_message: str, 
                           processing_time_ms: float, raw_output_preview: str = ""):
        """Log validation error"""
        self.logger.error("validation_error", extra={
            "agent_name": agent_name,
            "error_type": error_type,
            "error_message": error_message,
            "processing_time_ms": processing_time_ms,
            "raw_output_preview": raw_output_preview[:200] + "..." if len(raw_output_preview) > 200 else raw_output_preview,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_circuit_breaker_event(self, agent_name: str, event_type: str, details: Dict[str, Any]):
        """Log circuit breaker state changes"""
        self.logger.warning("circuit_breaker_event", extra={
            "agent_name": agent_name,
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_performance_metrics(self, agent_name: str, metrics: Dict[str, Any]):
        """Log performance metrics"""
        self.logger.info("performance_metrics", extra={
            "agent_name": agent_name,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        })


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        # Base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                              'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process', 'message']:
                    log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, logger: ValidationLogger, agent_name: str):
        self.operation_name = operation_name
        self.logger = logger
        self.agent_name = agent_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        processing_time_ms = (self.end_time - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.log_performance_metrics(self.agent_name, {
                "operation": self.operation_name,
                "processing_time_ms": processing_time_ms,
                "status": "success"
            })
        else:
            self.logger.log_performance_metrics(self.agent_name, {
                "operation": self.operation_name,
                "processing_time_ms": processing_time_ms,
                "status": "error",
                "error_type": exc_type.__name__,
                "error_message": str(exc_val)
            })
    
    def get_elapsed_ms(self) -> float:
        """Get elapsed time in milliseconds"""
        if self.start_time is None:
            return 0.0
        current_time = time.perf_counter()
        return (current_time - self.start_time) * 1000


def performance_logging(operation_name: str):
    """Decorator for automatic performance logging"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Try to get agent name from first argument or kwargs
            agent_name = "unknown"
            if args and hasattr(args[0], 'agent_name'):
                agent_name = args[0].agent_name
            elif 'agent_name' in kwargs:
                agent_name = kwargs['agent_name']
            
            logger = get_validation_logger()
            
            with PerformanceTimer(operation_name, logger, agent_name):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Try to get agent name from first argument or kwargs
            agent_name = "unknown"
            if args and hasattr(args[0], 'agent_name'):
                agent_name = args[0].agent_name
            elif 'agent_name' in kwargs:
                agent_name = kwargs['agent_name']
            
            logger = get_validation_logger()
            
            with PerformanceTimer(operation_name, logger, agent_name):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global logger instance
_global_validation_logger = None


def get_validation_logger() -> ValidationLogger:
    """Get the global validation logger instance"""
    global _global_validation_logger
    if _global_validation_logger is None:
        _global_validation_logger = ValidationLogger()
    return _global_validation_logger


def setup_validation_logging(log_level: str = "INFO", structured: bool = True):
    """Setup validation logging configuration"""
    logger = get_validation_logger()
    
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.logger.setLevel(level)
    
    # Configure root logger to ensure our logs are captured
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        if structured:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    root_logger.setLevel(level)
    
    logger.logger.info("validation_logging_setup", extra={
        "log_level": log_level,
        "structured": structured,
        "timestamp": datetime.now().isoformat()
    })
    
    return logger


@contextmanager
def validation_context(agent_name: str, operation: str):
    """Context manager for validation operations with automatic logging"""
    logger = get_validation_logger()
    start_time = time.perf_counter()
    
    logger.logger.debug("validation_context_start", extra={
        "agent_name": agent_name,
        "operation": operation,
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        yield logger
    except Exception as e:
        processing_time_ms = (time.perf_counter() - start_time) * 1000
        logger.log_validation_error(
            agent_name=agent_name,
            error_type=type(e).__name__,
            error_message=str(e),
            processing_time_ms=processing_time_ms
        )
        raise
    finally:
        processing_time_ms = (time.perf_counter() - start_time) * 1000
        logger.logger.debug("validation_context_end", extra={
            "agent_name": agent_name,
            "operation": operation,
            "processing_time_ms": processing_time_ms,
            "timestamp": datetime.now().isoformat()
        })