# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Test cases for the Monitoring module."""

import json
import tempfile
import time
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from genomics_microcosting.monitoring import (
    AlertManager,
    HealthCheckError,
    MonitoringMiddleware,
    PerformanceMetricsCollector,
    SystemHealthChecker,
    UsageAnalytics,
)
from tests.checks import require_keys, require_runtime_instance


class TestSystemHealthChecker(unittest.TestCase):
    """Test cases for SystemHealthChecker."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.health_checker = SystemHealthChecker()

    def test_init(self) -> None:
        """Test SystemHealthChecker initialization."""
        require_runtime_instance(self.health_checker, SystemHealthChecker)
        if not ((self.health_checker.checks) == ({})):
            raise AssertionError

    def test_register_health_check(self) -> None:
        """Test registering a health check."""

        def test_check() -> str:
            return "healthy"

        self.health_checker.register_health_check("test_check", test_check)
        if ("test_check") not in (self.health_checker.checks):
            raise AssertionError
        if not ((self.health_checker.checks["test_check"]) == (test_check)):
            raise AssertionError

    def test_run_health_check(self) -> None:
        """Test running health checks."""

        def healthy_check() -> dict[str, str]:
            return {"status": "ok"}

        def failing_check() -> None:
            message = "Check failed"
            raise HealthCheckError(message)

        self.health_checker.register_health_check("healthy_check", healthy_check)
        self.health_checker.register_health_check("failing_check", failing_check)

        results = self.health_checker.run_health_check()

        require_keys(results, ("timestamp", "status", "checks"))
        if not ((results["status"]) == ("unhealthy")):
            raise AssertionError  # Because one check fails

        if ("healthy_check") not in (results["checks"]):
            raise AssertionError
        if not ((results["checks"]["healthy_check"]["status"]) == ("healthy")):
            raise AssertionError
        if not ((results["checks"]["healthy_check"]["result"]) == ({"status": "ok"})):
            raise AssertionError

        if ("failing_check") not in (results["checks"]):
            raise AssertionError
        if not ((results["checks"]["failing_check"]["status"]) == ("unhealthy")):
            raise AssertionError
        if ("error") not in (results["checks"]["failing_check"]):
            raise AssertionError

    @patch("psutil.disk_usage")
    def test_check_disk_space_healthy(self, mock_disk_usage: Mock) -> None:
        """Test disk space check with healthy disk space."""
        mock_disk_usage.return_value.free = 2 * 1024**3  # 2 GB free
        mock_disk_usage.return_value.total = 10 * 1024**3  # 10 GB total
        mock_disk_usage.return_value.used = 8 * 1024**3  # 8 GB used
        mock_disk_usage.return_value.percent = 80

        result = self.health_checker.check_disk_space(min_free_gb=1.0)

        require_runtime_instance(result, dict)
        require_keys(result, ("total_gb", "used_gb", "free_gb", "percent_used"))
        if not ((result["free_gb"]) >= (1.0)):
            raise AssertionError

    @patch("psutil.disk_usage")
    def test_check_disk_space_unhealthy(self, mock_disk_usage: Mock) -> None:
        """Test disk space check with low disk space."""
        mock_disk_usage.return_value.free = 0.5 * 1024**3  # 0.5 GB free
        mock_disk_usage.return_value.total = 10 * 1024**3  # 10 GB total
        mock_disk_usage.return_value.used = 9.5 * 1024**3  # 9.5 GB used
        mock_disk_usage.return_value.percent = 95

        with pytest.raises(HealthCheckError):
            self.health_checker.check_disk_space(min_free_gb=1.0)

    @patch("psutil.virtual_memory")
    def test_check_memory_usage_healthy(self, mock_virtual_memory: Mock) -> None:
        """Test memory usage check with healthy memory usage."""
        mock_memory = Mock()
        mock_memory.percent = 50.0
        mock_memory.total = 8 * 1024**3  # 8 GB total
        mock_memory.available = 4 * 1024**3  # 4 GB available
        mock_memory.used = 4 * 1024**3  # 4 GB used
        mock_virtual_memory.return_value = mock_memory

        result = self.health_checker.check_memory_usage(max_percent=90.0)

        require_runtime_instance(result, dict)
        require_keys(result, ("total_gb", "available_gb", "used_gb", "percent_used"))
        maximum_memory_percent = 90.0
        if not ((result["percent_used"]) <= maximum_memory_percent):
            raise AssertionError

    @patch("psutil.virtual_memory")
    def test_check_memory_usage_unhealthy(self, mock_virtual_memory: Mock) -> None:
        """Test memory usage check with high memory usage."""
        mock_memory = Mock()
        mock_memory.percent = 95.0
        mock_memory.total = 8 * 1024**3  # 8 GB total
        mock_memory.available = 0.4 * 1024**3  # 0.4 GB available
        mock_memory.used = 7.6 * 1024**3  # 7.6 GB used
        mock_virtual_memory.return_value = mock_memory

        with pytest.raises(HealthCheckError):
            self.health_checker.check_memory_usage(max_percent=90.0)

    @patch("psutil.cpu_percent")
    @patch("psutil.cpu_count")
    def test_check_cpu_usage_healthy(
        self,
        mock_cpu_count: Mock,
        mock_cpu_percent: Mock,
    ) -> None:
        """Test CPU usage check with healthy CPU usage."""
        mock_cpu_percent.return_value = 50.0
        mock_cpu_count.return_value = 4

        result = self.health_checker.check_cpu_usage(max_percent=95.0)

        require_runtime_instance(result, dict)
        require_keys(result, ("percent_used", "cpu_count"))
        maximum_cpu_percent = 95.0
        if not ((result["percent_used"]) <= maximum_cpu_percent):
            raise AssertionError
        expected_cpu_count = 4
        if not ((result["cpu_count"]) == expected_cpu_count):
            raise AssertionError

    @patch("psutil.cpu_percent")
    @patch("psutil.cpu_count")
    def test_check_cpu_usage_unhealthy(
        self,
        mock_cpu_count: Mock,
        mock_cpu_percent: Mock,
    ) -> None:
        """Test CPU usage check with high CPU usage."""
        mock_cpu_percent.return_value = 98.0
        mock_cpu_count.return_value = 4

        with pytest.raises(HealthCheckError):
            self.health_checker.check_cpu_usage(max_percent=95.0)

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_check_data_availability_healthy(
        self,
        mock_glob: Mock,
        mock_exists: Mock,
    ) -> None:
        """Test data availability check with available data."""
        mock_exists.return_value = True
        mock_files = [Mock()]
        mock_files[0].name = "test.parquet"
        mock_glob.return_value = mock_files

        result = self.health_checker.check_data_availability("test/data")

        require_runtime_instance(result, dict)
        require_keys(result, ("data_dir", "file_count", "sample_files"))
        if not ((result["file_count"]) == (1)):
            raise AssertionError

    @patch("pathlib.Path.exists")
    def test_check_data_availability_missing_dir(self, mock_exists: Mock) -> None:
        """Test data availability check with missing data directory."""
        mock_exists.return_value = False

        with pytest.raises(HealthCheckError):
            self.health_checker.check_data_availability("missing/data")


class TestPerformanceMetricsCollector(unittest.TestCase):
    """Test cases for PerformanceMetricsCollector."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.metrics_collector = PerformanceMetricsCollector(max_history=5)

    def test_init(self) -> None:
        """Test PerformanceMetricsCollector initialization."""
        require_runtime_instance(self.metrics_collector, PerformanceMetricsCollector)
        expected_history_limit = 5
        if not ((self.metrics_collector.max_history) == expected_history_limit):
            raise AssertionError

    def test_record_metric(self) -> None:
        """Test recording a metric."""
        self.metrics_collector.record_metric("test.metric", 42.5, {"tag": "value"})

        current_metrics = self.metrics_collector.get_current_metrics()
        if ("test.metric") not in (current_metrics):
            raise AssertionError
        expected_metric_value = 42.5
        if not ((current_metrics["test.metric"]["value"]) == expected_metric_value):
            raise AssertionError
        if not ((current_metrics["test.metric"]["tags"]) == ({"tag": "value"})):
            raise AssertionError

    def test_get_metric_history(self) -> None:
        """Test getting metric history."""
        # Record multiple values for the same metric
        for i in range(3):
            self.metrics_collector.record_metric("test.metric", float(i))

        history = self.metrics_collector.get_metric_history("test.metric")
        expected_sample_count = 3
        if not ((len(history)) == expected_sample_count):
            raise AssertionError
        if not ((history[0]["value"]) == (0.0)):
            raise AssertionError
        if not ((history[1]["value"]) == (1.0)):
            raise AssertionError
        expected_third_value = 2.0
        if not ((history[2]["value"]) == expected_third_value):
            raise AssertionError

    def test_history_limit(self) -> None:
        """Test that history is limited to max_history."""
        # Record more values than max_history
        for i in range(10):
            self.metrics_collector.record_metric("test.metric", float(i))

        history = self.metrics_collector.get_metric_history("test.metric")
        expected_retained_count = 5
        if not ((len(history)) == expected_retained_count):
            raise AssertionError  # Limited to max_history
        expected_oldest_value = 5.0
        if not ((history[0]["value"]) == expected_oldest_value):
            raise AssertionError  # Oldest values should be dropped
        expected_newest_value = 9.0
        if not ((history[4]["value"]) == expected_newest_value):
            raise AssertionError  # Newest values should be kept

    def test_get_metrics_summary(self) -> None:
        """Test getting metrics summary."""
        # Record some metrics
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.metrics_collector.record_metric("test.metric", value)

        summary = self.metrics_collector.get_metrics_summary()
        if ("test.metric") not in (summary):
            raise AssertionError

        metric_summary = summary["test.metric"]
        expected_current = 5.0
        if not ((metric_summary["current"]) == expected_current):
            raise AssertionError
        if not ((metric_summary["min"]) == (1.0)):
            raise AssertionError
        expected_maximum = 5.0
        if not ((metric_summary["max"]) == expected_maximum):
            raise AssertionError
        expected_average = 3.0
        if not ((metric_summary["avg"]) == expected_average):
            raise AssertionError
        expected_count = 5
        if not ((metric_summary["count"]) == expected_count):
            raise AssertionError


