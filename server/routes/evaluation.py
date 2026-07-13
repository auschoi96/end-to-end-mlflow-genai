"""Evaluation routes for running MLflow LLM judge evaluations."""

import json
import logging
import os
from typing import Optional

import mlflow
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from mlflow_demo.utils.mlflow_helpers import get_mlflow_experiment_id
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/evaluation', tags=['evaluation'])

# Fallback questions if the curated dataset can't be loaded
EVAL_QUESTIONS = [
  'How does the 2024 Kansas City Chiefs offense approach third-and-long situations?',
  'What are the most common passing concepts used by the 2023 San Francisco 49ers in the red zone?',
  'How does the 2024 Baltimore Ravens offense adjust when facing a blitz-heavy defense?',
  'What tendencies does the 2024 Dallas Cowboys offense show on first down?',
  'Which running plays are most effective for the 2023 Cleveland Browns against a blitz?',
  'How does the 2024 Miami Dolphins offense attack Cover 2 defenses?',
  'What is the typical play sequence for the 2024 Buffalo Bills with under two minutes left in the half?',
  'How does the 2024 Green Bay Packers offense change their approach in the red zone?',
  'Which receivers are most targeted by the 2024 Los Angeles Rams on third down?',
  'How does the 2024 New England Patriots offense exploit man-to-man coverage?',
]

# Curated single-turn eval dataset (questions sourced from real app traces).
# Fully-qualified UC name; override via env when the dataset lives outside
# the app's UC_CATALOG.UC_SCHEMA (e.g. schema-permission constraints).
SINGLE_TURN_EVAL_DATASET = 'single_turn_eval_set'


def get_single_turn_dataset_name() -> str:
  """Resolve the fully-qualified UC name of the single-turn eval dataset."""
  override = os.environ.get('SINGLE_TURN_EVAL_DATASET_NAME')
  if override:
    return override
  catalog = os.environ.get('UC_CATALOG', '')
  schema = os.environ.get('UC_SCHEMA', '')
  return f'{catalog}.{schema}.{SINGLE_TURN_EVAL_DATASET}'


def read_dataset_table_via_sql(table_name: str, column: str) -> list[str]:
  """Read one column of a dataset's synced UC table via the SQL API.

  Fallback for Databricks Apps: databricks-agents' get_dataset() syncs the
  dataset to UC on every read, which imports pyspark — not available in the
  app container — so it always raises there. The synced UC table itself is
  readable with just databricks-sdk. Requires SQL_WAREHOUSE_ID.
  """
  from databricks.sdk import WorkspaceClient

  warehouse_id = os.environ.get('SQL_WAREHOUSE_ID', '')
  if not warehouse_id:
    raise RuntimeError('SQL_WAREHOUSE_ID not set; cannot read dataset table via SQL')

  w = WorkspaceClient()
  resp = w.statement_execution.execute_statement(
    statement=f'SELECT {column} FROM {table_name}',
    warehouse_id=warehouse_id,
    wait_timeout='50s',
  )
  state = str(getattr(resp.status, 'state', ''))
  if 'SUCCEEDED' not in state:
    raise RuntimeError(f'SQL read of {table_name} failed: {state} {getattr(resp.status, "error", "")}')
  rows = resp.result.data_array or []
  return [r[0] for r in rows if r and r[0]]


