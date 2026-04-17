import time
import uuid
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import iterate_in_threadpool
from loguru import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Determine logical flags based on path
        path = request.url.path
        flag = "[API]"
        if "/auth" in path: flag = "[AUTH]"
        elif "/users" in path: flag = "[USER]"
        elif "/kyc" in path: flag = "[KYC]"
        elif "/plots" in path: flag = "[PLOT]"

        # Log Request Metadata and Body
        body_log = ""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # Provide original body to the next handler by wrapping the request
                    # Note: We must re-send the body in a way it can be re-read
                    # For BaseHTTPMiddleware, we can't easily re-read, so we use simpler logging:
                    body_json = json.loads(body.decode())
                    body_log = f"\n📦 PAYLOAD: {json.dumps(body_json, indent=2)}"
                    
                    # Workaround to allow endpoint to read body again
                    async def receive():
                        return {"type": "http.request", "body": body, "more_body": False}
                    request._receive = receive
            except Exception:
                body_log = "\n📦 PAYLOAD: <binary or unparseable>"

        logger.info(f"🚀 {flag} {request.method} {path} {body_log} [{request_id}]")

        start_time = time.time()
        try:
            response = await call_next(request)
            latency = time.time() - start_time
            
            # Log Response
            logger.info(f"✅ {flag} {request.method} {path} - {response.status_code} ({latency:.4f}s) [{request_id}]")
            
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"❌ {flag} {request.method} {path} - {latency:.4f}s [{request_id}] - Error: {str(e)}")
            raise e
