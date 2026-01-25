# Frontend Architecture Plan: NFL Defensive Coordinator Assistant

## Overview

Adapt the existing MLflow GenAI Demo app from email personalization to an NFL Defensive Coordinator (DC) Assistant use case. The backend agent with Unity Catalog tools and data ingestion is already complete. This plan focuses on frontend UI changes to demonstrate MLflow capabilities in the DC Assistant context.

**Core Goal**: Reuse existing UI patterns (cards, streaming, feedback) while updating content and flow to showcase:
- Observe agent behavior with tracing
- Evaluate with LLM judges
- Capture expert (coach) feedback
- Align judges to domain expertise
- Optimize prompts automatically
- Continuous improvement loop

**Key Constraint**: Backend agent/tools are ready - this is pure UI plumbing work.

---

## Section Mapping: Old Use Case → New Use Case

| Current Section | New Section | Purpose | Reuse % |
|----------------|-------------|---------|---------|
| Demo Overview | Demo Overview | Landing page with DC Assistant intro | 60% |
| Email Generator | DC Assistant Chat | Main interface with categorized questions | 70% |
| Step 1: Observe with Tracing | Step 1: Observe with Tracing | Show MLflow traces for game analysis | 80% |
| Step 2: Create Quality Metrics | Step 2: Evaluate with Judges | LLM judges for DC recommendations | 75% |
| Step 3: Find & Fix Issues | Step 3: Capture Expert Feedback | MLflow Labeling Sessions for coaches | 60% |
| Step 4: Link to Business KPIs | Step 4: Align Judges to Experts | Judge alignment with SME feedback | 40% |
| Step 5: Production Monitoring | Step 5: Optimize Prompts | Automatic prompt improvement | 50% |
| Step 6: Human Review | Step 6: Continuous Loop | Full optimization cycle | 65% |

---

## Critical Files to Modify

### 1. Navigation & Routing

**File**: `client/src/components/app-sidebar.tsx`

**Changes**:
- Update `mlflowSteps` array with new titles:
  - "Observe with tracing" → "Observe DC Analysis"
  - "Create quality metrics" → "Evaluate Recommendations"
  - "Find & fix quality issues" → "Capture Coach Feedback"
  - "Link to business KPIs" → "Align Judges to Experts"
  - "Production Monitoring" → "Optimize Prompts"
  - "Human Review" → "Continuous Optimization"

- Update NavMain section:
  - Change "Sales email generator" to "DC Assistant"
  - Update description to "Analyze opponent tendencies"
  - Change route from `/email` to `/dc-assistant`

**File**: `client/src/routes.ts`

**Changes**:
- Add new route: `"dc-assistant": "/dc-assistant"`
- Keep all step routes (just update component content)

**File**: `client/src/App.tsx`

**Changes**:
- Update ViewType union: `"email"` → `"dc-assistant"`
- Add routing case for dc-assistant view
- Import new `DcAssistant` component instead of `EmailGenerator`

---

### 2. Main Chat Interface (Replaces Email Generator)

**New Component**: `client/src/components/dc-assistant/DcAssistant.tsx`

**Architecture**: Clone `EmailGenerator.tsx` pattern but adapt for DC use case

**Layout**:
```
┌─────────────────────────────────────────────────┐
│ Header: "NFL Defensive Coordinator Assistant"  │
├──────────────────┬──────────────────────────────┤
│  LEFT COLUMN     │  RIGHT COLUMN                │
│  (Input)         │  (Output)                    │
├──────────────────┼──────────────────────────────┤
│ Question         │ Analysis Output              │
│ Category         │ ┌──────────────────────────┐ │
│ ┌──────────────┐ │ │ Streaming Response       │ │
│ │ 3rd Down     │ │ │ • Key Tendencies         │ │
│ │ Red Zone     │ │ │ • Player Stats           │ │
│ │ Two-Minute   │ │ │ • Recommendations        │ │
│ │ Personnel    │ │ └──────────────────────────┘ │
│ └──────────────┘ │                              │
│                  │ Feedback UI                  │
│ Specific         │ ┌──────────────────────────┐ │
│ Question         │ │ 👍 👎                     │ │
│ ┌──────────────┐ │ │ Add coaching notes...    │ │
│ │ Who gets...  │ │ └──────────────────────────┘ │
│ │ the ball...  │ │                              │
│ └──────────────┘ │ MLflow Trace Link            │
│                  │ [View in MLflow →]           │
│ [Analyze]        │                              │
└──────────────────┴──────────────────────────────┘
```

