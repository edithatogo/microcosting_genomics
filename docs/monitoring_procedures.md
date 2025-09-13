# Monitoring and Observability Procedures

This document outlines the monitoring and observability procedures for the Genomics Microcosting Project, ensuring system health, performance tracking, and operational visibility.

## Overview

The monitoring system provides comprehensive observability through:
- System health checks
- Performance metrics collection
- Usage analytics tracking
- Alerting for critical events

## Monitoring Components

### 1. System Health Checker

The [SystemHealthChecker](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/monitoring.py#L28-L152) monitors system-level metrics and application health.

#### Key Features:
- Disk space monitoring
- Memory usage tracking
- CPU utilization monitoring
- Data availability verification
- Custom health check registration

#### Usage Example:
```python
from unimelb_phd_phase_1.monitoring import SystemHealthChecker

health_checker = SystemHealthChecker()
health_checker.register_health_check("custom_check", my_custom_check_function)
health_results = health_checker.run_health_check()
```

### 2. Performance Metrics Collector

The [PerformanceMetricsCollector](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/monitoring.py#L155-L236) collects and stores performance metrics for analysis.

#### Key Features:
- Metric recording with timestamps
- Historical data retention
- Metrics summary generation
- Configurable history limits

#### Usage Example:
```python
from unimelb_phd_phase_1.monitoring import PerformanceMetricsCollector

metrics_collector = PerformanceMetricsCollector()
metrics_collector.record_metric("analysis.duration", 42.5, {"dataset": "large"})
summary = metrics_collector.get_metrics_summary()
```

### 3. Usage Analytics

The [UsageAnalytics](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/monitoring.py#L239-L315) tracks user interactions and application usage patterns.

#### Key Features:
- User action logging
- Usage statistics generation
- Activity pattern analysis
- Persistent storage

#### Usage Example:
```python
from unimelb_phd_phase_1.monitoring import UsageAnalytics

usage_analytics = UsageAnalytics()
usage_analytics.log_user_action("user123", "run_analysis", "cost_driver", {"parameters": {"iterations": 1000}})
stats = usage_analytics.get_usage_statistics()
```

### 4. Alert Manager

The [AlertManager](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/monitoring.py#L318-L383) handles critical event notifications and alerting.

#### Key Features:
- Multi-level severity alerts (info, warning, error, critical)
- Persistent alert storage
- Recent alerts retrieval
- Alert filtering and categorization

#### Usage Example:
```python
from unimelb_phd_phase_1.monitoring import AlertManager

alert_manager = AlertManager()
alert_manager.send_alert("low_disk_space", "Disk space below 10%", "warning", {"free_gb": 0.5})
recent_alerts = alert_manager.get_recent_alerts()
```

### 5. Monitoring Middleware

The [MonitoringMiddleware](file:///Users/doughnut/GitHub/microcosting_genomics/src/unimelb_phd_phase_1/monitoring.py#L386-L434) provides automatic monitoring of function execution.

#### Key Features:
- Automatic execution time monitoring
- Success/error status tracking
- Decorator-based instrumentation
- Integration with metrics collector

#### Usage Example:
```python
from unimelb_phd_phase_1.monitoring import MonitoringMiddleware, PerformanceMetricsCollector

metrics_collector = PerformanceMetricsCollector()
middleware = MonitoringMiddleware(metrics_collector)

@middleware.monitor_execution_time("data_processing")
def process_data(data):
    # Processing logic here
    pass
```

## Web Interface Monitoring

The web application includes built-in monitoring endpoints:

### Health Check Endpoint
```
GET /health
```
Returns system health status and detailed check results.

### Metrics Endpoint
```
GET /metrics
```
Returns current performance metrics and summaries.

### Alerts Endpoint
```
GET /alerts
```
Returns recent system alerts.

## Implementation Examples

### Complete Monitoring Setup
```python
from unimelb_phd_phase_1.monitoring import setup_standard_monitoring

# Set up all monitoring components
health_checker, metrics_collector, usage_analytics, alert_manager, monitoring_middleware = setup_standard_monitoring()

# Run health check
health_results = health_checker.run_health_check()
print(f"System status: {health_results['status']}")

# Record a metric
metrics_collector.record_metric("data_processing.files_processed", 42)

# Log user action
usage_analytics.log_user_action("user123", "view_table", "detailed_table")

# Send an alert
alert_manager.send_alert("processing_complete", "Data processing finished", "info")
```

### Custom Health Check
```python
def check_database_connection():
    """Custom health check for database connectivity."""
    try:
        # Database connection logic
        return {"status": "connected", "latency_ms": 5.2}
    except Exception as e:
        raise HealthCheckError(f"Database connection failed: {e}")

# Register the custom check
health_checker.register_health_check("database", check_database_connection)
```

### Performance Monitoring Decorator
```python
@monitoring_middleware.monitor_execution_time("analysis.run_cost_driver")
def run_cost_driver_analysis(parameters):
    """Run cost driver analysis with automatic performance monitoring."""
    # Analysis logic here
    pass
```

## Testing Monitoring Features

The monitoring module includes comprehensive unit tests:

```bash
python -m pytest tests/test_monitoring.py -v
```

Test coverage includes:
- Health check functionality
- Performance metrics collection
- Usage analytics tracking
- Alert management
- Monitoring middleware

## Best Practices

### Health Checks
- Implement checks for all critical system dependencies
- Set appropriate thresholds for resource usage
- Regularly review and update health check criteria
- Test health checks under various failure conditions

### Performance Metrics
- Record metrics at key operational points
- Use meaningful metric names with clear hierarchy
- Include relevant tags for filtering and analysis
- Monitor metric trends over time

### Usage Analytics
- Log significant user actions for behavior analysis
- Include contextual information with actions
- Respect user privacy in data collection
- Regularly review usage patterns

### Alerting
- Use appropriate severity levels for different alert types
- Implement alert deduplication to avoid noise
- Define clear escalation procedures
- Regularly review and tune alert thresholds

## Troubleshooting

### Common Issues

1. **Health Check Failures**: Review failing checks and system resources
2. **Metrics Not Recording**: Verify metrics collector is properly initialized
3. **Alerts Not Sending**: Check alert manager configuration and storage permissions
4. **Performance Monitoring Gaps**: Ensure middleware is properly applied to functions

### Debugging Tips

- Enable debug logging for detailed monitoring information
- Use the `/health` endpoint to diagnose system issues
- Check log files for monitoring-related error messages
- Verify that all monitoring components are properly initialized

## Integration with External Monitoring

The monitoring system can be extended to integrate with external monitoring platforms:

### Prometheus Integration
```python
# Export metrics in Prometheus format
def export_to_prometheus(metrics_collector):
    """Export metrics to Prometheus format."""
    # Implementation here
    pass
```

### Grafana Dashboard
Create dashboards using the collected metrics for real-time visualization.

### Log Aggregation
Integrate with centralized logging systems like ELK stack.

## Future Enhancements

Planned monitoring improvements include:

- Real-time alerting through email or messaging systems
- Integration with cloud monitoring services
- Advanced anomaly detection for metrics
- Distributed tracing for complex workflows
- Automated scaling recommendations based on metrics