class TestUsageAnalytics(unittest.TestCase):
    """Test cases for UsageAnalytics."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_file = Path(self.temp_dir.name) / "usage.log"
        self.usage_analytics = UsageAnalytics(str(self.log_file))

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_init(self) -> None:
        """Test UsageAnalytics initialization."""
        require_runtime_instance(self.usage_analytics, UsageAnalytics)
        if not (self.log_file.exists()):
            raise AssertionError

    def test_log_user_action(self) -> None:
        """Test logging a user action."""
        self.usage_analytics.log_user_action(
            "user123",
            "view_table",
            "detailed_table",
            {"rows": 1000, "columns": 20},
        )

        # Check that the log file contains the event
        with Path(self.log_file).open() as f:
            content = f.read()
            require_keys(content, ("user123", "view_table", "detailed_table", "1000"))

    def test_get_usage_statistics(self) -> None:
        """Test getting usage statistics."""
        # Log some actions
        self.usage_analytics.log_user_action("user1", "view", "table1")
        self.usage_analytics.log_user_action("user1", "analyze", "table1")
        self.usage_analytics.log_user_action("user2", "view", "table2")

        stats = self.usage_analytics.get_usage_statistics()

        require_runtime_instance(stats, dict)
        require_keys(
            stats,
            (
                "total_events",
                "unique_users",
                "user_activity",
                "action_distribution",
                "resource_usage",
            ),
        )

        expected_event_count = 3
        if not ((stats["total_events"]) == expected_event_count):
            raise AssertionError
        expected_user_count = 2
        if not ((stats["unique_users"]) == expected_user_count):
            raise AssertionError
        expected_user_actions = 2
        if not ((stats["user_activity"]["user1"]) == expected_user_actions):
            raise AssertionError
        if not ((stats["user_activity"]["user2"]) == (1)):
            raise AssertionError


class TestAlertManager(unittest.TestCase):
    """Test cases for AlertManager."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.alert_file = Path(self.temp_dir.name) / "alerts.log"
        self.alert_manager = AlertManager(str(self.alert_file))

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def test_init(self) -> None:
        """Test AlertManager initialization."""
        require_runtime_instance(self.alert_manager, AlertManager)
        if not (self.alert_file.exists()):
            raise AssertionError

    def test_send_alert(self) -> None:
        """Test sending an alert."""
        self.alert_manager.send_alert(
            "test_alert",
            "This is a test alert",
            "warning",
            {"test_data": "value"},
        )

        # Check that the alert file contains the alert
        with Path(self.alert_file).open() as f:
            content = f.read()
            require_keys(
                content,
                ("test_alert", "This is a test alert", "warning", "value"),
            )

    def test_get_recent_alerts(self) -> None:
        """Test getting recent alerts."""
        # Send some alerts
        self.alert_manager.send_alert("alert1", "First alert", "info")
        self.alert_manager.send_alert("alert2", "Second alert", "warning")

        alerts = self.alert_manager.get_recent_alerts()

        require_runtime_instance(alerts, list)
        expected_alert_count = 2
        if not ((len(alerts)) == expected_alert_count):
            raise AssertionError

        # Check alert content
        if not ((alerts[0]["type"]) == ("alert1")):
            raise AssertionError
        if not ((alerts[0]["message"]) == ("First alert")):
            raise AssertionError
        if not ((alerts[0]["severity"]) == ("info")):
            raise AssertionError

        if not ((alerts[1]["type"]) == ("alert2")):
            raise AssertionError
        if not ((alerts[1]["message"]) == ("Second alert")):
            raise AssertionError
        if not ((alerts[1]["severity"]) == ("warning")):
            raise AssertionError