**State Management** (mirror EmailGenerator pattern):
```typescript
const [questionCategories] = useState([
  { id: "3rd-down", label: "3rd Down Situations" },
  { id: "red-zone", label: "Red Zone Plays" },
  { id: "two-minute", label: "Two-Minute Drill" },
  { id: "personnel", label: "Personnel Packages" },
]);
const [selectedCategory, setSelectedCategory] = useState("");
const [specificQuestions, setSpecificQuestions] = useState<string[]>([]);
const [selectedQuestion, setSelectedQuestion] = useState("");
const [analysis, setAnalysis] = useState<any>(null);
const [isStreaming, setIsStreaming] = useState(false);
const [currentTraceId, setCurrentTraceId] = useState<string | null>(null);
const [feedbackRating, setFeedbackRating] = useState<"up" | "down" | null>(null);
```

**API Integration**:
```typescript
// Stream analysis (mirrors email streaming pattern)
const response = await fetch("/api/dc-assistant/analyze-stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    question: selectedQuestion,
    category: selectedCategory
  })
});

// SSE parsing (same pattern as EmailGenerator)
const reader = response.body?.getReader();
const decoder = new TextDecoder();
// Parse 'token', 'done', 'error' types
```

**Question Data Structure** (hardcoded initially):
```typescript
const QUESTIONS_BY_CATEGORY = {
  "3rd-down": [
    "What do the Cowboys do on 3rd and short?",
    "Who gets the ball for the 49ers on 3rd and 6?",
    "What formations do the Chiefs use on 3rd and long?"
  ],
  "red-zone": [
    "What are the Packers' red zone tendencies?",
    "Who scores TDs for the Ravens in the red zone?",
    "What plays do the Eagles run inside the 10?"
  ],
  "two-minute": [
    "What do the Bills do in the last 2 minutes of halves?",
    "How do the Bengals attack in hurry-up offense?",
    "What's the Patriots' clock management strategy?"
  ],
  "personnel": [
    "What does the Dolphins' 11 personnel look like?",
    "Who gets the ball in the Titans' 12 personnel?",
    "What are the Cardinals' 21 personnel tendencies?"
  ]
};
```

---

### 3. Supporting Components (Create/Adapt)

**New Components to Create**:

**`client/src/components/dc-assistant/QuestionSelector.tsx`**
- Dropdown for category selection
- List of questions filtered by category
- Reuse Select/SelectContent from shadcn/ui

**`client/src/components/dc-assistant/AnalysisDisplay.tsx`**
- Similar to EmailDisplay.tsx
- Show streaming analysis output
- Display tool calls/data sources used
- Link to MLflow trace

**`client/src/components/dc-assistant/FeedbackForm.tsx`**
- Identical to email feedback pattern
- Submit coaching feedback with trace_id
- POST to `/api/feedback` endpoint

---

### 4. Demo Step Components (Modify Existing)

#### Step 1: Observe with Tracing
**File**: `client/src/components/demo-pages/observe-with-tracing.tsx`

**Changes**:
- Update intro markdown to explain DC Assistant tracing
- Change code examples from email to DC Assistant:
  - RETRIEVER span: "Load play-by-play data"
  - PARSER span: "Format game situation"
  - LLM span: "Generate DC recommendations"
- Update demo section with DC-specific example questions
- Keep same MLflow trace linking pattern

