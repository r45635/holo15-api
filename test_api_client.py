#!/usr/bin/env python3
"""
Test script to verify API client examples from documentation
Tests the external API usage examples
"""
import requests
import sys

API_URL = "http://127.0.0.1:8000"
API_KEY = "mplkhLEdJ-LJ-RJm29OIIToQ1pw16rwc"  # Replace with your key

def test_basic_request():
    """Test 1: Basic text request with requests library"""
    print("\n" + "="*70)
    print("TEST 1: Basic text request (requests library)")
    print("="*70)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/v1/chat/completions",
        headers=headers,
        json={
            "model": "Hcompany/Holo1.5-7B",
            "messages": [
                {"role": "user", "content": "Dis bonjour en français"}
            ],
            "max_tokens": 50,
            "temperature": 0.7
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result['choices'][0]['message']['content']}")
        print("✅ PASSED")
        return True
    else:
        print(f"❌ FAILED: {response.text}")
        return False

def test_error_handling():
    """Test 2: Error handling - missing auth"""
    print("\n" + "="*70)
    print("TEST 2: Error handling (missing authentication)")
    print("="*70)
    
    response = requests.post(
        f"{API_URL}/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        json={
            "model": "Hcompany/Holo1.5-7B",
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 10
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print(f"Expected error: {response.json()['detail']}")
        print("✅ PASSED - Error handling works correctly")
        return True
    else:
        print(f"❌ FAILED: Expected 401, got {response.status_code}")
        return False

def test_rate_limit_headers():
    """Test 3: Check rate limit headers"""
    print("\n" + "="*70)
    print("TEST 3: Rate limit headers")
    print("="*70)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/v1/chat/completions",
        headers=headers,
        json={
            "model": "Hcompany/Holo1.5-7B",
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 5
        }
    )
    
    print(f"Status: {response.status_code}")
    print(f"X-Request-Id: {response.headers.get('X-Request-Id', 'N/A')}")
    print(f"Cache-Control: {response.headers.get('Cache-Control', 'N/A')}")
    
    if 'X-Request-Id' in response.headers:
        print("✅ PASSED - Headers present")
        return True
    else:
        print("❌ FAILED - Missing expected headers")
        return False

def test_health_check():
    """Test 4: Health check endpoint (public)"""
    print("\n" + "="*70)
    print("TEST 4: Health check (public endpoint)")
    print("="*70)
    
    response = requests.get(f"{API_URL}/health")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Device: {data['device']}")
        print(f"Model: {data['model']}")
        print("✅ PASSED")
        return True
    else:
        print(f"❌ FAILED: {response.status_code}")
        return False

def test_openai_sdk_compatible():
    """Test 5: OpenAI SDK compatibility check"""
    print("\n" + "="*70)
    print("TEST 5: OpenAI SDK compatibility")
    print("="*70)
    
    try:
        from openai import OpenAI
        
        client = OpenAI(
            base_url=f"{API_URL}/v1",
            api_key=API_KEY
        )
        
        response = client.chat.completions.create(
            model="Hcompany/Holo1.5-7B",
            messages=[
                {"role": "user", "content": "Say 'test' in one word"}
            ],
            max_tokens=10
        )
        
        print(f"Response: {response.choices[0].message.content}")
        print("✅ PASSED - OpenAI SDK compatible")
        return True
    
    except ImportError:
        print("⚠️  SKIPPED - OpenAI SDK not installed")
        print("   Install with: pip install openai")
        return None
    
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_invalid_token_limit():
    """Test 6: Token limit validation"""
    print("\n" + "="*70)
    print("TEST 6: Token limit validation")
    print("="*70)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_URL}/v1/chat/completions",
        headers=headers,
        json={
            "model": "Hcompany/Holo1.5-7B",
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 10000  # Exceeds limit
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print(f"Expected error: {response.json()['detail']}")
        print("✅ PASSED - Token limit validation works")
        return True
    else:
        print(f"❌ FAILED: Expected 400, got {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("\n")
    print("🧪" * 35)
    print("API Client Examples Verification")
    print("Testing documentation examples...")
    print("🧪" * 35)
    
    tests = [
        test_health_check,
        test_basic_request,
        test_error_handling,
        test_rate_limit_headers,
        test_openai_sdk_compatible,
        test_invalid_token_limit,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            result = test()
            if result is True:
                passed += 1
            elif result is False:
                failed += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("="*70)
    
    if failed == 0:
        print("🎉 All documentation examples are valid!")
        return 0
    else:
        print("⚠️  Some examples need fixing")
        return 1

if __name__ == "__main__":
    sys.exit(main())
