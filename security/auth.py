"""
API Key Authentication for Holo 1.5 API
Handles Bearer token validation, expiration, and scopes
"""
import bcrypt
import yaml
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path


@dataclass
class APIKeyInfo:
    """API Key metadata"""
    key_id: str
    hash: str
    owner: str
    scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime]


@dataclass
class Principal:
    """Authenticated request principal"""
    key_id: str
    owner: str
    scopes: List[str]
    
    def has_scope(self, scope: str) -> bool:
        """Check if principal has a specific scope"""
        return scope in self.scopes or "*" in self.scopes


class APIKeyManager:
    """Manages API keys loaded from YAML file"""
    
    def __init__(self, keys_file: str):
        self.keys_file = Path(keys_file)
        self.keys: Dict[str, APIKeyInfo] = {}
        self.load_keys()
    
    def load_keys(self):
        """Load API keys from YAML file"""
        if not self.keys_file.exists():
            print(f"⚠️  API keys file not found: {self.keys_file}")
            print(f"   API will reject all authenticated requests.")
            print(f"   Create it with: python scripts/generate_api_key.py")
            return
        
        try:
            with open(self.keys_file, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data or 'keys' not in data:
                print(f"⚠️  No keys found in {self.keys_file}")
                return
            
            for key_data in data['keys']:
                key_info = APIKeyInfo(
                    key_id=key_data['key_id'],
                    hash=key_data['hash'],
                    owner=key_data.get('owner', 'unknown'),
                    scopes=key_data.get('scopes', ['*']),
                    created_at=datetime.fromisoformat(key_data.get('created_at', '2025-01-01T00:00:00Z').replace('Z', '+00:00')),
                    expires_at=datetime.fromisoformat(key_data['expires_at'].replace('Z', '+00:00')) if key_data.get('expires_at') else None
                )
                self.keys[key_info.key_id] = key_info
            
            print(f"✅ Loaded {len(self.keys)} API key(s) from {self.keys_file}")
        
        except Exception as e:
            print(f"❌ Error loading API keys: {e}")
            self.keys = {}
    
    def verify_key(self, provided_token: str) -> Optional[Principal]:
        """
        Verify API key against stored hashes
        Returns Principal if valid, None otherwise
        """
        # Try each key (constant-time comparison)
        for key_id, key_info in self.keys.items():
            try:
                # Constant-time hash comparison
                if bcrypt.checkpw(provided_token.encode('utf-8'), key_info.hash.encode('utf-8')):
                    # Check expiration
                    if key_info.expires_at and datetime.now(key_info.expires_at.tzinfo) > key_info.expires_at:
                        return None  # Expired
                    
                    # Return principal
                    return Principal(
                        key_id=key_info.key_id,
                        owner=key_info.owner,
                        scopes=key_info.scopes
                    )
            except Exception:
                continue  # Invalid hash format, skip
        
        return None


# Global key manager
_key_manager: Optional[APIKeyManager] = None

# HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)


def init_auth(keys_file: str):
    """Initialize authentication system"""
    global _key_manager
    _key_manager = APIKeyManager(keys_file)


def get_key_manager() -> APIKeyManager:
    """Get global key manager"""
    if _key_manager is None:
        raise RuntimeError("Authentication not initialized. Call init_auth() first.")
    return _key_manager


async def get_principal(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Principal:
    """
    FastAPI dependency to extract and validate API key
    Raises 401 if missing/invalid, 403 if expired
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Use: Authorization: Bearer <API_KEY>",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    manager = get_key_manager()
    principal = manager.verify_key(token)
    
    if principal is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return principal


async def get_principal_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[Principal]:
    """
    Optional authentication - returns None if no credentials provided
    Useful for endpoints that are public but want to identify the caller
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    manager = get_key_manager()
    return manager.verify_key(token)
