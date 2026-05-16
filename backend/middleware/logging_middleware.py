"""API 请求/响应日志中间件。"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.logger_service import log_api, log_error


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start) * 1000
            query = f"?{request.url.query}" if request.url.query else ""
            log_api(
                request.method,
                f"{request.url.path}{query}",
                response.status_code,
                duration_ms,
            )
            return response
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            log_error("API", f"{request.method} {request.url.path} {e}", duration_ms=f"{duration_ms:.0f}ms")
            raise
