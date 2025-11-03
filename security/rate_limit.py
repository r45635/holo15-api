"""
Rate Limiting for Holo 1.5 API
Token bucket implementation with per-IP and per-API-key limits
"""
import time
import threading
from typing import Dict, Tuple
from fastapi import HTTPException, Request
from dataclasses import dataclass


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: int  # Maximum tokens (burst)
    refill_rate: float  # Tokens per second
    tokens: float  # Current tokens
    last_refill: float  # Last refill timestamp
    
    def consume(self, amount: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        # Try to consume
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
    
    def retry_after(self) -> int:
        """Calculate seconds until next token is available"""
        if self.tokens >= 1:
            return 0
        tokens_needed = 1 - self.tokens
        return int(tokens_needed / self.refill_rate) + 1


class RateLimiter:
    """
    Thread-safe rate limiter with separate limits for IP and API keys
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        self.ip_buckets: Dict[str, TokenBucket] = {}
        self.key_buckets: Dict[str, TokenBucket] = {}
        
        # Default limits (overridden by config)
        self.ip_limit = (60, 10)  # (requests_per_minute, burst)
        self.key_limit = (120, 20)
    
    def configure(self, ip_limit: str, key_limit: str, burst_ip: int, burst_key: int):
        """
        Configure rate limits
        Format: "requests/period" e.g. "60/minute", "10/second"
        """
        self.ip_limit = (self._parse_limit(ip_limit), burst_ip)
        self.key_limit = (self._parse_limit(key_limit), burst_key)
        print(f"✅ Rate limiting configured:")
        print(f"   IP: {ip_limit} (burst: {burst_ip})")
        print(f"   Key: {key_limit} (burst: {burst_key})")
    
    def _parse_limit(self, limit_str: str) -> float:
        """Parse rate limit string to requests per second"""
        parts = limit_str.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid rate limit format: {limit_str}")
        
        count = int(parts[0])
        period = parts[1].lower()
        
        if period in ('s', 'sec', 'second'):
            return count
        elif period in ('m', 'min', 'minute'):
            return count / 60.0
        elif period in ('h', 'hour'):
            return count / 3600.0
        else:
            raise ValueError(f"Unknown period: {period}")
    
    def _get_or_create_bucket(self, key: str, buckets: Dict[str, TokenBucket], 
                               rate: float, capacity: int) -> TokenBucket:
        """Get existing bucket or create new one"""
        if key not in buckets:
            buckets[key] = TokenBucket(
                capacity=capacity,
                refill_rate=rate,
                tokens=capacity,  # Start full
                last_refill=time.time()
            )
        return buckets[key]
    
    def check_ip_limit(self, ip: str) -> Tuple[bool, int]:
        """
        Check if IP is within rate limit
        Returns: (allowed, retry_after_seconds)
        """
        with self.lock:
            rate, burst = self.ip_limit
            bucket = self._get_or_create_bucket(ip, self.ip_buckets, rate, burst)
            
            if bucket.consume():
                return True, 0
            else:
                return False, bucket.retry_after()
    
    def check_key_limit(self, key_id: str) -> Tuple[bool, int]:
        """
        Check if API key is within rate limit
        Returns: (allowed, retry_after_seconds)
        """
        with self.lock:
            rate, burst = self.key_limit
            bucket = self._get_or_create_bucket(key_id, self.key_buckets, rate, burst)
            
            if bucket.consume():
                return True, 0
            else:
                return False, bucket.retry_after()
    
    def cleanup_old_buckets(self, max_age: int = 3600):
        """Remove buckets that haven't been used in max_age seconds"""
        now = time.time()
        with self.lock:
            # Cleanup IP buckets
            old_ips = [ip for ip, bucket in self.ip_buckets.items() 
                      if now - bucket.last_refill > max_age]
            for ip in old_ips:
                del self.ip_buckets[ip]
            
            # Cleanup key buckets
            old_keys = [key for key, bucket in self.key_buckets.items() 
                       if now - bucket.last_refill > max_age]
            for key in old_keys:
                del self.key_buckets[key]
            
            if old_ips or old_keys:
                print(f"🧹 Cleaned up {len(old_ips)} IP buckets and {len(old_keys)} key buckets")


# Global rate limiter
_rate_limiter: RateLimiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance"""
    return _rate_limiter


def check_rate_limit_ip(request: Request):
    """
    FastAPI dependency to check IP rate limit
    Raises 429 if exceeded
    """
    # Get client IP (will be set by middleware)
    client_ip = getattr(request.state, 'client_ip', request.client.host if request.client else '127.0.0.1')
    
    limiter = get_rate_limiter()
    allowed, retry_after = limiter.check_ip_limit(client_ip)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for IP. Try again in {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limiter.ip_limit[0] * 60),  # Convert to per-minute
                "X-RateLimit-Remaining": "0"
            }
        )


def check_rate_limit_key(request: Request):
    """
    FastAPI dependency to check API key rate limit
    Raises 429 if exceeded
    Requires principal to be set in request.state (by auth middleware)
    """
    principal = getattr(request.state, 'principal', None)
    if not principal:
        return  # No key, skip key rate limiting
    
    limiter = get_rate_limiter()
    allowed, retry_after = limiter.check_key_limit(principal.key_id)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for API key '{principal.key_id}'. Try again in {retry_after} seconds.",
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limiter.key_limit[0] * 60),
                "X-RateLimit-Remaining": "0"
            }
        )
