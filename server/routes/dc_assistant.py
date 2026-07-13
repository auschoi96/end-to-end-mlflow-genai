"""DC Assistant routes for NFL analysis."""

import json
import logging
import os
from enum import Enum
from typing import Optional
from uuid import uuid4

import mlflow
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from mlflow_demo.agent.session_store import SessionStore
from mlflow_demo.utils.mlflow_helpers import get_mlflow_experiment_id
from pydantic import BaseModel
from server.dependencies.auth import RequestUserContext, get_user_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/dc-assistant', tags=['dc-assistant'])

# Mode selection: 'local' uses the agent directly, 'endpoint' uses serving endpoint
DC_ASSISTANT_MODE = os.getenv('DC_ASSISTANT_MODE', 'local')

# Per-session conversation state for /multi-turn, keyed by session_id.
# Single process only -- see SessionStore docstring for why that's fine here.
session_store = SessionStore()


class DcAnalysisRequest(BaseModel):
  """Request for DC Assistant analysis."""

  question: str
  # Optional multimodal input: base64-encoded image (no data: prefix) plus its
  # mime type, e.g. a formation/coverage diagram the coach is asking about.
  image_base64: Optional[str] = None
  image_mime_type: str = 'image/png'


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


class MultiTurnRequest(BaseModel):
  """Request for multi-turn conversation."""

  question: str
  session_id: Optional[str] = None
  is_first_turn: bool = False


class MultiTurnResponse(BaseModel):
  """Response for multi-turn conversation."""

  response: str
  session_id: str
  trace_id: Optional[str] = None


async def _generate_with_local_agent(
  question: str,
  user_ctx: RequestUserContext,
  image_base64: Optional[str] = None,
  image_mime_type: str = 'image/png',
):
  """Generate response using local agent.

  Single-turn requests don't need conversation continuity: no session_id is
  passed, so the trace carries no session metadata (keeps the MLflow
  Sessions view clean), and this never touches the shared SessionStore/AGENT
  state -- it must not be able to clobber an in-flight /multi-turn
  conversation.

  When image_base64 is provided, the question and image are sent as a single
  multimodal user turn (see agent.py's _to_chat_messages_with_images for how
  the image content part survives the Responses -> ChatCompletions conversion).
  """
  from mlflow_demo.agent.agent import AGENT

  done_sent = False
  full_response = ''
  trace_id = None

  # A single extra content part attached to this turn's user message -- not
  # conversation_history, which represents *prior* turns. Passing this as
  # conversation_history would make predict_stream count the current turn
  # twice (see agent.py predict_stream_local's image_content parameter).
  image_content = None
  if image_base64:
    image_content = [
      {
        'type': 'input_image',
        'image_url': f'data:{image_mime_type};base64,{image_base64}',
      },
    ]

  try:
    # Set MLflow experiment for tracing
    mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

    logger.info('=' * 80)
    logger.info(f'🚀 CALLING AGENT.predict_stream_local()')
    logger.info(f'📝 Question: {question}')
    logger.info(f'🖼️  Image attached: {bool(image_base64)}')
    logger.info('=' * 80)

    for event in AGENT.predict_stream_local(
      question,
      image_content=image_content,
      user_id=user_ctx.user_id,
      model_serving_client=user_ctx.model_serving_client,
    ):
      event_type = event.get('type')

      if event_type == 'token':
        token = event.get('content', '')
        full_response += token
        yield f'data: {json.dumps({"type": "token", "content": token})}\n\n'

      elif event_type == 'tool_call':
        tool_info = event.get('tool', {})
        yield f'data: {json.dumps({"type": "tool_call", "tool": tool_info})}\n\n'

      elif event_type == 'done':
        # Use the trace_id from the agent's event
        trace_id = event.get('trace_id')
        logger.info(f'📊 Trace ID from agent event: {trace_id}')
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
    # Try to get trace_id from active span one more time
    active_span = mlflow.get_current_active_span()
    trace_id = active_span.trace_id if active_span else None
    yield f'data: {json.dumps({"type": "done", "trace_id": trace_id})}\n\n'


