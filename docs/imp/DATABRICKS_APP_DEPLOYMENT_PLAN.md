# Databricks App Deployment Plan - DC Assistant Demo

## Quick Deployment Summary

**Actual deployment time: ~5 minutes**

The deployment itself is straightforward:
1. Git push (1 min)
2. Create Databricks App from git source (2-3 min)
3. App spins up automatically

**Backend development work needed before deployment: 4-6 hours** (implementing missing API endpoints - see section 8)

---

## 1. Prerequisites

Before starting, ensure you have:

**MLflow Resources**:
- MLflow experiment ID for DC Assistant demo
- Deployed model serving endpoint (e.g., `dc-assistant-endpoint`)
- Unity Catalog location for storing:
  - Prompt templates
  - LLM judges
  - Labeling schemas
  - Inference logs table for monitoring

**Access Requirements**:
- Databricks workspace with Apps capability
- Unity Catalog CREATE permissions (catalog.schema)
- MLflow experiment read/write permissions
- Model serving endpoint permissions
- Git repository access for deployment

**Local Development Setup**:
- Node.js 18+ and npm
- Python 3.10+
- Databricks CLI configured

---

## 2. Backend Adaptation Required

### 2.1 New Route File: `server/routes/dc_assistant.py`

This will replace the email demo's `server/routes/email.py` functionality. Create endpoints for:

**Required Endpoints**:

```
GET /api/dc-assistant/experiment-info
- Returns experiment ID, name, tracking URI
- Similar to existing /api/experiment endpoint

GET /api/dc-assistant/traces
- Returns sample traces from DC Assistant runs
- Used by "Create LLM Judges" section to show traces

GET /api/dc-assistant/judges
- Returns created judge configurations
- Used by "Create LLM Judges" results display

GET /api/dc-assistant/labeling-sessions
- Returns labeling session details
- Used by "Collect Ground Truth Labels" section

GET /api/dc-assistant/alignment-results
- Returns SIMBA/MemAlign optimization results
- Used by "Align Judges to Experts" demo

GET /api/dc-assistant/gepa-results
- Returns GEPA prompt optimization results
- Used by "Optimize Prompts" section

GET /api/dc-assistant/monitoring-metrics
- Returns production monitoring metrics
- Used by "Production Monitoring" dashboard

GET /api/dc-assistant/notebook-links
- Returns Databricks notebook URLs for each section
- Generates links like: https://<workspace-url>/notebooks/<notebook-id>
```

### 2.2 Update `server/app.py`

**Changes needed**:
1. Import new DC Assistant routes instead of email routes
2. Update CORS origins if needed
3. Add validation for DC-specific environment variables on startup

**Code pattern** (reference existing email.py integration):
```python
# In server/app.py
from server.routes.dc_assistant import router as dc_router

app.include_router(dc_router, prefix="/api")
```

### 2.3 Data Structures for Preloaded Results

Since the demo shows "preloaded" results, you'll need JSON files or Python dictionaries containing:

**`server/data/dc_assistant_preloaded.py`** (or JSON files):
- Sample traces (5-10 DC Assistant Q&A pairs)
- Judge evaluation results
- Labeling session mock data
- Alignment optimization diff results
- GEPA prompt optimization comparisons
- Monitoring metrics snapshot

This follows the pattern from the email demo where results are precomputed for demo purposes.

---

## 3. Environment Configuration

### 3.1 Update `app.yaml`

**Current variables to adapt**:
```yaml
env:
  - name: MLFLOW_TRACKING_URI
    value: "databricks"

  - name: MLFLOW_EXPERIMENT_ID
    value: "<DC_ASSISTANT_EXPERIMENT_ID>"

  - name: UC_CATALOG
    value: "<your_catalog>"

  - name: UC_SCHEMA
    value: "<your_schema>"

  - name: MODEL_ENDPOINT_NAME
    value: "dc-assistant-endpoint"

  - name: INFERENCE_TABLE
    value: "<catalog>.<schema>.dc_assistant_inference_logs"

  - name: DATABRICKS_HOST
    value: "${DATABRICKS_HOST}"

  - name: DATABRICKS_TOKEN
    value: "${DATABRICKS_TOKEN}"
```

**New variables to add**:
```yaml
  - name: JUDGES_TABLE
    value: "<catalog>.<schema>.dc_assistant_judges"

  - name: LABELING_SESSION_TABLE
    value: "<catalog>.<schema>.dc_assistant_labels"

  - name: WORKSPACE_URL
    value: "<your-workspace>.cloud.databricks.com"
```

### 3.2 Local Development `.env.local`