def load_single_turn_eval_data():
  """Load eval data from the curated dataset, falling back to EVAL_QUESTIONS.

  Tries mlflow.genai.datasets first (links the dataset to the run in the
  MLflow UI when it works), then a direct SQL read of the synced UC table,
  then the hardcoded fallback questions.

  Returns (data, source_name, record_count).
  """
  dataset_name = get_single_turn_dataset_name()
  try:
    ds = mlflow.genai.datasets.get_dataset(name=dataset_name)
    n_records = len(ds.to_df())
    if n_records > 0:
      logger.info(f'Loaded eval dataset {dataset_name} ({n_records} records)')
      return ds, dataset_name, n_records
    logger.warning(f'Eval dataset {dataset_name} is empty')
  except Exception as e:
    logger.warning(f'mlflow.genai.datasets could not load {dataset_name}: {e}')

  try:
    raw_inputs = read_dataset_table_via_sql(dataset_name, 'inputs')
    records = []
    for raw in raw_inputs:
      inputs = json.loads(raw) if isinstance(raw, str) else raw
      if isinstance(inputs, dict) and inputs.get('input'):
        records.append({'inputs': inputs})
    if records:
      logger.info(f'Loaded eval dataset {dataset_name} via SQL ({len(records)} records)')
      return records, f'{dataset_name} (via SQL)', len(records)
  except Exception as e:
    logger.warning(f'SQL read of {dataset_name} failed: {e}; using fallback questions')

  fallback = [
    {'inputs': {'input': [{'role': 'user', 'content': q}]}} for q in EVAL_QUESTIONS
  ]
  return fallback, 'builtin_fallback', len(fallback)


class RunEvalRequest(BaseModel):
  """Request to run evaluation with selected scorers."""

  builtin_judges: list[str] = []
  custom_guidelines: list[dict] = []


class RunSessionEvalRequest(BaseModel):
  """Request to run session-level evaluation with selected scorers."""

  session_judges: list[str] = []


