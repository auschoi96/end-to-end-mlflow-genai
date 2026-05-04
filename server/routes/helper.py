"""Helper routes for notebook URLs and utilities."""

import os

from fastapi import APIRouter


def ensure_https_protocol(host: str | None) -> str:
  """Ensure the host URL has HTTPS protocol and strip trailing slashes."""
  if not host:
    return ''

  # Add protocol if missing
  if not (host.startswith('https://') or host.startswith('http://')):
    host = f'https://{host}'

  # Strip trailing slashes to avoid double slashes when concatenating paths
  return host.rstrip('/')


router = APIRouter(prefix='/api', tags=['helper'])


def get_notebook_url(name: str) -> str:
  """Get the URL for a notebook by name."""
  # Map notebook names (as used by demo pages) to environment variable names
  notebook_env_vars = {
    '1_observe_with_traces': 'NOTEBOOK_URL_1_observe_with_traces',
    '2_create_quality_metrics': 'NOTEBOOK_URL_2_create_quality_metrics',
    '3_collect_ground_truth_labels': 'NOTEBOOK_URL_3_collect_ground_truth_labels',
    '4_align_judges_to_experts': 'NOTEBOOK_URL_4_align_judges_to_experts',
    '5_optimize_prompts': 'NOTEBOOK_URL_5_optimize_prompts',
    '6_production_monitoring': 'NOTEBOOK_URL_6_production_monitoring',
  }

  # Get the environment variable name for this notebook
  env_var_name = notebook_env_vars.get(name)
  if env_var_name:
    url = os.getenv(env_var_name)
    if url:
      return url

  return 'NOT FOUND'


@router.get('/get-notebook-url/{name}')
async def get_notebook_url_route(name: str):
  """Get the URL for a notebook by name."""
  url = get_notebook_url(name)
  return {'notebook_name': name, 'url': url}
