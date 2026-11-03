"""
Cloud experiment service — workload simulation, resource allocation,
reactive vs predictive autoscaling, metrics collection.

This is the core research experiment engine. It runs actual simulations
and records real metrics. No fabricated results.
"""
import uuid
import time
import math
import random
import threading
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.cloud_metrics import (
    CloudExperiment, ExperimentStatus, CloudMetric,
    WorkloadObservation, WorkloadForecast, InferenceLog,
)
from app.schemas import ExperimentConfig, ExperimentOut, ExperimentMetrics


# ────────────────── Workload Generators ──────────────────

def generate_workload(config: ExperimentConfig, duration_s: int, interval_s: int = 10) -> list[dict]:
    """Generate a workload trace based on the scenario."""
    rng = random.Random(config.random_seed)
    steps = duration_s // interval_s
    trace = []
    t = 0

    for i in range(steps):
        base = config.base_request_rate

        if config.scenario == "normal":
            # Gentle sinusoidal variation
            rate = base + base * 0.3 * math.sin(2 * math.pi * i / steps)
            rate += rng.gauss(0, base * 0.1)

        elif config.scenario == "increasing":
            # Linearly increasing
            rate = base * (1 + 2 * i / steps)
            rate += rng.gauss(0, base * 0.1)

        elif config.scenario == "burst":
            # Normal with sudden bursts
            rate = base + rng.gauss(0, base * 0.1)
            if 0.3 < (i / steps) < 0.4 or 0.7 < (i / steps) < 0.75:
                rate = base * config.burst_multiplier + rng.gauss(0, base * 0.2)

        elif config.scenario == "deadline":
            # Gradually increasing then spike near end
            progress = i / steps
            if progress < 0.6:
                rate = base * (1 + progress)
            else:
                rate = base * (1 + 3 * (progress - 0.6) / 0.4)
            rate += rng.gauss(0, base * 0.15)

        elif config.scenario == "low":
            # Very low traffic with occasional small bumps
            rate = base * 0.2 + rng.gauss(0, base * 0.05)
            if rng.random() < 0.1:
                rate = base * 0.5

        elif config.scenario == "mixed":
            # Combination of patterns
            progress = i / steps
            if progress < 0.2:
                rate = base
            elif progress < 0.4:
                rate = base * (1 + 2 * (progress - 0.2) / 0.2)
            elif progress < 0.5:
                rate = base * config.burst_multiplier
            elif progress < 0.7:
                rate = base * 0.5
            else:
                rate = base * (1 + (progress - 0.7) / 0.3)
            rate += rng.gauss(0, base * 0.1)
        else:
            rate = base

        rate = max(1, rate)
        trace.append({
            "step": i,
            "time_s": t,
            "request_rate": round(rate, 2),
        })
        t += interval_s

    return trace


# ────────────────── Workload Forecasting ──────────────────

class WorkloadForecaster:
    """Simple moving-average + trend forecaster for workload prediction."""

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.history: list[float] = []

    def observe(self, value: float):
        self.history.append(value)

    def predict(self, horizon_steps: int = 1) -> tuple[float, float, float]:
        """Returns (prediction, lower_bound, upper_bound)."""
        if len(self.history) < 2:
            val = self.history[-1] if self.history else 10.0
            return val, val * 0.8, val * 1.2

        window = self.history[-self.window_size:]
        avg = np.mean(window)

        # Simple trend estimation
        if len(window) >= 2:
            trend = (window[-1] - window[0]) / len(window)
        else:
            trend = 0

        prediction = avg + trend * horizon_steps
        std = np.std(window) if len(window) > 1 else avg * 0.1
        prediction = max(1, prediction)

        return (
            round(prediction, 2),
            round(max(1, prediction - 1.96 * std), 2),
            round(prediction + 1.96 * std, 2),
        )


# ────────────────── Inference Simulator ──────────────────

def simulate_inference_latency(
    request_rate: float, active_instances: int,
    base_latency_ms: float = 50.0, rng: random.Random = None
) -> tuple[float, float, float]:
    """
    Simulate inference latency based on load and capacity.
    Returns (avg_latency, p95_latency, p99_latency).
    """
    if rng is None:
        rng = random.Random()

    capacity_per_instance = 15.0  # requests per interval per instance
    total_capacity = active_instances * capacity_per_instance
    load_factor = request_rate / total_capacity if total_capacity > 0 else 10

    # Latency increases with load (M/M/1 queueing approximation)
    if load_factor >= 1.0:
        avg_latency = base_latency_ms * (5 + 10 * (load_factor - 1))
    else:
        avg_latency = base_latency_ms / (1 - load_factor * 0.8 + 0.01)

    avg_latency = max(base_latency_ms, avg_latency)
    avg_latency += rng.gauss(0, base_latency_ms * 0.1)
    avg_latency = max(10, avg_latency)

    # p95 and p99
    p95 = avg_latency * (1.5 + 0.5 * load_factor)
    p99 = avg_latency * (2.0 + load_factor)

    return round(avg_latency, 2), round(p95, 2), round(p99, 2)


