"""Quick test of the API endpoint."""

import requests
import json

# Test the analyze-stream endpoint
url = "http://localhost:8000/api/dc-assistant/analyze-stream"
data = {"question": "What do raiders in 2024 typically do after turnovers?"}

print(f"Testing POST {url}")
print(f"Data: {data}")
print("\nResponse:")
print("-" * 80)

response = requests.post(url, json=data, stream=True)

if response.status_code == 200:
    print(f"✅ Status: {response.status_code}")
    print("\nStreaming response:")
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            if decoded_line.startswith('data: '):
                event_data = decoded_line[6:]  # Remove 'data: ' prefix
                try:
                    event = json.loads(event_data)
                    print(f"  {event}")
                    if event.get('type') == 'done':
                        print(f"\n✅ Trace ID: {event.get('trace_id')}")
                        break
                except json.JSONDecodeError:
                    print(f"  Raw: {event_data}")
else:
    print(f"❌ Status: {response.status_code}")
    print(f"Error: {response.text}")
