from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Severity = Literal["low", "medium", "high", "critical"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TimeRange(StrictModel):
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def ordered(self):
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("Use timezone-aware timestamps")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must precede end_time")
        return self


class Filters(StrictModel):
    asset_ids: list[str] = Field(default_factory=list, max_length=100)
    unit: str | None = None
    site: str | None = None
    time_range: TimeRange | None = None
    severity: list[Severity] = Field(default_factory=list)
    alarm_types: list[Literal["process", "safety", "device"]] = Field(default_factory=list)


class SummaryRequest(Filters):
    group_by: list[Literal["asset_id", "asset_name", "alarm_name", "severity", "unit", "site"]] = (
        Field(default=["alarm_name"])
    )
    kpis: list[
        Literal[
            "alarm_count",
            "critical_count",
            "recurring_rate",
            "avg_ack_delay",
            "suppression_candidate_rate",
        ]
    ] = Field(default=["alarm_count"])


class TrendsRequest(Filters):
    bucket: Literal["hourly", "daily", "weekly"] = "daily"
    metrics: list[Literal["alarm_count", "avg_ack_delay"]] = Field(default=["alarm_count"])


class CorrelationRequest(Filters):
    correlation_method: Literal["cooccurrence"] = "cooccurrence"
    lag_window_minutes: int = Field(default=15, ge=1, le=1440)
    severity_threshold: Severity = "medium"
    min_support: int = Field(default=1, ge=1)


class FloodRequest(Filters):
    threshold_count: int = Field(default=10, ge=1)
    rolling_window_minutes: int = Field(default=10, ge=1, le=1440)


class RationalizationRequest(Filters):
    recurrence_threshold: int = Field(default=5, ge=2)
    stale_minutes_threshold: int = Field(default=180, ge=1)


class AlarmRequest(StrictModel):
    alarm_id: str = Field(min_length=1, max_length=100)


class RecommendationRequest(AlarmRequest):
    include_related: bool = False
    include_asset_context: bool = False
    include_historical_pattern: bool = False


CalculationType = Literal[
    "alarm_flood_index",
    "critical_alarm_density",
    "operator_response_efficiency",
    "nuisance_alarm_score",
]


class CalculationFilters(StrictModel):
    unit: str | None = None
    site: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None

    @model_validator(mode="after")
    def ordered(self):
        if bool(self.start_time) != bool(self.end_time):
            raise ValueError("Supply both start_time and end_time")
        if self.start_time and self.end_time:
            TimeRange(start_time=self.start_time, end_time=self.end_time)
        return self


class GenerateRequest(StrictModel):
    calculation_type: CalculationType
    filters: CalculationFilters = Field(default_factory=CalculationFilters)


class ExecuteRequest(StrictModel):
    calculation_id: str = Field(min_length=1)
    filters: CalculationFilters = Field(default_factory=CalculationFilters)


class ToolResult(StrictModel):
    """Stable MCP output envelope; payload schema depends on the documented API operation."""

    data: dict[str, Any]
    trace_id: str
    api_status: int = 200
    retries: int = 0


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9-]{1,64}$")
    degraded_demo: bool = False
