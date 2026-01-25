import React from "react";
import { StepLayout } from "@/components/step-layout";
import { CodeSnippet } from "@/components/code-snippet";
import { CollapsibleSection } from "@/components/collapsible-section";
import { MarkdownContent } from "@/components/markdown-content";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { NotebookReference } from "@/components/notebook-reference";
import { Textarea } from "@/components/ui/textarea";
import {
  ExternalLink,
  Activity,
  Sparkles,
  TrendingUp,
  CheckCircle2,
  Play,
  Loader2,
  ArrowRight,
  Zap,
  Target,
} from "lucide-react";
import ReactDiffViewer from "react-diff-viewer";

const introContent = `
# Automatically Optimize Prompts with GEPA

You've now built the complete quality improvement infrastructure:
- ✅ **Aligned judges** that reflect coaching expertise
- ✅ **Labeled dataset** from SME review sessions
- ✅ **Quality metrics** calibrated to expert judgment

Now comes the payoff: **Automatically improving your prompts** to maximize quality as measured by your expert-aligned judges.

## The Challenge: Manual Prompt Engineering is Brittle

Traditional prompt engineering is time-consuming and unreliable:
- Developers iterate blindly, guessing what changes might help
- Prompts become long and fragile with ad-hoc rules
- No systematic way to know if changes actually improve quality
- Each iteration requires manual testing and evaluation

**You need automated optimization guided by your quality metrics.**

## The Solution: GEPA (Generalized Preference Alignment)

GEPA is MLflow's prompt optimization algorithm that automatically improves prompts to maximize alignment with your expert-calibrated judges. Instead of manual trial-and-error, GEPA uses AI to:

1. **Generate candidate prompts** - Creates systematic variations of your baseline prompt
2. **Test against aligned judges** - Evaluates each candidate using your coaching-aligned judges
3. **Learn what works** - Identifies patterns in high-scoring vs low-scoring prompts
4. **Select the best** - Chooses the prompt with highest judge scores

## What Powers GEPA Under the Hood

GEPA combines multiple AI techniques to efficiently search the space of possible prompts:

### 1. **Prompt Mutation Engine**
- Uses an LLM to propose targeted improvements to your baseline prompt
- Mutations are guided by failure patterns from low-scoring traces
- Generates diverse candidates (additions, deletions, rephrasing, restructuring)
- Balances exploration (new ideas) with exploitation (refining promising approaches)

### 2. **Bayesian Optimization Search**
- Treats prompt optimization as a black-box optimization problem
- Builds a probabilistic model of how prompt changes affect judge scores
- Intelligently selects which candidates to evaluate next (acquisition function)
- Converges to high-quality prompts with fewer evaluations than random search

### 3. **Multi-Armed Bandit Strategy**
- Allocates evaluation budget to promising prompt candidates
- Quickly abandons low-performing variations
- Focuses compute on refining top candidates
- Balances breadth (trying new mutations) vs depth (testing variations of good prompts)

### 4. **Aligned Judge Feedback Loop**
- Every candidate is evaluated by your expert-aligned judges
- Judge scores guide the search toward prompts that match coaching expertise
- No human labeling required during optimization—judges scale SME judgment
- Optimization directly targets the quality metrics you care about

## GEPA vs Manual Prompt Engineering

| Approach | Speed | Quality | Scalability | Expertise Required |
|----------|-------|---------|-------------|-------------------|
| **Manual Iteration** | Slow (days-weeks) | Unpredictable | Doesn't scale | High (domain + prompt engineering) |
| **GEPA Optimization** | Fast (hours) | Systematically improves | Scales via judges | Low (just define judges) |

## What You Get

- **Higher quality outputs** - Prompts optimized for your domain-specific judges
- **Concise prompts** - GEPA often produces shorter, clearer prompts than manual attempts
- **Faster iteration** - Automatic improvement vs. manual trial-and-error
- **Continuous improvement** - Re-run optimization as you collect more labeled data

With aligned judges and labeled data from coaching staff, GEPA can optimize your DC Assistant prompts to maximize strategic value without manual prompt engineering.
`;