**Content Updates**:
```markdown
## Observe DC Analysis with MLflow Tracing

When a coach asks "What do the Cowboys do on 3rd and 6?", the agent:
1. **RETRIEVER**: Queries Unity Catalog for play-by-play data
2. **PARSER**: Formats situation parameters (down, distance, team)
3. **LLM**: Generates contextualized recommendations

Each trace includes:
- Tool calls made (which SQL functions were invoked)
- Data returned (play statistics, tendencies)
- Final analysis and recommendations
```

---

#### Step 2: Evaluate with Judges
**File**: `client/src/components/demo-pages/create-quality-metrics.tsx`

**Changes**:
- Update content to focus on DC-specific evaluation criteria
- Change judge examples:
  - RelevanceToQuery: "Does the analysis address the coach's question?"
  - Football Language: "Uses appropriate NFL terminology?"
  - Strategic Value: "Provides actionable defensive recommendations?"
- Update code snippets to show DC Assistant judges

**Content Updates**:
```python
# Custom judge for DC Assistant
football_analysis_judge = make_judge(
  name="football_analysis_base",
  instructions=(
    "Evaluate if the response appropriately analyzes the available data "
    "and provides an actionable recommendation for the defensive coordinator. "
    "Consider: data accuracy, contextual relevance, strategic advantage."
  ),
  feedback_value_type=float,
  model=JUDGE_MODEL,
)
```

---

#### Step 3: Capture Expert Feedback
**File**: `client/src/components/demo-pages/find-fix-quality-issues.tsx`

**Changes**:
- Rename title: "Capture Expert Feedback from Coaches"
- Focus on MLflow Labeling Sessions
- Show how coaches review agent outputs
- Explain structured feedback collection

**Content Updates**:
- Remove iterative testing section (not relevant)
- Add MLflow Labeling Session UI screenshots
- Show coach feedback flow:
  1. Coach asks question via DC Assistant
  2. Reviews response and trace
  3. Opens Labeling Session in MLflow
  4. Provides score (1-5) and feedback comments
  5. Feedback linked to trace_id

**Demo Section**:
- Embed screenshot of Review App (from blog page 14)
- Show label schema matching judge criteria
- Link to MLflow Labeling Session documentation

---

#### Step 4: Align Judges to Experts
**File**: `client/src/components/demo-pages/business-metrics.tsx` → Rename to `judge-alignment.tsx`

**Changes**:
- Complete content overhaul (only 40% reuse of layout)
- Explain judge alignment concept
- Show SIMBA optimizer process
- Display before/after judge performance

**New Content Structure**:
```markdown
## Align Judges to Expert Feedback

Generic LLM judges miss domain-specific nuance. The alignment process:

1. **Baseline Judge**: Created with best-effort rubric
2. **SME Feedback**: Coaches label agent outputs via MLflow
3. **Alignment**: SIMBA optimizer calibrates judge to match expert scores
4. **Aligned Judge**: Reflects coaching expertise at scale

### Judge Improvement Metrics
- Baseline correlation with coaches: 0.62
- Aligned correlation with coaches: 0.89
- Key improvements: Better assessment of strategic value and game context
```

**Code Examples**:
```python
# Load baseline judge
football_analysis_judge = get_scorer(name="football_analysis_base")

# Configure SIMBA optimizer
likert_optimizer = LikertSIMBAAlignmentOptimizer(
  model=REFLECTION_MODEL,
  batch_size=6,
  max_demos=0
)

# Align judge to coach feedback
aligned_judge = football_analysis_judge.align(
  traces=traces_for_alignment,
  optimizer=likert_optimizer
)
```

---

#### Step 5: Optimize Prompts
**File**: `client/src/components/demo-pages/prod-monitoring.tsx` → Rename to `prompt-optimization.tsx`

**Changes**:
- Remove production monitoring content
- Focus on GEPA optimizer and prompt optimization
- Show before/after prompt comparison
- Display performance improvements