Create `.env.local` in project root for local testing:
```bash
MLFLOW_TRACKING_URI=databricks
MLFLOW_EXPERIMENT_ID=/Users/<your-email>/dc-assistant-demo
UC_CATALOG=your_catalog
UC_SCHEMA=your_schema
MODEL_ENDPOINT_NAME=dc-assistant-endpoint
INFERENCE_TABLE=your_catalog.your_schema.dc_assistant_inference_logs
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<your-pat>
WORKSPACE_URL=<workspace>.cloud.databricks.com
```

---

## 4. Validation Strategy

### 4.1 Pre-Deployment Validation Script

Create `server/validate_setup.py`:

**Purpose**: Verify all MLflow resources and environment variables before deployment

**Validation checks**:
1. ✅ MLflow experiment exists and is accessible
2. ✅ Model serving endpoint is deployed and serving
3. ✅ Unity Catalog tables exist (or can be created)
4. ✅ Databricks authentication works (host + token)
5. ✅ Required environment variables are set
6. ✅ Workspace URL is valid and accessible

**Script outline**:
```python
import os
import mlflow
from databricks.sdk import WorkspaceClient

def validate_environment():
    """Validate all required environment variables are set"""
    required_vars = [
        'MLFLOW_EXPERIMENT_ID',
        'UC_CATALOG',
        'UC_SCHEMA',
        'MODEL_ENDPOINT_NAME',
        'DATABRICKS_HOST',
        'DATABRICKS_TOKEN'
    ]
    # Check each var...

def validate_mlflow_access():
    """Validate MLflow experiment and tracking URI"""
    # Test mlflow.set_experiment()
    # Verify experiment ID exists

def validate_model_endpoint():
    """Validate model serving endpoint is accessible"""
    # Use WorkspaceClient to check endpoint status

def validate_uc_resources():
    """Validate Unity Catalog resources"""
    # Check catalog.schema exists
    # Verify table permissions

if __name__ == "__main__":
    print("🔍 Validating Databricks App Setup...")
    validate_environment()
    validate_mlflow_access()
    validate_model_endpoint()
    validate_uc_resources()
    print("✅ All validations passed!")
```

**Run before deployment**:
```bash
python server/validate_setup.py
```

### 4.2 API Health Checks

Create `server/routes/health.py` (or add to existing):

```
GET /api/health
- Returns 200 OK with system status

GET /api/health/mlflow
- Validates MLflow connectivity
- Returns experiment info

GET /api/health/endpoint
- Checks model endpoint is serving
- Returns endpoint status

GET /api/health/resources
- Validates all UC tables exist
- Returns resource availability
```

---

## 5. Testing Checklist

### 5.1 Local Development Testing

**Frontend + Backend Integration**:
```bash
# Terminal 1 - Backend
cd /Users/nethra.ranganathan/projects/mlflow-app/mlflow-demo
source .venv/bin/activate
uvicorn server.app:app --reload --port 8000

# Terminal 2 - Frontend
cd client
npm run dev
```

**Test each section**:
- [ ] Navigate to `http://localhost:3000`
- [ ] Create LLM Judges section loads
- [ ] Click "View Experiment in MLflow UI" opens correct URL
- [ ] Collect Ground Truth Labels section displays
- [ ] Align Judges section loads, click "Run Optimization" works
- [ ] Optimize Prompts section loads, click "Run GEPA" works
- [ ] Production Monitoring section displays metrics
- [ ] All API calls return 200 status codes

### 5.2 API Endpoint Verification

Test each endpoint using curl or browser:
```bash
# Test experiment info
curl http://localhost:8000/api/dc-assistant/experiment-info

# Test health check
curl http://localhost:8000/api/health

# Test traces endpoint
curl http://localhost:8000/api/dc-assistant/traces
```

**Expected responses**:
- Valid JSON with correct data structure
- No 404 or 500 errors
- Consistent with frontend component expectations

### 5.3 Frontend Build Validation

**Production build test**:
```bash
cd client
npm run build
```

**Verify**:
- [ ] Build completes without errors
- [ ] `client/dist/` directory created
- [ ] Assets properly fingerprinted
- [ ] index.html references correct asset paths

**Test production build locally**:
```bash
# Serve production build
cd client/dist
python -m http.server 3000

# Backend still running on 8000
# Navigate to http://localhost:3000
```

### 5.4 Static Asset Serving

Verify FastAPI serves frontend correctly:

**In production mode** (`server/app.py` already configured):
```python
# Should mount static files from client/dist
app.mount("/", StaticFiles(directory="client/dist", html=True), name="static")
```

**Test**:
- [ ] Root path `/` serves index.html
- [ ] JavaScript bundles load from `/assets/`
- [ ] CSS files load correctly
- [ ] Routing works (React Router paths)

---

## 6. Deployment Preparation

### 6.1 Git Repository Structure

