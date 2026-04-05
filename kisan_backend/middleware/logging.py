import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.time()
        try:
            response = await call_next(request)
            latency = time.time() - start_time
            print(f"{request.method} {request.url.path} - {response.status_code} ({latency:.4f}s) [{request_id}]")
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            latency = time.time() - start_time
            print(f"ERROR {request.method} {request.url.path} - {latency:.4f}s [{request_id}]: {e}")
            raise e
