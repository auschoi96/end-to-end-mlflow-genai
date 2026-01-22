# DC Assistant: NFL Defensive Coordinator AI Agent

An MLflow-powered AI agent that helps NFL defensive coordinators prepare game plans by analyzing offensive tendencies, formations, and play distributions.

## Overview

This project demonstrates an end-to-end GenAI workflow on Databricks:

1. **Data Collection** - Load NFL play-by-play data into Unity Catalog
2. **Tool Creation** - Define SQL UDFs as agent tools
3. **Agent Development** - Build a tool-calling agent with MLflow
4. **Evaluation** - Assess agent quality with automated judges
5. **Human Feedback** - Collect SME labels via MLflow Labeling Sessions
6. **Judge Alignment** - Calibrate judges to match SME preferences
7. **Prompt Optimization** - Automatically improve the agent prompt

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DC Assistant Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ 00_setup │ → │ 01_Data  │ → │ 02_Funcs │ → │ 03_Agent │ → │ 04_Eval  │  │
│  │          │   │Collection│   │Definition│   │Definition│   │          │  │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └────┬─────┘  │
│                                                                    │        │
│                                                                    ▼        │
│                                                           ┌──────────────┐  │
│                                                           │ SME Labeling │  │
│                                                           │   Session    │  │
│                                                           └──────┬───────┘  │
│                                                                  │          │
│  ┌──────────────────────────────────────────────────────────────┐│          │
│  │                    Automated Pipeline (DAB)                   ││          │
│  │  ┌──────────────────┐        ┌─────────────────────────┐     ││          │
│  │  │ 05_JudgeAlignment│   →    │ 06_PromptOptimization   │ ◄───┘│          │
│  │  └──────────────────┘        └─────────────────────────┘      │          │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Self-Optimizing AI with Enterprise Expertise

This pipeline implements a **self-optimizing feedback loop** where enterprise-specific human expertise continuously improves AI quality:

### The Challenge

Generic LLM judges and prompts often fail to capture domain and enterprise-specific nuances.
For an agent to be effective, it needs to directly incorporate and understand enterprise expertise

### The Solution

Rather than relying on static prompts and generic evaluators, this system:

1. **Captures Human Expertise** — Subject matter experts (defensive coordinators, analysts) review agent outputs and provide structured feedback through MLflow Labeling Sessions

2. **Aligns AI Judges** — The SIMBA optimizer calibrates the LLM judge to match SME preferences, teaching it *what good looks like* for this specific domain

3. **Optimizes Automatically** — GEPA uses the aligned judge to iteratively improve the agent's system prompt, amplifying the patterns that experts prefer

4. **Compounds Over Time** — Each labeling session adds new signal. The judge becomes more aligned, the prompts become more effective, and the agent produces better analyses

| Traditional Approach | Self-Optimizing Loop |
|---------------------|---------------------|
| Static prompts | Continuously improving prompts |
| Generic evaluators | Domain-aligned judges |
| Manual prompt engineering | Automated optimization |
| Expert knowledge stays tacit | Expert knowledge encoded in system |


## Prerequisites

- Databricks workspace with Unity Catalog enabled
- MLflow 3.6+
- Service Principal with OAuth credentials (for agent authentication)
- Secret scope configured with OAuth client ID/secret

## Notebooks

### `00_setup.ipynb` - Configuration

Defines all configurable variables for the workflow:

| Category | Variables |
|----------|-----------|
| Workspace | `CATALOG`, `SCHEMA` |
| Data | `SEASONS` (e.g., [2023, 2024]) |
| MLflow | `EXPERIMENT_ID` |
| LLM | `LLM_ENDPOINT_NAME`, `JUDGE_MODEL`, `REFLECTION_MODEL` |
| Agent | `MODEL_NAME`, `UC_MODEL_NAME`, `PROMPT_NAME` |
| Evaluation | `DATASET_NAME`, `LABELING_SESSION_NAME` |
| Tools | `UC_TOOL_NAMES` (list of SQL UDFs) |
| Auth | `SECRET_SCOPE_NAME`, OAuth keys |

**Outputs:**
- `config/dc_assistant.json` - Configuration consumed by all downstream notebooks
- `{CATALOG}.{SCHEMA}.alignment_runs` - Delta table for tracking alignment job runs