const baselinePrompt = `You are an expert NFL defensive coordinator assistant. Your role is to analyze play-by-play data and provide strategic defensive recommendations.

When answering questions:
- Query the available Unity Catalog tables for relevant play-by-play data
- Analyze offensive tendencies and patterns
- Provide actionable defensive adjustments
- Reference specific data points and percentages

Always ground your analysis in the actual data retrieved from tool calls.`;

const optimizedPrompt = `You are an expert NFL defensive coordinator assistant. Your role is to analyze play-by-play data and provide strategic defensive recommendations tailored to the coaching staff's needs.

## Query Analysis Framework

**CRITICAL: Identify the query type before answering**

1. **Sequence Questions** (keywords: "typical sequence", "play-by-play", "what do they call first/next", "script")
   - Provide an **ordered progression** of plays (Step 1, Step 2, Step 3 OR "1st play:..., 2nd play:...")
   - Include situational context (down, distance, clock, field position)
   - Describe specific play concepts in sequence order
   - Example: "Typical 2-minute drill: (1) Quick out to boundary WR, (2) Dig route to move chains, (3) Shot play to TE on seam"

2. **Tendency/Concept Questions** (keywords: "how do they use X", "what concepts", "tendencies")
   - Focus on schematic patterns and frequencies
   - Reference specific formations, personnel packages, route concepts
   - Provide actionable coaching takeaways and counters
   - No need for step-by-step sequences unless explicitly asked

3. **Scoped Queries** (keywords: "red zone only", "3rd down", "after turnover", "under 2 minutes")
   - **ONLY use data matching the requested scope**
   - If asked about "red zone", filter to plays inside the 20-yard line
   - If asked about "3rd down", analyze 3rd down plays only
   - State the scope in your answer: "In red zone situations specifically..."

## Data Analysis Requirements

- **Always query Unity Catalog tables** for play-by-play data before answering
- **Ground all claims in retrieved data** - cite percentages, frequencies, specific plays
- **No hallucination** - if data doesn't support a claim, don't make it
- Use standard NFL terminology:
  - Personnel: 11 (1 RB, 1 TE, 3 WR), 12 (1 RB, 2 TE, 2 WR), etc.
  - Coverage: Cover 2, Cover 3, Quarter-Quarter-Half, etc.
  - Down notation: "3rd and 6", "2nd and long"

## Strategic Recommendations

- Provide **specific defensive adjustments** (coverage calls, pressure schemes, personnel)
- Reference **key matchups** and player-specific insights
- Make recommendations **actionable** for game planning (not generic advice)

## Multi-Part Questions

If a question has multiple parts (e.g., "What concepts do they use AND who do they target?"):
- Address **all parts** explicitly
- Overall quality constrained by weakest sub-answer
- Don't skip parts—partial answers receive partial credit`;

const loadPromptCode = `import mlflow
from mlflow.genai.scorers import get_scorer

# Load current production prompt from Prompt Registry
PROMPT_NAME = "dc_assistant_system_prompt"
baseline_prompt = mlflow.genai.load_prompt(
    f"prompts://{UC_CATALOG}.{UC_SCHEMA}.{PROMPT_NAME}@production"
)

print(f"Current prompt version: {baseline_prompt.version}")
print(f"Baseline prompt length: {len(baseline_prompt.get_text())} characters")
print(f"\\nBaseline prompt:\\n{baseline_prompt.get_text()}")`;

