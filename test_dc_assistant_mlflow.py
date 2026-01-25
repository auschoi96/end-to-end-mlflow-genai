#!/usr/bin/env python3
"""Test DC Assistant using MLflow Agent client."""

import os
import mlflow
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

print("🔧 Testing DC Assistant via MLflow Agent Client")
print("=" * 60)

# Configuration
host = os.getenv('DATABRICKS_HOST')
model = os.getenv('LLM_MODEL')
experiment_id = os.getenv('MLFLOW_EXPERIMENT_ID')

print(f"\n📍 Configuration:")
print(f"  Host: {host}")
print(f"  Model: {model}")
print(f"  Experiment: {experiment_id}")
print()

# Set MLflow tracking URI
mlflow.set_tracking_uri("databricks")
mlflow.set_experiment(experiment_id=experiment_id)

print(f"\n🏈 Testing DC Assistant: {model}")
print("Question: 'What types of questions can you answer?'")
print("-" * 60)

try:
    # Load the agent from Model Serving
    agent = mlflow.deployments.get_deploy_client("databricks").predict(
        endpoint=model,
        inputs={"messages": [{"role": "user", "content": "What types of questions can you answer?"}]}
    )

    print("✅ Response received!")
    print("\n📊 Response:")
    print("-" * 60)
    print(agent)
    print("-" * 60)

except Exception as e:
    print(f"❌ Request failed: {e}")
    import traceback
    traceback.print_exc()

    # Try alternative format
    print("\n🔄 Trying alternative format...")
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient(profile="fieldengwest")

        # Try calling it like a chat model
        from mlflow.deployments import get_deploy_client
        client = get_deploy_client("databricks")

        response = client.predict(
            endpoint=model,
            inputs={
                "prompt": "What types of questions can you answer?"
            }
        )
        print("✅ Alternative format worked!")
        print(response)
    except Exception as e2:
        print(f"❌ Alternative also failed: {e2}")
        traceback.print_exc()

print("\n💡 Next steps:")
print("  1. Figure out correct input format for DC Assistant")
print("  2. Test streaming responses")
print("  3. Create backend routes")