**New Content**:
```markdown
## Automatically Optimize Prompts

With an aligned judge that reflects coaching expertise, MLflow can automatically improve the agent's system prompt:

### GEPA Optimizer Process
1. Takes current production prompt
2. Generates candidate improvements
3. Evaluates each candidate with aligned judge
4. Selects best performing prompt
5. Registers new version to MLflow Prompt Registry

### Example Improvement
**Before**: "You are an assistant for NFL defensive coordinators..."
**After**: "You are a Defensive Game-Planning Assistant. Analyze play-by-play data to identify opponent tendencies. Focus on down-and-distance, formation/personnel, and situational context. Provide specific player matchups and scheme recommendations..."
```

**Code Examples**:
```python
# Load current prompt
system_prompt = mlflow.genai.load_prompt(f"prompts:/{PROMPT_NAME}@production")

# Run optimization
result = mlflow.genai.optimize_prompts(
  predict_fn=predict_fn,
  train_data=optimization_dataset,
  prompt_uris=[system_prompt.uri],
  optimizer=GepaPromptOptimizer(
    reflection_model=REFLECTION_MODEL,
    max_metric_calls=75
  ),
  scorers=[aligned_judge]
)
```

---

#### Step 6: Continuous Optimization Loop
**File**: `client/src/components/demo-pages/human-review.tsx` → Rename to `continuous-loop.tsx`

**Changes**:
- Show full optimization cycle
- Display pipeline diagram (from blog page 5)
- Explain automation possibilities
- Link all previous steps together

**New Content**:
```markdown
## Continuous Optimization Loop

The DC Assistant improves automatically as coaches use it:

1. **Coaches use the assistant** → Generate traces
2. **Label promising/problematic outputs** → MLflow Labeling Sessions
3. **Judge alignment runs** → Calibrate to latest coach preferences
4. **Prompt optimization runs** → Generate improved prompts
5. **Conditional promotion** → Deploy if performance threshold met
6. **Repeat** → Compound improvements over time

### Automation Options
- Fully automated: Auto-promote prompts exceeding performance thresholds
- Semi-automated: Manual review before promotion
- Manual: Use insights to inform hand-crafted improvements
```

**Demo Section**:
- Embed pipeline diagram from blog
- Show Databricks Job/workflow for automation
- Link to MLflow experiment showing progression of prompt versions

---

### 5. Demo Overview Page

**File**: `client/src/components/demo-overview.tsx`

**Changes**:
- Update hero section:
  - Title: "NFL Defensive Coordinator Assistant"
  - Subtitle: "Self-optimizing game analysis guided by coaching expertise"
  - Description: "Learn how to build, evaluate, and continuously improve an agentic assistant that helps defensive coordinators anticipate opponent tendencies."

- Update step cards:
  - Keep 6-step flow
  - Update titles/descriptions to match new sections
  - Update icons if needed (use Football icon for DC Assistant)

- Update "Why This Matters" section:
  - Change from sales email context to DC coaching context
  - Emphasize domain expertise encoding
  - Highlight continuous improvement

**Content Example**:
```markdown
## The Challenge

Generic LLM judges and static prompts fail to capture domain-specific nuance. Determining what makes an NFL defensive analysis "good" requires deep football knowledge: coverage schemes, formation tendencies, situational context.

## The Solution

A self-optimizing architecture where coaching expertise continuously improves AI quality:
- Coaches provide feedback on agent outputs
- MLflow aligns judges to match coaching preferences
- System automatically optimizes prompts guided by aligned judges
- Agent improves without manual prompt engineering
```

---

## API Endpoint Requirements

### Existing Endpoints to Reuse (No Changes Needed)
- `/api/tracing_experiment` - MLflow experiment metadata
- `/api/feedback` - Submit user feedback with trace_id
- `/api/preloaded-results` - Evaluation result URLs
- `/api/get-notebook-url/{name}` - Notebook links
- `/api/fixed-prompt` - Fixed prompt template
- `/api/current-production-prompt` - Production prompt from registry