**Required files** for Databricks App deployment:
```
mlflow-demo/
├── app.yaml                 # Databricks App config
├── server/
│   ├── app.py              # FastAPI entry point
│   ├── routes/
│   │   ├── dc_assistant.py # DC Assistant endpoints
│   │   └── health.py       # Health checks
│   ├── data/
│   │   └── dc_assistant_preloaded.py  # Preloaded demo data
│   └── validate_setup.py   # Validation script
├── client/dist/            # Built frontend (run npm build)
├── requirements.txt        # Python dependencies
└── README.md              # Setup instructions
```

**Important**: Commit the built frontend (`client/dist/`) to git for app deployment, or ensure build happens during deployment.

### 6.2 Build Process Documentation

**Steps before deployment**:

1. **Install dependencies**:
   ```bash
   cd client
   npm install
   ```

2. **Build frontend**:
   ```bash
   npm run build
   # Outputs to client/dist/
   ```

3. **Validate setup**:
   ```bash
   python server/validate_setup.py
   ```

4. **Commit built assets**:
   ```bash
   git add client/dist
   git commit -m "Build frontend for deployment"
   git push
   ```

### 6.3 Requirements.txt Verification

**Ensure `requirements.txt` includes**:
```
fastapi
uvicorn[standard]
mlflow>=2.18.0
databricks-sdk
python-dotenv
```

---

## 7. Final Validation Checklist

Before declaring "ready for deployment":

### Backend Validation:
- [ ] `server/routes/dc_assistant.py` created with all 7 endpoints
- [ ] Preloaded demo data populated in `server/data/`
- [ ] `server/validate_setup.py` runs successfully
- [ ] All environment variables documented in `app.yaml`
- [ ] Health check endpoints return 200

### Frontend Validation:
- [ ] `npm run build` completes without errors
- [ ] Production build tested locally
- [ ] All 6 demo sections display correctly
- [ ] Interactive buttons ("Run Optimization", "Run GEPA") work
- [ ] MLflow UI links generate correctly
- [ ] No console errors in browser

### Integration Validation:
- [ ] Frontend calls to `/api/dc-assistant/*` return valid data
- [ ] Notebook links open to correct Databricks workspace
- [ ] Experiment links use correct tracking URI
- [ ] Static assets served correctly in production mode

### Documentation Validation:
- [ ] Deployment documentation clear and complete
- [ ] `.env.local.example` provided for local development
- [ ] README updated with DC Assistant specific setup
- [ ] Environment variables all documented

---

## 8. Handoff Notes - What Needs to be Done

**What's already complete**:
- ✅ All 6 frontend demo sections completed with interactive features
- ✅ React components fully implemented
- ✅ FastAPI backend structure exists
- ✅ `app.yaml` configuration template ready

**What needs to be implemented** (4-6 hours development work):

### Task 1: Create `server/routes/dc_assistant.py` (~200-300 lines, 2-3 hours)
- Implement 7 API endpoints listed in section 2.1
- Can use preloaded data initially (no real MLflow calls needed for demo)
- Follow pattern from existing `server/routes/email.py`

### Task 2: Create `server/data/dc_assistant_preloaded.py` (~100-150 lines, 1-2 hours)
- Sample traces from DC Assistant (5-10 Q&A examples)
- Mock judge results with scores
- Mock alignment/optimization results (before/after diffs)
- Mock monitoring metrics (success rates, latency, etc.)

### Task 3: Create `server/validate_setup.py` (~100 lines, 1 hour)
- Environment variable validation functions
- MLflow connectivity checks
- Endpoint status verification
- UC resource checks

### Task 4: Update environment configuration (~30 minutes)
- Fill in `app.yaml` with your specific values
- Create `.env.local` for local testing
- Update `server/app.py` to import DC Assistant routes

### Task 5: Test and validate (~1 hour)
- Run validation script
- Test all API endpoints
- Build and test frontend production build
- Verify all 6 sections load correctly

**Key resources needed**:
- Your MLflow experiment ID (from creating DC Assistant experiment)
- Your model endpoint name (from deploying DC Assistant model)
- Your Unity Catalog location (catalog.schema)

---

## 9. Actual Deployment Steps (5 minutes)

Once all development work is complete:

1. **Build frontend**:
   ```bash
   cd client
   npm run build
   ```

2. **Commit and push**:
   ```bash
   git add .
   git commit -m "DC Assistant demo ready for deployment"
   git push origin main
   ```

3. **Create Databricks App**:
   - Navigate to Databricks workspace
   - Go to Apps section
   - Click "Create App from Git"
   - Point to your git repository
   - App will automatically detect `app.yaml` and deploy
   - Wait 2-3 minutes for app to spin up

4. **Verify deployment**:
   - Open app URL
   - Check all 6 sections load
   - Test interactive features
   - Verify API calls work

**Done!** 🎉
