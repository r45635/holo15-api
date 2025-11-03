"""
Middleware for Holo 1.5 API
Handles request ID, logging, IP extraction, body size limits, and audit logging
"""
import uuid
import time
import json
import logging
from pathlib import Path
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Setup structured logging
class JSONFormatter(logging.Formatter):
    """Format logs as JSON"""
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Add extra fields if present
        for key in ['request_id', 'method', 'path', 'ip', 'user', 'status', 'latency_ms', 'error']:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        return json.dumps(log_data)


def setup_logging(log_level: str, audit_log_file: str):
    """Setup structured JSON logging"""
    # Main application logger
    app_logger = logging.getLogger("holo_api")
    app_logger.setLevel(log_level)
    
    # Console handler with JSON format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    app_logger.addHandler(console_handler)
    
    # Audit log for security events
    audit_logger = logging.getLogger("holo_api.audit")
    audit_logger.setLevel(logging.INFO)
    
    # File handler for audit log
    audit_file = Path(audit_log_file)
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(audit_log_file)
    file_handler.setFormatter(JSONFormatter())
    audit_logger.addHandler(file_handler)
    
    print(f"✅ Logging configured: level={log_level}, audit={audit_log_file}")
    return app_logger, audit_logger


def extract_client_ip(request: Request, trust_proxy: bool, trusted_count: int) -> str:
    """
    Extract real client IP from request
    If trust_proxy=True, use X-Forwarded-For header (last N IPs where N=trusted_count)
    Otherwise use direct client IP
    """
    if trust_proxy and "x-forwarded-for" in request.headers:
        # X-Forwarded-For: client, proxy1, proxy2, ...
        # We trust the last 'trusted_count' proxies
        forwarded = request.headers["x-forwarded-for"]
        ips = [ip.strip() for ip in forwarded.split(",")]
        
        # Get the client IP (before trusted proxies)
        if len(ips) >= trusted_count:
            client_ip = ips[-(trusted_count + 1)] if len(ips) > trusted_count else ips[0]
        else:
            client_ip = ips[0]
        
        return client_ip
    
    # Fallback to direct client
    return request.client.host if request.client else "127.0.0.1"


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Main security middleware that:
    - Adds request ID
    - Extracts client IP
    - Checks body size limits
    - Logs all requests
    - Handles audit logging for security events
    """
    
    def __init__(self, app: ASGIApp, settings):
        super().__init__(app)
        self.settings = settings
        self.app_logger = logging.getLogger("holo_api")
        self.audit_logger = logging.getLogger("holo_api.audit")
        self.max_body_bytes = int(settings.max_body_mb * 1024 * 1024)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Extract client IP
        client_ip = extract_client_ip(
            request,
            self.settings.trust_proxy_headers,
            self.settings.trusted_proxy_count
        )
        request.state.client_ip = client_ip
        
        # Check body size (if Content-Length header present)
        if "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
            if content_length > self.max_body_bytes:
                self._log_audit(request_id, client_ip, request.method, request.url.path,
                               status=413, reason="body_too_large")
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Maximum: {self.settings.max_body_mb}MB"},
                    headers={"X-Request-Id": request_id}
                )
        
        # Process request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000
            
            # Add request ID to response headers
            response.headers["X-Request-Id"] = request_id
            
            # Log request
            self._log_request(request, response, request_id, client_ip, latency_ms)
            
            # Audit log for security-relevant events
            if response.status_code in [401, 403, 413, 415, 429]:
                self._log_audit(request_id, client_ip, request.method, request.url.path,
                               status=response.status_code)
            
            return response
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            
            # Log error
            self.app_logger.error(
                f"Request failed: {e}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "ip": client_ip,
                    "latency_ms": round(latency_ms, 2),
                    "error": str(e)
                }
            )
            
            # Audit log
            self._log_audit(request_id, client_ip, request.method, request.url.path,
                           status=500, reason=str(e))
            
            # Return 500
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
                headers={"X-Request-Id": request_id}
            )
    
    def _log_request(self, request: Request, response: Response, 
                    request_id: str, client_ip: str, latency_ms: float):
        """Log request details"""
        # Get user/key info if available
        principal = getattr(request.state, 'principal', None)
        user = principal.key_id if principal else None
        
        self.app_logger.info(
            f"{request.method} {request.url.path} -> {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "ip": client_ip,
                "user": user,
                "status": response.status_code,
                "latency_ms": round(latency_ms, 2)
            }
        )
    
    def _log_audit(self, request_id: str, client_ip: str, method: str, path: str,
                   status: int, reason: str = None):
        """Log security-relevant events to audit log"""
        self.audit_logger.info(
            f"Security event: {status}",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "ip": client_ip,
                "status": status,
                "reason": reason or self._status_reason(status)
            }
        )
    
    def _status_reason(self, status: int) -> str:
        """Get reason for status code"""
        reasons = {
            401: "unauthorized",
            403: "forbidden",
            413: "body_too_large",
            415: "unsupported_media_type",
            429: "rate_limit_exceeded"
        }
        return reasons.get(status, "unknown")
