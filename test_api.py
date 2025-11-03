#!/usr/bin/env python3
"""
Test script for Holo 1.5 API
Run this after starting the server with ./launch.sh
"""
import requests
import base64
import json
from pathlib import Path
import os

# Configuration
BASE_URL = os.environ.get("API_URL", "http://vincents-Mac-Studio.local:8000")

def test_health():
    """Test the health endpoint"""
    print("\n🏥 Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.json()

def test_text_only():
    """Test chat with text only (no image)"""
    print("\n💬 Testing text-only chat...")
    payload = {
        "model": "Holo1.5-7B",
        "messages": [
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "max_tokens": 100,
        "temperature": 0.2
    }
    response = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload)
    print(f"Status Code: {response.status_code}")
    result = response.json()
    print(f"Response: {result['choices'][0]['message']['content']}")
    return result

def test_image_chat(image_path: str):
    """Test chat with an image"""
    print(f"\n🖼️  Testing image chat with: {image_path}")
    
    # Read and encode image as base64
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    payload = {
        "model": "Holo1.5-7B",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What do you see in this image?"},
                    {"type": "image", "image": {"b64": img_b64}}
                ]
            }
        ],
        "max_tokens": 200,
        "temperature": 0.3
    }
    
    response = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result['choices'][0]['message']['content']}")
        return result
    else:
        print(f"Error: {response.text}")
        return None

def main():
    print("=" * 60)
    print("🚀 Holo 1.5 API Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Health check
        health = test_health()
        if health.get("status") != "ok":
            print(f"\n❌ Server is not ready: {health.get('load_error', 'Unknown error')}")
            return
        
        # Test 2: Text-only chat
        test_text_only()
        
        # Test 3: Image chat (if you have a test image)
        print("\n" + "=" * 60)
        print("📝 To test with an image, run:")
        print("   python test_api.py <path-to-image.jpg>")
        print("=" * 60)
        
        print("\n✅ Basic tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to the API server.")
        print("   Make sure the server is running with: ./launch.sh")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # If image path provided, test with image
        image_path = sys.argv[1]
        if Path(image_path).exists():
            test_health()
            test_image_chat(image_path)
        else:
            print(f"❌ Image file not found: {image_path}")
    else:
        main()
