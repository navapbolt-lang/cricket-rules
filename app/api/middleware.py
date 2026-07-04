"""FastAPI middleware for auth, rate limiting, and logging."""

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
from loguru import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with latency."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                f"Method: {request.method} Path: {request.url.path} "
                f"Status: {response.status_code} Duration: {duration:.4f}s"
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Method: {request.method} Path: {request.url.path} "
                f"Failed: {str(e)} Duration: {duration:.4f}s"
            )
            raise e


class CORSMiddleware(BaseHTTPMiddleware):
    """Handle CORS for partner websites."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, Authorization"
            response.headers["Access-Control-Max-Age"] = "86400"
            return response
            
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, Authorization"
        return response
