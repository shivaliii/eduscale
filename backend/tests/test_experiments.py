"""
Tests for cloud experiment API endpoints.

Covers:
  - POST /api/v1/experiments/run — run experiment with different scenarios/policies
  - GET /api/v1/experiments — list experiments
  - GET /api/v1/experiments/{id} — get experiment detail
  - GET /api/v1/experiments/{id}/metrics — get time-series metrics
  - GET /api/v1/experiments/compare/{r_id}/{p_id} — compare experiments
  - GET /api/v1/experiments/{id}/export/csv — CSV export
  - GET /api/v1/experiments/{id}/export/json — JSON export
  - GET /api/v1/experiments/cloud/overview — cloud overview stats

All experiments use the simulation engine (no real cloud deployment).
Results are actual simulation outputs — not fabricated.
"""
import pytest


class TestCloudOverview:
    """Tests for the cloud overview endpoint."""

    def test_get_overview(self, client, seeded_db):
        """Cloud overview returns platform health stats."""
        response = client.get("/api/v1/experiments/cloud/overview")
        assert response.status_code == 200
        data = response.json()

        assert "current_request_rate" in data
        assert "predicted_request_rate" in data
        assert "avg_latency_ms" in data
        assert "p95_latency_ms" in data
        assert "cpu_utilization" in data
        assert "memory_utilization" in data
        assert "estimated_cost_usd" in data
        assert "sla_status" in data
        assert "total_experiments" in data


class TestRunExperiment:
    """Tests for running experiments."""

    def test_run_reactive_normal(self, client, seeded_db):
        """Run a reactive scaling experiment with normal workload."""
        response = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Test-Reactive-Normal",
                "scenario": "normal",
                "scaling_policy": "reactive",
                "duration_seconds": 60,
                "base_request_rate": 20,
                "burst_multiplier": 2.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 5,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "experiment_id" in data
        assert data["status"] == "completed"
        assert "results_summary" in data
        assert data["message"] == "Experiment completed successfully"

        # Verify results have expected metrics
        summary = data["results_summary"]
        assert "avg_latency_ms" in summary
        assert "total_requests" in summary
        assert "sla_violations" in summary
        assert "total_cost" in summary
        assert summary["avg_latency_ms"] > 0
        assert summary["total_requests"] > 0

    def test_run_predictive_burst(self, client, seeded_db):
        """Run a predictive scaling experiment with burst workload."""
        response = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Test-Predictive-Burst",
                "scenario": "burst",
                "scaling_policy": "predictive",
                "duration_seconds": 60,
                "base_request_rate": 20,
                "burst_multiplier": 3.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 5,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_run_deadline_scenario(self, client, seeded_db):
        """Run an experiment with deadline (assessment) workload pattern."""
        response = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Test-Deadline",
                "scenario": "deadline",
                "scaling_policy": "predictive",
                "duration_seconds": 60,
                "base_request_rate": 15,
                "burst_multiplier": 4.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 8,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"


class TestListExperiments:
    """Tests for experiment listing."""

    def test_list_experiments(self, client, seeded_db):
        """Can list all experiments."""
        # Run one first
        client.post(
            "/api/v1/experiments/run",
            json={
                "name": "List-Test",
                "scenario": "low",
                "scaling_policy": "reactive",
                "duration_seconds": 30,
                "base_request_rate": 10,
                "burst_multiplier": 2.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 3,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )

        response = client.get("/api/v1/experiments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        exp = data[0]
        assert "id" in exp
        assert "name" in exp
        assert "scenario" in exp
        assert "scaling_policy" in exp
        assert "status" in exp


class TestExperimentMetrics:
    """Tests for experiment metrics retrieval."""

    def test_get_metrics(self, client, seeded_db):
        """Can retrieve time-series metrics for an experiment."""
        # Run experiment
        run_resp = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Metrics-Test",
                "scenario": "normal",
                "scaling_policy": "reactive",
                "duration_seconds": 60,
                "base_request_rate": 20,
                "burst_multiplier": 2.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 5,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        exp_id = run_resp.json()["experiment_id"]

        # Get metrics
        response = client.get(f"/api/v1/experiments/{exp_id}/metrics")
        assert response.status_code == 200
        data = response.json()

        assert "experiment_id" in data
        assert "timestamps" in data
        assert "request_counts" in data
        assert "predicted_requests" in data
        assert "avg_latencies" in data
        assert "p95_latencies" in data
        assert "p99_latencies" in data
        assert "cpu_utilizations" in data
        assert "memory_utilizations" in data
        assert "active_instances" in data
        assert "scaling_actions" in data
        assert "sla_violations" in data
        assert "costs" in data

        # All arrays should have the same length
        n = len(data["timestamps"])
        assert n > 0
        assert len(data["request_counts"]) == n
        assert len(data["avg_latencies"]) == n
        assert len(data["active_instances"]) == n


class TestCompareExperiments:
    """Tests for experiment comparison."""

    def test_compare_reactive_vs_predictive(self, client, seeded_db):
        """Can compare reactive vs predictive experiments."""
        # Run reactive
        r_resp = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Compare-Reactive",
                "scenario": "burst",
                "scaling_policy": "reactive",
                "duration_seconds": 60,
                "base_request_rate": 25,
                "burst_multiplier": 3.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 5,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        r_id = r_resp.json()["experiment_id"]

        # Run predictive with same config
        p_resp = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Compare-Predictive",
                "scenario": "burst",
                "scaling_policy": "predictive",
                "duration_seconds": 60,
                "base_request_rate": 25,
                "burst_multiplier": 3.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 5,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        p_id = p_resp.json()["experiment_id"]

        # Compare
        response = client.get(
            f"/api/v1/experiments/compare/{r_id}/{p_id}"
        )
        assert response.status_code == 200
        data = response.json()

        assert "reactive" in data
        assert "predictive" in data
        assert "comparison" in data

        comp = data["comparison"]
        assert "latency_improvement_pct" in comp
        assert "p95_improvement_pct" in comp
        assert "sla_violation_diff" in comp
        assert "cost_diff_usd" in comp
        assert "scaling_actions_diff" in comp


class TestExperimentExport:
    """Tests for CSV/JSON export."""

    def test_export_csv(self, client, seeded_db):
        """Can export experiment metrics as CSV."""
        # Run experiment
        run_resp = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Export-CSV-Test",
                "scenario": "normal",
                "scaling_policy": "reactive",
                "duration_seconds": 30,
                "base_request_rate": 10,
                "burst_multiplier": 2.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 3,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        exp_id = run_resp.json()["experiment_id"]

        response = client.get(f"/api/v1/experiments/{exp_id}/export/csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_export_json(self, client, seeded_db):
        """Can export experiment metrics as JSON."""
        run_resp = client.post(
            "/api/v1/experiments/run",
            json={
                "name": "Export-JSON-Test",
                "scenario": "normal",
                "scaling_policy": "reactive",
                "duration_seconds": 30,
                "base_request_rate": 10,
                "burst_multiplier": 2.0,
                "forecast_horizon_seconds": 30,
                "min_instances": 1,
                "max_instances": 3,
                "sla_latency_ms": 200,
                "scaling_cooldown_seconds": 10,
                "random_seed": 42,
            },
        )
        exp_id = run_resp.json()["experiment_id"]

        response = client.get(f"/api/v1/experiments/{exp_id}/export/json")
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

