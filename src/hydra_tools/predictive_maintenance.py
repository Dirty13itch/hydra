"""
Predictive Maintenance Module for Hydra

Provides trend analysis and failure prediction capabilities:
- Disk fill-rate prediction
- VRAM exhaustion forecasting
- GPU thermal trend analysis
- Memory pressure prediction
- Cluster health aggregation

Uses Prometheus recording rules for real-time predictions.
"""

import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException


def sanitize_float(value: float) -> float:
    """Convert NaN/Inf to safe values for JSON serialization."""
    if value is None:
        return 0.0
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return value


# Configuration
PROMETHEUS_URL = "http://192.168.1.244:9090"


class PredictionSeverity(str, Enum):
    HEALTHY = "healthy"
    WATCH = "watch"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Prediction:
    """A single prediction result."""
    metric: str
    current_value: float
    predicted_value: float
    prediction_horizon: str  # e.g., "1h", "24h"
    severity: PredictionSeverity
    message: str
    action: Optional[str] = None
    labels: dict = field(default_factory=dict)


@dataclass
class DiskPrediction(Prediction):
    """Disk space prediction."""
    mountpoint: str = ""
    time_to_full_hours: Optional[float] = None


@dataclass
class VRAMPrediction(Prediction):
    """GPU VRAM prediction."""
    gpu_name: str = ""
    node: str = ""


@dataclass
class ThermalPrediction(Prediction):
    """GPU thermal prediction."""
    gpu_name: str = ""
    node: str = ""
    temp_change_rate: float = 0.0  # degrees per minute


@dataclass
class MemoryPrediction(Prediction):
    """System memory prediction."""
    node: str = ""


@dataclass
class ClusterHealthReport:
    """Aggregated cluster health with predictions."""
    timestamp: str
    overall_score: float
    status: PredictionSeverity
    disk_predictions: list[DiskPrediction]
    vram_predictions: list[VRAMPrediction]
    thermal_predictions: list[ThermalPrediction]
    memory_predictions: list[MemoryPrediction]
    active_alerts: int
    recommendations: list[str]


