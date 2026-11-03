"""Workload and Cloud metrics models for research experiments."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Float, Integer, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSON
import enum

from app.database import Base


class WorkloadObservation(Base):
    """Records actual workload observations for analysis and training."""
    __tablename__ = "workload_observations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    cpu_utilization: Mapped[float] = mapped_column(Float, nullable=True)
    memory_utilization: Mapped[float] = mapped_column(Float, nullable=True)
    scenario: Mapped[str] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="simulation")
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )


class WorkloadForecast(Base):
    """Stores workload predictions from forecasting models."""
    __tablename__ = "workload_forecasts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    forecast_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    target_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    predicted_requests: Mapped[float] = mapped_column(Float, nullable=False)
    actual_requests: Mapped[int] = mapped_column(Integer, nullable=True)
    forecast_horizon_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=True)
    prediction_error: Mapped[float] = mapped_column(Float, nullable=True)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )


class ExperimentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CloudExperiment(Base):
    """Records cloud experiment configurations and results."""
    __tablename__ = "cloud_experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario: Mapped[str] = mapped_column(String(100), nullable=False)
    scaling_policy: Mapped[str] = mapped_column(String(50), nullable=False)  # reactive, predictive
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        SAEnum(ExperimentStatus), default=ExperimentStatus.PENDING
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    results_summary: Mapped[dict] = mapped_column(JSON, nullable=True)
    # results_summary: {
    #   "total_requests", "avg_latency_ms", "p95_latency_ms", "p99_latency_ms",
    #   "sla_violations", "total_scaling_actions", "avg_cpu", "avg_memory",
    #   "estimated_cost_usd", "prediction_mae", "prediction_rmse"
    # }
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CloudMetric(Base):
    """Time-series cloud performance metrics per experiment."""
    __tablename__ = "cloud_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    p95_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    p99_latency_ms: Mapped[float] = mapped_column(Float, nullable=True)
    cpu_utilization: Mapped[float] = mapped_column(Float, nullable=True)
    memory_utilization: Mapped[float] = mapped_column(Float, nullable=True)
    active_instances: Mapped[int] = mapped_column(Integer, default=1)
    scaling_action: Mapped[str] = mapped_column(String(50), nullable=True)  # scale_up, scale_down, none
    sla_violated: Mapped[bool] = mapped_column(Boolean, default=False)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=True)
    predicted_requests: Mapped[float] = mapped_column(Float, nullable=True)
    actual_requests: Mapped[int] = mapped_column(Integer, nullable=True)


class InferenceLog(Base):
    """Logs every inference request for latency and performance tracking."""
    __tablename__ = "inference_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    deployment_type: Mapped[str] = mapped_column(String(50), default="local")
    processing_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="success")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
