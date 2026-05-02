"""SSE event parsing and response shaping for the telco model-serving endpoint.

The endpoint occasionally emits oversized SSE chunks containing the entire
response payload at once with malformed JSON (truncated near databricks_output
trace info). The recovery helpers here extract the assistant text out of those
chunks so the UI still renders something useful instead of dropping the event.
"""

import json
import logging
import re
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
  """Chat message in the conversation history."""

  role: str
  content: str


class AgentResponse(BaseModel):
  """Parsed non-streaming response from the telco agent endpoint."""

  response: str
  agent_type: Optional[str] = None
  custom_outputs: Optional[dict] = None
  tools_used: Optional[list[dict]] = None
  trace_id: Optional[str] = None


def parse_sse_line(line: str) -> Optional[dict]:
  """Parse a single SSE line into an event dict, with recovery for malformed chunks."""
  line = line.strip()

  if not line or line.startswith(':'):
    return None

  if not line.startswith('data: '):
    return None

  data_content = line[6:]

  if data_content == '[DONE]':
    return {'type': 'done'}

  try:
    return json.loads(data_content)
  except json.JSONDecodeError as err:
    return _recover_from_malformed_chunk(data_content, err)


def _recover_from_malformed_chunk(data_content: str, err: json.JSONDecodeError) -> Optional[dict]:
  """Best-effort extraction of assistant text from a malformed SSE chunk."""
  if 'databricks_output' not in data_content or 'trace' not in data_content:
    if len(data_content) > 100:
      logger.warning('Failed to parse SSE data: %s..., error: %s', data_content[:100], err)
    return None

  logger.debug('Recovering large databricks_output chunk (%d chars)', len(data_content))

  recovered = _extract_assistant_text_via_item(data_content)
  if recovered:
    return recovered

  longest = _extract_longest_text_field(data_content)
  if longest and len(longest) > 100:
    logger.info('Recovered %d chars from malformed chunk via text-field scan', len(longest))
    return _wrap_as_output_item_done(longest)

  return None


def _extract_assistant_text_via_item(data_content: str) -> Optional[dict]:
  """Try to extract a complete assistant message by parsing the 'item' object."""
  if (
    '"type":"response.output_item.done"' not in data_content
    or '"role":"assistant"' not in data_content
  ):
    return None

  item_match = re.search(
    r'"item"\s*:\s*({[^}]*"role"\s*:\s*"assistant"[^}]*})',
    data_content,
  )
  if not item_match:
    return None

  try:
    item_str = item_match.group(1)
    content_start = item_str.find('"content":')
    if content_start == -1:
      return None
    content_start = item_str.find('[', content_start)
    if content_start == -1:
      return None

    bracket_count = 0
    content_end = content_start
    for i in range(content_start, len(item_str)):
      if item_str[i] == '[':
        bracket_count += 1
      elif item_str[i] == ']':
        bracket_count -= 1
        if bracket_count == 0:
          content_end = i + 1
          break

    content_array = json.loads(item_str[content_start:content_end])
    for content_item in content_array:
      if content_item.get('type') == 'output_text':
        text = content_item.get('text', '')
        if text:
          logger.info('Recovered %d chars from item-match path', len(text))
          return _wrap_as_output_item_done(text)
  except Exception as e:
    logger.debug('Item-match recovery failed: %s', e)

  return None