def simulate_resource_utilization(
    request_rate: float, active_instances: int, rng: random.Random = None
) -> tuple[float, float]:
    """Simulate CPU and memory utilization. Returns (cpu%, memory%)."""
    if rng is None:
        rng = random.Random()

    capacity = active_instances * 15.0
    load = request_rate / capacity if capacity > 0 else 1.0

    cpu = min(98, max(5, load * 70 + rng.gauss(0, 5)))
    memory = min(95, max(15, 30 + load * 40 + rng.gauss(0, 3)))

    return round(cpu, 1), round(memory, 1)


# ────────────────── Resource Allocation Policies ──────────────────

class ReactivePolicy:
    """Reactive autoscaling — scale based on current observed metrics."""

    def __init__(self, config: ExperimentConfig):
        self.min_instances = config.min_instances
        self.max_instances = config.max_instances
        self.cooldown = config.scaling_cooldown_seconds
        self.current_instances = config.min_instances
        self.last_scale_time = 0
        self.scale_up_threshold = 70.0   # CPU %
        self.scale_down_threshold = 30.0

    def decide(self, step_time: float, cpu: float, memory: float, request_rate: float) -> tuple[int, str]:
        """Returns (new_instance_count, action)."""
        if step_time - self.last_scale_time < self.cooldown:
            return self.current_instances, "cooldown"

        action = "none"
        new_count = self.current_instances

        if cpu > self.scale_up_threshold or memory > 85:
            new_count = min(self.max_instances, self.current_instances + 1)
            if new_count != self.current_instances:
                action = "scale_up"
                self.last_scale_time = step_time

        elif cpu < self.scale_down_threshold and memory < 40:
            new_count = max(self.min_instances, self.current_instances - 1)
            if new_count != self.current_instances:
                action = "scale_down"
                self.last_scale_time = step_time

        self.current_instances = new_count
        return new_count, action


class PredictivePolicy:
    """Predictive autoscaling — scale based on forecasted workload."""

    def __init__(self, config: ExperimentConfig):
        self.min_instances = config.min_instances
        self.max_instances = config.max_instances
        self.cooldown = config.scaling_cooldown_seconds
        self.current_instances = config.min_instances
        self.last_scale_time = 0
        self.capacity_per_instance = 15.0
        self.safety_margin = 1.3  # 30% headroom

    def decide(
        self, step_time: float, predicted_rate: float,
        cpu: float, request_rate: float
    ) -> tuple[int, str]:
        """Use predicted demand to proactively allocate resources."""
        if step_time - self.last_scale_time < self.cooldown:
            return self.current_instances, "cooldown"

        # Estimate required instances from prediction
        required = math.ceil(
            (predicted_rate * self.safety_margin) / self.capacity_per_instance
        )
        required = max(self.min_instances, min(self.max_instances, required))

        action = "none"
        if required > self.current_instances:
            action = "scale_up"
            self.last_scale_time = step_time
        elif required < self.current_instances and cpu < 35:
            action = "scale_down"
            self.last_scale_time = step_time
            required = max(self.min_instances, self.current_instances - 1)

        self.current_instances = required
        return required, action


# ────────────────── Cost Estimation ──────────────────

def estimate_cost(active_instances: int, interval_seconds: int, deployment_type: str = "ec2") -> float:
    """Estimate cloud cost for the interval. Uses configurable hourly rates."""
    hourly_rates = {
        "ec2": 0.0416,       # t3.medium ~$0.0416/hr
        "ecs_fargate": 0.05, # ~$0.05/hr for 1 vCPU, 2GB
        "lambda": 0.00,      # Per-request pricing handled separately
    }
    rate = hourly_rates.get(deployment_type, 0.0416)
    hours = interval_seconds / 3600
    return round(active_instances * rate * hours, 6)


# ────────────────── Experiment Runner ──────────────────

