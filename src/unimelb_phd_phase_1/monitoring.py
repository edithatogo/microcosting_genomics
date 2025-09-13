"""Monitoring and observability system for genomics microcosting analysis.

This module provides comprehensive monitoring capabilities including
system health checks, performance metrics collection, usage analytics,
and alerting for critical events.
"""

import logging
import time
import psutil
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from functools import wraps
from collections import defaultdict, deque
import json
from pathlib import Path

from .logging_config import get_logger


class HealthCheckError(Exception):
    """Custom exception for health check failures."""
    pass


class SystemHealthChecker:
    """System health checker for monitoring application status."""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize the system health checker.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.checks = {}
    
    def register_health_check(self, name: str, check_function):
        """Register a health check function.
        
        Args:
            name: Name of the health check
            check_function: Function that performs the health check
        """
        self.checks[name] = check_function
        self.logger.info(f"Registered health check: {name}")
    
    def run_health_check(self) -> Dict[str, Any]:
        """Run all registered health checks.
        
        Returns:
            Dictionary with health check results
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "checks": {}
        }
        
        for name, check_function in self.checks.items():
            try:
                check_result = check_function()
                results["checks"][name] = {
                    "status": "healthy",
                    "result": check_result
                }
            except Exception as e:
                results["checks"][name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                results["status"] = "unhealthy"
                self.logger.error(f"Health check '{name}' failed: {e}")
        
        return results
    
    def check_disk_space(self, min_free_gb: float = 1.0) -> Dict[str, Any]:
        """Check available disk space.
        
        Args:
            min_free_gb: Minimum free space in GB
            
        Returns:
            Dictionary with disk space information
        """
        disk_usage = psutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        
        if free_gb < min_free_gb:
            raise HealthCheckError(f"Low disk space: {free_gb:.2f} GB free, minimum {min_free_gb} GB required")
        
        return {
            "total_gb": disk_usage.total / (1024**3),
            "used_gb": disk_usage.used / (1024**3),
            "free_gb": free_gb,
            "percent_used": disk_usage.percent
        }
    
    def check_memory_usage(self, max_percent: float = 90.0) -> Dict[str, Any]:
        """Check system memory usage.
        
        Args:
            max_percent: Maximum memory usage percentage
            
        Returns:
            Dictionary with memory usage information
        """
        memory = psutil.virtual_memory()
        
        if memory.percent > max_percent:
            raise HealthCheckError(f"High memory usage: {memory.percent}% used, maximum {max_percent}% allowed")
        
        return {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "used_gb": memory.used / (1024**3),
            "percent_used": memory.percent
        }
    
    def check_cpu_usage(self, max_percent: float = 95.0) -> Dict[str, Any]:
        """Check CPU usage.
        
        Args:
            max_percent: Maximum CPU usage percentage
            
        Returns:
            Dictionary with CPU usage information
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        
        if cpu_percent > max_percent:
            raise HealthCheckError(f"High CPU usage: {cpu_percent}% used, maximum {max_percent}% allowed")
        
        return {
            "percent_used": cpu_percent,
            "cpu_count": psutil.cpu_count()
        }
    
    def check_data_availability(self, data_dir: str = "data/prepared") -> Dict[str, Any]:
        """Check if required data files are available.
        
        Args:
            data_dir: Path to prepared data directory
            
        Returns:
            Dictionary with data availability information
        """
        data_path = Path(data_dir)
        if not data_path.exists():
            raise HealthCheckError(f"Data directory not found: {data_dir}")
        
        files = list(data_path.glob("*.parquet"))
        if not files:
            raise HealthCheckError(f"No prepared data files found in: {data_dir}")
        
        return {
            "data_dir": str(data_path),
            "file_count": len(files),
            "sample_files": [f.name for f in files[:5]]
        }


