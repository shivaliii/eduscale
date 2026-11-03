"""Cloud experiment API routes — run experiments, view metrics, compare, export."""
import uuid
import csv
import io
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cloud_metrics import CloudExperiment, ExperimentStatus, CloudMetric
from app.schemas import ExperimentConfig
from app.services.experiment_service import (
    run_experiment, get_experiment_metrics, compare_experiments,
)

router = APIRouter(prefix="/experiments", tags=["Cloud Experiments"])


@router.post("/run")
def run_cloud_experiment(
    config: ExperimentConfig,
    db: Session = Depends(get_db),
):
    """Execute a cloud simulation experiment with the specified configuration."""
    try:
        experiment_id = run_experiment(db, config)
        experiment = db.query(CloudExperiment).filter(CloudExperiment.id == experiment_id).first()
        return {
            "experiment_id": str(experiment_id),
            "status": experiment.status.value,
            "results_summary": experiment.results_summary,
            "message": "Experiment completed successfully",
        }
    except Exception as e:
        raise HTTPException(500, f"Experiment failed: {str(e)}")


@router.get("")
def list_experiments(
    status: Optional[str] = None,
    scenario: Optional[str] = None,
    policy: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all experiments with optional filtering."""
    query = db.query(CloudExperiment).order_by(CloudExperiment.created_at.desc())
    if status:
        query = query.filter(CloudExperiment.status == status)
    if scenario:
        query = query.filter(CloudExperiment.scenario == scenario)
    if policy:
        query = query.filter(CloudExperiment.scaling_policy == policy)

    experiments = query.limit(limit).all()
    return [
        {
            "id": str(e.id), "name": e.name, "scenario": e.scenario,
            "scaling_policy": e.scaling_policy,
            "status": e.status.value if hasattr(e.status, 'value') else e.status,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "duration_seconds": e.duration_seconds,
            "results_summary": e.results_summary,
            "is_simulation": e.is_simulation,
            "created_at": e.created_at.isoformat(),
        }
        for e in experiments
    ]


@router.get("/{experiment_id}")
def get_experiment(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get experiment details."""
    exp = db.query(CloudExperiment).filter(CloudExperiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(404, "Experiment not found")
    return {
        "id": str(exp.id), "name": exp.name, "scenario": exp.scenario,
        "scaling_policy": exp.scaling_policy, "configuration": exp.configuration,
        "status": exp.status.value if hasattr(exp.status, 'value') else exp.status,
        "started_at": exp.started_at.isoformat() if exp.started_at else None,
        "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
        "duration_seconds": exp.duration_seconds,
        "results_summary": exp.results_summary,
        "is_simulation": exp.is_simulation,
    }


@router.get("/{experiment_id}/metrics")
def get_metrics(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get time-series metrics for an experiment."""
    exp = db.query(CloudExperiment).filter(CloudExperiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(404, "Experiment not found")
    return get_experiment_metrics(db, experiment_id)


@router.get("/compare/{reactive_id}/{predictive_id}")
def compare(
    reactive_id: uuid.UUID,
    predictive_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Compare reactive vs predictive experiment results."""
    result = compare_experiments(db, reactive_id, predictive_id)
    if not result:
        raise HTTPException(404, "One or both experiments not found")
    return result


@router.get("/{experiment_id}/export/csv")
def export_csv(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Export experiment metrics as CSV."""
    metrics = db.query(CloudMetric).filter(
        CloudMetric.experiment_id == experiment_id
    ).order_by(CloudMetric.timestamp).all()

    if not metrics:
        raise HTTPException(404, "No metrics found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp", "request_count", "predicted_requests",
        "avg_latency_ms", "p95_latency_ms", "p99_latency_ms",
        "cpu_utilization", "memory_utilization", "active_instances",
        "scaling_action", "sla_violated", "estimated_cost_usd",
    ])
    for m in metrics:
        writer.writerow([
            m.timestamp.isoformat(), m.request_count, m.predicted_requests,
            m.avg_latency_ms, m.p95_latency_ms, m.p99_latency_ms,
            m.cpu_utilization, m.memory_utilization, m.active_instances,
            m.scaling_action, m.sla_violated, m.estimated_cost_usd,
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=experiment_{experiment_id}.csv"},
    )


@router.get("/{experiment_id}/export/json")
def export_json(
    experiment_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Export experiment results and metrics as JSON."""
    exp = db.query(CloudExperiment).filter(CloudExperiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(404, "Experiment not found")

    metrics = get_experiment_metrics(db, experiment_id)
    data = {
        "experiment": {
            "id": str(exp.id), "name": exp.name,
            "scenario": exp.scenario, "scaling_policy": exp.scaling_policy,
            "configuration": exp.configuration,
            "results_summary": exp.results_summary,
            "is_simulation": exp.is_simulation,
        },
        "metrics": metrics,
    }

    output = io.BytesIO(json.dumps(data, indent=2).encode())
    return StreamingResponse(
        output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=experiment_{experiment_id}.json"},
    )


@router.get("/cloud/overview")
def cloud_overview(db: Session = Depends(get_db)):
    """Get cloud research overview metrics."""
    total = db.query(CloudExperiment).count()
    active = db.query(CloudExperiment).filter(
        CloudExperiment.status == ExperimentStatus.RUNNING
    ).count()

    # Get latest completed experiment metrics
    latest = db.query(CloudExperiment).filter(
        CloudExperiment.status == ExperimentStatus.COMPLETED
    ).order_by(CloudExperiment.completed_at.desc()).first()

    if latest and latest.results_summary:
        s = latest.results_summary
        return {
            "current_request_rate": s.get("total_requests", 0) / max(1, s.get("total_steps", 1)),
            "predicted_request_rate": 0,
            "avg_latency_ms": s.get("avg_latency_ms", 0),
            "p95_latency_ms": s.get("p95_latency_ms", 0),
            "cpu_utilization": s.get("avg_cpu", 0),
            "memory_utilization": s.get("avg_memory", 0),
            "estimated_cost_usd": s.get("estimated_cost_usd", 0),
            "sla_status": "healthy" if s.get("sla_violation_rate", 0) < 5 else "degraded",
            "active_experiments": active,
            "total_experiments": total,
        }

    return {
        "current_request_rate": 0, "predicted_request_rate": 0,
        "avg_latency_ms": 0, "p95_latency_ms": 0,
        "cpu_utilization": 0, "memory_utilization": 0,
        "estimated_cost_usd": 0, "sla_status": "no_data",
        "active_experiments": active, "total_experiments": total,
    }