---

### `01_DataCollection.ipynb` - Data Ingestion

Loads NFL play-by-play and roster data using `nflreadpy`:

| Table | Description |
|-------|-------------|
| `football_pbp_data` | Play-by-play data (300+ columns) |
| `football_participation` | Player participation per play |
| `football_rosters` | Team rosters |
| `football_teams` | Team metadata |
| `football_players` | Player metadata |

---

### `02_FunctionDefinition.ipynb` - Tool Creation

Creates Unity Catalog SQL UDFs that the agent can call:

| Function | Purpose |
|----------|---------|
| `who_got_ball_by_down_distance` | Ball carriers/targets by down & distance |
| `tendencies_by_offense_formation` | Formation/personnel usage rates |
| `tendencies_by_down_distance` | Pass/run splits by situation |
| `tendencies_two_minute_drill` | 2-minute drill tendencies |
| `screen_play_tendencies` | Screen play effectiveness |
| `success_by_pass_rush_and_coverage` | Performance vs blitz/coverage |
| ... | (12 tools total) |

---

### `03_AgentDefinition.ipynb` - Agent Development

Builds the `ResponsesAgent` using MLflow:

```python
from mlflow.models import ResponsesAgent
from unitycatalog.ai.toolkit import UCFunctionToolkit

# Load tools from Unity Catalog
toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)

# Create agent with system prompt from Prompt Registry
agent = ResponsesAgent(
    model=LLM_ENDPOINT_NAME,
    tools=toolkit.tools,
    system_prompt=mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}@production")
)
```

**Outputs:**
- `agent.py` - Agent code file
- Registered model in Unity Catalog
- Deployed serving endpoint

---

### `04-Evaluation.ipynb` - Agent Assessment

Evaluates agent quality and sets up human feedback collection:

1. **Define evaluation questions** - Sample queries for the agent
2. **Create custom judge** - `football_analysis_base` scorer with Likert scale (1-5)
3. **Run automated evaluation** - `mlflow.genai.evaluate()` with judges
4. **Tag traces** - Mark traces with `eval: complete` for downstream processing
5. **Create labeling session** - MLflow GenAI labeling session for SME review

**Outputs:**
- Evaluation traces in MLflow experiment
- `{DATASET_NAME}` - MLflow GenAI dataset with traces
- Labeling session for SME feedback

---

### `05-JudgeAlignment.ipynb` - Judge Calibration

Aligns the LLM judge with human SME preferences using SIMBA optimization:

```python
# Check for new traces since last alignment
last_alignment = spark.sql(f"SELECT MAX(alignment_timestamp) FROM {ALIGNMENT_RUNS_TABLE}")

# Filter to only new labeled traces
traces_for_alignment = [t for t in all_traces if t.timestamp > last_alignment]

# Skip if nothing new
if len(traces_for_alignment) == 0:
    dbutils.notebook.exit("SKIPPED - no new traces")

# Align judge using Likert-aware SIMBA
aligned_judge = base_judge.align(
    traces=traces_for_alignment,
    optimizer=LikertSIMBAAlignmentOptimizer(model=REFLECTION_MODEL)
)

# Register aligned judge
aligned_judge.register(name=ALIGNED_JUDGE_NAME, experiment_id=EXPERIMENT_ID)

# Log successful run
spark.sql(f"INSERT INTO {ALIGNMENT_RUNS_TABLE} VALUES ('{run_id}', now(), {count}, 'SUCCESS')")
```

**Key Features:**
- **Incremental processing** - Only processes traces created since last successful run
- **Delta table tracking** - Records run history in `alignment_runs` table
- **Early exit** - Skips execution if no new labels available

---

### `06-PromptOptimization.ipynb` - Prompt Improvement

Uses GEPA (Generative Pre-trained Agent) optimization to improve the agent's system prompt:

```python
# Load aligned judge
aligned_judge = get_scorer(name=ALIGNED_JUDGE_NAME)

# Optimize prompt using GEPA
result = mlflow.genai.optimize_prompts(
    predict_fn=predict_fn,
    train_data=optimization_dataset,
    prompt_uris=[f"prompts:/{PROMPT_NAME}@production"],
    optimizer=GepaPromptOptimizer(reflection_model=REFLECTION_MODEL),
    scorers=[aligned_judge],
)

# Register optimized prompt if improved
if result.final_eval_score > result.initial_eval_score:
    mlflow.genai.register_prompt(name=PROMPT_NAME, template=result.optimized_prompts[0].template)
    mlflow.genai.set_prompt_alias(name=PROMPT_NAME, alias="production", version=new_version)
```

