"""Judge alignment + prompt optimization routes.

Wires the /kpis "Optimize Judge" and /monitoring "Optimize Prompt" buttons to
real MLflow workflows (MemAlign + GEPA). Streams progress over SSE.
"""

import json
import logging
import os
import random
from datetime import datetime

import mlflow
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from mlflow_demo.utils.mlflow_helpers import get_mlflow_experiment_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/optimization', tags=['optimization'])


JUDGE_MODEL = os.environ.get('JUDGE_MODEL', 'databricks:/databricks-claude-sonnet-4-6')
EMBEDDING_MODEL = os.environ.get(
  'JUDGE_EMBEDDING_MODEL', 'databricks:/databricks-qwen3-embedding-0-6b'
)

BASE_JUDGE_NAME = 'football_analysis_base'
ALIGNED_JUDGE_NAME = 'football_analysis_judge_align_memalign_v2'

# GEPA optimizes an NFL defensive-coordinator prompt. The legacy email prompt
# (env PROMPT_NAME=email_generation) is intentionally not used here.
NFL_PROMPT_SHORT_NAME = os.environ.get('NFL_PROMPT_NAME', 'football_analysis_prompt')

NFL_INITIAL_PROMPT_TEMPLATE = (
  "You are an expert NFL defensive coordinator assistant. When a user asks about an "
  "offense's tendencies, formations, personnel, or situational play (down & distance, "
  "red zone, two-minute drill, etc.), you will analyze the data available to you and "
  "respond with:\n"
  "1. A concise summary of the offense's patterns in the specific situation asked about.\n"
  "2. Concrete, actionable defensive adjustments or counters the coaching staff can call.\n"
  "3. Strategic recommendations tied to the data, with clear reasoning.\n\n"
  "Be precise with team names, seasons, and statistics. Do not invent numbers. "
  "Avoid generic football truisms — every recommendation must be grounded in either the "
  "retrieved data or the specific situational context the user asked about. If the user "
  "asks for a typical play sequence, provide an ordered step-by-step sequence with "
  "situational context (down/distance/clock). Otherwise provide schematic explanations "
  "of formations, route concepts, and coverage matchups."
)

BASE_JUDGE_INSTRUCTIONS = (
  'Evaluate if the response in {{ outputs }} appropriately analyzes the available data '
  'and provides an actionable recommendation to the question in {{ inputs }}. '
  'The response should be accurate, contextually relevant, and give a strategic advantage '
  'to the person making the request. '
  'Your grading criteria should be: '
  ' 1: Completely unacceptable. Incorrect data interpretation or no recommendations. '
  ' 2: Mostly unacceptable. Irrelevant or spurious feedback or weak recommendations with minimal advantage. '
  ' 3: Somewhat acceptable. Relevant feedback with some strategic advantage. '
  ' 4: Mostly acceptable. Relevant feedback with strong strategic advantage. '
  ' 5: Completely acceptable. Relevant feedback with excellent strategic advantage.'
)

# Trace-label targets for synthetic HUMAN labels that create learnable
# disagreement with the baseline judge. Questions asking for a "sequence" should
# receive a low human score — that's the pattern MemAlign will learn.
SEQUENCE_KEYWORDS = ('sequence', 'play-by-play', 'script', 'under two minutes', 'with under')


def _sse(payload: dict) -> str:
  return f'data: {json.dumps(payload)}\n\n'


def _is_sequence_question(text: str) -> bool:
  t = (text or '').lower()
  return any(k in t for k in SEQUENCE_KEYWORDS)


def _build_base_judge():
  """Build football_analysis_base as an in-memory judge pinned to a Databricks
  model. We do NOT register it — registration hits a workspace monitoring job
  (718526545475311) that this app's service principal can't modify, and MemAlign
  doesn't require the input judge to be persisted server-side.

  `model=` is pinned to JUDGE_MODEL (Databricks) explicitly; otherwise make_judge
  silently defaults to openai:/gpt-4.1-mini which would need OPENAI_API_KEY.
  """
  from mlflow.genai.judges import make_judge
  return make_judge(
    name=BASE_JUDGE_NAME,
    instructions=BASE_JUDGE_INSTRUCTIONS,
    model=JUDGE_MODEL,
    feedback_value_type=int,
  )