### New Endpoints Needed (Backend Already Implemented)
- `/api/dc-assistant/analyze-stream` - POST - Stream DC analysis with SSE
  - Request: `{question: string, category?: string}`
  - Response: SSE stream with token/done/error chunks
  - Returns: `{type: 'done', trace_id: string, analysis: {tendencies, recommendations, stats}}`

- `/api/dc-assistant/questions` - GET - List categorized questions
  - Response: `{categories: Array<{id, label, questions: string[]}>}`
  - Can be hardcoded initially, dynamic later

### API Integration Pattern (Same as Email)

**Streaming Request**:
```typescript
const response = await fetch("/api/dc-assistant/analyze-stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ question: selectedQuestion, category: selectedCategory })
});

const reader = response.body?.getReader();
const decoder = new TextDecoder();
let accumulated = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split("\n");

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));

      if (data.type === "token") {
        accumulated += data.content;
        setAnalysis(accumulated);
      } else if (data.type === "done") {
        setCurrentTraceId(data.trace_id);
        setIsStreaming(false);
      } else if (data.type === "error") {
        setError(data.error);
        setIsStreaming(false);
      }
    }
  }
}
```

**Feedback Submission** (Reuse existing):
```typescript
const feedbackData = {
  trace_id: currentTraceId,
  rating: feedbackRating, // "up" or "down"
  comment: feedbackComment,
  sales_rep_name: "Coach Smith" // Optional
};

await EmailService.submitFeedbackApiFeedbackPost(feedbackData);
```

---

## Component Reuse Matrix

### High Reuse (80%+) - Minimal Changes
- `StepLayout.tsx` - No changes, just pass new content
- `CollapsibleSection.tsx` - No changes
- `CodeSnippet.tsx` - No changes
- `MarkdownContent.tsx` - No changes
- `Spinner.tsx` - No changes
- All shadcn/ui components (Button, Card, Input, etc.) - No changes

### Medium Reuse (50-80%) - Content Updates
- `observe-with-tracing.tsx` - Update examples and markdown content
- `create-quality-metrics.tsx` - Update judge examples
- Demo overview page - Update titles and descriptions
- Sidebar navigation - Update labels and routes

### Low Reuse (20-50%) - Significant Refactoring
- `DcAssistant.tsx` (from EmailGenerator) - Adapt streaming pattern
- `find-fix-quality-issues.tsx` - Focus on feedback capture
- `business-metrics.tsx` → `judge-alignment.tsx` - New content

### New Components (0% Reuse)
- `QuestionSelector.tsx` - Category + question picker
- `AnalysisDisplay.tsx` - Display DC analysis output
- `prompt-optimization.tsx` - New step for GEPA optimizer
- `continuous-loop.tsx` - New step for full cycle

---

## Implementation Strategy

### Phase 1: Infrastructure Setup
1. Create new component directories:
   - `client/src/components/dc-assistant/`
   - Move/rename demo page files as needed

2. Update routing and navigation:
   - Modify `app-sidebar.tsx` with new section titles
   - Update `routes.ts` with dc-assistant route
   - Update `App.tsx` ViewType and routing logic

3. Set up API integration:
   - Verify backend endpoints are working
   - Test `/api/dc-assistant/analyze-stream` with curl
   - Confirm MLflow tracing is active

### Phase 2: Main Chat Interface
1. Create `DcAssistant.tsx` by cloning `EmailGenerator.tsx`
2. Implement question categorization UI:
   - Category selector dropdown
   - Dynamic question list based on category
   - Hardcode initial question sets
3. Adapt streaming pattern:
   - Reuse SSE parsing logic
   - Update state variables for DC context
   - Style output for game analysis format
4. Implement feedback form:
   - Reuse existing feedback pattern
   - Update labels ("Helpful for game planning?")