class PredictiveMaintenanceEngine:
    """
    Engine for predictive maintenance analysis.

    Queries Prometheus for trend data and generates predictions.
    """

    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self.prometheus_url = prometheus_url
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _query_prometheus(self, query: str) -> list[dict]:
        """Execute a Prometheus instant query."""
        try:
            response = await self.client.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query}
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
            return []
        except Exception as e:
            print(f"Prometheus query error: {e}")
            return []

    async def _query_prometheus_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "5m"
    ) -> list[dict]:
        """Execute a Prometheus range query."""
        try:
            response = await self.client.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start.isoformat() + "Z",
                    "end": end.isoformat() + "Z",
                    "step": step
                }
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                return data.get("data", {}).get("result", [])
            return []
        except Exception as e:
            print(f"Prometheus range query error: {e}")
            return []

    async def get_disk_predictions(self) -> list[DiskPrediction]:
        """Get disk space predictions for all mountpoints."""
        predictions = []

        # Query predicted usage in 24h
        results = await self._query_prometheus('disk:predicted_usage_24h:percent')
        time_to_full = await self._query_prometheus('disk:time_to_full:hours')

        # Create lookup for time_to_full
        ttf_map = {}
        for r in time_to_full:
            key = (r['metric'].get('instance', ''), r['metric'].get('mountpoint', ''))
            try:
                ttf_map[key] = sanitize_float(float(r['value'][1]))
            except (IndexError, ValueError):
                pass

        for result in results:
            metric = result.get('metric', {})
            instance = metric.get('instance', 'unknown')
            mountpoint = metric.get('mountpoint', '/')

            try:
                predicted = sanitize_float(float(result['value'][1]))
            except (IndexError, ValueError):
                continue

            if predicted <= 0:
                continue  # Skip invalid values

            # Determine severity
            if predicted > 95:
                severity = PredictionSeverity.CRITICAL
                message = f"Disk {mountpoint} predicted to be {predicted:.1f}% full in 24h"
                action = "Run emergency disk cleanup immediately"
            elif predicted > 90:
                severity = PredictionSeverity.WARNING
                message = f"Disk {mountpoint} predicted to be {predicted:.1f}% full in 24h"
                action = "Run disk cleanup or expand storage"
            elif predicted > 80:
                severity = PredictionSeverity.WATCH
                message = f"Disk {mountpoint} predicted to be {predicted:.1f}% full in 24h"
                action = "Monitor disk usage"
            else:
                severity = PredictionSeverity.HEALTHY
                message = f"Disk {mountpoint} healthy at {predicted:.1f}% predicted"
                action = None

            ttf = ttf_map.get((instance, mountpoint))

            predictions.append(DiskPrediction(
                metric="disk:predicted_usage_24h:percent",
                current_value=predicted - 5,  # Approximate current
                predicted_value=predicted,
                prediction_horizon="24h",
                severity=severity,
                message=message,
                action=action,
                labels=metric,
                mountpoint=mountpoint,
                time_to_full_hours=ttf
            ))

        return predictions

    async def get_vram_predictions(self) -> list[VRAMPrediction]:
        """Get GPU VRAM predictions."""
        predictions = []

        # Query both nvidia-smi and DCGM formats
        results = await self._query_prometheus('gpu:predicted_vram_1h:percent')
        results_dcgm = await self._query_prometheus('gpu:predicted_vram_1h_dcgm:percent')

        all_results = results + results_dcgm

        for result in all_results:
            metric = result.get('metric', {})
            gpu = metric.get('gpu', metric.get('GPU_I_ID', 'unknown'))
            instance = metric.get('instance', 'unknown')

            try:
                predicted = sanitize_float(float(result['value'][1]))
            except (IndexError, ValueError):
                continue

            if predicted > 95:
                severity = PredictionSeverity.CRITICAL
                message = f"GPU {gpu} VRAM predicted to exceed 95% in 1 hour"
                action = "Unload models or reduce batch size"
            elif predicted > 90:
                severity = PredictionSeverity.WARNING
                message = f"GPU {gpu} VRAM predicted to reach {predicted:.1f}% in 1 hour"
                action = "Monitor inference workload"
            elif predicted > 80:
                severity = PredictionSeverity.WATCH
                message = f"GPU {gpu} VRAM at {predicted:.1f}% predicted"
                action = None
            else:
                severity = PredictionSeverity.HEALTHY
                message = f"GPU {gpu} VRAM healthy"
                action = None

            predictions.append(VRAMPrediction(
                metric="gpu:predicted_vram_1h:percent",
                current_value=predicted - 2,
                predicted_value=predicted,
                prediction_horizon="1h",
                severity=severity,
                message=message,
                action=action,
                labels=metric,
                gpu_name=gpu,
                node=instance
            ))

        return predictions

    async def get_thermal_predictions(self) -> list[ThermalPrediction]:
        """Get GPU thermal predictions."""
        predictions = []

        # Query predicted temperatures
        results = await self._query_prometheus('gpu:predicted_temp_10m:celsius')
        results_dcgm = await self._query_prometheus('gpu:predicted_temp_10m_dcgm:celsius')

        # Query change rates
        change_rates = await self._query_prometheus('gpu:temp_change_rate:per_minute')
        change_rates_dcgm = await self._query_prometheus('gpu:temp_change_rate_dcgm:per_minute')

        # Build change rate map
        rate_map = {}
        for r in change_rates + change_rates_dcgm:
            key = r['metric'].get('gpu', r['metric'].get('GPU_I_ID', 'unknown'))
            try:
                rate_map[key] = sanitize_float(float(r['value'][1]))
            except (IndexError, ValueError):
                pass

        all_results = results + results_dcgm

        for result in all_results:
            metric = result.get('metric', {})
            gpu = metric.get('gpu', metric.get('GPU_I_ID', 'unknown'))
            instance = metric.get('instance', 'unknown')

            try:
                predicted = sanitize_float(float(result['value'][1]))
            except (IndexError, ValueError):
                continue

            change_rate = rate_map.get(gpu, 0.0)

            if predicted > 85:
                severity = PredictionSeverity.CRITICAL
                message = f"GPU {gpu} predicted to reach {predicted:.0f}°C in 10 minutes"
                action = "Reduce power limit or halt workload immediately"
            elif predicted > 80:
                severity = PredictionSeverity.WARNING
                message = f"GPU {gpu} predicted to reach {predicted:.0f}°C - thermal throttling risk"
                action = "Reduce workload or improve cooling"
            elif predicted > 70 or change_rate > 2:
                severity = PredictionSeverity.WATCH
                message = f"GPU {gpu} temperature trending up ({change_rate:+.1f}°C/min)"
                action = "Monitor thermal conditions"
            else:
                severity = PredictionSeverity.HEALTHY
                message = f"GPU {gpu} thermal conditions healthy ({predicted:.0f}°C predicted)"
                action = None

            predictions.append(ThermalPrediction(
                metric="gpu:predicted_temp_10m:celsius",
                current_value=predicted - (change_rate * 10),
                predicted_value=predicted,
                prediction_horizon="10m",
                severity=severity,
                message=message,
                action=action,
                labels=metric,
                gpu_name=gpu,
                node=instance,
                temp_change_rate=change_rate
            ))

        return predictions

    async def get_memory_predictions(self) -> list[MemoryPrediction]:
        """Get system memory predictions."""
        predictions = []

        results = await self._query_prometheus('node:predicted_memory_usage_1h:percent')

        for result in results:
            metric = result.get('metric', {})
            instance = metric.get('instance', 'unknown')

            try:
                predicted = sanitize_float(float(result['value'][1]))
            except (IndexError, ValueError):
                continue

            if predicted > 95:
                severity = PredictionSeverity.CRITICAL
                message = f"Memory exhaustion imminent on {instance}"
                action = "Kill memory-heavy processes or restart services"
            elif predicted > 90:
                severity = PredictionSeverity.WARNING
                message = f"Memory predicted to reach {predicted:.1f}% in 1 hour"
                action = "Investigate memory consumers"
            elif predicted > 80:
                severity = PredictionSeverity.WATCH
                message = f"Memory usage trending up ({predicted:.1f}% predicted)"
                action = "Monitor memory usage"
            else:
                severity = PredictionSeverity.HEALTHY
                message = f"Memory healthy on {instance}"
                action = None

            predictions.append(MemoryPrediction(
                metric="node:predicted_memory_usage_1h:percent",
                current_value=predicted - 5,
                predicted_value=predicted,
                prediction_horizon="1h",
                severity=severity,
                message=message,
                action=action,
                labels=metric,
                node=instance
            ))

        return predictions

    async def get_cluster_health_score(self) -> float:
        """Get the aggregate cluster health score (0-100)."""
        results = await self._query_prometheus('cluster:health_score:percent')

        if results:
            try:
                return sanitize_float(float(results[0]['value'][1]))
            except (IndexError, ValueError):
                pass

        return 100.0  # Default healthy

    async def get_active_alerts_count(self) -> int:
        """Get count of currently firing alerts."""
        try:
            response = await self.client.get(
                f"{self.prometheus_url}/api/v1/alerts"
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                alerts = data.get("data", {}).get("alerts", [])
                return len([a for a in alerts if a.get("state") == "firing"])
            return 0
        except Exception:
            return 0

    async def get_full_health_report(self) -> ClusterHealthReport:
        """Generate a comprehensive health report with all predictions."""
        # Gather all predictions concurrently
        disk_task = self.get_disk_predictions()
        vram_task = self.get_vram_predictions()
        thermal_task = self.get_thermal_predictions()
        memory_task = self.get_memory_predictions()
        score_task = self.get_cluster_health_score()
        alerts_task = self.get_active_alerts_count()

        (disk_preds, vram_preds, thermal_preds, memory_preds,
         score, alerts) = await asyncio.gather(
            disk_task, vram_task, thermal_task, memory_task,
            score_task, alerts_task
        )

        # Determine overall status
        all_severities = (
            [p.severity for p in disk_preds] +
            [p.severity for p in vram_preds] +
            [p.severity for p in thermal_preds] +
            [p.severity for p in memory_preds]
        )

        if PredictionSeverity.CRITICAL in all_severities:
            status = PredictionSeverity.CRITICAL
        elif PredictionSeverity.WARNING in all_severities:
            status = PredictionSeverity.WARNING
        elif PredictionSeverity.WATCH in all_severities:
            status = PredictionSeverity.WATCH
        else:
            status = PredictionSeverity.HEALTHY

        # Generate recommendations
        recommendations = []
        for p in disk_preds + vram_preds + thermal_preds + memory_preds:
            if p.action and p.severity in (PredictionSeverity.WARNING, PredictionSeverity.CRITICAL):
                recommendations.append(f"[{p.severity.value.upper()}] {p.action}")

        return ClusterHealthReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            overall_score=score,
            status=status,
            disk_predictions=disk_preds,
            vram_predictions=vram_preds,
            thermal_predictions=thermal_preds,
            memory_predictions=memory_preds,
            active_alerts=alerts,
            recommendations=list(set(recommendations))  # Dedupe
        )


