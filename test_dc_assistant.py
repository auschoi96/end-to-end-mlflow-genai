#!/usr/bin/env python3
"""Test script to verify DC Assistant Model Serving endpoint is accessible."""

import os
import json
import requests
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("🔧 Testing DC Assistant Model Serving Endpoint")
print("=" * 60)

# Configuration
host = os.getenv('DATABRICKS_HOST')
model = os.getenv('LLM_MODEL')
profile = os.getenv('DATABRICKS_CONFIG_PROFILE')

print(f"\n📍 Configuration:")
print(f"  Host: {host}")
print(f"  Model: {model}")
print(f"  Profile: {profile}")
print()

# Get authentication token
print("🔑 Getting authentication token...")
try:
    result = subprocess.run(
        ["databricks", "auth", "token", "--host", host, "--profile", profile],
        capture_output=True,
        text=True,
        check=True
    )
    token_data = json.loads(result.stdout)
    auth_token = token_data["access_token"]
    print("✅ Token retrieved successfully!")
except Exception as e:
    print(f"❌ Failed to get token: {e}")
    exit(1)

# Test DC Assistant
print(f"\n🏈 Testing DC Assistant endpoint: {model}")
print("Question: 'We are playing the 2024 Green Bay Packers - When do they run screens?'")
print("-" * 60)

try:
    url = f"{host}/serving-endpoints/{model}/invocations"

    payload = {
        "input": [
            {
                "role": "user",
                "content": "We are playing the 2024 Green Bay Packers - When do they run screens?"
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }

    print(f"\n📤 Request URL: {url}")
    print(f"📦 Payload:")
    print(json.dumps(payload, indent=2))
    print()

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=60
    )

    response.raise_for_status()
    result = response.json()

    print("✅ Response received!")
    print("\n📊 Response:")
    print("-" * 60)
    print(json.dumps(result, indent=2))
    print("-" * 60)

    # Extract the actual response
    if 'choices' in result and len(result['choices']) > 0:
        print("\n💬 DC Assistant Response:")
        print("-" * 60)
        print(result['choices'][0]['message']['content'])
        print("-" * 60)

except Exception as e:
    print(f"❌ Request failed: {e}")
    if 'response' in locals():
        print(f"\n📥 Response status: {response.status_code}")
        print(f"📄 Response body: {response.text}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✅ Test completed successfully!")
print("\n💡 Next steps:")
print("  1. Test streaming responses")
print("  2. Create backend FastAPI routes in server/routes/dc_assistant.py")
print("  3. Start building frontend UI")