const prepareOptimizationDataCode = `import mlflow
import pandas as pd

# Load labeled traces from SME review sessions (from step 3)
labeling_session = mlflow.genai.get_labeling_session("dc_quality_review_20250115")
labeled_traces = labeling_session.get_labeled_traces()

# Convert to optimization dataset with expert feedback
optimization_data = []
for trace in labeled_traces:
    labels = trace.get_labels()

    optimization_data.append({
        "question": trace.inputs["question"],
        "response": trace.outputs["response"],
        "expert_overall_quality": int(labels.get("overall_quality", {}).get("value", 3)),
        "expert_football_language": labels.get("football_language", {}).get("value") == "pass",
        "expert_data_grounded": labels.get("data_grounded", {}).get("value") == "pass",
    })

optimization_df = pd.DataFrame(optimization_data)
optimization_dataset = mlflow.data.from_pandas(
    optimization_df,
    source="coach_labeling_sessions",
    name="dc_optimization_dataset_v1"
)

print(f"✅ Prepared optimization dataset: {len(optimization_df)} labeled traces")
print(f"   Avg expert overall quality: {optimization_df['expert_overall_quality'].mean():.2f}/5")`;

const runGepaOptimizationCode = `from mlflow.genai.optimizers import GepaPromptOptimizer
from mlflow.genai import optimize_prompts

# Load aligned judge from step 4
aligned_judge = get_scorer(name="football_analysis_aligned")

# Define prediction function that uses the prompt being optimized
def predict_fn(inputs):
    """Generate DC analysis using candidate prompt."""
    messages = [
        {"role": "system", "content": inputs["system_prompt"]},
        {"role": "user", "content": inputs["question"]}
    ]

    # Call your DC Assistant agent
    response = dc_assistant_agent.predict(messages=messages)
    return {"response": response}

# Run GEPA optimization
print("🚀 Starting GEPA optimization...")
print("   This will test ~50-75 candidate prompts against aligned judges\\n")

result = optimize_prompts(
    predict_fn=predict_fn,
    train_data=optimization_dataset,
    prompt_uris=[baseline_prompt.uri],  # Prompt to optimize
    optimizer=GepaPromptOptimizer(
        reflection_model="databricks-meta-llama-3-1-70b-instruct",
        max_metric_calls=75,  # Test up to 75 candidate prompts
        num_candidates_per_iteration=5,  # Generate 5 candidates per round
        convergence_threshold=0.02  # Stop if improvement < 2%
    ),
    scorers=[aligned_judge],  # Use your coaching-aligned judge
    experiment_name="dc_prompt_optimization"
)

# GEPA automatically selects the best prompt
best_prompt = result.best_prompt
baseline_score = result.baseline_score
best_score = result.best_score

print(f"\\n✅ GEPA Optimization Complete!")
print(f"   Baseline score: {baseline_score:.3f}")
print(f"   Optimized score: {best_score:.3f}")
print(f"   Improvement: {((best_score - baseline_score) / baseline_score * 100):.1f}%")
print(f"   Candidates tested: {result.num_prompts_evaluated}")
print(f"\\nBest prompt preview:")
print(best_prompt.get_text()[:500] + "...")`;

const registerOptimizedPromptCode = `import mlflow

# Register optimized prompt to Prompt Registry
new_version = mlflow.genai.save_prompt(
    prompt=best_prompt,
    name=f"{UC_CATALOG}.{UC_SCHEMA}.{PROMPT_NAME}",
    tags={
        "optimization_method": "gepa",
        "baseline_score": str(baseline_score),
        "optimized_score": str(best_score),
        "improvement_pct": str((best_score - baseline_score) / baseline_score * 100),
        "aligned_to": "coach_feedback"
    }
)

print(f"✅ Registered optimized prompt as version {new_version}")

# Option 1: Manual promotion after review
print(f"\\n📋 Review optimized prompt at: {new_version.uri}")
print(f"   To promote to production:")
print(f"   mlflow.tracking.MlflowClient().set_registered_model_alias(")
print(f"       name='{UC_CATALOG}.{UC_SCHEMA}.{PROMPT_NAME}',")
print(f"       alias='production',")
print(f"       version={new_version}")
print(f"   )")

# Option 2: Automatic promotion with threshold
PROMOTION_THRESHOLD = 0.75  # Require 75% judge score

if best_score >= PROMOTION_THRESHOLD:
    client = mlflow.tracking.MlflowClient()
    client.set_registered_model_alias(
        name=f"{UC_CATALOG}.{UC_SCHEMA}.{PROMPT_NAME}",
        alias="production",
        version=new_version
    )
    print(f"\\n🚀 Automatically promoted to production (score {best_score:.3f} >= {PROMOTION_THRESHOLD})")
else:
    print(f"\\n⏸️ Manual review required (score {best_score:.3f} below threshold {PROMOTION_THRESHOLD})")
    print(f"   Registered as version {new_version}, not promoted to production")`;

