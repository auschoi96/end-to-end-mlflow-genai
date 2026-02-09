"""Test multi-turn conversation functionality."""
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mlflow_demo.agent import AGENT
import mlflow
from mlflow_demo.utils.mlflow_helpers import get_mlflow_experiment_id

def test_multi_turn():
    """Test multi-turn conversation with session tracking."""
    print("🧪 Testing Multi-Turn Conversation")
    print("=" * 60)

    # Set up MLflow
    mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

    # Start a session
    session_id = "test-session-123"
    mlflow.start_session(session_id=session_id)
    print(f"✓ Started session: {session_id}\n")

    # Conversation history
    conversation_history = []

    # Turn 1: Ask about Raiders
    print("Turn 1: What do raiders in 2024 typically do after turnovers?")
    print("-" * 60)

    question_1 = "What do raiders in 2024 typically do after turnovers?"
    conversation_history.append({"role": "user", "content": question_1})

    response_1 = ""
    trace_id_1 = None

    for event in AGENT.predict_stream_local(question_1, conversation_history=conversation_history):
        if event["type"] == "token":
            response_1 += event["content"]
            print(event["content"], end="", flush=True)
        elif event["type"] == "done":
            trace_id_1 = event.get("trace_id")

    conversation_history.append({"role": "assistant", "content": response_1})

    print(f"\n\n✓ Turn 1 complete. Trace ID: {trace_id_1}\n")

    # Turn 2: Follow-up comparing to Cowboys
    print("Turn 2: Compare them to the Dallas Cowboys")
    print("-" * 60)

    question_2 = "Compare them to the Dallas Cowboys"
    conversation_history.append({"role": "user", "content": question_2})

    response_2 = ""
    trace_id_2 = None

    for event in AGENT.predict_stream_local(question_2, conversation_history=conversation_history):
        if event["type"] == "token":
            response_2 += event["content"]
            print(event["content"], end="", flush=True)
        elif event["type"] == "done":
            trace_id_2 = event.get("trace_id")

    conversation_history.append({"role": "assistant", "content": response_2})

    print(f"\n\n✓ Turn 2 complete. Trace ID: {trace_id_2}\n")

    print("=" * 60)
    print("✅ Multi-turn test completed successfully!")
    print(f"Session ID: {session_id}")
    print(f"Trace 1: {trace_id_1}")
    print(f"Trace 2: {trace_id_2}")
    print("\nConversation History:")
    for i, msg in enumerate(conversation_history, 1):
        print(f"{i}. [{msg['role']}] {msg['content'][:80]}...")

if __name__ == "__main__":
    test_multi_turn()
