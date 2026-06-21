"""Request/response logging + unhandled-exception capture middleware."""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = uuid.uuid4().hex[:8]
        t0 = time.perf_counter()
        client = request.client.host if request.client else "?"
        logger.info("→ [%s] %s %s from %s", rid, request.method, request.url.path, client)

        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001
            dur = (time.perf_counter() - t0) * 1000
            logger.exception("✗ [%s] %s %s unhandled error after %.0fms",
                             rid, request.method, request.url.path, dur)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": rid},
            )

        dur = (time.perf_counter() - t0) * 1000
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(level, "← [%s] %s %s → %d (%.0fms)",
                   rid, request.method, request.url.path, response.status_code, dur)
        response.headers["X-Request-ID"] = rid
        return response