### Phase 3: Demo Steps (Sequential Updates)
1. **Step 1: Observe with Tracing**
   - Update intro markdown with DC context
   - Replace code examples (email → DC)
   - Update demo section with DC questions

2. **Step 2: Evaluate with Judges**
   - Update judge examples for football analysis
   - Replace evaluation criteria
   - Keep same structure and layout

3. **Step 3: Capture Expert Feedback**
   - Remove iterative testing content
   - Focus on MLflow Labeling Sessions
   - Add coach feedback workflow

4. **Step 4: Align Judges**
   - Rename file from business-metrics
   - Write new content on judge alignment
   - Add SIMBA optimizer examples
   - Show before/after comparisons

5. **Step 5: Optimize Prompts**
   - Rename file from prod-monitoring
   - Write new content on GEPA optimizer
   - Show prompt evolution examples
   - Display performance improvements

6. **Step 6: Continuous Loop**
   - Rename file from human-review
   - Write new content showing full cycle
   - Embed pipeline diagram
   - Link to automation examples

### Phase 4: Polish and Testing
1. Update demo overview page:
   - New hero content
   - Updated step cards
   - DC Assistant context throughout

2. Test end-to-end flow:
   - Navigate through all sections
   - Verify DC Assistant chat works
   - Test streaming responses
   - Confirm feedback submission works
   - Check MLflow trace linking

3. Fix any TypeScript errors:
   - Missing imports
   - Type mismatches
   - Route definitions

4. Visual polish:
   - Ensure consistent styling
   - Responsive layout testing
   - Loading states work correctly
   - Error handling displays properly

---

## Content Guidelines

### Writing Style
- **Educational tone**: Explain "why" not just "how"
- **Coach-centric language**: "game planning", "opponent tendencies", "strategic advantage"
- **Concrete examples**: Use real NFL teams and situations
- **Technical accuracy**: Align with MLflow 3.0 terminology

### Example Questions (Categorized)

**3rd Down Situations**:
- "What do the Cowboys do on 3rd and short in 11 personnel?"
- "Who gets the ball for the 49ers on 3rd and 6?"
- "What formations do the Chiefs use on 3rd and long?"
- "How do the Eagles attack the blitz on 3rd down?"

**Red Zone Plays**:
- "What are the Packers' red zone tendencies?"
- "Who scores touchdowns for the Ravens inside the 10?"
- "What plays do the Bills run in goal-to-go situations?"
- "How do the Dolphins use motion in the red zone?"

**Two-Minute Drill**:
- "What do the Bengals do in the last 2 minutes of halves?"
- "How do the Patriots manage the clock in hurry-up?"
- "What's the Chiefs' two-minute personnel package?"
- "How do the Raiders attack prevent defense?"

**Personnel Packages**:
- "What does the Titans' 12 personnel look like?"
- "Who gets the ball in the Lions' 11 personnel?"
- "What are the Cardinals' 21 personnel tendencies?"
- "How do the Seahawks use 10 personnel formations?"

### Code Snippet Updates
Replace all email-related variable names:
- `email_generator` → `dc_assistant`
- `generate_email` → `analyze_game_situation`
- `customer_data` → `play_data` or `game_data`
- `EmailOutput` → `AnalysisOutput`
- `subject_line` → `key_tendencies`
- `body` → `recommendations`

### Markdown Content Structure
Each step should follow this pattern:
1. **Intro section**: High-level explanation (2-3 paragraphs)
2. **Code section**: Python examples with MLflow code
3. **Demo section**: Interactive UI or screenshots

---

## Testing Checklist

### Functionality Testing
- [ ] Navigation works between all sections
- [ ] DC Assistant chat loads and displays questions
- [ ] Category selection filters questions correctly
- [ ] Streaming analysis displays in real-time
- [ ] Trace ID is captured and stored
- [ ] Feedback submission works with trace linking
- [ ] MLflow experiment links work
- [ ] All step pages load without errors
- [ ] Code snippets render with syntax highlighting
- [ ] Markdown content displays properly

