"""Metrics collection — Prometheus if installed, else an in-process registry.

Exposes a Starlette middleware that counts requests and records latency per
method+path-template+status, and a render function that returns Prometheus text
exposition format (works in both backends).
"""
import logging
import time
from collections import defaultdict
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except Exception:  # noqa: BLE001
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


class _FallbackMetrics:
    """Minimal counter/latency store with Prometheus-text rendering."""

    def __init__(self) -> None:
        self.requests: Dict[Tuple[str, str, int], int] = defaultdict(int)
        self.latency_sum: Dict[Tuple[str, str], float] = defaultdict(float)
        self.latency_count: Dict[Tuple[str, str], int] = defaultdict(int)

    def observe(self, method: str, path: str, status: int, dur_s: float) -> None:
        self.requests[(method, path, status)] += 1
        self.latency_sum[(method, path)] += dur_s
        self.latency_count[(method, path)] += 1

    def render(self) -> str:
        lines = [
            "# HELP http_requests_total Total HTTP requests",
            "# TYPE http_requests_total counter",
        ]
        for (m, p, s), c in sorted(self.requests.items()):
            lines.append(f'http_requests_total{{method="{m}",path="{p}",status="{s}"}} {c}')
        lines += [
            "# HELP http_request_duration_seconds_sum Sum of request durations",
            "# TYPE http_request_duration_seconds_sum counter",
        ]
        for (m, p), total in sorted(self.latency_sum.items()):
            lines.append(f'http_request_duration_seconds_sum{{method="{m}",path="{p}"}} {total:.4f}')
            lines.append(
                f'http_request_duration_seconds_count{{method="{m}",path="{p}"}} {self.latency_count[(m, p)]}'
            )
        return "\n".join(lines) + "\n"


class _PromMetrics:
    def __init__(self) -> None:
        self._counter = Counter(
            "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
        )
        self._hist = Histogram(
            "http_request_duration_seconds", "HTTP request latency", ["method", "path"]
        )

    def observe(self, method: str, path: str, status: int, dur_s: float) -> None:
        self._counter.labels(method, path, str(status)).inc()
        self._hist.labels(method, path).observe(dur_s)

    def render(self) -> str:
        return generate_latest().decode("utf-8")


metrics = _PromMetrics() if PROMETHEUS_AVAILABLE else _FallbackMetrics()


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t0 = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            dur = time.perf_counter() - t0
            try:
                metrics.observe(request.method, _route_template(request), status, dur)
            except Exception:  # noqa: BLE001
                pass


def render_metrics() -> str:
    return metrics.render()
