"""
Configuration management for Holo 1.5 API
Loads settings from environment variables with sensible defaults
"""
import os
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings loaded from environment"""
    
    # API Keys & Authentication
    api_keys_file: str
    
    # Rate Limiting
    rate_limit_ip: str  # Format: "requests/period" e.g. "60/minute"
    rate_limit_key: str
    burst_ip: int
    burst_key: int
    
    # Request Limits
    max_body_mb: float
    max_image_side: int
    max_tokens_limit: int
    
    # CORS
    cors_allow_origins: List[str]
    
    # Features
    allow_docs: bool
    
    # Security
    denylist_file: str
    abuse_threshold_errors: int
    abuse_window_seconds: int
    
    # Logging
    log_level: str
    audit_log_file: str
    
    # Server
    host: str
    port: int
    workers: int
    
    # Model (existing)
    model_id: str
    holo_max_side: int
    
    # Trust proxy headers
    trust_proxy_headers: bool
    trusted_proxy_count: int


def load_settings() -> Settings:
    """Load settings from environment variables"""
    
    # Parse CORS origins (CSV format)
    cors_origins_str = os.getenv("CORS_ALLOW_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500")
    cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
    
    # Parse rate limits
    rate_limit_ip = os.getenv("RATE_LIMIT_IP", "60/minute")
    rate_limit_key = os.getenv("RATE_LIMIT_KEY", "120/minute")
    
    return Settings(
        # API Keys
        api_keys_file=os.getenv("API_KEYS_FILE", "ops/api_keys.yaml"),
        
        # Rate Limiting
        rate_limit_ip=rate_limit_ip,
        rate_limit_key=rate_limit_key,
        burst_ip=int(os.getenv("BURST_IP", "10")),
        burst_key=int(os.getenv("BURST_KEY", "20")),
        
        # Request Limits
        max_body_mb=float(os.getenv("MAX_BODY_MB", "10.0")),
        max_image_side=int(os.getenv("MAX_IMAGE_SIDE", "2048")),
        max_tokens_limit=int(os.getenv("MAX_TOKENS_LIMIT", "2048")),
        
        # CORS
        cors_allow_origins=cors_origins,
        
        # Features
        allow_docs=os.getenv("ALLOW_DOCS", "true").lower() in ("true", "1", "yes"),
        
        # Security
        denylist_file=os.getenv("DENYLIST_FILE", "ops/denylist.txt"),
        abuse_threshold_errors=int(os.getenv("ABUSE_THRESHOLD_ERRORS", "5")),
        abuse_window_seconds=int(os.getenv("ABUSE_WINDOW_SECONDS", "30")),
        
        # Logging
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        audit_log_file=os.getenv("AUDIT_LOG_FILE", "logs/audit.log"),
        
        # Server
        host=os.getenv("HOLO_HOST", "127.0.0.1"),
        port=int(os.getenv("HOLO_PORT", "8000")),
        workers=int(os.getenv("UVICORN_WORKERS", "1")),
        
        # Model
        model_id=os.getenv("HOLO_MODEL", "Hcompany/Holo1.5-7B"),
        holo_max_side=int(os.getenv("HOLO_MAX_SIDE", "1440")),
        
        # Proxy
        trust_proxy_headers=os.getenv("TRUST_PROXY_HEADERS", "false").lower() in ("true", "1", "yes"),
        trusted_proxy_count=int(os.getenv("TRUSTED_PROXY_COUNT", "1")),
    )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings
