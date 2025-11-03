"""
Abuse Detection for Holo 1.5 API
Tracks suspicious behavior and maintains deny-list
"""
import time
import threading
from typing import Dict, List, Set
from pathlib import Path
from dataclasses import dataclass, field
from collections import deque


@dataclass
class AbuseContext:
    """Context information for abuse check"""
    ip: str
    key_id: str | None
    status_code: int
    error_type: str | None = None  # e.g., "invalid_image", "oversized", "decode_error"
    

@dataclass
class AbuseTracker:
    """Track abuse metrics for an entity (IP or key)"""
    errors: deque = field(default_factory=lambda: deque(maxlen=100))  # Recent error timestamps
    violations: List[str] = field(default_factory=list)  # Types of violations
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    total_requests: int = 0
    blocked: bool = False


class AbuseDetector:
    """
    Detects and blocks abusive behavior
    """
    
    def __init__(self, denylist_file: str, threshold_errors: int = 5, window_seconds: int = 30):
        self.denylist_file = Path(denylist_file)
        self.threshold_errors = threshold_errors
        self.window_seconds = window_seconds
        
        self.lock = threading.Lock()
        self.trackers: Dict[str, AbuseTracker] = {}
        self.denied: Set[str] = set()
        
        self._load_denylist()
    
    def _load_denylist(self):
        """Load blocked IPs/keys from file"""
        if not self.denylist_file.exists():
            self.denylist_file.parent.mkdir(parents=True, exist_ok=True)
            self.denylist_file.touch()
            return
        
        try:
            with open(self.denylist_file, 'r') as f:
                for line in f:
                    entry = line.strip()
                    if entry and not entry.startswith('#'):
                        self.denied.add(entry)
            
            if self.denied:
                print(f"🚫 Loaded {len(self.denied)} denied entries from {self.denylist_file}")
        except Exception as e:
            print(f"⚠️  Error loading denylist: {e}")
    
    def _append_to_denylist(self, identifier: str, reason: str):
        """Append entry to denylist file"""
        try:
            with open(self.denylist_file, 'a') as f:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{identifier}  # Blocked: {reason} at {timestamp}\n")
            print(f"🚫 Added to denylist: {identifier} (reason: {reason})")
        except Exception as e:
            print(f"⚠️  Error writing to denylist: {e}")
    
    def is_denied(self, identifier: str) -> bool:
        """Check if IP or key is in deny-list"""
        return identifier in self.denied
    
    def track_request(self, ctx: AbuseContext):
        """Track a request for abuse detection"""
        with self.lock:
            # Track by IP
            self._track_entity(ctx.ip, ctx)
            
            # Track by key if present
            if ctx.key_id:
                self._track_entity(f"key:{ctx.key_id}", ctx)
    
    def _track_entity(self, identifier: str, ctx: AbuseContext):
        """Track metrics for an entity"""
        now = time.time()
        
        if identifier not in self.trackers:
            self.trackers[identifier] = AbuseTracker()
        
        tracker = self.trackers[identifier]
        tracker.last_seen = now
        tracker.total_requests += 1
        
        # Track errors (4xx/5xx)
        if ctx.status_code >= 400:
            tracker.errors.append(now)
            if ctx.error_type:
                tracker.violations.append(ctx.error_type)
            
            # Check if threshold exceeded in window
            recent_errors = [t for t in tracker.errors if now - t <= self.window_seconds]
            
            if len(recent_errors) >= self.threshold_errors and not tracker.blocked:
                self._block_entity(identifier, f"{len(recent_errors)} errors in {self.window_seconds}s")
    
    def _block_entity(self, identifier: str, reason: str):
        """Block an entity for abuse"""
        tracker = self.trackers[identifier]
        tracker.blocked = True
        self.denied.add(identifier)
        self._append_to_denylist(identifier, reason)
    
    def check_and_maybe_block(self, ctx: AbuseContext) -> bool:
        """
        Check if request should be blocked
        Returns True if blocked, False if allowed
        """
        # Check deny-list
        if self.is_denied(ctx.ip):
            return True
        
        if ctx.key_id and self.is_denied(f"key:{ctx.key_id}"):
            return True
        
        # Track this request
        self.track_request(ctx)
        
        # Check if just got blocked
        if ctx.ip in self.denied:
            return True
        
        if ctx.key_id and f"key:{ctx.key_id}" in self.denied:
            return True
        
        return False
    
    def get_stats(self) -> Dict:
        """Get abuse detection statistics"""
        with self.lock:
            return {
                "denied_count": len(self.denied),
                "tracked_entities": len(self.trackers),
                "threshold_errors": self.threshold_errors,
                "window_seconds": self.window_seconds
            }
    
    def cleanup_old_trackers(self, max_age: int = 3600):
        """Remove trackers that haven't been seen in max_age seconds"""
        now = time.time()
        with self.lock:
            old_entities = [entity for entity, tracker in self.trackers.items() 
                           if now - tracker.last_seen > max_age and not tracker.blocked]
            for entity in old_entities:
                del self.trackers[entity]
            
            if old_entities:
                print(f"🧹 Cleaned up {len(old_entities)} abuse trackers")


# Global abuse detector
_abuse_detector: AbuseDetector | None = None


def init_abuse_detector(denylist_file: str, threshold_errors: int, window_seconds: int):
    """Initialize abuse detector"""
    global _abuse_detector
    _abuse_detector = AbuseDetector(denylist_file, threshold_errors, window_seconds)
    print(f"✅ Abuse detection initialized: {threshold_errors} errors in {window_seconds}s window")


def get_abuse_detector() -> AbuseDetector:
    """Get global abuse detector"""
    if _abuse_detector is None:
        raise RuntimeError("Abuse detector not initialized")
    return _abuse_detector
