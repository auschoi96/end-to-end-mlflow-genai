#!/usr/bin/env python3
"""Test script to verify DC Assistant works - either via local agent or serving endpoint."""

import argparse
import json
import os
import subprocess
import sys

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')


def test_local_agent():
  """Test the local DC Assistant agent directly."""
  print('🔧 Testing DC Assistant Local Agent')
  print('=' * 60)

  try:
    from mlflow_demo.agent import AGENT

    print('\n📍 Using centralized AGENT from agent.py...')
    print('✅ Agent loaded successfully!')

    question = 'We are playing the 2024 Green Bay Packers - When do they run screens?'
    print(f"\n🏈 Testing with question: '{question}'")
    print('-' * 60)

    print('\n📤 Streaming response:')
    full_response = ''
    for event in AGENT.predict_stream_local(question):
      event_type = event.get('type')
      if event_type == 'token':
        token = event.get('content', '')
        print(token, end='', flush=True)
        full_response += token
      elif event_type == 'tool_call':
        tool = event.get('tool', {})
        print(f"\n🔧 Tool call: {tool.get('name')} with args: {tool.get('arguments')}")
      elif event_type == 'done':
        print(f"\n\n✅ Done! Trace ID: {event.get('trace_id')}")
      elif event_type == 'error':
        print(f"\n❌ Error: {event.get('error')}")

    print('\n' + '-' * 60)
    print('✅ Local agent test completed!')

  except Exception as e:
    print(f'❌ Local agent test failed: {e}')
    import traceback

    traceback.print_exc()
    sys.exit(1)


def test_serving_endpoint():
  """Test the DC Assistant via Databricks serving endpoint."""
  print('🔧 Testing DC Assistant Model Serving Endpoint')
  print('=' * 60)

  # Configuration
  host = os.getenv('DATABRICKS_HOST')
  model = os.getenv('LLM_MODEL')
  profile = os.getenv('DATABRICKS_CONFIG_PROFILE')

  print(f'\n📍 Configuration:')
  print(f'  Host: {host}')
  print(f'  Model: {model}')
  print(f'  Profile: {profile}')
  print()

  # Get authentication token
  print('🔑 Getting authentication token...')
  try:
    result = subprocess.run(
      ['databricks', 'auth', 'token', '--host', host, '--profile', profile],
      capture_output=True,
      text=True,
      check=True,
    )
    token_data = json.loads(result.stdout)
    auth_token = token_data['access_token']
    print('✅ Token retrieved successfully!')
  except Exception as e:
    print(f'❌ Failed to get token: {e}')
    sys.exit(1)

  # Test DC Assistant
  print(f'\n🏈 Testing DC Assistant endpoint: {model}')
  print("Question: 'We are playing the 2024 Green Bay Packers - When do they run screens?'")
  print('-' * 60)

  try:
    url = f'{host}/serving-endpoints/{model}/invocations'

    payload = {
      'input': [
        {'role': 'user', 'content': 'We are playing the 2024 Green Bay Packers - When do they run screens?'}
      ]
    }

    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {auth_token}'}

    print(f'\n📤 Request URL: {url}')
    print(f'📦 Payload:')
    print(json.dumps(payload, indent=2))
    print()

    response = requests.post(url, json=payload, headers=headers, timeout=60)

    response.raise_for_status()
    result = response.json()

    print('✅ Response received!')
    print('\n📊 Response:')
    print('-' * 60)
    print(json.dumps(result, indent=2))
    print('-' * 60)

    # Extract the actual response
    if 'choices' in result and len(result['choices']) > 0:
      print('\n💬 DC Assistant Response:')
      print('-' * 60)
      print(result['choices'][0]['message']['content'])
      print('-' * 60)

  except Exception as e:
    print(f'❌ Request failed: {e}')
    if 'response' in locals():
      print(f'\n📥 Response status: {response.status_code}')
      print(f'📄 Response body: {response.text}')
    import traceback

    traceback.print_exc()
    sys.exit(1)

  print('\n✅ Endpoint test completed!')


def test_fastapi_server():
  """Test the FastAPI server endpoint."""
  print('🔧 Testing DC Assistant FastAPI Server')
  print('=' * 60)

  server_url = os.getenv('SERVER_URL', 'http://localhost:8000')
  question = 'We are playing the 2024 Green Bay Packers - When do they run screens?'

  print(f'\n📍 Server URL: {server_url}')
  print(f"🏈 Question: '{question}'")
  print('-' * 60)

  try:
    response = requests.post(
      f'{server_url}/api/dc-assistant/analyze-stream',
      json={'question': question},
      stream=True,
      timeout=120,
    )

    response.raise_for_status()

    print('\n📤 Streaming response:')
    for line in response.iter_lines():
      if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
          data = json.loads(line_str[6:])
          if data.get('type') == 'token':
            print(data.get('content', ''), end='', flush=True)
          elif data.get('type') == 'tool_call':
            tool = data.get('tool', {})
            print(f"\n🔧 Tool: {tool.get('name')}")
          elif data.get('type') == 'done':
            print(f"\n✅ Done! Trace ID: {data.get('trace_id')}")
          elif data.get('type') == 'error':
            print(f"\n❌ Error: {data.get('error')}")

    print('\n' + '-' * 60)
    print('✅ FastAPI server test completed!')

  except Exception as e:
    print(f'❌ FastAPI test failed: {e}')
    import traceback

    traceback.print_exc()
    sys.exit(1)


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Test DC Assistant')
  parser.add_argument(
    '--mode',
    choices=['local', 'endpoint', 'server'],
    default='local',
    help='Test mode: local (agent), endpoint (serving), server (FastAPI)',
  )
  args = parser.parse_args()

  if args.mode == 'local':
    test_local_agent()
  elif args.mode == 'endpoint':
    test_serving_endpoint()
  elif args.mode == 'server':
    test_fastapi_server()