class PerformanceMetricsCollector:
    """Collects and stores performance metrics for analysis."""
    
    def __init__(self, max_history: int = 1000, logger: logging.Logger = None):
        """Initialize the performance metrics collector.
        
        Args:
            max_history: Maximum number of metrics to store
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.max_history = max_history
        self.metrics_history = defaultdict(lambda: deque(maxlen=max_history))
        self.current_metrics = {}
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        timestamp = datetime.now().isoformat()
        metric_data = {
            "timestamp": timestamp,
            "value": value,
            "tags": tags or {}
        }
        
        self.metrics_history[metric_name].append(metric_data)
        self.current_metrics[metric_name] = metric_data
        
        self.logger.debug(f"Recorded metric {metric_name}: {value}")
    
    def get_metric_history(self, metric_name: str) -> List[Dict[str, Any]]:
        """Get historical data for a metric.
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            List of metric data points
        """
        return list(self.metrics_history[metric_name])
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics.
        
        Returns:
            Dictionary of current metrics
        """
        return self.current_metrics
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics.
        
        Returns:
            Dictionary with metrics summary
        """
        summary = {}
        for metric_name, metric_data in self.current_metrics.items():
            history = self.get_metric_history(metric_name)
            if history:
                values = [m["value"] for m in history]
                summary[metric_name] = {
                    "current": metric_data["value"],
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "count": len(values)
                }
        return summary


class UsageAnalytics:
    """Tracks usage analytics for the application."""
    
    def __init__(self, log_file: str = "logs/usage.log", logger: logging.Logger = None):
        """Initialize the usage analytics tracker.
        
        Args:
            log_file: File to store usage logs
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create log file if it doesn't exist
        if not self.log_file.exists():
            self.log_file.touch()
    
    def log_user_action(self, user_id: str, action: str, resource: str, 
                       details: Dict[str, Any] = None):
        """Log a user action.
        
        Args:
            user_id: User identifier
            action: Action performed
            resource: Resource acted upon
            details: Additional details about the action
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {}
        }
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
            self.logger.debug(f"Logged user action: {user_id} {action} {resource}")
        except Exception as e:
            self.logger.error(f"Error logging user action: {e}")
    
    def get_usage_statistics(self, start_time: str = None, end_time: str = None) -> Dict[str, Any]:
        """Get usage statistics.
        
        Args:
            start_time: Start time for statistics (ISO format)
            end_time: End time for statistics (ISO format)
            
        Returns:
            Dictionary with usage statistics
        """
        events = []
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        event = json.loads(line.strip())
                        if start_time and event["timestamp"] < start_time:
                            continue
                        if end_time and event["timestamp"] > end_time:
                            continue
                        events.append(event)
        except Exception as e:
            self.logger.error(f"Error reading usage log: {e}")
            return {}
        
        # Calculate statistics
        user_actions = defaultdict(int)
        action_types = defaultdict(int)
        resources = defaultdict(int)
        
        for event in events:
            user_actions[event["user_id"]] += 1
            action_types[event["action"]] += 1
            resources[event["resource"]] += 1
        
        return {
            "total_events": len(events),
            "unique_users": len(user_actions),
            "user_activity": dict(user_actions),
            "action_distribution": dict(action_types),
            "resource_usage": dict(resources),
            "time_range": {
                "start": start_time,
                "end": end_time
            }
        }


class AlertManager:
    """Manages alerts for critical events."""
    
    def __init__(self, alert_file: str = "logs/alerts.log", logger: logging.Logger = None):
        """Initialize the alert manager.
        
        Args:
            alert_file: File to store alerts
            logger: Logger instance (optional)
        """
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
        self.alert_file = Path(alert_file)
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create alert file if it doesn't exist
        if not self.alert_file.exists():
            self.alert_file.touch()
    
    def send_alert(self, alert_type: str, message: str, severity: str = "warning",
                  details: Dict[str, Any] = None):
        """Send an alert.
        
        Args:
            alert_type: Type of alert
            message: Alert message
            severity: Severity level (info, warning, error, critical)
            details: Additional details about the alert
        """
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "message": message,
            "severity": severity,
            "details": details or {}
        }
        
        try:
            with open(self.alert_file, 'a') as f:
                f.write(json.dumps(alert) + '\n')
            self.logger.log(
                getattr(logging, severity.upper(), logging.WARNING),
                f"ALERT [{severity.upper()}] {alert_type}: {message}"
            )
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of recent alerts
        """
        alerts = []
        try:
            with open(self.alert_file, 'r') as f:
                for line in f:
                    if line.strip():
                        alert = json.loads(line.strip())
                        alerts.append(alert)
        except Exception as e:
            self.logger.error(f"Error reading alerts: {e}")
            return []
        
        # Filter by time (simplified - in a real implementation, you'd parse the timestamp)
        return alerts[-100:]  # Return last 100 alerts