class TestMonitoringMiddleware(unittest.TestCase):
    """Test cases for MonitoringMiddleware."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.metrics_collector = PerformanceMetricsCollector()
        self.middleware = MonitoringMiddleware(self.metrics_collector)

    def test_init(self) -> None:
        """Test MonitoringMiddleware initialization."""
        require_runtime_instance(self.middleware, MonitoringMiddleware)
        if not ((self.middleware.metrics_collector) == (self.metrics_collector)):
            raise AssertionError

    def test_monitor_execution_time(self) -> None:
        """Test monitoring execution time."""

        @self.middleware.monitor_execution_time("test_function")
        def test_function() -> str:
            time.sleep(0.01)  # Sleep for 10ms
            return "result"

        result = test_function()

        if not ((result) == ("result")):
            raise AssertionError

        # Check that metrics were recorded
        current_metrics = self.metrics_collector.get_current_metrics()
        metric_name = "test_function.execution_time"
        if (metric_name) not in (current_metrics):
            raise AssertionError

        # The execution time should be approximately 0.01 seconds
        execution_time = current_metrics[metric_name]["value"]
        if not ((execution_time) > (0.0)):
            raise AssertionError
        if not ((execution_time) < (1.0)):
            raise AssertionError  # Should be much less than 1 second

    def test_monitor_execution_time_with_error(self) -> None:
        """Test monitoring execution time with function error."""

        @self.middleware.monitor_execution_time("failing_function")
        def failing_function() -> None:
            message = "Test error"
            raise HealthCheckError(message)

        with pytest.raises(HealthCheckError):
            failing_function()

        # Check that metrics were recorded with error status
        current_metrics = self.metrics_collector.get_current_metrics()
        metric_name = "failing_function.execution_time"
        if (metric_name) not in (current_metrics):
            raise AssertionError
        if not ((current_metrics[metric_name]["tags"]["status"]) == ("error")):
            raise AssertionError


if __name__ == "__main__":
    unittest.main()


def test_monitoring_preserves_base_exception_and_records_error() -> None:
    """Cancellation must retain its identity and record an error outcome."""
    collector = PerformanceMetricsCollector()
    middleware = MonitoringMiddleware(collector)
    cancellation = KeyboardInterrupt("synthetic cancellation")

    @middleware.monitor_execution_time("cancelled")
    def cancel() -> None:
        raise cancellation

    try:
        cancel()
    except KeyboardInterrupt as error:
        if error is not cancellation:
            raise AssertionError from error
    else:
        message = "Cancellation was swallowed"
        raise AssertionError(message)
    if collector.get_current_metrics()["cancelled.execution_time"]["tags"] != {
        "status": "error",
    }:
        raise AssertionError


def test_recent_alerts_honours_requested_hours(tmp_path: Path) -> None:
    """Return recent alerts while excluding old aware and legacy naive entries."""
    alert_file = tmp_path / "alerts.jsonl"
    now = datetime.now(UTC)
    records = [
        {"timestamp": (now - timedelta(hours=1)).isoformat(), "message": "recent"},
        {"timestamp": (now - timedelta(hours=25)).isoformat(), "message": "old"},
        {
            "timestamp": (datetime.now().astimezone() - timedelta(hours=25))
            .replace(tzinfo=None)
            .isoformat(),
            "message": "legacy-old",
        },
    ]
    alert_file.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    manager = AlertManager(str(alert_file))
    actual = manager.get_recent_alerts(hours=24)
    if actual != records[:1]:
        raise AssertionError(actual)


def test_usage_bounds_compare_instants_across_offsets(tmp_path: Path) -> None:
    """Filter offset-bearing timestamps by instant rather than lexical order."""
    log = tmp_path / "usage.jsonl"
    log.write_text(
        json.dumps(
            {
                "timestamp": "2026-01-02T10:00:00+10:00",
                "user_id": "synthetic-user",
                "action": "read",
                "resource": "fixture",
            },
        )
        + "\n",
    )
    statistics = UsageAnalytics(str(log)).get_usage_statistics(
        start_time="2026-01-02T01:00:00+00:00",
    )
    if statistics["total_events"] != 0:
        raise AssertionError(statistics)
