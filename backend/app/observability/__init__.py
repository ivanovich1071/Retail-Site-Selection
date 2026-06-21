"""Observability — request metrics with a Prometheus backend and a
dependency-free in-process fallback (counts + latency histograms).
"""
from backend.app.observability.metrics import (
    metrics, MetricsMiddleware, render_metrics, PROMETHEUS_AVAILABLE,
)

__all__ = ["metrics", "MetricsMiddleware", "render_metrics", "PROMETHEUS_AVAILABLE"]