@router.post('/run')
async def run_evaluation(request: RunEvalRequest):
  """Run mlflow.genai.evaluate() with selected scorers, streaming progress via SSE."""

  async def generate():
    from mlflow.genai.scorers import Guidelines

    try:
      # Set experiment
      mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

      # Build scorers list
      scorers = []

      # Add built-in judges
      from mlflow.genai import scorers as mlflow_scorers

      # Map frontend checkbox names to actual scorer classes
      builtin_map = {
        'RelevanceToQuery': mlflow_scorers.RelevanceToQuery,
        'Safety': mlflow_scorers.Safety,
        'ToolCallCorrectness': mlflow_scorers.ToolCallCorrectness,
        'ToolCallEfficiency': mlflow_scorers.ToolCallEfficiency,
      }

      logger.info(f'Requested built-in judges: {request.builtin_judges}')
      logger.info(f'Available builtin_map keys: {list(builtin_map.keys())}')

      for name in request.builtin_judges:
        if name in builtin_map:
          scorers.append(builtin_map[name]())
          logger.info(f'Added built-in scorer: {name}')
        else:
          logger.warning(f'Built-in scorer not found: {name}')

      # Add custom guidelines judges (always included)
      logger.info(f'Requested custom guidelines: {[g.get("name") for g in request.custom_guidelines]}')
      for g in request.custom_guidelines:
        if g.get('name') and g.get('guideline'):
          scorers.append(Guidelines(name=g['name'], guidelines=g['guideline']))
          logger.info(f'Added custom guideline scorer: {g["name"]}')

      # Load curated eval questions from the UC dataset (fallback: EVAL_QUESTIONS)
      eval_data, dataset_source, total_questions = load_single_turn_eval_data()
      total_scorers = len(scorers)
      logger.info(f'Total scorers built: {total_scorers} ({[type(s).__name__ for s in scorers]})')

      yield f'data: {json.dumps({"type": "start", "total_questions": total_questions, "total_scorers": total_scorers, "dataset": dataset_source})}\n\n'

      logger.info(
        f'Starting evaluation: {total_questions} questions from {dataset_source}, {total_scorers} scorers'
      )

      # 'input' key matches predict_fn parameter name
      from mlflow_demo.agent.agent import AGENT
      from mlflow.types.responses import ResponsesAgentRequest

      def predict_fn(input):
        # Stateless predict: each eval question gets its own auto-generated
        # session id and empty conversation history.
        return AGENT.predict(ResponsesAgentRequest(input=input))

      # Send progress updates as we go
      # We'll run the actual evaluation and stream progress
      yield f'data: {json.dumps({"type": "progress", "step": "loading", "message": "Loading agent and scorers...", "percent": 5})}\n\n'

      yield f'data: {json.dumps({"type": "progress", "step": "running", "message": f"Running {total_scorers} scorers against {total_questions} questions...", "percent": 15})}\n\n'

      # Run mlflow.genai.evaluate()
      from datetime import datetime

      with mlflow.start_run(
        run_name=f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_dc_eval'
      ) as run:
        results = mlflow.genai.evaluate(
          data=eval_data,
          predict_fn=predict_fn,
          scorers=scorers,
        )
        run_id = run.info.run_id

      yield f'data: {json.dumps({"type": "progress", "step": "finalizing", "message": "Finalizing results...", "percent": 90})}\n\n'

      # Extract summary metrics
      metrics_summary = {}
      if hasattr(results, 'metrics') and results.metrics:
        metrics_summary = {
          k: v for k, v in results.metrics.items() if isinstance(v, (int, float))
        }

      yield f'data: {json.dumps({"type": "done", "run_id": run_id, "metrics": metrics_summary, "percent": 100})}\n\n'

      logger.info(f'Evaluation complete. Run ID: {run_id}')

    except Exception as e:
      logger.error(f'Evaluation error: {e}')
      yield f'data: {json.dumps({"type": "error", "error": str(e)})}\n\n'

  return StreamingResponse(
    generate(),
    media_type='text/event-stream',
    headers={
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  )


@router.get('/latest-run')
async def get_latest_eval_run(run_type: str = 'single'):
  """Return the most recent evaluation run of the given type.

  run_type 'single' matches runs named *_dc_eval (built-in judge evals);
  'session' matches *_session_eval. Used by the UI so "View Pre-run Results"
  deep-links to a specific run instead of the all-runs list.
  """
  from mlflow.tracking import MlflowClient

  suffix = '_session_eval' if run_type == 'session' else '_dc_eval'
  try:
    client = MlflowClient()
    runs = client.search_runs(
      [get_mlflow_experiment_id()],
      order_by=['attributes.start_time DESC'],
      max_results=100,
    )
    for r in runs:
      name = r.info.run_name or ''
      if name.endswith(suffix) and r.info.status == 'FINISHED':
        return {'run_id': r.info.run_id, 'run_name': name}
  except Exception as e:
    logger.warning(f'latest-run lookup failed: {e}')
  return {'run_id': None, 'run_name': None}


# Dataset name for session-level evaluation traces. Fully-qualified UC name;
# override via env when the dataset lives outside the app's UC_CATALOG.UC_SCHEMA
# (mirrors SINGLE_TURN_EVAL_DATASET_NAME below).
SESSION_EVAL_DATASET = 'short_eval_session_set'


def get_session_dataset_name() -> str:
  """Resolve the fully-qualified UC name of the session eval dataset."""
  override = os.environ.get('SESSION_EVAL_DATASET_NAME')
  if override:
    return override
  catalog = os.environ.get('UC_CATALOG', '')
  schema = os.environ.get('UC_SCHEMA', '')
  return f'{catalog}.{schema}.{SESSION_EVAL_DATASET}'


@router.post('/run-session')
async def run_session_evaluation(request: RunSessionEvalRequest):
  """Run session-level evaluation on pre-collected multi-turn traces via SSE."""

  async def generate():
    try:
      from mlflow.genai import scorers as mlflow_scorers
      from datetime import datetime

      exp_id = get_mlflow_experiment_id()
      mlflow.set_experiment(experiment_id=exp_id)

      # Map frontend names to session-level scorer classes
      session_scorer_map = {
        'ConversationCompleteness': mlflow_scorers.ConversationCompleteness,
        'ConversationalRoleAdherence': mlflow_scorers.ConversationalRoleAdherence,
        'ConversationalSafety': mlflow_scorers.ConversationalSafety,
        'ConversationalToolCallEfficiency': mlflow_scorers.ConversationalToolCallEfficiency,
        'KnowledgeRetention': mlflow_scorers.KnowledgeRetention,
        'UserFrustration': mlflow_scorers.UserFrustration,
      }

      # Build scorers
      scorers = []
      for name in request.session_judges:
        if name in session_scorer_map:
          scorers.append(session_scorer_map[name]())
          logger.info(f'Added session scorer: {name}')
        else:
          logger.warning(f'Session scorer not found: {name}')

      total_scorers = len(scorers)
      logger.info(f'Session evaluation: {total_scorers} scorers')

      yield f'data: {json.dumps({"type": "start", "total_scorers": total_scorers})}\n\n'

      # Load trace IDs from the evaluation dataset
      dataset_name = get_session_dataset_name()

      logger.info(f'Loading dataset: {dataset_name}')
      trace_ids = set()
      try:
        ds = mlflow.genai.datasets.get_dataset(name=dataset_name)
        df = ds.to_df()
        for _, row in df.iterrows():
          source = row.get('source', {})
          if isinstance(source, dict) and 'trace' in source:
            trace_ids.add(source['trace']['trace_id'])
      except Exception as e:
        # In the app container get_dataset() fails (needs pyspark for UC
        # sync); read the synced UC table directly instead.
        logger.warning(f'mlflow.genai.datasets could not load {dataset_name}: {e}; trying SQL')
        for raw in read_dataset_table_via_sql(dataset_name, 'source'):
          source = json.loads(raw) if isinstance(raw, str) else raw
          trace = source.get('trace') if isinstance(source, dict) else None
          if trace and trace.get('trace_id'):
            trace_ids.add(trace['trace_id'])

      logger.info(f'Dataset contains {len(trace_ids)} trace IDs')

      yield f'data: {json.dumps({"type": "progress", "message": f"Loaded {len(trace_ids)} traces from dataset"})}\n\n'

      # Load each dataset trace directly by ID — avoids brittle search/filter and max_results caps.
      dataset_traces = []
      for tid in trace_ids:
        try:
          trace = mlflow.get_trace(tid)
          if trace is not None:
            dataset_traces.append(trace)
        except Exception as e:
          logger.warning(f'Could not load trace {tid}: {e}')
      logger.info(f'Loaded {len(dataset_traces)} traces from dataset IDs')

      if not dataset_traces:
        yield f'data: {json.dumps({"type": "error", "error": "No traces could be loaded from dataset IDs"})}\n\n'
        return

      # Count sessions
      sessions = set()
      for t in dataset_traces:
        sid = t.info.request_metadata.get('mlflow.trace.session', '')
        if sid:
          sessions.add(sid)

      yield f'data: {json.dumps({"type": "progress", "message": f"Evaluating {len(sessions)} sessions ({len(dataset_traces)} traces) with {total_scorers} scorers..."})}\n\n'

      # Run mlflow.genai.evaluate with session-level scorers
      with mlflow.start_run(
        run_name=f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_session_eval'
      ) as run:
        results = mlflow.genai.evaluate(
          data=dataset_traces,
          scorers=scorers,
        )
        run_id = run.info.run_id

      # Extract summary metrics
      metrics_summary = {}
      if hasattr(results, 'metrics') and results.metrics:
        metrics_summary = {
          k: v for k, v in results.metrics.items() if isinstance(v, (int, float))
        }

      yield f'data: {json.dumps({"type": "done", "run_id": run_id, "metrics": metrics_summary, "sessions": len(sessions), "traces": len(dataset_traces)})}\n\n'

      logger.info(f'Session evaluation complete. Run ID: {run_id}')

    except Exception as e:
      logger.error(f'Session evaluation error: {e}')
      yield f'data: {json.dumps({"type": "error", "error": str(e)})}\n\n'

  return StreamingResponse(
    generate(),
    media_type='text/event-stream',
    headers={
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  )