### Visual Testing
- [ ] Responsive layout on different screen sizes
- [ ] Loading spinners appear during streaming
- [ ] Error messages display clearly
- [ ] Cards and sections have proper spacing
- [ ] Icons display correctly in sidebar
- [ ] Active navigation state highlights correctly
- [ ] Scroll behavior works smoothly
- [ ] Button states (hover, active) work

### Integration Testing
- [ ] Backend endpoints respond correctly
- [ ] SSE streaming parses all chunk types
- [ ] MLflow tracing captures all spans
- [ ] Feedback API links to correct trace
- [ ] Prompt registry integration works
- [ ] Experiment metadata loads correctly

### Content Testing
- [ ] All NFL examples are accurate
- [ ] Terminology is appropriate for coaches
- [ ] Code examples are syntactically correct
- [ ] Links to notebooks work
- [ ] Blog references are accurate

---

## File Change Summary

### Files to Create (New)
```
client/src/components/dc-assistant/
  ├── DcAssistant.tsx                    # Main chat interface
  ├── QuestionSelector.tsx               # Category + question picker
  ├── AnalysisDisplay.tsx                # Analysis output display
  └── FeedbackForm.tsx                   # Coaching feedback UI

client/src/components/demo-pages/
  ├── judge-alignment.tsx                # New step 4 content
  ├── prompt-optimization.tsx            # New step 5 content
  └── continuous-loop.tsx                # New step 6 content
```

### Files to Modify
```
client/src/
  ├── App.tsx                            # Update routing, ViewType
  ├── routes.ts                          # Add dc-assistant route
  └── components/
      ├── app-sidebar.tsx                # Update nav labels
      ├── demo-overview.tsx              # Update landing page
      └── demo-pages/
          ├── observe-with-tracing.tsx   # Update content
          ├── create-quality-metrics.tsx # Update content
          └── find-fix-quality-issues.tsx # Update content
```

### Files to Rename
```
client/src/components/demo-pages/
  business-metrics.tsx → judge-alignment.tsx
  prod-monitoring.tsx → prompt-optimization.tsx
  human-review.tsx → continuous-loop.tsx
```

### Files to Keep Unchanged
```
client/src/components/
  ├── step-layout.tsx
  ├── collapsible-section.tsx
  ├── code-snippet.tsx
  ├── markdown-content.tsx
  ├── spinner.tsx
  └── ui/ (all shadcn components)

client/src/queries/ (all query hooks)
```

---

## Critical Files Reference

### Frontend Entry Points
- `client/src/main.tsx` - App entry point (no changes)
- `client/src/App.tsx` - Router and main view switching (update ViewType, routing)
- `client/src/components/app-sidebar.tsx` - Navigation (update labels)

### Component Templates
- `client/src/components/step-layout.tsx` - Reusable step template (no changes)
- `client/src/components/email-generator/EmailGenerator.tsx` - Pattern to clone for DcAssistant

### API Integration
- `client/src/fastapi_client/` - Auto-generated API client (regenerates on backend changes)
- `client/src/queries/` - React Query hooks (add new hooks if needed)

### Styling
- `client/src/index.css` - Global styles (no changes expected)
- Tailwind config - Defined in project root (no changes)

---

## Success Criteria

### Must Have (MVP)
1. DC Assistant chat interface works with categorized questions
2. Streaming analysis displays in real-time
3. Feedback submission links to MLflow traces
4. All 6 demo steps load and display content
5. Navigation between sections works smoothly
6. MLflow experiment links function correctly

### Nice to Have (Enhancements)
1. Dynamic question loading from backend
2. Rich analysis formatting (tables, charts for stats)
3. Tool call visualization (show which SQL functions ran)
4. Judge score history charts
5. Prompt diff viewer (before/after optimization)
6. Animation for streaming responses

### Out of Scope (Future Work)
1. Backend agent implementation (already done)
2. MLflow labeling session UI customization
3. Real-time judge alignment execution
4. Automated prompt promotion workflows
5. Multi-user coaching feedback aggregation