class MonitoringMiddleware:
    """Middleware for automatic monitoring of function calls."""
    
    def __init__(self, metrics_collector: PerformanceMetricsCollector = None,
                 logger: logging.Logger = None):
        """Initialize the monitoring middleware.
        
        Args:
            metrics_collector: Performance metrics collector
            logger: Logger instance (optional)
        """
        self.metrics_collector = metrics_collector or PerformanceMetricsCollector()
        self.logger = logger or get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def monitor_execution_time(self, metric_name: str = None):
        """Decorator to monitor execution time of functions.
        
        Args:
            metric_name: Name for the timing metric (defaults to function name)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    status = "success"
                except Exception as e:
                    status = "error"
                    raise
                finally:
                    end_time = time.time()
                    execution_time = end_time - start_time
                    
                    name = metric_name or f"{func.__module__}.{func.__name__}"
                    self.metrics_collector.record_metric(
                        f"{name}.execution_time", 
                        execution_time,
                        {"status": status}
                    )
                
                return result
            return wrapper
        return decorator


# Convenience functions for monitoring setup
def setup_standard_monitoring(logger: logging.Logger = None) -> tuple:
    """Set up standard monitoring components.
    
    Args:
        logger: Logger instance (optional)
        
    Returns:
        Tuple of (SystemHealthChecker, PerformanceMetricsCollector, 
                 UsageAnalytics, AlertManager, MonitoringMiddleware)
    """
    logger = logger or get_logger(__name__)
    
    health_checker = SystemHealthChecker(logger)
    metrics_collector = PerformanceMetricsCollector(logger=logger)
    usage_analytics = UsageAnalytics(logger=logger)
    alert_manager = AlertManager(logger=logger)
    monitoring_middleware = MonitoringMiddleware(metrics_collector, logger)
    
    # Register default health checks
    health_checker.register_health_check("disk_space", health_checker.check_disk_space)
    health_checker.register_health_check("memory_usage", health_checker.check_memory_usage)
    health_checker.register_health_check("cpu_usage", health_checker.check_cpu_usage)
    health_checker.register_health_check("data_availability", health_checker.check_data_availability)
    
    return health_checker, metrics_collector, usage_analytics, alert_manager, monitoring_middleware


# Example usage:
if __name__ == "__main__":
    # Set up monitoring components
    health_checker, metrics_collector, usage_analytics, alert_manager, monitoring_middleware = setup_standard_monitoring()
    
    # Example 1: Health check
    health_results = health_checker.run_health_check()
    print("Health Check Results:")
    print(json.dumps(health_results, indent=2))
    
    # Example 2: Performance metrics
    @monitoring_middleware.monitor_execution_time("example_task")
    def example_task():
        """Example task to demonstrate monitoring."""
        time.sleep(0.1)  # Simulate work
        return "Task completed"
    
    result = example_task()
    print(f"\nTask result: {result}")
    
    # Record some metrics
    metrics_collector.record_metric("data_processing.files_processed", 42)
    metrics_collector.record_metric("data_processing.errors", 0)
    
    # Get metrics summary
    metrics_summary = metrics_collector.get_metrics_summary()
    print("\nMetrics Summary:")
    print(json.dumps(metrics_summary, indent=2))
    
    # Example 3: Usage analytics
    usage_analytics.log_user_action("user123", "view_table", "detailed_table", {"rows": 1000})
    usage_analytics.log_user_action("user123", "run_analysis", "cost_driver_analysis", {"parameters": {"iterations": 10000}})
    
    usage_stats = usage_analytics.get_usage_statistics()
    print("\nUsage Statistics:")
    print(json.dumps(usage_stats, indent=2))
    
    # Example 4: Alerts
    alert_manager.send_alert("low_disk_space", "Disk space is below 10%", "warning", 
                           {"free_space_gb": 0.5})
    
    recent_alerts = alert_manager.get_recent_alerts()
    print("\nRecent Alerts:")
    print(json.dumps(recent_alerts, indent=2))