export function MonitoringDemo() {
  const [isOptimizing, setIsOptimizing] = React.useState(false);
  const [hasOptimized, setHasOptimized] = React.useState(false);
  const [optimizationProgress, setOptimizationProgress] = React.useState(0);
  const [currentIteration, setCurrentIteration] = React.useState(0);
  const [viewMode, setViewMode] = React.useState<"side-by-side" | "diff">("side-by-side");

  const runOptimization = () => {
    setIsOptimizing(true);
    setHasOptimized(false);
    setOptimizationProgress(0);
    setCurrentIteration(0);

    // Simulate GEPA optimization progress
    let iteration = 0;
    const progressInterval = setInterval(() => {
      setOptimizationProgress((prev) => {
        if (prev >= 100) {
          clearInterval(progressInterval);
          return 100;
        }
        return prev + 5;
      });

      // Update iteration every 20%
      if (optimizationProgress % 20 === 0 && iteration < 5) {
        iteration += 1;
        setCurrentIteration(iteration);
      }
    }, 400);

    // Complete after ~8 seconds
    setTimeout(() => {
      clearInterval(progressInterval);
      setOptimizationProgress(100);
      setCurrentIteration(5);
      setIsOptimizing(false);
      setHasOptimized(true);
    }, 8000);
  };

  const introSection = <MarkdownContent content={introContent} />;

  const codeSection = (
    <div className="space-y-6">
      <CollapsibleSection
        title="1. Load baseline prompt"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/"
      >
        <div className="space-y-4">
          <MarkdownContent content="Start with your current production prompt from the MLflow Prompt Registry. This serves as the baseline that GEPA will improve." />
          <CodeSnippet
            code={loadPromptCode}
            title="Load Production Prompt"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="2. Prepare optimization dataset"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/build-eval-dataset"
      >
        <div className="space-y-4">
          <MarkdownContent content="Use traces with expert labels from SME review sessions as the optimization dataset. GEPA will generate prompts that maximize performance on these coaching-validated examples." />
          <CodeSnippet
            code={prepareOptimizationDataCode}
            title="Prepare Labeled Dataset"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="3. Run GEPA optimization"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/prompt-optimization/"
      >
        <div className="space-y-4">
          <MarkdownContent content="GEPA generates candidate prompts, tests them against your aligned judges, and selects the best performer. The optimizer uses Bayesian optimization and multi-armed bandits to efficiently search the prompt space." />
          <CodeSnippet
            code={runGepaOptimizationCode}
            title="Run GEPA Optimization"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="4. Register and promote optimized prompt"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/"
      >
        <div className="space-y-4">
          <MarkdownContent content="Save the optimized prompt to the Prompt Registry and optionally promote to production. You can use automatic promotion with a score threshold or manual review before deployment." />
          <CodeSnippet
            code={registerOptimizedPromptCode}
            title="Register Optimized Prompt"
          />
        </div>
      </CollapsibleSection>

      <NotebookReference
        notebookPath="mlflow_demo/notebooks/5_optimize_prompts.ipynb"
        notebookName="5_optimize_prompts"
        description="Run GEPA optimization to automatically improve prompts using aligned judges"
      />
    </div>
  );

  const demoSection = (
    <div className="space-y-6">
      <MarkdownContent content="Experience how GEPA automatically optimizes prompts using your coaching-aligned judges. Click the button below to simulate the optimization process and see how the prompt improves." />

      {/* GEPA Overview Card */}
      <Card className="border-2 border-purple-200 bg-purple-50/30 dark:border-purple-800 dark:bg-purple-950/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-purple-900 dark:text-purple-100">
            <Sparkles className="h-5 w-5" />
            How GEPA Works: From Baseline to Optimized
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="border rounded-lg p-4 bg-white dark:bg-gray-900">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center text-sm font-semibold text-blue-700 dark:text-blue-300">
                  1
                </div>
                <h4 className="font-semibold text-sm">Generate Candidates</h4>
              </div>
              <p className="text-xs text-muted-foreground">
                Mutation engine creates ~5 prompt variations per iteration using an LLM. Guided by failure patterns from low-scoring traces.
              </p>
            </div>

            <div className="border rounded-lg p-4 bg-white dark:bg-gray-900">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center text-sm font-semibold text-green-700 dark:text-green-300">
                  2
                </div>
                <h4 className="font-semibold text-sm">Test with Judges</h4>
              </div>
              <p className="text-xs text-muted-foreground">
                Each candidate evaluated against aligned judges on labeled dataset. Scores guide search toward coach-preferred outputs.
              </p>
            </div>

            <div className="border rounded-lg p-4 bg-white dark:bg-gray-900">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center text-sm font-semibold text-purple-700 dark:text-purple-300">
                  3
                </div>
                <h4 className="font-semibold text-sm">Select Best</h4>
              </div>
              <p className="text-xs text-muted-foreground">
                Bayesian optimization and multi-armed bandits focus compute on promising candidates. Converges to optimal prompt.
              </p>
            </div>
          </div>

          <div className="p-3 bg-purple-100 dark:bg-purple-950/40 rounded-lg border border-purple-300 dark:border-purple-700">
            <p className="text-xs font-semibold text-purple-900 dark:text-purple-100 mb-1">
              GEPA Efficiency
            </p>
            <p className="text-xs text-purple-800 dark:text-purple-200">
              Typically tests 50-75 candidate prompts across 10-15 iterations to find the optimal version. Much faster than manual iteration, which could take weeks of trial-and-error.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Run GEPA Button */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Run GEPA Optimization
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Simulate the GEPA optimization process. GEPA will generate candidate prompts, evaluate them with your aligned judges, and select the best performer.
          </p>

          <Button
            onClick={runOptimization}
            disabled={isOptimizing}
            size="lg"
            className="w-full"
          >
            {isOptimizing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Running GEPA Optimization... (Iteration {currentIteration}/5)
              </>
            ) : hasOptimized ? (
              <>
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Optimization Complete - Run Again
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run GEPA Optimization
              </>
            )}
          </Button>

          {isOptimizing && (
            <div className="space-y-3">
              <Progress value={optimizationProgress} className="w-full" />
              <div className="space-y-1">
                <p className="text-xs text-center text-muted-foreground">
                  {optimizationProgress < 20 && "Loading baseline prompt and optimization dataset..."}
                  {optimizationProgress >= 20 && optimizationProgress < 40 && "Iteration 1: Generating 5 candidate prompts..."}
                  {optimizationProgress >= 40 && optimizationProgress < 60 && "Iteration 2-3: Testing candidates with aligned judges..."}
                  {optimizationProgress >= 60 && optimizationProgress < 80 && "Iteration 4: Refining top-performing prompts..."}
                  {optimizationProgress >= 80 && optimizationProgress < 100 && "Iteration 5: Final candidate evaluation..."}
                  {optimizationProgress === 100 && "Selecting best prompt based on judge scores!"}
                </p>
                {optimizationProgress >= 20 && optimizationProgress < 100 && (
                  <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
                    <Activity className="h-3 w-3 animate-pulse" />
                    <span>Testing candidate prompts on {Math.floor(optimizationProgress / 20) * 5}/25 traces</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results Section */}
      {hasOptimized && (
        <>
          {/* Success Message */}
          <Card className="border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                <div className="flex-1">
                  <p className="font-semibold text-green-900 dark:text-green-100">
                    GEPA Optimization Complete
                  </p>
                  <p className="text-sm text-green-800 dark:text-green-200 mt-1">
                    The prompt has been optimized to maximize performance on your coaching-aligned judges. Review the refined prompt below.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Optimization Results Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Optimization Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 border rounded-lg bg-blue-50 dark:bg-blue-950/20">
                  <div className="text-2xl font-bold text-blue-600">67</div>
                  <div className="text-xs text-muted-foreground">Prompts Tested</div>
                </div>
                <div className="text-center p-4 border rounded-lg bg-green-50 dark:bg-green-950/20">
                  <div className="text-2xl font-bold text-green-600">+18%</div>
                  <div className="text-xs text-muted-foreground">Judge Score Improvement</div>
                </div>
                <div className="text-center p-4 border rounded-lg bg-purple-50 dark:bg-purple-950/20">
                  <div className="text-2xl font-bold text-purple-600">0.68 → 0.80</div>
                  <div className="text-xs text-muted-foreground">Baseline → Optimized</div>
                </div>
                <div className="text-center p-4 border rounded-lg bg-orange-50 dark:bg-orange-950/20">
                  <div className="text-2xl font-bold text-orange-600">5</div>
                  <div className="text-xs text-muted-foreground">Optimization Iterations</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* View Toggle */}
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Optimized Prompt Comparison</h3>
            <div className="flex gap-2">
              <Button
                variant={viewMode === "side-by-side" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("side-by-side")}
              >
                Side by Side
              </Button>
              <Button
                variant={viewMode === "diff" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("diff")}
              >
                Diff View
              </Button>
            </div>
          </div>

          {/* Prompt Comparison */}
          {viewMode === "side-by-side" ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-muted-foreground">
                    <Target className="h-5 w-5" />
                    Baseline Prompt
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Badge variant="outline">Original</Badge>
                      <Badge variant="outline">{baselinePrompt.length} chars</Badge>
                    </div>
                    <Textarea
                      value={baselinePrompt}
                      rows={20}
                      className="font-mono text-xs"
                      readOnly
                    />
                    <p className="text-xs text-muted-foreground">
                      Judge Score: 0.68/1.0
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-green-600">
                    <TrendingUp className="h-5 w-5" />
                    GEPA-Optimized Prompt
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Badge className="bg-green-600">Optimized</Badge>
                      <Badge className="bg-green-600">{optimizedPrompt.length} chars</Badge>
                      <Badge variant="outline" className="text-green-600">+{optimizedPrompt.length - baselinePrompt.length} chars</Badge>
                    </div>
                    <Textarea
                      value={optimizedPrompt}
                      rows={20}
                      className="font-mono text-xs border-green-300"
                      readOnly
                    />
                    <p className="text-xs text-green-700 font-medium">
                      Judge Score: 0.80/1.0 (+18% improvement)
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Prompt Diff: What GEPA Added</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="border rounded-md overflow-hidden">
                  <ReactDiffViewer
                    oldValue={baselinePrompt}
                    newValue={optimizedPrompt}
                    splitView={false}
                    useDarkTheme={false}
                    hideLineNumbers={true}
                    showDiffOnly={false}
                    styles={{
                      variables: {
                        light: {
                          codeFoldGutterBackground: "#f8f9fa",
                          codeFoldBackground: "#f8f9fa",
                        },
                      },
                      contentText: {
                        fontSize: "11px",
                        fontFamily:
                          'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
                      },
                    }}
                  />
                </div>
                <p className="text-sm text-muted-foreground mt-4">
                  <strong>Green highlights</strong> show what GEPA learned from coaching feedback. The optimizer added structured frameworks for query analysis, scoping requirements, and multi-part question handling.
                </p>
              </CardContent>
            </Card>
          )}

          {/* Key Improvements Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Key Improvements Added by GEPA
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="p-4 border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950/20 rounded-r-lg">
                  <p className="font-semibold text-blue-900 dark:text-blue-100">Query Type Framework</p>
                  <p className="text-sm text-blue-800 dark:text-blue-200 mt-1">
                    Added structured analysis to distinguish sequence vs tendency vs scoped questions. Ensures responses match the question type coaching staff asked.
                  </p>
                </div>

                <div className="p-4 border-l-4 border-green-500 bg-green-50 dark:bg-green-950/20 rounded-r-lg">
                  <p className="font-semibold text-green-900 dark:text-green-100">Scope Detection Rules</p>
                  <p className="text-sm text-green-800 dark:text-green-200 mt-1">
                    Added explicit instructions to filter data to requested scope (red zone, 3rd down, etc.). Prevents using all-field data for scoped queries.
                  </p>
                </div>

                <div className="p-4 border-l-4 border-purple-500 bg-purple-50 dark:bg-purple-950/20 rounded-r-lg">
                  <p className="font-semibold text-purple-900 dark:text-purple-100">Multi-Part Question Handling</p>
                  <p className="text-sm text-purple-800 dark:text-purple-200 mt-1">
                    Added requirements to address all parts of multi-part questions. Quality constrained by weakest sub-answer—no partial credit.
                  </p>
                </div>

                <div className="p-4 border-l-4 border-orange-500 bg-orange-50 dark:bg-orange-950/20 rounded-r-lg">
                  <p className="font-semibold text-orange-900 dark:text-orange-100">Actionability Requirements</p>
                  <p className="text-sm text-orange-800 dark:text-orange-200 mt-1">
                    Emphasized specific defensive adjustments (coverage calls, pressure schemes, personnel) vs. generic coaching platitudes.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Next Steps */}
          <Card className="border-blue-200 bg-blue-50/30 dark:border-blue-800 dark:bg-blue-950/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
                <ArrowRight className="h-5 w-5" />
                Next: Deploy and Monitor
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-blue-900/90 dark:text-blue-100/90">
              <p>
                With an optimized prompt that performs 18% better on coaching-aligned judges, you're ready to:
              </p>
              <ol className="list-decimal pl-6 space-y-2">
                <li>
                  <strong>Register to Prompt Registry:</strong> Save the optimized prompt as a new version with metadata about the optimization
                </li>
                <li>
                  <strong>A/B test in staging:</strong> Compare optimized vs. baseline on fresh traces before full rollout
                </li>
                <li>
                  <strong>Promote to production:</strong> Deploy when A/B testing confirms improvement
                </li>
                <li>
                  <strong>Continue the loop:</strong> As you collect more coach feedback, re-run GEPA to keep improving
                </li>
              </ol>
              <p className="pt-2 font-medium">
                This creates a self-improving system: expert feedback → aligned judges → optimized prompts → better outputs → more expert feedback.
              </p>
            </CardContent>
          </Card>
        </>
      )}

      {/* Call to Action */}
      {!hasOptimized && !isOptimizing && (
        <Card className="border-blue-200 bg-blue-50/30 dark:border-blue-800 dark:bg-blue-950/20">
          <CardContent className="pt-6 text-center">
            <p className="text-sm text-muted-foreground mb-2">
              Click "Run GEPA Optimization" above to see how automatic prompt optimization works
            </p>
            <p className="text-xs text-muted-foreground">
              The demo will simulate GEPA testing ~67 candidate prompts and show you the optimized result
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );

  return (
    <StepLayout
      title="Optimize Prompts with GEPA"
      description="Automatically improve prompts using Generalized Preference Alignment guided by coaching-aligned judges"
      intro={introSection}
      codeSection={codeSection}
      demoSection={demoSection}
    />
  );
}