**Outputs:**
- New prompt version in MLflow Prompt Registry
- Updated `@production` alias (if improved)

---

## Automation

### Databricks Asset Bundle

The `databricks.yml` and `resources/alignment_pipeline.yml` files define a Databricks job that automates the post-labeling workflow.

#### Structure

```
├── databricks.yml              # Bundle configuration
└── resources/
    └── alignment_pipeline.yml  # Job definition
```

#### Job: `dc_assistant_alignment`

| Task | Notebook | Depends On |
|------|----------|------------|
| `judge_alignment` | `05-JudgeAlignment` | - |
| `prompt_optimization` | `06-PromptOptimization` | `judge_alignment` |

**Schedule:** Daily at 8 AM Pacific (paused by default)

**Compute:** Serverless

#### Incremental Processing

The job intelligently handles incremental updates:

```
Job Runs Daily
     │
     ▼
Query alignment_runs table
for last SUCCESS timestamp
     │
     ▼
Filter traces to those
created AFTER that time
     │
     ▼
┌─────────────┐
│ New = 0?    │
└──────┬──────┘
   YES │  NO
       │
  ┌────┴────┐
  ▼         ▼
SKIP      Run alignment
(exit)    Log SUCCESS
```

#### Deployment

```bash
# Validate bundle
databricks bundle validate

# Deploy to workspace
databricks bundle deploy

# Run manually
databricks bundle run dc_assistant_alignment

# Enable scheduled runs (edit alignment_pipeline.yml)
# Change: pause_status: PAUSED → pause_status: UNPAUSED
databricks bundle deploy
```

---

## Configuration Variables

Key variables defined in `databricks.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `notebook_root` | `/Users/wesley.pasfield@databricks.com/dc-assistant-agent` | Workspace path to notebooks |

---

## Workflow Summary

### Initial Setup (Run Once)

1. **Configure** - Run `00_setup.ipynb` to set variables and create config
2. **Load Data** - Run `01_DataCollection.ipynb` to ingest NFL data
3. **Create Tools** - Run `02_FunctionDefinition.ipynb` to define SQL UDFs
4. **Build Agent** - Run `03_AgentDefinition.ipynb` to deploy the agent
5. **Evaluate** - Run `04-Evaluation.ipynb` to assess and create labeling session

### Iterative Improvement Loop

1. **SME Labels** - Subject matter experts provide feedback in the labeling session
2. **Automated Trigger** - DAB job runs (scheduled or manual)
3. **Judge Alignment** - `05-JudgeAlignment` calibrates the judge to SME preferences
4. **Prompt Optimization** - `06-PromptOptimization` improves the agent prompt
5. **Repeat** - Continue collecting feedback and running optimization

---

## Key Technologies

| Component | Technology |
|-----------|------------|
| Data Storage | Delta Lake on Unity Catalog |
| Agent Framework | MLflow ResponsesAgent |
| Tools | Unity Catalog SQL UDFs |
| Prompt Management | MLflow Prompt Registry |
| Evaluation | MLflow GenAI Evaluate |
| Judge Alignment | SIMBA Optimizer |
| Prompt Optimization | GEPA Optimizer |
| Orchestration | Databricks Asset Bundles |
| Compute | Serverless |

---

## File Structure

```
.
├── 00_setup.ipynb              # Configuration
├── 01_DataCollection.ipynb     # Data ingestion
├── 02_FunctionDefinition.ipynb # Tool creation
├── 03_AgentDefinition.ipynb    # Agent development
├── 04-Evaluation.ipynb         # Evaluation & labeling
├── 05-JudgeAlignment.ipynb     # Judge calibration
├── 06-PromptOptimization.ipynb # Prompt improvement
├── agent.py                    # Agent code
├── config/
│   └── dc_assistant.json       # Runtime configuration
├── databricks.yml              # DAB bundle config
├── resources/
│   └── alignment_pipeline.yml  # Job definition
└── README.md                   # This file
```