def _collect_labeled_traces(experiment_id: str, target_count: int = 20):
  """Pick ~target_count traces and ensure each has both a judge score and a
  synthetic HUMAN label for BASE_JUDGE_NAME. Returns the loaded Trace objects.
  """
  from mlflow.entities.assessment import AssessmentSource, AssessmentSourceType

  # Pull recent traces from the experiment
  traces = mlflow.search_traces(
    locations=[experiment_id],
    return_type='list',
    max_results=target_count * 3,
  )
  if not traces:
    raise RuntimeError(f'No traces found in experiment {experiment_id}')

  usable = []
  for t in traces:
    req = t.data.request if hasattr(t.data, 'request') else None
    resp = t.data.response if hasattr(t.data, 'response') else None
    if req and resp:
      usable.append(t)
    if len(usable) >= target_count:
      break

  if not usable:
    raise RuntimeError('No traces with both request and response found')

  # Label each trace: LLM_JUDGE score + synthetic HUMAN score
  labeled_trace_ids = []
  rng = random.Random(42)
  for t in usable:
    tid = t.info.trace_id
    # Parse the user question out of the request for keyword detection
    try:
      req = t.data.request
      if isinstance(req, str):
        req_obj = json.loads(req)
      else:
        req_obj = req
      # request shape can be {"input":[{"role":"user","content":"..."}]} or {"messages":[...]}
      msgs = req_obj.get('input') or req_obj.get('messages') or []
      user_text = next(
        (m.get('content', '') for m in reversed(msgs) if m.get('role') == 'user'), ''
      )
    except Exception:
      user_text = ''

    # Judge score: assign a plausible 4 or 5 (the "sounds-good" failure mode)
    judge_score = rng.choice([4, 5])
    # Human score: sequence questions get 2 (disagreement); others align ±1 with judge
    if _is_sequence_question(user_text):
      human_score = 2
    else:
      human_score = max(1, min(5, judge_score + rng.choice([-1, 0, 0])))

    # Log both assessments under BASE_JUDGE_NAME
    try:
      mlflow.log_feedback(
        trace_id=tid,
        name=BASE_JUDGE_NAME,
        value=judge_score,
        source=AssessmentSource(
          source_type=AssessmentSourceType.LLM_JUDGE,
          source_id=JUDGE_MODEL,
        ),
        rationale='Synthetic judge score for alignment demo.',
      )
      mlflow.log_feedback(
        trace_id=tid,
        name=BASE_JUDGE_NAME,
        value=human_score,
        source=AssessmentSource(
          source_type=AssessmentSourceType.HUMAN,
          source_id='demo_sme',
        ),
        rationale='Synthetic expert label for alignment demo.',
      )
      mlflow.set_trace_tag(trace_id=tid, key='eval', value='complete')
      labeled_trace_ids.append(tid)
    except Exception as e:
      logger.warning(f'Failed to label trace {tid}: {e}')

  # Reload traces so the alignment call sees assessments attached
  reloaded = []
  for tid in labeled_trace_ids:
    try:
      reloaded.append(mlflow.get_trace(tid))
    except Exception as e:
      logger.warning(f'Could not reload trace {tid}: {e}')
  return reloaded


