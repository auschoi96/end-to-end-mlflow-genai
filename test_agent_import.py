"""Quick test to verify agent can be imported and called."""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from .env.local
env_file = Path(__file__).parent / '.env.local'
if env_file.exists():
    print(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes from value
                value = value.strip('"').strip("'")
                os.environ[key] = value
                print(f"  Set {key}={value}")

print("\nTesting agent import...")

try:
    from mlflow_demo.agent import AGENT
    print("✅ Agent imported successfully!")

    # Try a simple prediction
    print("\nTesting agent.predict_stream_local()...")
    question = "What do raiders in 2024 typically do after turnovers?"

    response_text = ""
    for event in AGENT.predict_stream_local(question):
        event_type = event.get('type')
        if event_type == 'token':
            response_text += event.get('content', '')
        elif event_type == 'done':
            trace_id = event.get('trace_id')
            print(f"\n✅ Agent prediction complete!")
            print(f"Response length: {len(response_text)} chars")
            print(f"Trace ID: {trace_id}")
            print(f"\nFirst 200 chars of response:")
            print(response_text[:200])
            break

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
