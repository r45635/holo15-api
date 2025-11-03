#!/usr/bin/env python3
"""
Generate API Key for Holo 1.5 API
Creates a random API key and outputs the bcrypt hash + YAML entry
"""
import secrets
import string
import bcrypt
import sys
from datetime import datetime, timedelta


def generate_random_key(length: int = 32) -> str:
    """Generate a cryptographically secure random API key"""
    alphabet = string.ascii_letters + string.digits + "-_"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_key(key: str) -> str:
    """Hash API key with bcrypt"""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(key.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def main():
    print("=" * 70)
    print("Holo 1.5 API Key Generator")
    print("=" * 70)
    print()
    
    # Get key ID
    key_id = input("Enter key ID (e.g., 'team-core', 'partner-acme'): ").strip()
    if not key_id:
        print("❌ Key ID is required")
        sys.exit(1)
    
    # Get owner
    owner = input("Enter owner email: ").strip()
    if not owner:
        owner = "unknown@example.com"
    
    # Get scopes
    print("\nAvailable scopes:")
    print("  - chat:read  (inference only)")
    print("  - chat:write (reserved for future)")
    print("  - *          (all scopes)")
    scopes_input = input("Enter scopes (comma-separated, default: chat:read): ").strip()
    if not scopes_input:
        scopes = ["chat:read"]
    else:
        scopes = [s.strip() for s in scopes_input.split(",")]
    
    # Get expiration
    print("\nExpiration:")
    print("  1 - 1 month")
    print("  2 - 3 months")
    print("  3 - 1 year")
    print("  4 - Custom date (YYYY-MM-DD)")
    print("  5 - No expiration")
    exp_choice = input("Choose (default: 1 year): ").strip() or "3"
    
    if exp_choice == "1":
        expires_at = datetime.now() + timedelta(days=30)
    elif exp_choice == "2":
        expires_at = datetime.now() + timedelta(days=90)
    elif exp_choice == "3":
        expires_at = datetime.now() + timedelta(days=365)
    elif exp_choice == "4":
        date_str = input("Enter expiration date (YYYY-MM-DD): ").strip()
        try:
            expires_at = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print("❌ Invalid date format")
            sys.exit(1)
    else:
        expires_at = None
    
    # Generate key
    print("\n🔐 Generating API key...")
    api_key = generate_random_key(32)
    api_hash = hash_key(api_key)
    created_at = datetime.now()
    
    # Output
    print("\n" + "=" * 70)
    print("✅ API Key Generated Successfully!")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT: Save this API key securely. It will NOT be shown again!")
    print()
    print(f"API Key (plain-text):")
    print(f"  {api_key}")
    print()
    print(f"Hash (bcrypt):")
    print(f"  {api_hash}")
    print()
    print("=" * 70)
    print("Add this entry to your ops/api_keys.yaml file:")
    print("=" * 70)
    print()
    print(f"  - key_id: \"{key_id}\"")
    print(f"    hash: \"{api_hash}\"")
    print(f"    owner: \"{owner}\"")
    print(f"    scopes: {scopes}")
    print(f"    created_at: \"{created_at.strftime('%Y-%m-%dT%H:%M:%SZ')}\"")
    if expires_at:
        print(f"    expires_at: \"{expires_at.strftime('%Y-%m-%dT%H:%M:%SZ')}\"")
    else:
        print(f"    expires_at: null  # No expiration")
    print()
    print("=" * 70)
    print()
    print("🔒 Security reminders:")
    print("  - Share the API key securely (never via email/chat)")
    print("  - Never commit the plain-text key to git")
    print("  - Rotate keys regularly")
    print("  - Delete unused keys from api_keys.yaml")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
        sys.exit(1)