---

## Verification Steps

### Local Development Testing
1. Start dev server: `cd client && bun dev`
2. Navigate to `http://localhost:8000/dc-assistant`
3. Verify DC Assistant interface loads
4. Select category and question
5. Click "Analyze" and verify streaming works
6. Check MLflow UI for trace generation
7. Submit feedback and verify it appears in MLflow
8. Navigate through all 6 demo steps
9. Check browser console for errors

### End-to-End Flow Test
```bash
# 1. Start development server
./watch.sh

# 2. Test DC Assistant endpoint
curl -X POST http://localhost:8000/api/dc-assistant/analyze-stream \
  -H "Content-Type: application/json" \
  -d '{"question": "What do the Cowboys do on 3rd and 6?", "category": "3rd-down"}'

# 3. Check for streaming response with trace_id

# 4. Open browser and test UI
open http://localhost:8000/dc-assistant

# 5. Verify MLflow experiment
open <MLFLOW_EXPERIMENT_URL>
```

### Build and Deploy Test
```bash
# 1. Build frontend
cd client && bun run build

# 2. Check build output
ls -la client/build/

# 3. Deploy to Databricks Apps
./deploy.sh

# 4. Verify deployment
databricks apps list | grep mlflow-demo

# 5. Test deployed app
open <DATABRICKS_APP_URL>
```

---

## Risk Mitigation

### Potential Issues & Solutions

**Issue**: Backend endpoint doesn't return expected format
- **Solution**: Test endpoints with curl first, verify response structure matches frontend expectations

**Issue**: Streaming breaks or displays incorrectly
- **Solution**: Reuse exact SSE parsing logic from EmailGenerator, test with smaller responses first

**Issue**: Trace ID not captured or linked incorrectly
- **Solution**: Add console.log debugging, verify backend returns trace_id in 'done' chunk

**Issue**: TypeScript errors after routing changes
- **Solution**: Update ViewType union, ensure all route mappings are consistent

**Issue**: Content doesn't fit in existing layouts
- **Solution**: Use CollapsibleSection for long content, adjust card widths as needed

**Issue**: MLflow links don't work
- **Solution**: Verify DATABRICKS_HOST environment variable is set correctly

---

## Additional Notes

### Development Tips
- Run `./fix.sh` before committing to ensure code formatting
- Use `bun dev` in client directory for fast hot reload
- Check `screen -r lha-dev` to see server logs
- Use browser DevTools Network tab to debug SSE streaming
- Test with multiple browsers (Chrome, Firefox) for compatibility

### Architecture Decisions
- **Streaming-first**: Follow existing pattern for consistency
- **Component reuse**: Maximize code reuse to minimize bugs
- **Gradual migration**: Update sections one at a time
- **Backward compatibility**: Keep all existing functionality working

### Future Enhancements
- Add visualization of tool calls (which UC functions were invoked)
- Show play diagrams or formations in analysis output
- Integrate film study clips (if available)
- Add comparison mode (compare multiple teams/situations)
- Build analytics dashboard for coaching feedback trends

---

## Conclusion

This plan provides a comprehensive roadmap for adapting the MLflow GenAI Demo frontend from email personalization to the NFL Defensive Coordinator Assistant use case. The architecture leverages existing patterns (streaming, feedback, MLflow integration) while updating content to demonstrate domain-specific AI optimization guided by expert feedback.

**Key Principles**:
1. **Maximize reuse**: Keep proven patterns for streaming, feedback, and tracing
2. **Focus on content**: Backend is ready, this is pure UI work
3. **Educational value**: Showcase MLflow capabilities in coaching context
4. **Iterative approach**: Build and test one section at a time
5. **Production quality**: Follow existing code standards and patterns

The result will be a polished demo that clearly shows how MLflow enables continuous improvement of AI agents through domain expert feedback, using the compelling NFL coaching use case.
