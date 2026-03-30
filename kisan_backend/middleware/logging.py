import time
import uuid
import json
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pythonjsonlogger import jsonlogger

# Config JSON Logger
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(timestamp)s %(levelname)s %(message)s %(request_id)s %(user_id)s %(path)s %(method)s %(latency)s'
)
log_handler.setFormatter(formatter)
logger = logging.getLogger("kisan_backend")
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            latency = time.time() - start_time
            
            log_data = {
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "latency": f"{latency:.4f}s",
                "status_code": response.status_code
            }
            
            logger.info("Request processed", extra=log_data)
            
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as e:
            latency = time.time() - start_time
            logger.exception("Request failed", extra={
                "request_id": request_id, 
                "path": request.url.path,
                "method": request.method,
                "latency": f"{latency:.4f}s"
            })
            raise e
