"""Test cases for the Monitoring module."""

import unittest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from genomics_microcosting.monitoring import (
    SystemHealthChecker, PerformanceMetricsCollector, UsageAnalytics,
    AlertManager, MonitoringMiddleware, HealthCheckError
)


class TestSystemHealthChecker(unittest.TestCase):
    """Test cases for SystemHealthChecker."""

    def setUp(self):
        """Set up test fixtures."""
        self.health_checker = SystemHealthChecker()

    def test_init(self):
        """Test SystemHealthChecker initialization."""
        self.assertIsInstance(self.health_checker, SystemHealthChecker)
        self.assertEqual(self.health_checker.checks, {})

    def test_register_health_check(self):
        """Test registering a health check."""
        def test_check():
            return "healthy"
        
        self.health_checker.register_health_check("test_check", test_check)
        self.assertIn("test_check", self.health_checker.checks)
        self.assertEqual(self.health_checker.checks["test_check"], test_check)

    def test_run_health_check(self):
        """Test running health checks."""
        def healthy_check():
            return {"status": "ok"}
        
        def failing_check():
            raise Exception("Check failed")
        
        self.health_checker.register_health_check("healthy_check", healthy_check)
        self.health_checker.register_health_check("failing_check", failing_check)
        
        results = self.health_checker.run_health_check()
        
        self.assertIn("timestamp", results)
        self.assertIn("status", results)
        self.assertIn("checks", results)
        self.assertEqual(results["status"], "unhealthy")  # Because one check fails
        
        self.assertIn("healthy_check", results["checks"])
        self.assertEqual(results["checks"]["healthy_check"]["status"], "healthy")
        self.assertEqual(results["checks"]["healthy_check"]["result"], {"status": "ok"})
        
        self.assertIn("failing_check", results["checks"])
        self.assertEqual(results["checks"]["failing_check"]["status"], "unhealthy")
        self.assertIn("error", results["checks"]["failing_check"])

    @patch('psutil.disk_usage')
    def test_check_disk_space_healthy(self, mock_disk_usage):
        """Test disk space check with healthy disk space."""
        mock_disk_usage.return_value.free = 2 * 1024**3  # 2 GB free
        mock_disk_usage.return_value.total = 10 * 1024**3  # 10 GB total
        mock_disk_usage.return_value.used = 8 * 1024**3  # 8 GB used
        mock_disk_usage.return_value.percent = 80
        
        result = self.health_checker.check_disk_space(min_free_gb=1.0)
        
        self.assertIsInstance(result, dict)
        self.assertIn("total_gb", result)
        self.assertIn("used_gb", result)
        self.assertIn("free_gb", result)
        self.assertIn("percent_used", result)
        self.assertGreaterEqual(result["free_gb"], 1.0)

    @patch('psutil.disk_usage')
    def test_check_disk_space_unhealthy(self, mock_disk_usage):
        """Test disk space check with low disk space."""
        mock_disk_usage.return_value.free = 0.5 * 1024**3  # 0.5 GB free
        mock_disk_usage.return_value.total = 10 * 1024**3  # 10 GB total
        mock_disk_usage.return_value.used = 9.5 * 1024**3  # 9.5 GB used
        mock_disk_usage.return_value.percent = 95
        
        with self.assertRaises(HealthCheckError):
            self.health_checker.check_disk_space(min_free_gb=1.0)

    @patch('psutil.virtual_memory')
    def test_check_memory_usage_healthy(self, mock_virtual_memory):
        """Test memory usage check with healthy memory usage."""
        mock_memory = Mock()
        mock_memory.percent = 50.0
        mock_memory.total = 8 * 1024**3  # 8 GB total
        mock_memory.available = 4 * 1024**3  # 4 GB available
        mock_memory.used = 4 * 1024**3  # 4 GB used
        mock_virtual_memory.return_value = mock_memory
        
        result = self.health_checker.check_memory_usage(max_percent=90.0)
        
        self.assertIsInstance(result, dict)
        self.assertIn("total_gb", result)
        self.assertIn("available_gb", result)
        self.assertIn("used_gb", result)
        self.assertIn("percent_used", result)
        self.assertLessEqual(result["percent_used"], 90.0)

    @patch('psutil.virtual_memory')
    def test_check_memory_usage_unhealthy(self, mock_virtual_memory):
        """Test memory usage check with high memory usage."""
        mock_memory = Mock()
        mock_memory.percent = 95.0
        mock_memory.total = 8 * 1024**3  # 8 GB total
        mock_memory.available = 0.4 * 1024**3  # 0.4 GB available
        mock_memory.used = 7.6 * 1024**3  # 7.6 GB used
        mock_virtual_memory.return_value = mock_memory
        
        with self.assertRaises(HealthCheckError):
            self.health_checker.check_memory_usage(max_percent=90.0)

    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    def test_check_cpu_usage_healthy(self, mock_cpu_count, mock_cpu_percent):
        """Test CPU usage check with healthy CPU usage."""
        mock_cpu_percent.return_value = 50.0
        mock_cpu_count.return_value = 4
        
        result = self.health_checker.check_cpu_usage(max_percent=95.0)
        
        self.assertIsInstance(result, dict)
        self.assertIn("percent_used", result)
        self.assertIn("cpu_count", result)
        self.assertLessEqual(result["percent_used"], 95.0)
        self.assertEqual(result["cpu_count"], 4)

    @patch('psutil.cpu_percent')
    @patch('psutil.cpu_count')
    def test_check_cpu_usage_unhealthy(self, mock_cpu_count, mock_cpu_percent):
        """Test CPU usage check with high CPU usage."""
        mock_cpu_percent.return_value = 98.0
        mock_cpu_count.return_value = 4
        
        with self.assertRaises(HealthCheckError):
            self.health_checker.check_cpu_usage(max_percent=95.0)

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.glob')
    def test_check_data_availability_healthy(self, mock_glob, mock_exists):
        """Test data availability check with available data."""
        mock_exists.return_value = True
        mock_files = [Mock()]
        mock_files[0].name = "test.parquet"
        mock_glob.return_value = mock_files
        
        result = self.health_checker.check_data_availability("test/data")
        
        self.assertIsInstance(result, dict)
        self.assertIn("data_dir", result)
        self.assertIn("file_count", result)
        self.assertIn("sample_files", result)
        self.assertEqual(result["file_count"], 1)

    @patch('pathlib.Path.exists')
    def test_check_data_availability_missing_dir(self, mock_exists):
        """Test data availability check with missing data directory."""
        mock_exists.return_value = False
        
        with self.assertRaises(HealthCheckError):
            self.health_checker.check_data_availability("missing/data")