def _extract_longest_text_field(data_content: str) -> str:
  """Scan for all text fields and return the longest one."""
  matches = re.findall(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', data_content)
  longest = ''
  for raw in matches:
    try:
      decoded = json.loads('"' + raw + '"')
      if len(decoded) > len(longest):
        longest = decoded
    except json.JSONDecodeError:
      continue
  return longest


def _wrap_as_output_item_done(text: str) -> dict:
  """Wrap recovered text in the response.output_item.done envelope."""
  return {
    'type': 'response.output_item.done',
    'item': {
      'type': 'message',
      'role': 'assistant',
      'content': [{'type': 'output_text', 'text': text}],
    },
  }


def parse_agent_response(databricks_response: dict[str, Any]) -> AgentResponse:
  """Parse a non-streaming response from the telco endpoint."""
  try:
    response_text = ''
    agent_type = None
    tools_used: list[dict] = []
    execution_steps: list[dict] = []

    trace_id = _extract_trace_id(databricks_response)

    output = databricks_response.get('output', [])
    for item in output:
      item_type = item.get('type')
      if item_type == 'message' and item.get('role') == 'assistant':
        for content_item in item.get('content', []):
          if content_item.get('type') == 'output_text':
            response_text += content_item.get('text', '')
      elif item_type == 'function_call':
        tool_call, step = _parse_function_call(item)
        tools_used.append(tool_call)
        execution_steps.append(step)
      elif item_type == 'function_call_output':
        execution_steps.append(_parse_function_call_output(item))

    custom_outputs = databricks_response.get('custom_outputs', {})
    routing_info = custom_outputs.get('routing', {})
    if routing_info:
      agent_type = routing_info.get('agent_type')

    if agent_type:
      execution_steps.insert(
        0,
        {
          'step_type': 'routing',
          'description': f'Query routed to {agent_type} agent',
          'reasoning': f'This query is best handled by the {agent_type} specialist',
        },
      )

    return AgentResponse(
      response=response_text
      or "I apologize, but I couldn't generate a proper response. Please try again.",
      agent_type=agent_type,
      custom_outputs={**custom_outputs, 'execution_steps': execution_steps},
      tools_used=tools_used,
      trace_id=trace_id,
    )
  except Exception as e:
    logger.error('Error parsing agent response: %s', e)
    return AgentResponse(
      response='I encountered an error processing your request. Please try again.',
    )


def _extract_trace_id(databricks_response: dict[str, Any]) -> Optional[str]:
  """Extract trace_id from a non-streaming response (multiple possible locations)."""
  databricks_output = databricks_response.get('databricks_output', {})
  if isinstance(databricks_output, dict):
    trace_info = databricks_output.get('trace', {})
    if isinstance(trace_info, dict):
      info = trace_info.get('info', {})
      if isinstance(info, dict) and info.get('trace_id'):
        return info.get('trace_id')
    if databricks_output.get('trace_id'):
      return databricks_output.get('trace_id')
    if databricks_output.get('request_id'):
      return databricks_output.get('request_id')
  return databricks_response.get('trace_id')


def _parse_function_call(item: dict) -> tuple[dict, dict]:
  """Parse a function_call output item into (tool_call, execution_step)."""
  function_name = item.get('name', 'unknown_function')
  function_args = item.get('arguments', '{}')
  call_id = item.get('call_id', '')

  try:
    parsed_args = (
      json.loads(function_args) if isinstance(function_args, str) else function_args
    )
  except (json.JSONDecodeError, TypeError):
    parsed_args = {'raw_arguments': function_args}

  tool_call = {
    'name': function_name,
    'arguments': parsed_args,
    'call_id': call_id,
    'type': 'function_call',
  }
  step = {
    'step_type': 'tool_call',
    'tool_name': function_name,
    'description': f'Calling {function_name}',
    'arguments': parsed_args,
    'reasoning': f'Using {function_name} to retrieve relevant information',
  }
  return tool_call, step


def _parse_function_call_output(item: dict) -> dict:
  """Parse a function_call_output item into an execution_step."""
  call_id = item.get('call_id', '')
  output_data = item.get('output', '')

  try:
    if isinstance(output_data, str) and output_data.startswith('{'):
      parsed_output = json.loads(output_data)
    else:
      parsed_output = output_data
  except (json.JSONDecodeError, TypeError):
    parsed_output = output_data

  return {
    'step_type': 'tool_result',
    'call_id': call_id,
    'description': 'Tool execution completed',
    'result': parsed_output,
    'reasoning': 'Retrieved relevant information to answer the query',
  }


def extract_streaming_trace_id(chunk: str) -> Optional[str]:
  """Pull a trace_id token like 'tr-xxxxx' out of a raw streaming chunk."""
  match = re.search(r'"trace_id":\s*"(tr-[^"]+)"', chunk)
  return match.group(1) if match else None


def routing_agent_type(routing_decision: str) -> Optional[str]:
  """Map a routing-decision string to a canonical agent type."""
  text = routing_decision.lower()
  if 'account agent' in text:
    return 'account'
  if 'billing agent' in text:
    return 'billing'
  if 'tech support agent' in text:
    return 'tech_support'
  if 'product agent' in text:
    return 'product'
  return None
