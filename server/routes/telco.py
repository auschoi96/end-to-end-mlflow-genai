"""Telco support agent routes.

Mounted under /api/telco/* to avoid collision with NFL DC Assistant routes.
Calls mlflow.set_experiment per-request inside the feedback handler so the
telco experiment stays isolated from the NFL one.
"""

import json
import logging
import traceback
from typing import Optional

import mlflow
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from mlflow.client import MlflowClient
from mlflow.entities import AssessmentSource, AssessmentSourceType
from pydantic import BaseModel, Field

from ..config.telco_settings import TelcoSettings, get_telco_settings
from ..services.telco_agent_service import TelcoAgentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/telco', tags=['telco'])


class ChatMessageModel(BaseModel):
  """Chat message model."""

  role: str = Field(..., description='Message role (user/assistant)')
  content: str = Field(..., description='Message content')


class ChatRequest(BaseModel):
  """Chat request model."""

  message: str = Field(..., description='User message')
  customer_id: str = Field(..., description='Customer ID, e.g. CUS-10001')
  conversation_history: list[ChatMessageModel] = Field(
    default_factory=list, description='Previous conversation messages'
  )


class AgentResponseModel(BaseModel):
  """Agent response model."""

  response: str
  agent_type: Optional[str] = None
  custom_outputs: Optional[dict] = None
  tools_used: Optional[list[dict]] = None
  trace_id: Optional[str] = None


class CustomerInfo(BaseModel):
  """Customer ID + display label."""

  customer_id: str
  display_name: str


class FeedbackRequest(BaseModel):
  """Feedback submission body."""

  trace_id: str = Field(..., description='MLflow trace ID')
  is_positive: bool = Field(..., description='Thumbs up = True, thumbs down = False')
  comment: Optional[str] = Field(None, description='Optional feedback comment')
  agent_id: str = Field(..., description='Reviewer ID who gave feedback')


class FeedbackResponse(BaseModel):
  """Feedback submission response."""

  status: str
  trace_id: str
  experiment_url: Optional[str] = None


def get_agent_service(
  settings: TelcoSettings = Depends(get_telco_settings),
) -> TelcoAgentService:
  """FastAPI dependency for the telco agent service."""
  return TelcoAgentService(settings)


@router.get('/customers', response_model=list[CustomerInfo])
async def get_demo_customers(settings: TelcoSettings = Depends(get_telco_settings)):
  """Return the demo customer list from env."""
  try:
    customers = []
    for customer_id in settings.demo_customer_ids:
      number = customer_id.replace('CUS-', '')
      customers.append(
        CustomerInfo(customer_id=customer_id, display_name=f'Customer {number}')
      )
    return customers
  except Exception as e:
    logger.error('Error getting demo customers: %s', e)
    logger.error(traceback.format_exc())
    raise HTTPException(status_code=500, detail=f'Error retrieving customers: {e}') from e


@router.post('/chat', response_model=AgentResponseModel)
async def chat(
  request: ChatRequest, agent_service: TelcoAgentService = Depends(get_agent_service)
):
  """Non-streaming chat completion."""
  try:
    response = await agent_service.send_message(
      message=request.message,
      customer_id=request.customer_id,
      conversation_history=[
        # The service expects its own ChatMessage model; convert here.
        _to_service_message(m) for m in request.conversation_history
      ],
    )
    return response
  except Exception as e:
    logger.error('Telco chat error: %s', e)
    logger.error(traceback.format_exc())
    raise HTTPException(status_code=500, detail=f'Chat processing error: {e}') from e


@router.post('/chat/stream')
async def chat_stream(
  request: ChatRequest, agent_service: TelcoAgentService = Depends(get_agent_service)
):
  """Streaming chat completion via Server-Sent Events."""
  try:
    async def event_generator():
      try:
        async for event_data in agent_service.send_message_stream(
          message=request.message,
          customer_id=request.customer_id,
          conversation_history=[_to_service_message(m) for m in request.conversation_history],
        ):
          yield event_data
      except Exception as e:
        logger.error('Streaming generator error: %s', e)
        logger.error(traceback.format_exc())
        yield f'data: {json.dumps({"type": "error", "error": str(e), "done": True})}\n\n'

    return StreamingResponse(
      event_generator(),
      media_type='text/event-stream',
      headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Cache-Control',
      },
    )
  except Exception as e:
    logger.error('Streaming setup error: %s', e)
    logger.error(traceback.format_exc())
    raise HTTPException(status_code=500, detail=f'Error setting up streaming request: {e}') from e


@router.get('/health')
async def agent_health(agent_service: TelcoAgentService = Depends(get_agent_service)):
  """Probe the model-serving endpoint with a tiny request."""
  try:
    is_healthy = await agent_service.health_check()
    return {
      'status': 'healthy' if is_healthy else 'unhealthy',
      'endpoint': agent_service.settings.databricks_endpoint,
    }
  except Exception as e:
    logger.error('Telco health check error: %s', e)
    return {'status': 'unhealthy', 'endpoint': 'unknown', 'error': str(e)}


@router.get('/mlflow-experiment')
async def get_mlflow_experiment_info(settings: TelcoSettings = Depends(get_telco_settings)):
  """Return the telco MLflow experiment URL for the trace-link UI."""
  try:
    experiment_id = settings.mlflow_experiment_id
    mlflow_host = settings.databricks_host.rstrip('/')
    return {
      'experiment_id': experiment_id,
      'experiment_path': settings.mlflow_experiment_path,
      'mlflow_url': f'{mlflow_host}/ml/experiments/{experiment_id}' if experiment_id else None,
      'environment': settings.environment,
    }
  except Exception as e:
    logger.error('MLflow experiment info error: %s', e)
    logger.error(traceback.format_exc())
    return {'error': str(e), 'experiment_path': settings.mlflow_experiment_path, 'mlflow_url': None}


@router.post('/feedback', response_model=FeedbackResponse)
async def submit_feedback(
  request: FeedbackRequest, settings: TelcoSettings = Depends(get_telco_settings)
):
  """Log thumbs-up/down feedback against a telco trace.

  Sets the telco MLflow experiment per request so traces don't cross-pollinate
  with the NFL experiment.
  """
  try:
    mlflow.set_tracking_uri('databricks')
    mlflow.set_experiment(settings.mlflow_experiment_path)

    client = MlflowClient()
    experiment_url = None
    try:
      trace = client.get_trace(request.trace_id)
      experiment_id = trace.info.experiment_id
      host = settings.databricks_host.rstrip('/')
      experiment_url = f'{host}/ml/experiments/{experiment_id}'
    except Exception as e:
      logger.warning('Could not resolve experiment URL from trace: %s', e)

    mlflow.log_feedback(
      trace_id=request.trace_id,
      name='user_feedback',
      value=request.is_positive,
      source=AssessmentSource(
        source_type=AssessmentSourceType.HUMAN,
        source_id=request.agent_id,
      ),
      rationale=request.comment,
    )

    return FeedbackResponse(
      status='success',
      trace_id=request.trace_id,
      experiment_url=experiment_url,
    )
  except Exception as e:
    logger.error('Feedback submission error: %s', e)
    logger.error(traceback.format_exc())
    raise HTTPException(status_code=500, detail=f'Error submitting feedback: {e}') from e


def _to_service_message(m: ChatMessageModel):
  """Convert a route-layer ChatMessageModel into the service-layer ChatMessage."""
  from ..services.telco_sse import ChatMessage

  return ChatMessage(role=m.role, content=m.content)
