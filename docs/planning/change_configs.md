# Configuration Guide: Changing Trace and Experiment URLs

This guide explains how to update the demo to point to different MLflow traces and experiments.

## Overview

The demo displays pre-generated MLflow traces via the "View sample trace" button in the Observe DC Analysis section. These traces are configured through environment variables and backend endpoints.

## Architecture

```
User clicks "View Sample Trace" button
    ↓
Frontend: observe-with-tracing.tsx (localhost:3000)
    ↓
React Query: useQueryPreloadedResults()
    ↓
API Client: DefaultService.getPreloadedResultsApiPreloadedResultsGet()
    ↓
Vite Proxy: /api → http://localhost:8000/api (DEV ONLY)
    ↓
Backend: GET /api/preloaded-results (localhost:8000)
    ↓
Returns: PreloadedResults with sample_trace_url
    ↓
Browser opens: {sample_trace_url} in new tab
```

**Note**: The Vite proxy layer only exists during development. In production, the frontend build is served from the same origin as the backend.

## Step-by-Step Configuration

### 1. Update Environment Variables

**File**: `.env.local` (root directory)

Add or update these environment variables:

```bash
# MLflow Experiment Configuration
MLFLOW_EXPERIMENT_ID="2517718719552044"

# Sample Trace Configuration
SAMPLE_TRACE_ID="tr-2a91cd9964876c016296dff8ec9f3e1e"

# Optional: Databricks workspace and SQL warehouse IDs
DATABRICKS_WORKSPACE_ID="1444828305810485"
SQL_WAREHOUSE_ID="4b9b953939869799"
```

**Key Variables**:
- `MLFLOW_EXPERIMENT_ID`: The experiment containing your traces
- `SAMPLE_TRACE_ID`: The specific trace to display (format: `tr-{UUID}`)
- `DATABRICKS_WORKSPACE_ID`: Workspace ID for Databricks UI (the `o` parameter in URLs)
- `SQL_WAREHOUSE_ID`: SQL warehouse ID for Unity Catalog queries

### 2. Backend URL Construction

**File**: `server/app.py` (lines 130-143)

The backend constructs the trace URL in the `get_preloaded_results()` endpoint:

```python
@app.get(f'{API_PREFIX}/preloaded-results')
async def get_preloaded_results() -> PreloadedResults:
  """Get preloaded evaluation results from setup scripts."""
  databricks_host = ensure_https_protocol(os.getenv('DATABRICKS_HOST'))

  # Build trace URL with all query parameters
  workspace_id = os.getenv('DATABRICKS_WORKSPACE_ID', '')
  sql_warehouse_id = os.getenv('SQL_WAREHOUSE_ID', '')
  trace_id = os.getenv('SAMPLE_TRACE_ID')
  experiment_id = get_mlflow_experiment_id()

  # Construct base URL
  trace_url = f'{databricks_host}/ml/experiments/{experiment_id}/traces'

  # Add query parameters
  params = []
  if workspace_id:
    params.append(f'o={workspace_id}')
  if sql_warehouse_id:
    params.append(f'sqlWarehouseId={sql_warehouse_id}')
  params.append(f'selectedEvaluationId={trace_id}')

  trace_url = f'{trace_url}?{"&".join(params)}'

  return PreloadedResults(
    sample_trace_url=trace_url,
    # ... other fields
  )
```

### 3. Finding Your Trace ID

**Option A: From MLflow UI**

1. Navigate to your MLflow experiment: `https://{host}/ml/experiments/{experiment_id}`
2. Click on the "Traces" tab
3. Find the trace you want to link
4. Copy the trace ID from the URL (format: `tr-{UUID}`)

**Option B: From trace URL**

If you have a full trace URL like:
```
https://e2-demo-field-eng.cloud.databricks.com/ml/experiments/2517718719552044/traces?o=1444828305810485&sqlWarehouseId=4b9b953939869799&selectedEvaluationId=tr-2a91cd9964876c016296dff8ec9f3e1e
```

Extract:
- Experiment ID: `2517718719552044` (from path `/ml/experiments/{id}/traces`)
- Workspace ID: `1444828305810485` (from `o=` parameter)
- SQL Warehouse ID: `4b9b953939869799` (from `sqlWarehouseId=` parameter)
- Trace ID: `tr-2a91cd9964876c016296dff8ec9f3e1e` (from `selectedEvaluationId=` parameter)

### 4. Restart the Development Server

After updating `.env.local`, restart the development server to pick up new values:

```bash
# Stop current server
./stop-server.sh  # or manually kill the screen session

# Start with new configuration
./watch.sh
```

The API will automatically regenerate and the frontend will fetch the new trace URL.

## Example: DC Assistant Configuration

For the NFL Defensive Coordinator Assistant demo:

```bash
# .env.local
DATABRICKS_HOST="https://e2-demo-field-eng.cloud.databricks.com"
MLFLOW_EXPERIMENT_ID="2517718719552044"
SAMPLE_TRACE_ID="tr-2a91cd9964876c016296dff8ec9f3e1e"
DATABRICKS_WORKSPACE_ID="1444828305810485"
SQL_WAREHOUSE_ID="4b9b953939869799"
```

This generates the URL:
```
https://e2-demo-field-eng.cloud.databricks.com/ml/experiments/2517718719552044/traces?o=1444828305810485&sqlWarehouseId=4b9b953939869799&selectedEvaluationId=tr-2a91cd9964876c016296dff8ec9f3e1e
```

## Other Configurable Traces

The `PreloadedResults` model includes several trace/session URLs:

