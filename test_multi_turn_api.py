"""Test the multi-turn conversation API."""

import requests
import json

url = "http://localhost:8000/api/dc-assistant/multi-turn"

# First turn
print("=" * 80)
print("TURN 1: Initial question")
print("=" * 80)
data1 = {
    "question": "What do raiders in 2024 typically do after turnovers?",
    "is_first_turn": True
}

response1 = requests.post(url, json=data1)
result1 = response1.json()
print(f"✅ Status: {response1.status_code}")
print(f"Session ID: {result1['session_id']}")
print(f"Trace ID: {result1.get('trace_id')}")
print(f"Response preview: {result1['response'][:200]}...")

# Second turn - using the session ID from first turn
print("\n" + "=" * 80)
print("TURN 2: Follow-up question")
print("=" * 80)
data2 = {
    "question": "Compare them to the Dallas Cowboys",
    "session_id": result1['session_id'],
    "is_first_turn": False
}

response2 = requests.post(url, json=data2)
result2 = response2.json()
print(f"✅ Status: {response2.status_code}")
print(f"Session ID: {result2['session_id']}")
print(f"Trace ID: {result2.get('trace_id')}")
print(f"Response preview: {result2['response'][:200]}...")

print("\n" + "=" * 80)
print("✅ Multi-turn conversation test complete!")
print("=" * 80)
