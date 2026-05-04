"""Lightweight live GEPA prompt optimization route.

Mirrors the SSE pattern in routes/evaluation.py. Runs a deliberately small
optimize_prompts call so users get a real result in ~1-3 minutes:
  - 3 training questions
  - max_metric_calls=20 (vs default 100)
  - Built-in Guidelines scorers for accuracy/relevance/actionability
    (the experiment doesn't yet have an aligned MemAlign judge registered)
"""

import json
import logging
import os
from datetime import datetime

import mlflow
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from mlflow_demo.utils.mlflow_helpers import get_mlflow_experiment_id
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/optimization', tags=['optimization'])

# Tiny training set keeps the run cheap. GEPA evaluates each candidate against
# this set, so smaller = faster.
TRAIN_QUESTIONS = [
  'How does the 2024 Kansas City Chiefs offense approach third-and-long?',
  'What are the most common red-zone passing concepts for the 2023 49ers?',
  'How do the 2024 Ravens adjust against blitz-heavy defenses?',
]

# Quality dimensions mirror the labeling schemas created on the experiment.
SCORER_GUIDELINES = {
  'accuracy': 'The response must only cite statistics, players, formations, and tendencies that appear in tool call results. No fabricated numbers.',
  'relevance': 'The response must directly answer the question about opponent tendencies, situations, or strategy.',
  'actionability': 'The response must include specific defensive adjustments or play calls a coach could use in game planning.',
}


class RunOptimizationRequest(BaseModel):
  """Future-proofing — currently no per-request knobs."""

  pass


@router.post('/run')
async def run_optimization(request: RunOptimizationRequest):
  """Run a lightweight GEPA optimization and register the result if score improves."""

  async def generate():
    try:
      from mlflow.genai.optimize import GepaPromptOptimizer
      from mlflow.genai.scorers import Guidelines

      mlflow.set_experiment(experiment_id=get_mlflow_experiment_id())

      uc_catalog = os.environ.get('UC_CATALOG', '')
      uc_schema = os.environ.get('UC_SCHEMA', '')
      prompt_short_name = os.environ.get('PROMPT_NAME', 'dc_assistant_system_prompt')
      prompt_full_name = (
        prompt_short_name
        if '.' in prompt_short_name
        else f'{uc_catalog}.{uc_schema}.{prompt_short_name}'
      )
      prompt_alias = os.environ.get('PROMPT_ALIAS', 'production')
      reflection_model = os.environ.get('REFLECTION_MODEL', 'databricks:/databricks-claude-sonnet-4-6')

      yield f'data: {json.dumps({"type": "start", "message": "Starting lightweight GEPA optimization..."})}\n\n'

      yield f'data: {json.dumps({"type": "progress", "step": "loading_prompt", "message": f"Loading current prompt {prompt_full_name}@{prompt_alias}...", "percent": 5})}\n\n'

      current_prompt = mlflow.genai.load_prompt(f'prompts:/{prompt_full_name}@{prompt_alias}')
      logger.info(f'Loaded prompt {prompt_full_name}@{prompt_alias}, len={len(current_prompt.template)}')

      from mlflow_demo.agent.agent import AGENT

      def predict_fn(input):
        AGENT.start_new_session()
        messages = [
          {'role': 'system', 'content': current_prompt.template},
          {'role': 'user', 'content': input[0]['content']},
        ]
        return AGENT.predict({'input': messages})

      train_data = [
        {'inputs': {'input': [{'role': 'user', 'content': q}]}}
        for q in TRAIN_QUESTIONS
      ]

      scorers = [
        Guidelines(name=name, guidelines=text)
        for name, text in SCORER_GUIDELINES.items()
      ]

      yield f'data: {json.dumps({"type": "progress", "step": "running", "message": f"Running GEPA with {len(scorers)} scorers on {len(train_data)} questions (max_metric_calls=20)...", "percent": 15})}\n\n'

      run_name = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}_gepa_lite'
      with mlflow.start_run(run_name=run_name) as run:
        result = mlflow.genai.optimize_prompts(
          predict_fn=predict_fn,
          train_data=train_data,
          prompt_uris=[current_prompt.uri],
          optimizer=GepaPromptOptimizer(
            reflection_model=reflection_model,
            max_metric_calls=20,
            display_progress_bar=False,
          ),
          scorers=scorers,
        )
        run_id = run.info.run_id

      yield f'data: {json.dumps({"type": "progress", "step": "scoring", "message": "Optimization complete, evaluating result...", "percent": 85})}\n\n'

      optimized = result.optimized_prompts[0]
      initial_score = float(getattr(result, 'initial_eval_score', 0.0) or 0.0)
      final_score = float(getattr(result, 'final_eval_score', 0.0) or 0.0)
      improved = final_score > initial_score

      registered_version = None
      if improved:
        new_version = mlflow.genai.register_prompt(
          name=prompt_full_name,
          template=optimized.template,
          commit_message=f'Live GEPA optimization (score {initial_score:.3f} -> {final_score:.3f})',
          tags={
            'optimization': 'GEPA-lite',
            'initial_score': f'{initial_score:.3f}',
            'final_score': f'{final_score:.3f}',
            'run_id': run_id,
          },
        )
        registered_version = new_version.version
        logger.info(f'Registered prompt version {registered_version} (improved)')
      else:
        logger.info(f'Score did not improve ({initial_score:.3f} -> {final_score:.3f}); skipping registration')

      payload = {
        'type': 'done',
        'run_id': run_id,
        'initial_score': initial_score,
        'final_score': final_score,
        'improved': improved,
        'registered_version': registered_version,
        'prompt_name': prompt_full_name,
        'optimized_template_preview': optimized.template[:500],
        'percent': 100,
      }
      yield f'data: {json.dumps(payload)}\n\n'

    except Exception as e:
      logger.exception(f'Optimization error: {e}')
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