@router.post('/align-judge')
async def align_judge():
  """Run MemAlign on football_analysis_base. SSE-streamed."""

  async def generate():
    try:
      exp_id = get_mlflow_experiment_id()
      mlflow.set_experiment(experiment_id=exp_id)

      yield _sse({'type': 'progress', 'step': 'setup', 'percent': 5,
                  'message': f'Preparing baseline judge for experiment {exp_id}...'})
      base_judge = _build_base_judge()

      yield _sse({'type': 'progress', 'step': 'labeling', 'percent': 15,
                  'message': 'Generating judge scores and synthetic expert labels...'})
      labeled = _collect_labeled_traces(exp_id, target_count=20)
      if len(labeled) < 4:
        yield _sse({'type': 'error', 'error': f'Only {len(labeled)} labeled traces — need >=4 for MemAlign'})
        return

      yield _sse({'type': 'progress', 'step': 'aligning', 'percent': 40,
                  'message': f'Running MemAlign on {len(labeled)} traces (this takes a few minutes)...'})

      from mlflow.genai.judges.optimizers import MemAlignOptimizer
      optimizer = MemAlignOptimizer(
        reflection_lm=JUDGE_MODEL,
        embedding_model=EMBEDDING_MODEL,
      )
      aligned = base_judge.align(traces=labeled, optimizer=optimizer)

      yield _sse({'type': 'progress', 'step': 'registering', 'percent': 85,
                  'message': f'Registering {ALIGNED_JUDGE_NAME}...'})

      from mlflow.genai.judges import make_judge
      from mlflow.genai.scorers import ScorerSamplingConfig

      aligned_judge = make_judge(
        name=ALIGNED_JUDGE_NAME,
        instructions=aligned.instructions,
        model=JUDGE_MODEL,
        feedback_value_type=int,
      )
      register_warning = None
      try:
        aligned_judge.register(experiment_id=exp_id)
      except ValueError as e:
        if 'has already been registered' in str(e):
          try:
            aligned_judge.update(
              experiment_id=exp_id,
              sampling_config=ScorerSamplingConfig(sample_rate=1),
            )
          except Exception as e2:
            register_warning = f'Update failed: {e2}'
        else:
          register_warning = f'Register failed: {e}'
      except Exception as e:
        register_warning = f'Register failed ({type(e).__name__}): {str(e)[:400]}'

      yield _sse({
        'type': 'done',
        'percent': 100,
        'aligned_judge_name': ALIGNED_JUDGE_NAME,
        'labeled_trace_count': len(labeled),
        'original_instructions': base_judge.instructions if hasattr(base_judge, 'instructions') else BASE_JUDGE_INSTRUCTIONS,
        'aligned_instructions': aligned.instructions,
        'experiment_id': exp_id,
        'register_warning': register_warning,
      })
    except Exception as e:
      logger.exception('align-judge failed')
      yield _sse({'type': 'error', 'error': f'{type(e).__name__}: {e}'})

  return StreamingResponse(
    generate(),
    media_type='text/event-stream',
    headers={
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  )


@router.post('/optimize-prompt')
async def optimize_prompt():
  """Run GEPA prompt optimization against the aligned judge. SSE-streamed."""

  async def generate():
    try:
      exp_id = get_mlflow_experiment_id()
      mlflow.set_experiment(experiment_id=exp_id)

      uc_catalog = os.environ.get('UC_CATALOG', '')
      uc_schema = os.environ.get('UC_SCHEMA', '')
      if not (uc_catalog and uc_schema):
        yield _sse({'type': 'error', 'error': 'UC_CATALOG and UC_SCHEMA env vars required'})
        return

      fq_prompt_name = f'{uc_catalog}.{uc_schema}.{NFL_PROMPT_SHORT_NAME}'

      yield _sse({'type': 'progress', 'step': 'load-prompt', 'percent': 5,
                  'message': f'Ensuring NFL baseline prompt {fq_prompt_name} exists...'})
      # Load the baseline NFL prompt; if missing, register an initial version.
      baseline_prompt = mlflow.genai.load_prompt(
        f'prompts:/{fq_prompt_name}', allow_missing=True
      )
      if baseline_prompt is None:
        logger.info(f'Registering initial NFL baseline prompt at {fq_prompt_name}')
        baseline_prompt = mlflow.genai.register_prompt(
          name=fq_prompt_name,
          template=NFL_INITIAL_PROMPT_TEMPLATE,
          commit_message='Initial NFL defensive-coordinator baseline prompt',
          tags={'purpose': 'football_analysis_baseline'},
        )

      yield _sse({'type': 'progress', 'step': 'load-judge', 'percent': 10,
                  'message': 'Loading aligned judge...'})

      from mlflow.genai.scorers import get_scorer
      try:
        judge = get_scorer(name=ALIGNED_JUDGE_NAME, experiment_id=exp_id)
      except Exception:
        logger.warning(f'{ALIGNED_JUDGE_NAME} not found, falling back to {BASE_JUDGE_NAME}')
        try:
          judge = get_scorer(name=BASE_JUDGE_NAME, experiment_id=exp_id)
        except Exception:
          yield _sse({'type': 'error',
                      'error': 'Neither aligned nor baseline judge exists. Run Align Judge first.'})
          return

      yield _sse({'type': 'progress', 'step': 'dataset', 'percent': 20,
                  'message': 'Building optimization dataset from labeled traces...'})

      traces = mlflow.search_traces(
        locations=[exp_id],
        filter_string="tag.eval = 'complete'",
        return_type='list',
        max_results=20,
      )
      if not traces:
        yield _sse({'type': 'error',
                    'error': 'No labeled traces found. Run Align Judge first to create them.'})
        return

      def _extract_question(raw) -> str:
        if raw is None:
          return ''
        if isinstance(raw, str):
          s = raw.strip()
          if s.startswith('{') or s.startswith('['):
            try:
              raw = json.loads(s)
            except Exception:
              return s
          else:
            return s
        if isinstance(raw, dict):
          msgs = raw.get('input') or raw.get('messages') or []
          for m in reversed(msgs):
            if m.get('role') == 'user':
              return m.get('content', '') or ''
          return raw.get('question') or raw.get('content') or ''
        return ''

      train_data = []
      for t in traces:
        try:
          q = _extract_question(t.data.request)
          if q:
            train_data.append({'inputs': {'question': q}})
        except Exception as e:
          logger.warning(f'extract fail: {e}')
          continue
      if len(train_data) < 3:
        yield _sse({'type': 'error', 'error': f'Only {len(train_data)} usable train rows'})
        return

      yield _sse({'type': 'progress', 'step': 'optimizing', 'percent': 35,
                  'message': f'Running GEPA with {len(train_data)} examples (several minutes)...'})

      from mlflow.genai.optimize import GepaPromptOptimizer
      from mlflow_demo.agent import AGENT

      # GEPA mutates the prompt at `baseline_prompt.uri` across candidates.
      # The predict_fn reloads the current candidate per call and injects it as
      # the system message to the agent — matching the notebook pattern in
      # 06-PromptOptimization.py.
      prompt_uri = baseline_prompt.uri

      def predict_fn(question: str):
        current_prompt = mlflow.genai.load_prompt(prompt_uri)
        system_content = current_prompt.format()
        AGENT.start_new_session()
        resp = AGENT.predict({
          'input': [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': question},
          ]
        })
        return {'response': str(resp)}

      optimizer = GepaPromptOptimizer(
        reflection_model=JUDGE_MODEL,
        max_metric_calls=30,
      )

      result = mlflow.genai.optimize_prompts(
        predict_fn=predict_fn,
        train_data=train_data,
        prompt_uris=[prompt_uri],
        optimizer=optimizer,
        scorers=[judge],
      )

      yield _sse({'type': 'progress', 'step': 'saving', 'percent': 90,
                  'message': 'Saving optimized prompt version to registry...'})

      # Extract the best prompt template from the result. The MLflow 3.11 API
      # returns `optimized_prompts` (a list of PromptVersion) — fall back to
      # common older attribute names just in case.
      optimized_template = None
      for attr_chain in (
        ('optimized_prompts', 0, 'template'),
        ('best_prompt', 'template'),
        ('optimized_prompt', 'template'),
      ):
        obj = result
        ok = True
        for step in attr_chain:
          if isinstance(step, int):
            try: obj = obj[step]
            except Exception: ok = False; break
          else:
            obj = getattr(obj, step, None)
            if obj is None: ok = False; break
        if ok and isinstance(obj, str):
          optimized_template = obj
          break

      if optimized_template is None:
        yield _sse({'type': 'error',
                    'error': 'optimize_prompts returned no recognizable template'})
        return

      initial_score = getattr(result, 'initial_eval_score', None) or getattr(result, 'baseline_score', None)
      final_score = getattr(result, 'final_eval_score', None) or getattr(result, 'best_score', None)

      new_version = mlflow.genai.register_prompt(
        name=fq_prompt_name,
        template=optimized_template,
        commit_message=f'GEPA-optimized against {judge.name if hasattr(judge, "name") else ALIGNED_JUDGE_NAME}',
        tags={
          'optimization_method': 'gepa',
          'initial_score': str(initial_score) if initial_score is not None else '',
          'final_score': str(final_score) if final_score is not None else '',
          'judge': judge.name if hasattr(judge, 'name') else ALIGNED_JUDGE_NAME,
        },
      )

      yield _sse({
        'type': 'done',
        'percent': 100,
        'prompt_name': fq_prompt_name,
        'new_version': getattr(new_version, 'version', str(new_version)),
        'baseline_score': initial_score,
        'best_score': final_score,
        'experiment_id': exp_id,
      })
    except Exception as e:
      logger.exception('optimize-prompt failed')
      yield _sse({'type': 'error', 'error': f'{type(e).__name__}: {e}'})

  return StreamingResponse(
    generate(),
    media_type='text/event-stream',
    headers={
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  )
