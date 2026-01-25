# DC Assistant Demo - Deployment Guide

**Quick Links**:
- 📋 [Configuration Guide](CONFIGURATION_GUIDE.md) - How to configure experiment IDs and environment
- 📝 [TODO Remaining Work](TODO_REMAINING_WORK.md) - What needs to be implemented

---

## Current Status

### ✅ Complete
- Frontend UI (all 6 demo sections)
- FastAPI backend structure
- Frontend production build
- Databricks App configuration

### ⚠️ Needs Work
- Backend API endpoints (see [TODO_REMAINING_WORK.md](TODO_REMAINING_WORK.md))
- Preloaded demo data
- Validation script

---

## Quick Deploy (What's Already Working)

### Step 1: Configure Environment

Edit `app.yaml` in project root:

```yaml
env:
  - name: 'MLFLOW_EXPERIMENT_ID'
    value: '/Users/your.email@company.com/dc-assistant-demo'  # ← CHANGE THIS

  - name: 'UC_CATALOG'
    value: 'your_catalog'  # ← CHANGE THIS

  - name: 'UC_SCHEMA'
    value: 'your_schema'  # ← CHANGE THIS

  - name: 'MODEL_ENDPOINT_NAME'
    value: 'dc-assistant-endpoint'  # ← CHANGE THIS
```

**See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) for complete details.**

---

### Step 2: Deploy to Databricks

1. Push code to git:
   ```bash
   git push origin ui-dev
   ```

2. In Databricks workspace:
   - Navigate to **Apps**
   - Click **Create App from Git**
   - Repository: `https://github.com/auschoi96/end-to-end-mlflow-genai.git`
   - Branch: `ui-dev`
   - Click **Create**

3. Wait 2-3 minutes for app to spin up

4. Access your app URL

---

### Step 3: Verify Deployment

**What currently works**:
- ✅ App loads and displays all 6 sections
- ✅ "View Experiment in MLflow UI" button opens your experiment
- ✅ Interactive UI components (buttons, cards, tabs)
- ✅ Code examples and documentation

**What doesn't work yet** (see TODO):
- ⚠️ "Run Optimization" and "Run GEPA" buttons show mock results (not connected to real data)
- ⚠️ Sample traces/judges are hardcoded examples
- ⚠️ No real MLflow API calls for dynamic data

---

## Local Development

### Setup

```bash
# 1. Create .env.local (see CONFIGURATION_GUIDE.md for template)
cat > .env.local << 'EOF'
MLFLOW_TRACKING_URI=databricks
MLFLOW_EXPERIMENT_ID=/Users/your.email@company.com/dc-assistant
UC_CATALOG=your_catalog
UC_SCHEMA=your_schema
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi...
EOF

# 2. Install backend dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Install frontend dependencies
cd client
npm install
cd ..
```

### Run Locally

```bash
# Terminal 1 - Backend
source .venv/bin/activate
uvicorn server.app:app --reload --port 8000

# Terminal 2 - Frontend
cd client
npm run dev
```

Open http://localhost:3000

---

## Next Steps (For Backend Implementation)

See [TODO_REMAINING_WORK.md](TODO_REMAINING_WORK.md) for:
1. Creating backend API endpoints (`server/routes/dc_assistant.py`)
2. Adding preloaded demo data (`server/data/dc_assistant_preloaded.py`)
3. Validation script (`server/validate_setup.py`)

**Estimated time**: 4-6 hours to get fully functional with mock data

---

## File Structure

```
mlflow-demo/
├── app.yaml                          # Databricks App config - EDIT THIS
├── .env.local                        # Local dev config - CREATE THIS
├── docs/
│   ├── DEPLOYMENT_GUIDE.md          # This file
│   ├── CONFIGURATION_GUIDE.md       # How to configure everything
│   └── TODO_REMAINING_WORK.md       # What needs to be implemented
├── server/
│   ├── app.py                       # FastAPI app - already configured
│   ├── routes/
│   │   ├── email.py                 # Old email demo routes
│   │   ├── helper.py                # Helper routes
│   │   └── dc_assistant.py          # TODO: Create this
│   └── data/
│       └── dc_assistant_preloaded.py # TODO: Create this
├── client/
│   ├── src/                         # React source (complete)
│   └── build/                       # Production build (ready)
└── mlflow_demo/
    └── utils/
        └── mlflow_helpers.py        # MLflow utilities (ready)
```

---

## Troubleshooting

### App deploys but shows blank page
- Check browser console for errors
- Verify `client/build/` directory exists in git
- Check backend logs in Databricks App UI

### "View Experiment" opens wrong experiment
- Update `MLFLOW_EXPERIMENT_ID` in `app.yaml`
- Redeploy app
- See [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)

### Local dev: Frontend can't reach backend
- Verify backend running on port 8000
- Check Vite proxy config in `client/vite.config.ts`
- Look for CORS errors in browser console

---

## Summary

**To deploy immediately**:
1. Edit `app.yaml` (4 environment variables)
2. Push to git
3. Create Databricks App from `ui-dev` branch
4. Done! ✅

**App will show**:
- Full DC Assistant UI with all 6 sections
- Interactive components and demos
- Links to your MLflow experiment

**App won't show yet**:
- Real-time data from your traces/judges
- Dynamic results from running optimizations
- *(These require backend implementation - see TODO)*

**For full functionality**: Complete tasks in [TODO_REMAINING_WORK.md](TODO_REMAINING_WORK.md)