class TestPerformanceMetricsCollector(unittest.TestCase):
    """Test cases for PerformanceMetricsCollector."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics_collector = PerformanceMetricsCollector(max_history=5)

    def test_init(self):
        """Test PerformanceMetricsCollector initialization."""
        self.assertIsInstance(self.metrics_collector, PerformanceMetricsCollector)
        self.assertEqual(self.metrics_collector.max_history, 5)

    def test_record_metric(self):
        """Test recording a metric."""
        self.metrics_collector.record_metric("test.metric", 42.5, {"tag": "value"})
        
        current_metrics = self.metrics_collector.get_current_metrics()
        self.assertIn("test.metric", current_metrics)
        self.assertEqual(current_metrics["test.metric"]["value"], 42.5)
        self.assertEqual(current_metrics["test.metric"]["tags"], {"tag": "value"})

    def test_get_metric_history(self):
        """Test getting metric history."""
        # Record multiple values for the same metric
        for i in range(3):
            self.metrics_collector.record_metric("test.metric", float(i))
        
        history = self.metrics_collector.get_metric_history("test.metric")
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["value"], 0.0)
        self.assertEqual(history[1]["value"], 1.0)
        self.assertEqual(history[2]["value"], 2.0)

    def test_history_limit(self):
        """Test that history is limited to max_history."""
        # Record more values than max_history
        for i in range(10):
            self.metrics_collector.record_metric("test.metric", float(i))
        
        history = self.metrics_collector.get_metric_history("test.metric")
        self.assertEqual(len(history), 5)  # Limited to max_history
        self.assertEqual(history[0]["value"], 5.0)  # Oldest values should be dropped
        self.assertEqual(history[4]["value"], 9.0)  # Newest values should be kept

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        # Record some metrics
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.metrics_collector.record_metric("test.metric", value)
        
        summary = self.metrics_collector.get_metrics_summary()
        self.assertIn("test.metric", summary)
        
        metric_summary = summary["test.metric"]
        self.assertEqual(metric_summary["current"], 5.0)
        self.assertEqual(metric_summary["min"], 1.0)
        self.assertEqual(metric_summary["max"], 5.0)
        self.assertEqual(metric_summary["avg"], 3.0)
        self.assertEqual(metric_summary["count"], 5)


class TestUsageAnalytics(unittest.TestCase):
    """Test cases for UsageAnalytics."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_file = Path(self.temp_dir.name) / "usage.log"
        self.usage_analytics = UsageAnalytics(str(self.log_file))

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test UsageAnalytics initialization."""
        self.assertIsInstance(self.usage_analytics, UsageAnalytics)
        self.assertTrue(self.log_file.exists())

    def test_log_user_action(self):
        """Test logging a user action."""
        self.usage_analytics.log_user_action(
            "user123", "view_table", "detailed_table", 
            {"rows": 1000, "columns": 20}
        )
        
        # Check that the log file contains the event
        with open(self.log_file, 'r') as f:
            content = f.read()
            self.assertIn("user123", content)
            self.assertIn("view_table", content)
            self.assertIn("detailed_table", content)
            self.assertIn("1000", content)

    def test_get_usage_statistics(self):
        """Test getting usage statistics."""
        # Log some actions
        self.usage_analytics.log_user_action("user1", "view", "table1")
        self.usage_analytics.log_user_action("user1", "analyze", "table1")
        self.usage_analytics.log_user_action("user2", "view", "table2")
        
        stats = self.usage_analytics.get_usage_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn("total_events", stats)
        self.assertIn("unique_users", stats)
        self.assertIn("user_activity", stats)
        self.assertIn("action_distribution", stats)
        self.assertIn("resource_usage", stats)
        
        self.assertEqual(stats["total_events"], 3)
        self.assertEqual(stats["unique_users"], 2)
        self.assertEqual(stats["user_activity"]["user1"], 2)
        self.assertEqual(stats["user_activity"]["user2"], 1)


class TestAlertManager(unittest.TestCase):
    """Test cases for AlertManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.alert_file = Path(self.temp_dir.name) / "alerts.log"
        self.alert_manager = AlertManager(str(self.alert_file))

    def tearDown(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test AlertManager initialization."""
        self.assertIsInstance(self.alert_manager, AlertManager)
        self.assertTrue(self.alert_file.exists())

    def test_send_alert(self):
        """Test sending an alert."""
        self.alert_manager.send_alert(
            "test_alert", "This is a test alert", "warning",
            {"test_data": "value"}
        )
        
        # Check that the alert file contains the alert
        with open(self.alert_file, 'r') as f:
            content = f.read()
            self.assertIn("test_alert", content)
            self.assertIn("This is a test alert", content)
            self.assertIn("warning", content)
            self.assertIn("value", content)

    def test_get_recent_alerts(self):
        """Test getting recent alerts."""
        # Send some alerts
        self.alert_manager.send_alert("alert1", "First alert", "info")
        self.alert_manager.send_alert("alert2", "Second alert", "warning")
        
        alerts = self.alert_manager.get_recent_alerts()
        
        self.assertIsInstance(alerts, list)
        self.assertEqual(len(alerts), 2)
        
        # Check alert content
        self.assertEqual(alerts[0]["type"], "alert1")
        self.assertEqual(alerts[0]["message"], "First alert")
        self.assertEqual(alerts[0]["severity"], "info")
        
        self.assertEqual(alerts[1]["type"], "alert2")
        self.assertEqual(alerts[1]["message"], "Second alert")
        self.assertEqual(alerts[1]["severity"], "warning")


class TestMonitoringMiddleware(unittest.TestCase):
    """Test cases for MonitoringMiddleware."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics_collector = PerformanceMetricsCollector()
        self.middleware = MonitoringMiddleware(self.metrics_collector)

    def test_init(self):
        """Test MonitoringMiddleware initialization."""
        self.assertIsInstance(self.middleware, MonitoringMiddleware)
        self.assertEqual(self.middleware.metrics_collector, self.metrics_collector)

    def test_monitor_execution_time(self):
        """Test monitoring execution time."""
        @self.middleware.monitor_execution_time("test_function")
        def test_function():
            time.sleep(0.01)  # Sleep for 10ms
            return "result"
        
        result = test_function()
        
        self.assertEqual(result, "result")
        
        # Check that metrics were recorded
        current_metrics = self.metrics_collector.get_current_metrics()
        metric_name = "test_function.execution_time"
        self.assertIn(metric_name, current_metrics)
        
        # The execution time should be approximately 0.01 seconds
        execution_time = current_metrics[metric_name]["value"]
        self.assertGreater(execution_time, 0.0)
        self.assertLess(execution_time, 1.0)  # Should be much less than 1 second

    def test_monitor_execution_time_with_error(self):
        """Test monitoring execution time with function error."""
        @self.middleware.monitor_execution_time("failing_function")
        def failing_function():
            raise Exception("Test error")
        
        with self.assertRaises(Exception):
            failing_function()
        
        # Check that metrics were recorded with error status
        current_metrics = self.metrics_collector.get_current_metrics()
        metric_name = "failing_function.execution_time"
        self.assertIn(metric_name, current_metrics)
        self.assertEqual(current_metrics[metric_name]["tags"]["status"], "error")


if __name__ == '__main__':
    unittest.main()