```python
class PreloadedResults(BaseModel):
  sample_trace_url: str                    # Main demo trace
  sample_labeling_session_url: str         # Labeling session example
  sample_labeling_trace_id: str | None     # Trace for labeling demo
  sample_labeling_trace_url: str           # Full URL for labeling trace
  low_accuracy_results_url: str | None     # Evaluation results
  regression_results_url: str | None       # Regression test results
  metrics_result_url: str | None           # Metrics dashboard
```

Add corresponding environment variables for each:
- `SAMPLE_LABELING_SESSION_ID`
- `SAMPLE_LABELING_TRACE_ID`
- `LOW_ACCURACY_RESULTS_URL`
- `REGRESSION_RESULTS_URL`

## Critical: Vite Proxy Configuration (Required for Development)

**⚠️ IMPORTANT**: For the frontend to communicate with the backend during local development, Vite must be configured to proxy API requests.

### What Was the Issue?

When initially testing the trace button, it appeared greyed out and the browser Network tab showed **404 errors** for `/api/preloaded-results` requests. The frontend couldn't reach the backend API even though the backend was running successfully on port 8000.

### Why Did This Happen?

**During development:**
- **Frontend (Vite)** runs on `http://localhost:3000`
- **Backend (FastAPI)** runs on `http://localhost:8000`
- When the frontend tries to call `/api/preloaded-results`, it makes a request to `http://localhost:3000/api/preloaded-results`
- **Without a proxy**, Vite doesn't know to forward this to the backend on port 8000, resulting in a 404 error

**In production:**
- The built frontend is served from the same origin as the backend (both on port 8000)
- No proxy needed because `/api/preloaded-results` naturally goes to the same server

### The Fix

**File**: `client/vite.config.ts`

Add proxy configuration to forward `/api` requests to the backend:

```typescript
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 3000,
    host: true,
    hmr: {
      port: 3001,
    },
    // ✅ CRITICAL: Proxy API requests to backend during development
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // Backend port
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "build",
    chunkSizeWarningLimit: 5000,
  },
});
```

**What this does:**
- Any request to `http://localhost:3000/api/*` gets forwarded to `http://localhost:8000/api/*`
- Vite automatically handles the proxying during development
- The `changeOrigin: true` option ensures the host header is rewritten correctly

### Future Configuration Changes

**If you change the backend port** (default is 8000):

1. Update `UVICORN_PORT` in your environment or `watch.sh`
2. Update the proxy target in `client/vite.config.ts`:
   ```typescript
   proxy: {
     '/api': {
       target: 'http://localhost:YOUR_NEW_PORT',
       changeOrigin: true,
     },
   },
   ```
3. Restart the dev server with `./watch.sh`

**If you add new API endpoints:**
- No changes needed to proxy config
- As long as they start with `/api`, they'll automatically be proxied

**If you add non-API proxied endpoints:**
- Add additional proxy rules:
   ```typescript
   proxy: {
     '/api': {
       target: 'http://localhost:8000',
       changeOrigin: true,
     },
     '/other-endpoint': {
       target: 'http://localhost:9000',
       changeOrigin: true,
     },
   },
   ```

### How to Verify It's Working

1. Start the dev server: `./watch.sh`
2. Open browser to `http://localhost:3000`
3. Open **Developer Tools** → **Network tab**
4. Navigate to "Observe DC Analysis" section
5. Look for request to `preloaded-results`
6. **Should show**: `Status 200 OK` from `localhost:3000/api/preloaded-results` (proxied to backend)
7. **Should NOT show**: `Status 404 Not Found`

### Symptoms This Proxy Config Fixes

- ✅ "View sample trace" button greyed out
- ✅ 404 errors in Network tab for `/api/*` requests
- ✅ Console errors like "Failed to fetch" or "Network request failed"
- ✅ Data not loading from backend even though backend is running

## Troubleshooting

**API requests return 404 (even with proxy configured)**:
- Check that both frontend (port 3000) and backend (port 8000) are running
- Verify `watch.sh` started both servers successfully
- Check `vite.config.ts` has the proxy configuration shown above
- Hard refresh browser (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)

**Trace URL returns 404 (after clicking button)**:
- Verify the trace ID exists in the experiment
- Check that MLFLOW_EXPERIMENT_ID matches the experiment containing the trace
- Ensure you have permissions to access the experiment

**Button is disabled**:
- Check that the backend is running (`./watch.sh`)
- Verify `.env.local` has `SAMPLE_TRACE_ID` set
- Check browser console for API errors
- Verify proxy configuration exists in `vite.config.ts`

**URL doesn't include workspace/warehouse IDs**:
- Verify `DATABRICKS_WORKSPACE_ID` and `SQL_WAREHOUSE_ID` are set in `.env.local`
- These are optional parameters; trace will still work without them
- Restart dev server after adding these variables

## Related Files

- **Frontend UI**: `client/src/components/demo-pages/observe-with-tracing.tsx` (View Sample Trace button)
- **Query Hook**: `client/src/queries/useQueryPreloadedResults.tsx` (API call wrapper)
- **Backend Endpoint**: `server/app.py` lines 130-168 (trace URL construction)
- **Environment Config**: `.env.local` (trace IDs, experiment IDs, workspace IDs)
- **Vite Proxy Config**: `client/vite.config.ts` (⚠️ CRITICAL for development - proxies /api to backend)
- **Pydantic Model**: `server/app.py` line 90 (`PreloadedResults` class definition)
- **Dev Server Script**: `watch.sh` (loads .env.local and starts both servers)
