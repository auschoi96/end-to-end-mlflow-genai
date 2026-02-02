"""DC Assistant routes for NFL analysis."""

import json
import logging
import os
from enum import Enum
from typing import Optional

import mlflow
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from mlflow_demo.utils.mlflow_helpers import get_mlflow_experiment_id
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/dc-assistant', tags=['dc-assistant'])

# Mode selection: 'local' uses the agent directly, 'endpoint' uses serving endpoint
DC_ASSISTANT_MODE = os.getenv('DC_ASSISTANT_MODE', 'local')


class DcAnalysisRequest(BaseModel):
  """Request for DC Assistant analysis."""

  question: str


class FeedbackRating(str, Enum):
  """Feedback rating enum."""

  THUMBS_UP = 'up'
  THUMBS_DOWN = 'down'


class FeedbackRequest(BaseModel):
  """Feedback request model."""

  trace_id: str
  rating: FeedbackRating
  comment: Optional[str] = None
  user_name: Optional[str] = None


class FeedbackResponse(BaseModel):
  """Feedback response model."""

  success: bool
  message: str


async def _generate_with_local_agent(question: str):
  """Generate response using local agent."""
  from mlflow_demo.agent import AGENT

  done_sent = False
  full_response = ''
  trace_id = None

  try:
    # Set MLflow experiment for tracing (autolog handles the actual tracing)
    mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

    logger.info(f'Using local DC Assistant agent for question: {question[:50]}...')

    for event in AGENT.predict_stream_local(question):
      event_type = event.get('type')

      if event_type == 'token':
        token = event.get('content', '')
        full_response += token
        yield f'data: {json.dumps({"type": "token", "content": token})}\n\n'

      elif event_type == 'tool_call':
        tool_info = event.get('tool', {})
        yield f'data: {json.dumps({"type": "tool_call", "tool": tool_info})}\n\n'

      elif event_type == 'done':
        trace_id = event.get('trace_id')
        yield f'data: {json.dumps({"type": "done", "trace_id": trace_id})}\n\n'
        done_sent = True

      elif event_type == 'error':
        error_msg = event.get('error', 'Unknown error')
        logger.error(f'Agent error: {error_msg}')
        yield f'data: {json.dumps({"type": "error", "error": error_msg})}\n\n'

  except Exception as e:
    logger.error(f'DC Assistant local agent error: {e}')
    yield f'data: {json.dumps({"type": "error", "error": str(e)})}\n\n'

  # Only send final done if we haven't sent one yet
  if not done_sent:
    yield f'data: {json.dumps({"type": "done", "trace_id": trace_id})}\n\n'


async def _generate_with_endpoint(question: str):
  """Generate response using Databricks serving endpoint."""
  from databricks.sdk import WorkspaceClient

  dc_endpoint = os.getenv('LLM_MODEL')
  done_sent = False

  try:
    if not dc_endpoint:
      yield f'data: {json.dumps({"type": "error", "error": "LLM_MODEL environment variable not set"})}\n\n'
      return

    # Set MLflow experiment for tracing
    mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

    w = WorkspaceClient()
    request_payload = {'input': [{'role': 'user', 'content': question}]}

    logger.info(f'Calling DC Assistant endpoint: {dc_endpoint}')

    response = w.serving_endpoints.query(name=dc_endpoint, inputs=request_payload, stream=True)

    full_response = ''

    for chunk in response:
      if hasattr(chunk, 'choices') and chunk.choices:
        delta = chunk.choices[0].delta
        if hasattr(delta, 'content') and delta.content:
          token = delta.content
          full_response += token
          yield f'data: {json.dumps({"type": "token", "content": token})}\n\n'

    # Try to get the trace ID from active trace
    trace_id = None
    try:
      active_trace = mlflow.get_current_active_trace()
      if active_trace:
        trace_id = active_trace.info.request_id
    except Exception:
      pass

    yield f'data: {json.dumps({"type": "done", "trace_id": trace_id})}\n\n'
    done_sent = True

  except Exception as e:
    logger.error(f'DC Assistant endpoint error: {e}')
    yield f'data: {json.dumps({"type": "error", "error": str(e)})}\n\n'

  if not done_sent:
    yield f'data: {json.dumps({"type": "done", "trace_id": None})}\n\n'


@router.post('/analyze-stream')
async def dc_assistant_analyze_stream(request_data: DcAnalysisRequest):
  """Stream DC Assistant analysis generation."""

  async def generate():
    if DC_ASSISTANT_MODE == 'endpoint':
      async for chunk in _generate_with_endpoint(request_data.question):
        yield chunk
    else:
      async for chunk in _generate_with_local_agent(request_data.question):
        yield chunk

  return StreamingResponse(
    generate(),
    media_type='text/event-stream',
    headers={
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  )


@router.post('/feedback', response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
  """Submit user feedback linked to trace."""
  try:
    is_positive = feedback.rating == FeedbackRating.THUMBS_UP

    mlflow.log_feedback(
      trace_id=feedback.trace_id,
      name='user_feedback',
      value=is_positive,
      rationale=feedback.comment,
      source=mlflow.entities.feedback.FeedbackSource(
        source_type='HUMAN',
        source_id=feedback.user_name or 'anonymous',
      ),
    )

    logger.info(f'Feedback logged for trace {feedback.trace_id}: {feedback.rating}')
    return FeedbackResponse(success=True, message='Feedback submitted successfully')

  except Exception as e:
    logger.error(f'Failed to log feedback: {e}')
    return FeedbackResponse(success=False, message=str(e))