# FastAPI Router
def create_predictive_router() -> APIRouter:
    """Create the predictive maintenance API router."""
    router = APIRouter(prefix="/predictive", tags=["predictive-maintenance"])
    engine = PredictiveMaintenanceEngine()

    @router.get("/health")
    async def get_health_report():
        """Get comprehensive predictive health report."""
        report = await engine.get_full_health_report()
        return {
            "timestamp": report.timestamp,
            "overall_score": report.overall_score,
            "status": report.status.value,
            "active_alerts": report.active_alerts,
            "summary": {
                "disk_issues": len([p for p in report.disk_predictions
                                   if p.severity != PredictionSeverity.HEALTHY]),
                "vram_issues": len([p for p in report.vram_predictions
                                   if p.severity != PredictionSeverity.HEALTHY]),
                "thermal_issues": len([p for p in report.thermal_predictions
                                      if p.severity != PredictionSeverity.HEALTHY]),
                "memory_issues": len([p for p in report.memory_predictions
                                     if p.severity != PredictionSeverity.HEALTHY]),
            },
            "recommendations": report.recommendations
        }

    @router.get("/disk")
    async def get_disk_predictions():
        """Get disk space predictions."""
        predictions = await engine.get_disk_predictions()
        return {
            "predictions": [
                {
                    "mountpoint": p.mountpoint,
                    "predicted_usage_24h": p.predicted_value,
                    "time_to_full_hours": p.time_to_full_hours,
                    "severity": p.severity.value,
                    "message": p.message,
                    "action": p.action,
                    "labels": p.labels
                }
                for p in predictions
            ]
        }

    @router.get("/vram")
    async def get_vram_predictions():
        """Get GPU VRAM predictions."""
        predictions = await engine.get_vram_predictions()
        return {
            "predictions": [
                {
                    "gpu": p.gpu_name,
                    "node": p.node,
                    "predicted_usage_1h": p.predicted_value,
                    "severity": p.severity.value,
                    "message": p.message,
                    "action": p.action
                }
                for p in predictions
            ]
        }

    @router.get("/thermal")
    async def get_thermal_predictions():
        """Get GPU thermal predictions."""
        predictions = await engine.get_thermal_predictions()
        return {
            "predictions": [
                {
                    "gpu": p.gpu_name,
                    "node": p.node,
                    "predicted_temp_10m": p.predicted_value,
                    "temp_change_rate_per_min": p.temp_change_rate,
                    "severity": p.severity.value,
                    "message": p.message,
                    "action": p.action
                }
                for p in predictions
            ]
        }

    @router.get("/memory")
    async def get_memory_predictions():
        """Get system memory predictions."""
        predictions = await engine.get_memory_predictions()
        return {
            "predictions": [
                {
                    "node": p.node,
                    "predicted_usage_1h": p.predicted_value,
                    "severity": p.severity.value,
                    "message": p.message,
                    "action": p.action
                }
                for p in predictions
            ]
        }

    @router.get("/score")
    async def get_cluster_score():
        """Get aggregate cluster health score."""
        score = await engine.get_cluster_health_score()

        if score >= 90:
            status = "excellent"
        elif score >= 80:
            status = "good"
        elif score >= 60:
            status = "degraded"
        else:
            status = "critical"

        return {
            "score": score,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    @router.get("/alerts/predictive")
    async def get_predictive_alerts():
        """Get currently firing predictive alerts."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{PROMETHEUS_URL}/api/v1/alerts"
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    alerts = data.get("data", {}).get("alerts", [])
                    predictive = [
                        a for a in alerts
                        if a.get("labels", {}).get("type") == "predictive"
                        and a.get("state") == "firing"
                    ]
                    return {
                        "total": len(predictive),
                        "alerts": [
                            {
                                "name": a.get("labels", {}).get("alertname"),
                                "severity": a.get("labels", {}).get("severity"),
                                "summary": a.get("annotations", {}).get("summary"),
                                "description": a.get("annotations", {}).get("description"),
                                "action": a.get("annotations", {}).get("action"),
                                "since": a.get("activeAt")
                            }
                            for a in predictive
                        ]
                    }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
