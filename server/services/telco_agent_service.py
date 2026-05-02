"""Async client for the telco support agent model-serving endpoint.

Wraps an httpx client that calls a Databricks model-serving endpoint configured
via TelcoSettings. Supports both non-streaming (send_message) and SSE-streaming
(send_message_stream) calls, with OAuth M2M token refresh on 403.
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

import httpx

from ..config.telco_settings import TelcoSettings
from .telco_sse import (
  AgentResponse,
  ChatMessage,
  extract_streaming_trace_id,
  parse_agent_response,
  parse_sse_line,
  routing_agent_type,
)

logger = logging.getLogger(__name__)


class TelcoAgentService:
  """HTTP client for the telco support agent model-serving endpoint."""

  def __init__(self, settings: TelcoSettings):
    """Initialize with settings; defer client creation if no auth is configured."""
    self.settings = settings

    if not settings.has_auth:
      logger.warning(
        'No Databricks auth for telco agent. Set DATABRICKS_TOKEN locally '
        'or run inside a Databricks App with OAuth M2M.'
      )
      self.client = None
      self.access_token = None
      return

    self.client = httpx.AsyncClient(timeout=httpx.Timeout(settings.request_timeout))
    self.access_token = None
    logger.info('Telco agent service initialized with auth=%s', settings.auth_method)

  async def _get_oauth_token(self) -> str:
    """Exchange client credentials for an OAuth bearer token."""
    if not self.settings.databricks_client_id or not self.settings.databricks_client_secret:
      raise ValueError('OAuth credentials not available')

    workspace_host = self.settings.databricks_host
    token_url = f'{workspace_host}/oidc/v1/token'

    data = {'grant_type': 'client_credentials', 'scope': 'all-apis'}
    auth = (self.settings.databricks_client_id, self.settings.databricks_client_secret)

    response = await self.client.post(
      token_url,
      data=data,
      auth=auth,
      headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )

    if response.status_code != 200:
      logger.error('OAuth token request failed: %d - %s', response.status_code, response.text)
      raise ValueError(f'Failed to get OAuth token: {response.status_code}')

    token_data = response.json()
    access_token = token_data.get('access_token')
    if not access_token:
      raise ValueError('No access_token in OAuth response')
    return access_token

  async def _get_headers(self) -> dict[str, str]:
    """Build request headers with the right Authorization."""
    headers = {'Content-Type': 'application/json'}

    if self.settings.auth_method == 'oauth':
      if not self.access_token:
        try:
          self.access_token = await self._get_oauth_token()
        except Exception as e:
          logger.error('OAuth token fetch failed: %s. Falling back to client_secret bearer.', e)
          headers['Authorization'] = f'Bearer {self.settings.databricks_client_secret}'
          return headers
      headers['Authorization'] = f'Bearer {self.access_token}'
    elif self.settings.auth_method == 'token':
      headers['Authorization'] = f'Bearer {self.settings.databricks_token}'

    return headers

  async def __aenter__(self):
    """Async context manager entry."""
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    """Async context manager exit closes the underlying client."""
    if self.client:
      await self.client.aclose()

  def _build_payload(
    self,
    message: str,
    customer_id: str,
    conversation_history: list[ChatMessage],
    stream: bool = False,
  ) -> dict[str, Any]:
    """Build the model-serving request body."""
    input_messages = [
      {'role': msg.role, 'content': msg.content} for msg in conversation_history
    ]
    input_messages.append({'role': 'user', 'content': message})

    payload: dict[str, Any] = {
      'input': input_messages,
      'custom_inputs': {'customer': customer_id},
      'databricks_options': {'return_trace': True},
    }
    if stream:
      payload['stream'] = True
    return payload

  async def send_message(
    self,
    message: str,
    customer_id: str,
    conversation_history: Optional[list[ChatMessage]] = None,
  ) -> AgentResponse:
    """Send a message non-streaming and return the parsed response."""
    if conversation_history is None:
      conversation_history = []

    if not self.client:
      return AgentResponse(
        response=(
          'Chat functionality is currently unavailable. '
          'Configure Databricks authentication to enable agent responses.'
        ),
        agent_type='error',
        custom_outputs={'error': 'no_authentication'},
      )

    payload = self._build_payload(message, customer_id, conversation_history, stream=False)
    logger.info('Telco chat request for customer %s', customer_id)

    try:
      headers = await self._get_headers()
      response = await self.client.post(
        self.settings.databricks_endpoint, json=payload, headers=headers
      )
      response.raise_for_status()
      return parse_agent_response(response.json())
    except httpx.HTTPStatusError as e:
      return await self._handle_http_status_error(e, payload)
    except httpx.RequestError as e:
      logger.error('Request error to telco endpoint: %s', e)
      return AgentResponse(
        response='Unable to connect to agent service. Please try again.',
        agent_type='error',
        custom_outputs={'error': 'connection_error'},
      )
    except Exception as e:
      logger.exception('Unexpected error in telco send_message')
      return AgentResponse(
        response=f'An unexpected error occurred: {e}',
        agent_type='error',
        custom_outputs={'error': 'unexpected_error'},
      )

  async def _handle_http_status_error(
    self, e: httpx.HTTPStatusError, payload: dict[str, Any]
  ) -> AgentResponse:
    """Refresh OAuth on 403 and retry once; otherwise return an error response."""
    logger.error('HTTP error from telco endpoint: %d - %s', e.response.status_code, e.response.text)
    if e.response.status_code == 403 and self.settings.auth_method == 'oauth':
      logger.info('403 received - refreshing OAuth token and retrying once')
      try:
        self.access_token = await self._get_oauth_token()
        headers = await self._get_headers()
        retry = await self.client.post(
          self.settings.databricks_endpoint, json=payload, headers=headers
        )
        retry.raise_for_status()
        return parse_agent_response(retry.json())
      except Exception as retry_error:
        logger.error('Retry after token refresh failed: %s', retry_error)
    return AgentResponse(
      response=f'Service temporarily unavailable (HTTP {e.response.status_code}). Please try again.',
      agent_type='error',
      custom_outputs={'error': 'http_error', 'status_code': e.response.status_code},
    )

  async def send_message_stream(
    self,
    message: str,
    customer_id: str,
    conversation_history: Optional[list[ChatMessage]] = None,
  ) -> AsyncGenerator[str, None]:
    """Send a message and yield SSE-formatted events as the response streams."""
    if conversation_history is None:
      conversation_history = []

    if not self.client:
      yield _sse_error('Chat functionality is currently unavailable.')
      return

    payload = self._build_payload(message, customer_id, conversation_history, stream=True)
    logger.info('Telco streaming chat request for customer %s', customer_id)

    try:
      headers = await self._get_headers()
      async with self.client.stream(
        'POST', self.settings.databricks_endpoint, json=payload, headers=headers
      ) as response:
        if response.status_code != 200:
          yield _sse_error(
            f'Service temporarily unavailable (HTTP {response.status_code}: {response.reason_phrase})'
          )
          return
        async for event in self._consume_stream(response):
          yield event
    except httpx.HTTPStatusError as e:
      logger.error('HTTP error in telco stream: %d - %s', e.response.status_code, e.response.text)
      if e.response.status_code == 403 and self.settings.auth_method == 'oauth':
        try:
          self.access_token = await self._get_oauth_token()
          async for event in self.send_message_stream(message, customer_id, conversation_history):
            yield event
          return
        except Exception as retry_error:
          logger.error('Stream retry after token refresh failed: %s', retry_error)
      yield _sse_error(f'Service temporarily unavailable (HTTP {e.response.status_code})')
    except httpx.RequestError as e:
      logger.error('Request error in telco stream: %s', e)
      yield _sse_error('Unable to connect to agent service. Please try again.')
    except Exception as e:
      logger.exception('Unexpected error in telco stream')
      yield _sse_error(f'An unexpected error occurred: {e}')

  async def _consume_stream(self, response: httpx.Response) -> AsyncGenerator[str, None]:
    """Consume the upstream SSE stream and yield reshaped events."""
    collected_tools: list[dict] = []
    current_response_text = ''
    agent_type: Optional[str] = None
    routing_info: Optional[str] = None
    trace_id: Optional[str] = None

    async for chunk in response.aiter_text():
      if not trace_id:
        trace_id = extract_streaming_trace_id(chunk)
        if trace_id:
          logger.info('Extracted trace_id from chunk: %s', trace_id)

      for line in chunk.split('\n'):
        event = parse_sse_line(line)
        if not event:
          continue
        event_type = event.get('type')

        if event_type == 'response.debug':
          for emitted in self._handle_debug_event(event):
            new_agent, new_routing, sse = emitted
            agent_type = new_agent or agent_type
            routing_info = new_routing or routing_info
            yield sse

        elif event_type == 'response.output_item.done':
          item = event.get('item', {})
          for emitted in self._handle_output_item(item, collected_tools):
            text, sse = emitted
            if text:
              current_response_text = text
            yield sse
          maybe_trace = _extract_item_trace_id(item)
          if maybe_trace:
            trace_id = maybe_trace

        elif event_type == 'done':
          break

    logger.info(
      'Telco stream complete: response=%d chars, tools=%d, trace_id=%s',
      len(current_response_text),
      len(collected_tools),
      trace_id,
    )
    yield _sse_event(
      {
        'type': 'completion',
        'agent_type': agent_type,
        'routing_decision': routing_info,
        'tools_used': collected_tools,
        'final_response': current_response_text,
        'trace_id': trace_id,
        'done': True,
      }
    )

  def _handle_debug_event(self, event: dict):
    """Yield routing events from response.debug payloads."""
    item = event.get('item', {})
    routing_decision = item.get('routing_decision', '')
    if 'routed to' not in routing_decision.lower():
      return
    agent_type = routing_agent_type(routing_decision)
    sse = _sse_event(
      {
        'type': 'routing',
        'agent_type': agent_type,
        'routing_decision': routing_decision,
      }
    )
    yield (agent_type, routing_decision, sse)

  def _handle_output_item(self, item: dict, collected_tools: list[dict]):
    """Yield tool_call / tool_result / response_text events for an output item."""
    item_type = item.get('type')

    if item_type == 'function_call':
      tool_info = {
        'type': 'tool_call',
        'tool_name': item.get('name', 'unknown'),
        'call_id': item.get('call_id'),
        'arguments': item.get('arguments', '{}'),
      }
      collected_tools.append(tool_info)
      yield (None, _sse_event(tool_info))

    elif item_type == 'function_call_output':
      call_id = item.get('call_id')
      output = item.get('output', '')
      for tool in collected_tools:
        if tool.get('call_id') == call_id:
          tool['output'] = output
          break
      yield (None, _sse_event({'type': 'tool_result', 'call_id': call_id, 'output': output}))

    elif item_type == 'message' and item.get('role') == 'assistant':
      for content_item in item.get('content', []):
        if content_item.get('type') == 'output_text':
          text = content_item.get('text', '')
          if text:
            yield (text, _sse_event({'type': 'response_text', 'text': text}))

  async def health_check(self) -> bool:
    """Probe the endpoint with a tiny request to confirm it's reachable."""
    if not self.client:
      return False
    try:
      payload = self._build_payload('Hello', 'CUS-10001', [])
      headers = await self._get_headers()
      response = await self.client.post(
        self.settings.databricks_endpoint, json=payload, headers=headers
      )
      return response.status_code == 200
    except Exception as e:
      logger.error('Telco health check failed: %s', e)
      return False

  async def close(self):
    """Close the underlying httpx client."""
    if self.client:
      await self.client.aclose()


def _sse_event(payload: dict) -> str:
  """Serialize a payload as an SSE 'data:' frame."""
  return f'data: {json.dumps(payload)}\n\n'


def _sse_error(error_message: str) -> str:
  """Build an SSE-formatted terminal error frame."""
  return _sse_event({'type': 'error', 'error': error_message, 'done': True})


def _extract_item_trace_id(item: dict) -> Optional[str]:
  """Pull trace_id out of a response.output_item.done payload, if present."""
  databricks_output = item.get('databricks_output', {})
  if not isinstance(databricks_output, dict):
    return None
  trace_info = databricks_output.get('trace', {})
  if not isinstance(trace_info, dict):
    return None
  info = trace_info.get('info', {})
  if isinstance(info, dict):
    return info.get('trace_id')
  return None