def run_experiment(db: Session, config: ExperimentConfig) -> uuid.UUID:
    """Execute a complete cloud experiment and store all metrics."""

    # Create experiment record
    experiment = CloudExperiment(
        name=config.name,
        scenario=config.scenario,
        scaling_policy=config.scaling_policy,
        configuration=config.model_dump(),
        status=ExperimentStatus.RUNNING,
        started_at=datetime.utcnow(),
        is_simulation=True,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    try:
        interval_s = 10  # 10-second intervals
        workload = generate_workload(config, config.duration_seconds, interval_s)
        rng = random.Random(config.random_seed)
        forecaster = WorkloadForecaster(window_size=5)

        # Select policy
        if config.scaling_policy == "predictive":
            policy = PredictivePolicy(config)
        else:
            policy = ReactivePolicy(config)

        total_requests = 0
        all_latencies = []
        sla_violations = 0
        total_scaling_actions = 0
        total_cost = 0.0
        all_cpu = []
        all_memory = []
        prediction_errors = []

        for step in workload:
            request_rate = step["request_rate"]
            step_time = step["time_s"]
            total_requests += int(request_rate)

            # Forecaster observes current workload
            forecaster.observe(request_rate)
            pred, pred_lower, pred_upper = forecaster.predict(
                horizon_steps=max(1, config.forecast_horizon_seconds // interval_s)
            )

            # Resource allocation decision
            current_instances = policy.current_instances
            cpu, memory = simulate_resource_utilization(request_rate, current_instances, rng)

            if config.scaling_policy == "predictive":
                new_instances, action = policy.decide(step_time, pred, cpu, request_rate)
            else:
                new_instances, action = policy.decide(step_time, cpu, memory, request_rate)

            # Simulate latency with NEW instance count
            avg_lat, p95_lat, p99_lat = simulate_inference_latency(
                request_rate, new_instances, rng=rng
            )
            all_latencies.append(avg_lat)
            all_cpu.append(cpu)
            all_memory.append(memory)

            # SLA check
            sla_violated = p95_lat > config.sla_latency_ms
            if sla_violated:
                sla_violations += 1

            if action in ("scale_up", "scale_down"):
                total_scaling_actions += 1

            # Cost
            step_cost = estimate_cost(new_instances, interval_s)
            total_cost += step_cost

            # Track prediction error (for next step)
            if len(workload) > step["step"] + 1:
                actual_next = workload[step["step"] + 1]["request_rate"]
                prediction_errors.append(abs(pred - actual_next))

            # Record metric
            timestamp = experiment.started_at + timedelta(seconds=step_time)
            metric = CloudMetric(
                experiment_id=experiment.id,
                timestamp=timestamp,
                request_count=int(request_rate),
                avg_latency_ms=avg_lat,
                p95_latency_ms=p95_lat,
                p99_latency_ms=p99_lat,
                cpu_utilization=cpu,
                memory_utilization=memory,
                active_instances=new_instances,
                scaling_action=action if action != "none" else None,
                sla_violated=sla_violated,
                estimated_cost_usd=step_cost,
                predicted_requests=pred,
                actual_requests=int(request_rate),
            )
            db.add(metric)

            # Record workload observation
            obs = WorkloadObservation(
                timestamp=timestamp,
                request_count=int(request_rate),
                interval_seconds=interval_s,
                avg_latency_ms=avg_lat,
                cpu_utilization=cpu,
                memory_utilization=memory,
                scenario=config.scenario,
                source="simulation",
                experiment_id=experiment.id,
            )
            db.add(obs)

            # Record forecast
            forecast = WorkloadForecast(
                forecast_timestamp=timestamp,
                target_timestamp=timestamp + timedelta(seconds=config.forecast_horizon_seconds),
                predicted_requests=pred,
                actual_requests=int(request_rate),
                forecast_horizon_seconds=config.forecast_horizon_seconds,
                model_version="moving_average_v1",
                prediction_error=abs(pred - request_rate),
                experiment_id=experiment.id,
            )
            db.add(forecast)

        # Compute summary
        mae = round(np.mean(prediction_errors), 2) if prediction_errors else 0
        rmse = round(np.sqrt(np.mean([e**2 for e in prediction_errors])), 2) if prediction_errors else 0

        all_lat_arr = np.array(all_latencies)
        results_summary = {
            "total_requests": total_requests,
            "avg_latency_ms": round(float(np.mean(all_lat_arr)), 2),
            "median_latency_ms": round(float(np.median(all_lat_arr)), 2),
            "p95_latency_ms": round(float(np.percentile(all_lat_arr, 95)), 2),
            "p99_latency_ms": round(float(np.percentile(all_lat_arr, 99)), 2),
            "sla_violations": sla_violations,
            "sla_violation_rate": round(sla_violations / len(workload) * 100, 2) if workload else 0,
            "total_scaling_actions": total_scaling_actions,
            "avg_cpu": round(float(np.mean(all_cpu)), 1),
            "avg_memory": round(float(np.mean(all_memory)), 1),
            "max_cpu": round(float(np.max(all_cpu)), 1),
            "max_memory": round(float(np.max(all_memory)), 1),
            "estimated_cost_usd": round(total_cost, 4),
            "prediction_mae": mae,
            "prediction_rmse": rmse,
            "total_steps": len(workload),
            "interval_seconds": interval_s,
            "final_instances": policy.current_instances,
        }

        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.utcnow()
        experiment.duration_seconds = config.duration_seconds
        experiment.results_summary = results_summary

        db.commit()
        return experiment.id

    except Exception as e:
        experiment.status = ExperimentStatus.FAILED
        experiment.results_summary = {"error": str(e)}
        experiment.completed_at = datetime.utcnow()
        db.commit()
        raise


def get_experiment_metrics(db: Session, experiment_id: uuid.UUID) -> dict:
    """Retrieve time-series metrics for an experiment."""
    metrics = db.query(CloudMetric).filter(
        CloudMetric.experiment_id == experiment_id
    ).order_by(CloudMetric.timestamp).all()

    return {
        "experiment_id": str(experiment_id),
        "timestamps": [m.timestamp.isoformat() for m in metrics],
        "request_counts": [m.request_count for m in metrics],
        "predicted_requests": [m.predicted_requests or 0 for m in metrics],
        "avg_latencies": [m.avg_latency_ms or 0 for m in metrics],
        "p95_latencies": [m.p95_latency_ms or 0 for m in metrics],
        "p99_latencies": [m.p99_latency_ms or 0 for m in metrics],
        "cpu_utilizations": [m.cpu_utilization or 0 for m in metrics],
        "memory_utilizations": [m.memory_utilization or 0 for m in metrics],
        "active_instances": [m.active_instances for m in metrics],
        "scaling_actions": [m.scaling_action or "none" for m in metrics],
        "sla_violations": [m.sla_violated for m in metrics],
        "costs": [m.estimated_cost_usd or 0 for m in metrics],
    }


def compare_experiments(db: Session, reactive_id: uuid.UUID, predictive_id: uuid.UUID) -> dict:
    """Compare reactive and predictive experiment results."""
    reactive = db.query(CloudExperiment).filter(CloudExperiment.id == reactive_id).first()
    predictive = db.query(CloudExperiment).filter(CloudExperiment.id == predictive_id).first()

    if not reactive or not predictive:
        return None

    reactive_metrics = get_experiment_metrics(db, reactive_id)
    predictive_metrics = get_experiment_metrics(db, predictive_id)

    r_summary = reactive.results_summary or {}
    p_summary = predictive.results_summary or {}

    comparison = {
        "latency_improvement_pct": _pct_change(r_summary.get("avg_latency_ms", 0), p_summary.get("avg_latency_ms", 0)),
        "p95_improvement_pct": _pct_change(r_summary.get("p95_latency_ms", 0), p_summary.get("p95_latency_ms", 0)),
        "sla_violation_diff": (r_summary.get("sla_violations", 0) - p_summary.get("sla_violations", 0)),
        "cost_diff_usd": round(r_summary.get("estimated_cost_usd", 0) - p_summary.get("estimated_cost_usd", 0), 4),
        "scaling_actions_diff": r_summary.get("total_scaling_actions", 0) - p_summary.get("total_scaling_actions", 0),
    }

    return {
        "reactive": {
            "experiment": _experiment_dict(reactive),
            "metrics": reactive_metrics,
        },
        "predictive": {
            "experiment": _experiment_dict(predictive),
            "metrics": predictive_metrics,
        },
        "comparison": comparison,
    }


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0
    return round((old - new) / old * 100, 2)


def _experiment_dict(exp: CloudExperiment) -> dict:
    return {
        "id": str(exp.id),
        "name": exp.name,
        "scenario": exp.scenario,
        "scaling_policy": exp.scaling_policy,
        "configuration": exp.configuration,
        "status": exp.status.value if hasattr(exp.status, 'value') else exp.status,
        "started_at": exp.started_at.isoformat() if exp.started_at else None,
        "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
        "duration_seconds": exp.duration_seconds,
        "results_summary": exp.results_summary,
        "is_simulation": exp.is_simulation,
    }
