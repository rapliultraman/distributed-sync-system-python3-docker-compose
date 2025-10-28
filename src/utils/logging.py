import logging
import sys
import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

class DistributedSystemLogger:
    """Centralized logging system for distributed sync system"""
    
    def __init__(self, node_id: str, log_level: str = "INFO"):
        self.node_id = node_id
        self.logger = logging.getLogger(f"distributed_sync_{node_id}")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(f'logs/{node_id}.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # JSON handler for structured logging
        json_handler = logging.FileHandler(f'logs/{node_id}_structured.log')
        json_formatter = JSONFormatter()
        json_handler.setFormatter(json_formatter)
        self.logger.addHandler(json_handler)
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message with context and exception details"""
        if exception:
            kwargs['exception'] = str(exception)
            kwargs['traceback'] = traceback.format_exc()
        self._log(logging.ERROR, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with context"""
        context = {
            'node_id': self.node_id,
            'timestamp': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        # Add context to message
        if context:
            context_str = json.dumps(context, default=str)
            full_message = f"{message} | Context: {context_str}"
        else:
            full_message = message
        
        self.logger.log(level, full_message)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)

class ErrorHandler:
    """Centralized error handling for distributed system"""
    
    def __init__(self, logger: DistributedSystemLogger):
        self.logger = logger
        self.error_counts = {}
        self.circuit_breakers = {}
    
    def handle_error(self, operation: str, error: Exception, context: Dict[str, Any] = None):
        """Handle and log errors with context"""
        error_type = type(error).__name__
        error_key = f"{operation}_{error_type}"
        
        # Count errors
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log error with context
        self.logger.error(
            f"Error in {operation}: {str(error)}",
            exception=error,
            operation=operation,
            error_type=error_type,
            error_count=self.error_counts[error_key],
            **(context or {})
        )
        
        # Check circuit breaker
        if self._should_open_circuit_breaker(error_key):
            self.logger.warning(f"Circuit breaker opened for {error_key}")
            return False
        
        return True
    
    def _should_open_circuit_breaker(self, error_key: str) -> bool:
        """Check if circuit breaker should be opened"""
        error_count = self.error_counts.get(error_key, 0)
        return error_count >= 10  # Open after 10 errors
    
    def reset_circuit_breaker(self, error_key: str):
        """Reset circuit breaker"""
        self.error_counts[error_key] = 0
        self.logger.info(f"Circuit breaker reset for {error_key}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors"""
        return {
            'error_counts': self.error_counts.copy(),
            'circuit_breakers': self.circuit_breakers.copy()
        }

class RetryHandler:
    """Retry mechanism for failed operations"""
    
    def __init__(self, logger: DistributedSystemLogger, max_retries: int = 3):
        self.logger = logger
        self.max_retries = max_retries
    
    async def retry_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Retry operation with exponential backoff"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(operation_func):
                    result = await operation_func(*args, **kwargs)
                else:
                    result = operation_func(*args, **kwargs)
                
                if attempt > 0:
                    self.logger.info(f"Operation {operation_name} succeeded on attempt {attempt + 1}")
                
                return result
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        f"Operation {operation_name} failed on attempt {attempt + 1}, retrying in {wait_time}s",
                        exception=e,
                        attempt=attempt + 1,
                        max_retries=self.max_retries
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"Operation {operation_name} failed after {self.max_retries + 1} attempts",
                        exception=e,
                        operation=operation_name
                    )
        
        raise last_exception

class HealthChecker:
    """Health checking system for distributed components"""
    
    def __init__(self, logger: DistributedSystemLogger):
        self.logger = logger
        self.health_status = {}
        self.last_check = {}
    
    async def check_component_health(self, component_name: str, check_func) -> bool:
        """Check health of a component"""
        try:
            start_time = datetime.utcnow()
            
            if asyncio.iscoroutinefunction(check_func):
                is_healthy = await check_func()
            else:
                is_healthy = check_func()
            
            check_duration = (datetime.utcnow() - start_time).total_seconds()
            
            self.health_status[component_name] = is_healthy
            self.last_check[component_name] = datetime.utcnow()
            
            if is_healthy:
                self.logger.debug(
                    f"Component {component_name} is healthy",
                    component=component_name,
                    check_duration=check_duration
                )
            else:
                self.logger.warning(
                    f"Component {component_name} is unhealthy",
                    component=component_name,
                    check_duration=check_duration
                )
            
            return is_healthy
        
        except Exception as e:
            self.health_status[component_name] = False
            self.last_check[component_name] = datetime.utcnow()
            
            self.logger.error(
                f"Health check failed for component {component_name}",
                exception=e,
                component=component_name
            )
            
            return False
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all components"""
        return {
            'components': self.health_status.copy(),
            'last_checks': {k: v.isoformat() for k, v in self.last_check.items()},
            'overall_health': all(self.health_status.values())
        }

# Global logger instance
_logger_instance: Optional[DistributedSystemLogger] = None
_error_handler_instance: Optional[ErrorHandler] = None

def get_logger(node_id: str = None) -> DistributedSystemLogger:
    """Get logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = DistributedSystemLogger(node_id or "unknown")
    return _logger_instance

def get_error_handler() -> ErrorHandler:
    """Get error handler instance"""
    global _error_handler_instance
    if _error_handler_instance is None:
        _error_handler_instance = ErrorHandler(get_logger())
    return _error_handler_instance

def setup_logging(node_id: str, log_level: str = "INFO"):
    """Setup logging for the distributed system"""
    import os
    os.makedirs('logs', exist_ok=True)
    
    global _logger_instance, _error_handler_instance
    _logger_instance = DistributedSystemLogger(node_id, log_level)
    _error_handler_instance = ErrorHandler(_logger_instance)
    
    _logger_instance.info(f"Logging initialized for node {node_id}", log_level=log_level)