async def _generate_with_endpoint(question: str, user_ctx: RequestUserContext):
  """Generate response using Databricks serving endpoint."""
  dc_endpoint = os.getenv('LLM_MODEL')
  done_sent = False

  try:
    if not dc_endpoint:
      yield f'data: {json.dumps({"type": "error", "error": "LLM_MODEL environment variable not set"})}\n\n'
      return

    # Set MLflow experiment for tracing
    mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

    w = user_ctx.workspace_client
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
async def dc_assistant_analyze_stream(
  request_data: DcAnalysisRequest, user_ctx: RequestUserContext = Depends(get_user_context)
):
  """Stream DC Assistant analysis generation."""

  async def generate():
    if DC_ASSISTANT_MODE == 'endpoint':
      async for chunk in _generate_with_endpoint(request_data.question, user_ctx):
        yield chunk
    else:
      async for chunk in _generate_with_local_agent(
        request_data.question,
        user_ctx,
        image_base64=request_data.image_base64,
        image_mime_type=request_data.image_mime_type,
      ):
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
async def submit_feedback(
  feedback: FeedbackRequest, user_ctx: RequestUserContext = Depends(get_user_context)
):
  """Submit user feedback linked to trace."""
  try:
    is_positive = feedback.rating == FeedbackRating.THUMBS_UP

    mlflow.log_feedback(
      trace_id=feedback.trace_id,
      name='user_feedback',
      value=is_positive,
      rationale=feedback.comment,
      source=mlflow.entities.AssessmentSource(
        source_type='HUMAN',
        source_id=feedback.user_name or user_ctx.user_email or 'anonymous',
      ),
    )

    logger.info(f'Feedback logged for trace {feedback.trace_id}: {feedback.rating}')
    return FeedbackResponse(success=True, message='Feedback submitted successfully')

  except Exception as e:
    logger.error(f'Failed to log feedback: {e}')
    return FeedbackResponse(success=False, message=str(e))


@router.post('/multi-turn', response_model=MultiTurnResponse)
async def multi_turn_conversation(
  request: MultiTurnRequest, user_ctx: RequestUserContext = Depends(get_user_context)
):
  """
  Handle multi-turn conversations with session tracking.

  This endpoint demonstrates MLflow's session tracking feature where multiple
  conversation turns are grouped together in a single session view.
  Conversation state lives in the module-level SessionStore, keyed by
  session_id, so concurrent conversations from different users/tabs never
  share state -- the agent itself is stateless per call.
  """
  from mlflow_demo.agent.agent import AGENT
  from mlflow.types.responses import Message, ResponsesAgentRequest

  try:
    # Set MLflow experiment
    mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

    # First turn always starts fresh state, even if the client sent a stale id.
    lookup_id = None if request.is_first_turn else request.session_id
    state = session_store.get_or_create(lookup_id, user_id=user_ctx.user_id)

    logger.info(
      f'Multi-turn request - Session: {state.session_id}, '
      f'History: {len(state.history)} messages'
    )

    # Build request with just the current question
    # The agent's predict_stream merges conversation_history internally
    agent_request = ResponsesAgentRequest(
      input=[Message(role='user', content=request.question)]
    )

    # Serialize turns within the same session (e.g. a double-submit); across
    # sessions this never blocks since each has its own lock.
    with state.lock:
      result = AGENT.predict(
        agent_request,
        session_id=state.session_id,
        user_id=state.user_id,
        conversation_history=state.history,
        model_serving_client=user_ctx.model_serving_client,
      )

    # Extract response text from result
    response_text = ''
    for item in result.output:
      item_dict = item.model_dump() if hasattr(item, 'model_dump') else (item if isinstance(item, dict) else {})
      if item_dict.get('type') == 'message' and item_dict.get('role') == 'assistant':
        content = item_dict.get('content', [])
        if isinstance(content, list) and len(content) > 0:
          if isinstance(content[0], dict) and 'text' in content[0]:
            response_text = content[0]['text']

    # Get trace ID
    trace_id = mlflow.get_last_active_trace_id()

    logger.info(f'Multi-turn response complete - {len(response_text)} chars, trace: {trace_id}')

    return MultiTurnResponse(
      response=response_text, session_id=state.session_id, trace_id=trace_id
    )

  except Exception as e:
    logger.error(f'Multi-turn conversation error: {e}')
    raise
