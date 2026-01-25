# DC Assistant Demo - Configuration Guide

**Purpose**: This document explains everything that was changed from the email demo to the DC Assistant demo, and how to configure the app for your MLflow experiment.

---

## Table of Contents
1. [What Was Changed](#what-was-changed)
2. [Configuration Points](#configuration-points)
3. [How to Update for Your Experiment](#how-to-update-for-your-experiment)
4. [File Reference Map](#file-reference-map)

---

## What Was Changed

### Frontend UI (Complete ✅)
All 6 demo sections were rebuilt with DC Assistant content:

| Old Section | New Section | Status |
|-------------|-------------|---------|
| Sales Email Generator | DC Assistant Chat Interface | ✅ Complete |
| Step 1: Observe with Tracing | Step 1: Observe with Tracing | ✅ Complete |
| Step 2: Create Quality Metrics | Step 2: Create LLM Judges | ✅ Complete |
| Step 3: Find & Fix Issues | Step 3: Collect Ground Truth Labels | ✅ Complete |
| Step 4: Link to Business KPIs | Step 4: Align Judges to Experts | ✅ Complete |
| Step 5: Production Monitoring | Step 5: Optimize Prompts (GEPA) | ✅ Complete |
| Step 6: Human Review | Step 6: Production Monitoring & Continuous Loop | ✅ Complete |

### Backend (Partial ⚠️)
- ✅ FastAPI structure ready (`server/app.py`)
- ✅ Health check endpoint working
- ✅ Static file serving configured
- ⚠️ **MISSING**: DC Assistant API endpoints (see TODO_REMAINING_WORK.md)

### Build & Deployment
- ✅ Frontend built for production (`client/build/`)
- ✅ `app.yaml` configured for Databricks App
- ✅ All dependencies in `requirements.txt`

---

## Configuration Points

### 1. MLflow Experiment Configuration

**Where to configure**: Multiple locations need updating

#### A. Environment Variables (Primary Configuration)

**File**: `app.yaml` (for Databricks App deployment)

```yaml
env:
  - name: 'MLFLOW_EXPERIMENT_ID'
    value: '/Users/your.email@company.com/dc-assistant-demo'  # ← CHANGE THIS

  - name: 'UC_CATALOG'
    value: 'your_catalog'  # ← CHANGE THIS

  - name: 'UC_SCHEMA'
    value: 'your_schema'  # ← CHANGE THIS

  - name: 'MODEL_ENDPOINT_NAME'
    value: 'dc-assistant-endpoint'  # ← CHANGE THIS if different

  - name: 'DATABRICKS_HOST'
    value: '${DATABRICKS_HOST}'  # Auto-populated by Databricks App

  - name: 'DATABRICKS_TOKEN'
    value: '${DATABRICKS_TOKEN}'  # Auto-populated by Databricks App
```

**File**: `.env.local` (for local development)

Create this file in the project root:

```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=databricks
MLFLOW_EXPERIMENT_ID=/Users/your.email@company.com/dc-assistant-demo

# Unity Catalog
UC_CATALOG=your_catalog
UC_SCHEMA=your_schema

# Model Serving
MODEL_ENDPOINT_NAME=dc-assistant-endpoint

# Databricks Connection (for local dev)
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi1234567890abcdef  # Your personal access token

# Optional: For trace URLs
DATABRICKS_WORKSPACE_ID=1444828305810485
SQL_WAREHOUSE_ID=4b9b953939869799

# Sample trace/session IDs (for demo purposes)
SAMPLE_TRACE_ID=tr-your-trace-id-here
SAMPLE_LABELING_SESSION_ID=your-session-id
```

#### B. Backend Code References

**File**: `server/app.py` (lines 115-127)

The experiment endpoint uses `get_mlflow_experiment_id()`:

```python
@app.get(f'{API_PREFIX}/tracing_experiment')
async def experiment():
  """Get the MLFlow experiment info."""
  databricks_host = ensure_https_protocol(os.getenv('DATABRICKS_HOST'))

  return ExperimentInfo(
    experiment_id=get_mlflow_experiment_id(),  # ← Reads from MLFLOW_EXPERIMENT_ID env var
    link=f'{databricks_host}/ml/experiments/{get_mlflow_experiment_id()}?compareRunsMode=TRACES',
    # ... more URLs constructed using experiment_id
  )
```

**No code changes needed** - it automatically reads from environment variables.

#### C. Frontend References (Display Only)

**File**: `client/src/components/demo-pages/observe-with-tracing.tsx` (line ~45)

Displays experiment ID in code example:

```typescript
const tracingSetupCode = `import mlflow

mlflow.set_tracking_uri("databricks")
+ mlflow.set_experiment(experiment_id=MLFLOW_EXPERIMENT_ID)  # ← Just for display
```

**No configuration needed** - this is just example code shown to users.

**File**: `client/src/components/demo-pages/business-metrics.tsx` (lines ~180, ~195)

Shows experiment ID in code snippets:

```typescript
experiment_ids=[EXPERIMENT_ID],  // ← Display only
aligned_judge_registered.register(experiment_id=EXPERIMENT_ID)  // ← Display only
```

**No configuration needed** - these are mock code examples for demonstration.

---

### 2. Model Serving Endpoint Configuration

**Where**: Same environment variable files as above

```yaml
# In app.yaml or .env.local
MODEL_ENDPOINT_NAME=dc-assistant-endpoint  # ← Change to your endpoint name
```

**Used by**:
- Backend will use this to call your deployed model
- Frontend displays this in code examples

---

### 3. Unity Catalog Configuration

**Where**: Environment variables (app.yaml and .env.local)

```yaml
UC_CATALOG=main          # ← Your catalog name
UC_SCHEMA=dc_assistant   # ← Your schema name
```

**What it affects**:
- Where LLM judges are stored: `{catalog}.{schema}.judge_name`
- Where prompts are registered: `{catalog}.{schema}.prompt_name`
- Where inference logs are stored: `{catalog}.{schema}.dc_assistant_inference_logs`

**Used in**:
- `mlflow_demo/utils/mlflow_helpers.py` - Constructs full resource paths
- Backend endpoints (when implemented) - Reads/writes to UC tables

---

### 4. Sample Trace/Session IDs (Optional)

**Where**: Environment variables

```bash
# In .env.local or app.yaml
SAMPLE_TRACE_ID=tr-2a91cd9964876c016296dff8ec9f3e1e
SAMPLE_LABELING_SESSION_ID=ls-abc123
```

**Purpose**:
- Powers the "View Sample Trace" button
- Links to specific examples in MLflow UI
- **Optional**: App works without these, buttons just won't have examples

**How to find your trace ID**:
1. Go to your MLflow experiment in Databricks
2. Click "Traces" tab
3. Select a trace
4. Look at URL: `...traces?selectedEvaluationId=tr-XXXXX`
5. Copy the `tr-XXXXX` value

---

## How to Update for Your Experiment

### Quick Start (5 minutes)

**Step 1**: Update `app.yaml` in project root

```yaml
env:
  - name: 'MLFLOW_EXPERIMENT_ID'
    value: '/Users/colleague.name@databricks.com/dc-assistant'
  - name: 'UC_CATALOG'
    value: 'main'
  - name: 'UC_SCHEMA'
    value: 'dc_demo'
  - name: 'MODEL_ENDPOINT_NAME'
    value: 'dc-assistant-endpoint'
```

**Step 2**: Create `.env.local` for local testing (copy from above template)

**Step 3**: Test locally

```bash
# Terminal 1 - Backend
source .venv/bin/activate
uvicorn server.app:app --reload --port 8000

# Terminal 2 - Frontend
cd client
npm run dev
```

**Step 4**: Verify

- Open http://localhost:3000
- Check that "View Experiment in MLflow UI" opens YOUR experiment
- Check browser console for errors

**Step 5**: Deploy to Databricks App

- Commit and push to your git branch
- Create Databricks App from git source
- App will use `app.yaml` configuration

---

## File Reference Map

### Files You MUST Update

| File | What to Change | Required? |
|------|----------------|-----------|
| `app.yaml` | MLFLOW_EXPERIMENT_ID, UC_CATALOG, UC_SCHEMA, MODEL_ENDPOINT_NAME | ✅ Yes |
| `.env.local` | Same as app.yaml + DATABRICKS_HOST, DATABRICKS_TOKEN | ✅ Yes (local dev) |

### Files That Auto-Read Configuration

| File | What It Does | Need to Edit? |
|------|--------------|---------------|
| `server/app.py` | Reads env vars, constructs MLflow UI URLs | ❌ No |
| `mlflow_demo/utils/mlflow_helpers.py` | Helper functions using env vars | ❌ No |
| `server/routes/email.py` | Email demo routes (not used for DC Assistant) | ❌ No |

### Files with Hardcoded Display Values (OK to leave as-is)

| File | Hardcoded Values | Impact |
|------|------------------|--------|
| `client/src/components/demo-pages/*.tsx` | Example experiment IDs in code snippets | None - just for display |
| `client/src/components/dc-assistant/DcTracingDemo.tsx` | Fallback experiment ID: '2517718719552044' | None - overridden by backend |

---

## Common Configuration Scenarios

### Scenario 1: Colleague Wants to Use Their Own Experiment

**What they need**:
1. MLflow experiment ID (or path)
2. Unity Catalog catalog.schema with appropriate permissions
3. Deployed model serving endpoint

**Steps**:
1. Edit `app.yaml` with their values
2. Push to git
3. Deploy Databricks App

**Time**: 5 minutes

---

### Scenario 2: Switching Between Experiments (Local Dev)

**Steps**:
1. Update `.env.local`:
   ```bash
   MLFLOW_EXPERIMENT_ID=/Users/me@company.com/experiment-2
   ```
2. Restart backend server (Ctrl+C, then re-run)
3. Refresh frontend

**Time**: 1 minute

---

### Scenario 3: Different Databricks Workspace

**Steps**:
1. Update `DATABRICKS_HOST` in both files:
   ```yaml
   DATABRICKS_HOST=https://different-workspace.cloud.databricks.com
   ```
2. Verify UC_CATALOG and UC_SCHEMA exist in new workspace
3. Deploy

**Time**: 5 minutes

---

## Troubleshooting Configuration Issues

### Problem: "View Experiment" button opens wrong experiment

**Check**:
1. `app.yaml`: MLFLOW_EXPERIMENT_ID value
2. Backend logs: Look for experiment ID being used
3. Browser network tab: Check `/api/tracing_experiment` response

**Fix**: Update `app.yaml` and redeploy

---

### Problem: Trace URLs are broken (404 or wrong workspace)

**Check**:
1. `DATABRICKS_HOST` is correct (should include https://)
2. `DATABRICKS_WORKSPACE_ID` matches your workspace
3. Backend endpoint response has correct URL

**Fix**: Update environment variables

---

### Problem: Local dev can't connect to MLflow

**Check**:
1. `.env.local` has DATABRICKS_HOST and DATABRICKS_TOKEN
2. Token is valid (not expired)
3. `MLFLOW_TRACKING_URI=databricks` is set

**Fix**:
```bash
# Test authentication
databricks auth login --host https://your-workspace.cloud.databricks.com

# Regenerate token if needed
```

---

## Summary: What to Change for New Deployment

**Minimum required changes**:
1. ✅ `app.yaml` - 4 environment variables
2. ✅ `.env.local` - Same 4 variables + authentication

**Everything else automatically adapts** based on these environment variables.

**Colleague handoff**: Just point them to this section and the two files to update.
