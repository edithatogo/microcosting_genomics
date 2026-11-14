# Copyright 2026 Dylan. SPDX-License-Identifier: Apache-2.0
"""Observed result records for local monitoring and log readers."""

from typing import Literal, NotRequired, TypedDict

from pydantic import ConfigDict, TypeAdapter, with_config


class HealthyCheck(TypedDict):
    """A callback result whose own payload is opaque to the health checker."""

    status: Literal["healthy"]
    result: object


class FailedCheck(TypedDict):
    """A failed callback with its visible error message."""

    status: Literal["unhealthy"]
    error: str


class HealthReport(TypedDict):
    """Combined local callback health, retaining every named result."""

    timestamp: str
    status: Literal["healthy", "unhealthy"]
    checks: dict[str, HealthyCheck | FailedCheck]


class MetricRecord(TypedDict):
    """One numeric sample and its original local tags."""

    timestamp: str
    value: float
    tags: dict[str, str]


class MetricSummary(TypedDict):
    """Summary of the retained numeric metric history."""

    current: float
    min: float
    max: float
    avg: float
    count: int


@with_config(ConfigDict(strict=True, extra="allow"))
class UsageEvent(TypedDict):
    """Fields actually required by usage aggregation; legacy details are optional."""

    timestamp: str
    user_id: str
    action: str
    resource: str
    details: NotRequired[dict[str, object]]


class TimeRange(TypedDict):
    """Caller-supplied inclusive usage query boundaries."""

    start: str | None
    end: str | None


class UsageStatistics(TypedDict):
    """Counts and query bounds returned by the local usage reader."""

    total_events: int
    unique_users: int
    user_activity: dict[str, int]
    action_distribution: dict[str, int]
    resource_usage: dict[str, int]
    time_range: TimeRange


USAGE_EVENT = TypeAdapter(UsageEvent)
LOG_RECORD = TypeAdapter(dict[str, object])


class DiskStatus(TypedDict):
    """Storage capacity observations in GiB and percent."""

    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


class MemoryStatus(TypedDict):
    """Memory observations in GiB and percent."""

    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float


class CPUStatus(TypedDict):
    """CPU percentage and the optional native processor count."""

    percent_used: float
    cpu_count: int | None


class DataStatus(TypedDict):
    """Prepared-data existence observations without reading private row values."""

    data_dir: str
    file_count: int
    sample_files: list[str]
