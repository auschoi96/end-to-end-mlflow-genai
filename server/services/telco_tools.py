"""function_tool wrappers around the telco UC functions in main.austin_choi_demo.

Each tool issues a SQL Statements API call against the configured warehouse.
The async SDK call is wrapped via asyncio.to_thread so the FastAPI event loop
stays responsive while the warehouse executes the function.
"""

import asyncio
import json
import logging
import os
from typing import Optional

from agents import function_tool
from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)

DEFAULT_WAREHOUSE = os.getenv('TELCO_TOOL_WAREHOUSE_ID') or os.getenv(
  'MLFLOW_TRACING_SQL_WAREHOUSE_ID', '75fd8278393d07eb'
)
TARGET_FN_PREFIX = os.getenv('TELCO_FUNCTION_PREFIX', 'main.austin_choi_demo')


def _quote(value: str) -> str:
  """SQL-quote a string literal."""
  return "'" + value.replace("'", "''") + "'"


def _execute_sql(stmt: str) -> str:
  """Execute a SQL statement synchronously and return the first row/col as a string."""
  client = WorkspaceClient()
  resp = client.statement_execution.execute_statement(
    warehouse_id=DEFAULT_WAREHOUSE,
    statement=stmt,
    wait_timeout='30s',
  )
  if resp.status and resp.status.state and resp.status.state.value not in ('SUCCEEDED',):
    err = resp.status.error.message if resp.status.error else 'unknown error'
    return json.dumps({'error': f'SQL failed: {err}'})
  if not resp.result or not resp.result.data_array:
    return json.dumps({'error': 'no rows'})
  return resp.result.data_array[0][0] or '{}'


async def _call_function(name: str, args_sql: str) -> str:
  """Run SELECT <prefix>.<name>(<args>) and return its single string output."""
  stmt = f'SELECT {TARGET_FN_PREFIX}.{name}({args_sql})'
  logger.debug('telco tool call: %s', stmt)
  return await asyncio.to_thread(_execute_sql, stmt)


# ---------------------------------------------------------------------------
# Tool definitions — names and docstrings are how the LLM picks them.
# ---------------------------------------------------------------------------


@function_tool
async def get_customer_info(customer: str) -> str:
  """Retrieve a customer's profile, status, location, loyalty tier, and account
  health metrics (churn risk, customer value, satisfaction).

  Args:
    customer: Customer ID like 'CUS-10001'.
  """
  return await _call_function('get_customer_info', _quote(customer))


@function_tool
async def customer_subscriptions(customer: str) -> str:
  """List the customer's active and past subscription records (plans, devices,
  billing cycles, start/end dates).

  Args:
    customer: Customer ID like 'CUS-10001'.
  """
  return await _call_function('customer_subscriptions', _quote(customer))


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
  args = [_quote(customer)]
  if billing_start_date:
    args.append(_quote(billing_start_date))
  if billing_end_date:
    args.append(_quote(billing_end_date))
  return await _call_function('get_billing_info', ', '.join(args))


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
    ', '.join([_quote(customer), _quote(usage_start_date), _quote(usage_end_date)]),
  )


@function_tool
async def get_customer_devices(customer: str) -> str:
  """List the devices currently associated with a customer's account
  (model, IMEI, status, activation date).

  Args:
    customer: Customer ID like 'CUS-10001'.
  """
  return await _call_function('get_customer_devices', _quote(customer))


@function_tool
async def get_devices_info() -> str:
  """List all available device models in the catalog with their specs and features.
  Use this to compare devices or answer questions about supported handsets.
  """
  return await _call_function('get_devices_info', '')


@function_tool
async def get_plans_info() -> str:
  """List all available subscription plans (features, prices, benefits).
  Use this for plan-comparison or recommendation questions.
  """
  return await _call_function('get_plans_info', '')


@function_tool
async def get_promotions_info() -> str:
  """List current and past promotions (discount type/value, validity period,
  description, active status).
  """
  return await _call_function('get_promotions_info', '')


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
