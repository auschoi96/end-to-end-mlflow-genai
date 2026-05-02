"""function_tool wrappers around the telco UC functions in main.austin_choi_demo.

Uses DatabricksFunctionClient with serverless execution, so we don't need a
SQL warehouse grant for the app SP — UC routes the function call to managed
serverless compute. The app SP only needs USE SCHEMA + EXECUTE on the schema
(already granted).
"""

import asyncio
import logging
import os
from typing import Optional

from agents import function_tool
from databricks_openai import DatabricksFunctionClient

logger = logging.getLogger(__name__)

TARGET_FN_PREFIX = os.getenv('TELCO_FUNCTION_PREFIX', 'main.austin_choi_demo')

# Lazy-initialized singleton: DatabricksFunctionClient bootstraps a
# WorkspaceClient + serverless session, both of which we want to share across
# tool calls. Initializing per-call would re-auth on every tool invocation.
_client: Optional[DatabricksFunctionClient] = None


def _get_client() -> DatabricksFunctionClient:
  global _client
  if _client is None:
    profile = os.getenv('DATABRICKS_CONFIG_PROFILE')
    kwargs = {'execution_mode': 'serverless'}
    if profile:
      kwargs['profile'] = profile
    _client = DatabricksFunctionClient(**kwargs)
  return _client


def _execute_sync(fn_name: str, params: dict) -> str:
  """Run the UC function on serverless and return its first-column value."""
  client = _get_client()
  result = client.execute_function(f'{TARGET_FN_PREFIX}.{fn_name}', params)
  if getattr(result, 'error', None):
    return f'{{"error": "{result.error}"}}'
  value = getattr(result, 'value', None)
  return value or '{}'


async def _call_function(fn_name: str, params: dict) -> str:
  """Async wrapper that executes the UC function in a worker thread."""
  return await asyncio.to_thread(_execute_sync, fn_name, params)


# ---------------------------------------------------------------------------
# Tool definitions — names and docstrings drive the LLM's tool selection.
# ---------------------------------------------------------------------------


@function_tool
async def get_customer_info(customer: str) -> str:
  """Retrieve a customer's profile, status, location, loyalty tier, and account
  health metrics (churn risk, customer value, satisfaction).

  Args:
    customer: Customer ID like 'CUS-10001'.
  """
  return await _call_function('get_customer_info', {'customer': customer})


@function_tool
async def customer_subscriptions(customer: str) -> str:
  """List the customer's active and past subscription records (plans, devices,
  billing cycles, start/end dates).

  Args:
    customer: Customer ID like 'CUS-10001'.
  """
  return await _call_function('customer_subscriptions', {'customer': customer})


@function_tool
async def get_billing_info(
  customer: str,
  billing_start_date: Optional[str] = None,
  billing_end_date: Optional[str] = None,
) -> str:
  """Retrieve billing records (charges, payment status, due dates) for a customer
  in a date range. If dates are omitted, returns the most recent records.

  Args:
    customer: Customer ID like 'CUS-10001'.
    billing_start_date: ISO date 'YYYY-MM-DD' (optional).
    billing_end_date: ISO date 'YYYY-MM-DD' (optional).
  """
  params: dict = {'customer': customer}
  if billing_start_date:
    params['billing_start_date'] = billing_start_date
  if billing_end_date:
    params['billing_end_date'] = billing_end_date
  return await _call_function('get_billing_info', params)


@function_tool
async def get_usage_info(
  customer: str,
  usage_start_date: str,
  usage_end_date: str,
) -> str:
  """Retrieve usage info (data, voice, SMS) for a customer between two dates.

  Args:
    customer: Customer ID like 'CUS-10001'.
    usage_start_date: ISO date 'YYYY-MM-DD'.
    usage_end_date: ISO date 'YYYY-MM-DD'.
  """
  return await _call_function(
    'get_usage_info',
    {
      'customer': customer,
      'usage_start_date': usage_start_date,
      'usage_end_date': usage_end_date,
    },
  )


@function_tool
async def get_customer_devices(customer: str) -> str:
  """List the devices currently associated with a customer's account
  (model, IMEI, status, activation date).

  Args:
    customer: Customer ID like 'CUS-10001'.
  """
  return await _call_function('get_customer_devices', {'customer': customer})


@function_tool
async def get_devices_info() -> str:
  """List all available device models in the catalog with their specs and features.
  Use this to compare devices or answer questions about supported handsets.
  """
  return await _call_function('get_devices_info', {})


@function_tool
async def get_plans_info() -> str:
  """List all available subscription plans (features, prices, benefits).
  Use this for plan-comparison or recommendation questions.
  """
  return await _call_function('get_plans_info', {})


@function_tool
async def get_promotions_info() -> str:
  """List current and past promotions (discount type/value, validity period,
  description, active status).
  """
  return await _call_function('get_promotions_info', {})


TELCO_TOOLS = [
  get_customer_info,
  customer_subscriptions,
  get_billing_info,
  get_usage_info,
  get_customer_devices,
  get_devices_info,
  get_plans_info,
  get_promotions_info,
]
