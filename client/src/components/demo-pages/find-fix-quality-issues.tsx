import React from "react";
import { StepLayout } from "@/components/step-layout";
import { CodeSnippet } from "@/components/code-snippet";
import { CollapsibleSection } from "@/components/collapsible-section";
import { MarkdownContent } from "@/components/markdown-content";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ExternalLink, Mail, Plus, UserCheck, BarChart3, Award } from "lucide-react";
import { useQueryPreloadedResults } from "@/queries/useQueryPreloadedResults";
import { NotebookReference } from "@/components/notebook-reference";

const introContent = `
# Collect Ground Truth Labels from Domain Experts

Following up from creating baseline LLM judges, we now need **expert validation** to ensure our automated quality metrics align with real coaching expertise. App developers typically aren't domain experts in the business use case—in this case, NFL defensive strategy—so getting structured feedback from SMEs (coaching staff) is critical for understanding what constitutes a high vs. low quality response.

## The Challenge: Making SME Feedback Scalable and Structured

Getting domain experts to review GenAI outputs requires more than just asking for opinions. You need:
- **A managed interface** that's accessible to non-technical users
- **Seamless integration** with your production tracing data
- **Structured labeling schemas** that capture the specific quality dimensions you care about
- **Consistent workflows** that make it easy for experts to provide feedback at scale

## MLflow Makes This Easy with Labeling Sessions

MLflow's **Labeling Sessions** provide a complete solution for collecting expert feedback:

1. **Flexible Schema Configuration** - Define exactly what information you want to collect for each trace (yes/no questions, ratings, categorical choices, free-text comments)
2. **Pre-built Review App UI** - Business users get a polished interface designed specifically for reviewing GenAI traces—no Databricks workspace access required
3. **Direct Trace Integration** - Sessions automatically pull in trace details, inputs, outputs, and tool calls for expert review
4. **Collaborative Workflows** - Assign specific reviewers, track progress, and aggregate feedback across multiple experts
5. **Programmatic Access** - Labels are stored in MLflow and can be exported as evaluation datasets to refine judges and benchmark quality

This creates a seamless feedback loop: **Traces → Labeling Sessions → Expert Review → Judge Refinement → Improved Quality**

![human-feedback-overview](https://i.imgur.com/7LNlgDP.gif)
`;

const createLabelingSchemasCode = `import mlflow
from mlflow.genai import label_schemas
from datetime import datetime

# Define labeling schemas tailored to DC Assistant quality assessment
# These schemas align with our custom LLM judges for consistency
schema_configs = {
    'football_language': {
        'title': 'Does the analysis use correct football terminology?',
        'instruction': '''Evaluate whether the response uses appropriate NFL terminology and coaching language:
        - Correct formation names (I-formation, shotgun, pistol, etc.)
        - Accurate personnel packages (11 = 1 RB, 1 TE, 3 WR; 12 = 1 RB, 2 TE, 2 WR, etc.)
        - Standard coverage/blitz terminology (Cover 2, Cover 3, A-gap pressure, etc.)
        - Proper down-and-distance notation (e.g., "3rd and 6", "2nd and long")

        PASS: All terminology is accurate and appropriate for coaching staff
        FAIL: Contains incorrect terminology or suggests lack of football knowledge''',
        'options': ['pass', 'fail']
    },
    'data_grounded': {
        'title': 'Is the analysis grounded in actual data?',
        'instruction': '''Check whether recommendations are based on real play-by-play data:
        - Analysis references specific percentages or frequency metrics from data
        - Tendencies are supported by actual statistics from tool call results
        - No hallucinated data that wasn't present in the query results

        PASS: All claims are backed by data shown in the trace
        FAIL: Contains unsupported claims or hallucinated statistics''',
        'options': ['pass', 'fail']
    },
    'strategic_soundness': {
        'title': 'Are the defensive recommendations strategically sound?',
        'instruction': '''Assess whether the defensive strategy makes sense for game planning:
        - Recommendations address the specific situation (down-and-distance, personnel, etc.)
        - Counter-strategies are appropriate for the opponent tendencies shown
        - Advice is actionable and specific (not generic coaching platitudes)
        - Key matchups and adjustments are relevant

        Rate from 1 (poor strategy) to 5 (excellent strategy)''',
        'options': ['1', '2', '3', '4', '5']
    },
    'overall_quality': {
        'title': 'Would you trust this analysis for actual game preparation?',
        'instruction': '''As a coaching professional, rate whether this analysis would be useful for preparing a game plan.

        1 = Not usable - contains errors or unhelpful advice
        3 = Acceptable - correct but not particularly insightful
        5 = Excellent - actionable insights that would inform game planning''',
        'options': ['1', '2', '3', '4', '5']
    }
}

# Create label schemas
created_schemas = {}
for schema_name, config in schema_configs.items():
    try:
        # Determine input type based on options
        if all(opt.isdigit() for opt in config['options']):
            input_schema = label_schemas.InputCategorical(
                options=config['options'],
                allow_multiple=False
            )
        else:
            input_schema = label_schemas.InputCategorical(
                options=config['options']
            )

        schema = label_schemas.create_label_schema(
            name=schema_name,
            type='feedback',
            title=config['title'],
            input=input_schema,
            instruction=config['instruction'],
            enable_comment=True,  # Allow reviewers to add contextual notes
            overwrite=True
        )
        created_schemas[schema_name] = schema
        print(f'✅ Created schema: {schema_name}')

    except Exception as e:
        print(f'⚠️  Error creating schema {schema_name}: {e}')

print(f"\\n✅ Created {len(created_schemas)} labeling schemas for DC Assistant review")`

const createLabelingSessionCode = `import mlflow
from datetime import datetime
import uuid

# Create labeling session with descriptive name
schema_names = [schema.name for schema in created_schemas.values()]
session_name = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}-dc_assistant_quality_review'

session = mlflow.genai.create_labeling_session(
    name=session_name,
    assigned_users=[],  # Empty list allows any authenticated user to label
    label_schemas=schema_names
)

print(f'✅ Created labeling session: {session_name}')

# Add production traces that need expert review
# Target traces where LLM judges had low confidence or disagreement
traces_for_review = mlflow.search_traces(
    filter_string="""
        attributes.status = "OK"
        AND tags.sample_data = "yes"
        AND (
            attributes.mlflow.feedback.football_language_score < 0.7
            OR attributes.mlflow.feedback.football_analysis_score < 0.7
        )
    """,
    max_results=20,
    order_by=['attributes.timestamp_ms DESC']
)

# Add traces to the labeling session
if len(traces_for_review) > 0:
    session.add_traces(traces_for_review)
    print(f'✅ Added {len(traces_for_review)} traces to labeling session for expert review')
else:
    print('⚠️  No traces found matching criteria')

# Generate Review App URL for coaching staff
print(f'\\n📱 Share this Review App URL with coaching staff:')
print(f'   {session.url}')
print(f'\\n📊 Track labeling progress in MLflow UI:')
print(f'   {mlflow_ui_url}/experiments/{experiment_id}/traces')`

const analyzeLabelingResultsCode = `import mlflow
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix
import numpy as np

# Retrieve labeling session and extract human labels
session = mlflow.genai.get_labeling_session(session_name)
labeled_traces = session.get_labeled_traces()

print(f"Collected {len(labeled_traces)} labeled traces from coaching staff\\n")

# Convert labels to DataFrame for analysis
label_data = []
for trace in labeled_traces:
    labels = trace.get_labels()  # Get all labels for this trace
    label_data.append({
        'trace_id': trace.trace_id,
        'football_language': labels.get('football_language', {}).get('value'),
        'data_grounded': labels.get('data_grounded', {}).get('value'),
        'strategic_soundness': labels.get('strategic_soundness', {}).get('value'),
        'overall_quality': labels.get('overall_quality', {}).get('value'),
        'comments': labels.get('football_language', {}).get('comment', ''),
    })

labels_df = pd.DataFrame(label_data)

# Compare human labels to LLM judge scores
def compare_judge_to_human(judge_scores_df, human_labels_df, dimension):
    """Calculate agreement between LLM judge and human expert."""

    # Convert to binary for comparison (pass/fail)
    if dimension in ['football_language', 'data_grounded']:
        human_binary = (human_labels_df[dimension] == 'pass').astype(int)
        judge_binary = (judge_scores_df[f'{dimension}_score'] >= 0.7).astype(int)
    else:
        # For rating dimensions (1-5 scale), convert to pass (>=3) / fail (<3)
        human_binary = (human_labels_df[dimension].astype(int) >= 3).astype(int)
        judge_binary = (judge_scores_df[f'{dimension}_score'] >= 0.6).astype(int)

    # Calculate agreement metrics
    kappa = cohen_kappa_score(human_binary, judge_binary)
    accuracy = (human_binary == judge_binary).mean()

    # Confusion matrix
    cm = confusion_matrix(human_binary, judge_binary)

    print(f"\\n{dimension.replace('_', ' ').title()} - Judge vs Human Agreement:")
    print(f"  Cohen's Kappa: {kappa:.3f} ({'good' if kappa >= 0.6 else 'needs improvement'})")
    print(f"  Accuracy: {accuracy:.1%}")
    print(f"  Confusion Matrix:")
    print(f"    {cm}")

    # Identify specific disagreements for investigation
    disagreements = human_labels_df[human_binary != judge_binary]
    if len(disagreements) > 0:
        print(f"  Found {len(disagreements)} disagreements - review these traces to refine judge guidelines")

    return {
        'dimension': dimension,
        'kappa': kappa,
        'accuracy': accuracy,
        'disagreement_count': len(disagreements),
        'disagreement_trace_ids': disagreements['trace_id'].tolist()
    }

# Run comparison for each quality dimension
alignment_results = []
for dimension in ['football_language', 'data_grounded', 'strategic_soundness']:
    result = compare_judge_to_human(judge_scores_df, labels_df, dimension)
    alignment_results.append(result)

# Summary of what needs refinement
print("\\n" + "="*60)
print("JUDGE REFINEMENT PRIORITIES:")
print("="*60)

for result in alignment_results:
    if result['kappa'] < 0.6:
        print(f"\\n⚠️  {result['dimension']}: Low agreement (κ={result['kappa']:.2f})")
        print(f"   → Review {result['disagreement_count']} disagreement cases")
        print(f"   → Refine guidelines to be more specific and measurable")
        print(f"   → Consider adding examples to judge instructions")`

const refineJudgesCode = `import mlflow
from mlflow.genai.scorers import Guidelines

# After reviewing disagreements, refine the judge guidelines
# Example: Refined Football Language judge based on SME feedback

refined_football_language_guidelines = """
## Refined Football Language Assessment

### PASS Criteria (Based on Coaching Staff Feedback):
1. Formation terminology must match standard NFL coaching nomenclature:
   - Correct: "11 personnel", "12 personnel", "21 personnel"
   - Incorrect: "3 WR set", "2 TE package" (use personnel numbers instead)

2. Coverage schemes must use standard terminology:
   - Correct: "Cover 2", "Cover 3 Buzz", "Quarter-Quarter-Half"
   - Incorrect: "Two-deep zone", "Three-deep coverage" (too generic)

3. Down-and-distance must use standard notation:
   - Correct: "3rd and 6", "2nd and long"
   - Incorrect: "third down, six yards to go"

4. Pressure concepts must reference standard coaching terms:
   - Correct: "A-gap pressure", "Mug look", "Fire Zone blitz"
   - Incorrect: "Blitz up the middle", "Show blitz" (not specific enough)

### AUTOMATIC FAIL Criteria:
- Incorrect personnel package numbers (e.g., "13 personnel" doesn't exist)
- Made-up coverage schemes not used in NFL coaching
- Misuse of technical terms (e.g., calling Cover 2 "two-man coverage")
- Generic descriptions instead of standard terminology

### Examples from SME Review:
[Include 2-3 specific examples from labeled traces that illustrate edge cases]
"""

# Create refined judge with updated guidelines
refined_judge = Guidelines(
    name="football_language_refined_v2",
    guidelines=refined_football_language_guidelines
)

# Re-evaluate with refined judge
results = mlflow.genai.evaluate(
    data=evaluation_dataset,
    predict_fn=predict_fn,
    scorers=[refined_judge],
)

print("✅ Re-evaluated with refined judge - check if alignment improved!")`

export function PromptTesting() {
  const { data: preloadedResultsData, isLoading: isPreloadedResultsLoading } =
    useQueryPreloadedResults();
  const preloadedLabelingSessionUrl =
    preloadedResultsData?.sample_labeling_session_url;
  const preloadedReviewAppUrl = preloadedResultsData?.sample_review_app_url;
  const preloadedLabelingTraceUrl =
    preloadedResultsData?.sample_labeling_trace_url;

  const introSection = <MarkdownContent content={introContent} />;

  const codeSection = (
    <div className="space-y-6">
      <CollapsibleSection
        title="1. Create Labeling Schemas"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/human-feedback/expert-feedback/label-existing-traces"
      >
        <div className="space-y-4">
          <MarkdownContent content="Define the specific quality dimensions you want coaching staff to evaluate. Schemas can use yes/no, rating scales, or categorical choices. Align schemas with your LLM judges for direct comparison." />
          <CodeSnippet
            code={createLabelingSchemasCode}
            title="Define Labeling Schemas for DC Assistant"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="2. Create Labeling Session & Add Traces"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/human-feedback/expert-feedback/label-existing-traces"
      >
        <div className="space-y-4">
          <MarkdownContent content="Create a labeling session that groups traces for review. Target traces where judges had low confidence or where you need human validation. The Review App URL can be shared with non-technical SMEs." />
          <CodeSnippet
            code={createLabelingSessionCode}
            title="Create Session and Add Traces"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="3. Analyze Labels & Compare to Judges"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/custom-judge/"
      >
        <div className="space-y-4">
          <MarkdownContent content="Once coaching staff complete their reviews, analyze the labels to identify where LLM judges disagree with human experts. Use Cohen's Kappa and confusion matrices to quantify alignment and find specific traces to investigate." />
          <CodeSnippet
            code={analyzeLabelingResultsCode}
            title="Analyze Human Labels vs Judge Scores"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="4. Refine Judges Based on SME Feedback"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/custom-judge/"
      >
        <div className="space-y-4">
          <MarkdownContent content="Use disagreement cases to refine judge guidelines with more specific criteria, examples, and edge case handling. This iterative process improves judge-human alignment over time." />
          <CodeSnippet
            code={refineJudgesCode}
            title="Refine Judge Guidelines"
          />
        </div>
      </CollapsibleSection>

      <NotebookReference
        notebookPath="mlflow_demo/notebooks/3_collect_ground_truth_labels.ipynb"
        notebookName="3_collect_ground_truth_labels"
        description="Set up labeling sessions and collect structured expert feedback for quality improvement"
      />
    </div>
  );

  const demoSection = (
    <div className="space-y-6">
      <MarkdownContent content="Let's walk through the complete SME feedback workflow. This demo uses pre-configured labeling sessions so you can immediately experience how coaching staff would review DC Assistant traces in the Review App." />

      <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20 mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
            <UserCheck className="h-5 w-5" />
            The SME Review Workflow
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-blue-900/90 dark:text-blue-100/90">
          <p>
            Getting quality feedback from domain experts (coaching staff) follows a systematic workflow:
          </p>
          <ol className="list-decimal pl-6 space-y-2">
            <li>
              <strong>Select traces for review:</strong> Choose production traces where judges had low confidence, user feedback indicated issues, or you need validation
            </li>
            <li>
              <strong>Create labeling session:</strong> Group traces with the quality dimensions (schemas) you want experts to evaluate
            </li>
            <li>
              <strong>Share Review App:</strong> Send the Review App URL to coaching staff—they can access it without Databricks workspace credentials
            </li>
            <li>
              <strong>Experts label traces:</strong> Coaching staff review each trace, answer structured questions, and add contextual comments
            </li>
            <li>
              <strong>Analyze alignment:</strong> Compare human labels to LLM judge scores to find disagreements and calibration issues
            </li>
            <li>
              <strong>Refine judges:</strong> Update judge guidelines based on where they disagree with expert judgment, then re-evaluate
            </li>
          </ol>
          <p className="pt-2">
            This creates a continuous improvement loop where each round of expert feedback makes your automated judges more accurate and aligned with coaching expertise.
          </p>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Step 1: View the trace for labeling
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-3">
            <MarkdownContent content="This trace represents a real DC Assistant interaction that we want coaching staff to review. Examine the trace to see the original question, the defensive analysis generated, tool calls made, and any existing judge scores. This context helps understand what experts will be evaluating." />
            <Button
              variant="open_mlflow_ui"
              size="lg"
              disabled={isPreloadedResultsLoading || !preloadedLabelingTraceUrl}
              onClick={() =>
                preloadedLabelingTraceUrl &&
                window.open(preloadedLabelingTraceUrl, "_blank")
              }
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View trace in MLflow UI
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5" />
              Step 2: View the labeling session configuration
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-3">
            <MarkdownContent content="The labeling session groups multiple traces with the quality dimensions (schemas) we want coaching staff to evaluate. This pre-configured session contains 3 traces and 4 labeling schemas aligned with our custom judges. In the MLflow UI, you can see the session details, track labeling progress, and manage assigned reviewers." />
            <Button
              variant="open_mlflow_ui"
              size="lg"
              disabled={
                isPreloadedResultsLoading || !preloadedLabelingSessionUrl
              }
              onClick={() =>
                preloadedLabelingSessionUrl &&
                window.open(preloadedLabelingSessionUrl, "_blank")
              }
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View the Labeling Session
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCheck className="h-5 w-5" />
              Step 3: Experience the Review App (SME perspective)
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-3">
            <MarkdownContent content="This is the Review App interface that coaching staff would use. It's designed for non-technical users and doesn't require Databricks workspace access. Try labeling a trace yourself to see the workflow: review the question and analysis, evaluate against each quality dimension, add comments with context, and submit. This is the exact experience your SMEs would have." />
            <Button
              variant="open_mlflow_ui"
              size="lg"
              disabled={isPreloadedResultsLoading || !preloadedReviewAppUrl}
              onClick={() =>
                preloadedReviewAppUrl &&
                window.open(preloadedReviewAppUrl, "_blank")
              }
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              Label in the Review App
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Step 4: View collected labels & analyze alignment
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-3">
            <MarkdownContent content="After coaching staff submit their labels, they appear back in the MLflow UI alongside the original traces. This is where you'd analyze judge-human alignment: compare label values to judge scores, identify systematic disagreements, and export labeled traces as evaluation datasets. These insights drive the next iteration of judge refinement." />
            <Button
              variant="open_mlflow_ui"
              size="lg"
              disabled={
                isPreloadedResultsLoading || !preloadedLabelingSessionUrl
              }
              onClick={() =>
                preloadedLabelingSessionUrl &&
                window.open(preloadedLabelingSessionUrl, "_blank")
              }
            >
              <ExternalLink className="h-4 w-4 mr-2" />
              View labels in the MLflow UI
            </Button>
          </CardContent>
        </Card>

        {/* Impact and Next Steps */}
        <Card className="border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20 mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-900 dark:text-green-100">
              <BarChart3 className="h-5 w-5" />
              Impact: Closing the Quality Improvement Loop
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-green-900/90 dark:text-green-100/90">
            <p>
              <strong>With expert labels collected, you've completed the critical feedback loop:</strong>
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
              <div className="border border-green-300 dark:border-green-700 rounded-lg p-3 bg-white/50 dark:bg-gray-900/30">
                <p className="font-semibold mb-2">Immediate Value</p>
                <ul className="list-disc pl-5 space-y-1 text-xs">
                  <li>Identify traces where judges disagree with experts</li>
                  <li>Quantify alignment using Cohen's Kappa and accuracy</li>
                  <li>Surface edge cases your guidelines didn't cover</li>
                  <li>Create ground truth dataset for benchmarking</li>
                </ul>
              </div>
              <div className="border border-green-300 dark:border-green-700 rounded-lg p-3 bg-white/50 dark:bg-gray-900/30">
                <p className="font-semibold mb-2">Long-term Benefits</p>
                <ul className="list-disc pl-5 space-y-1 text-xs">
                  <li>Iteratively improve judge-human alignment</li>
                  <li>Build evaluation datasets versioned in MLflow</li>
                  <li>Track quality improvements over time</li>
                  <li>Scale expert knowledge through automated judges</li>
                </ul>
              </div>
            </div>
            <p className="pt-2 font-medium">
              <strong>Next:</strong> Use the labeled traces to refine your judge guidelines, re-run evaluations, and measure whether alignment improved. This iterative refinement process continues until your automated judges reliably match coaching staff judgment—enabling you to evaluate quality at scale without constant manual review.
            </p>
          </CardContent>
        </Card>

        {/* Best Practices Callout */}
        <Card className="border-purple-200 bg-purple-50/50 dark:border-purple-800 dark:bg-purple-950/20 mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-purple-900 dark:text-purple-100">
              <Award className="h-5 w-5" />
              Best Practices for SME Labeling
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-purple-900/90 dark:text-purple-100/90">
            <ul className="list-disc pl-6 space-y-2">
              <li>
                <strong>Start small:</strong> Begin with 10-20 carefully selected traces rather than overwhelming experts with hundreds
              </li>
              <li>
                <strong>Provide context:</strong> Include clear instructions in schema descriptions explaining what "pass" vs "fail" means with examples
              </li>
              <li>
                <strong>Enable comments:</strong> Always allow free-text comments so experts can explain their reasoning and flag edge cases
              </li>
              <li>
                <strong>Target disagreements:</strong> Prioritize traces where judges had low confidence or where multiple judges disagreed
              </li>
              <li>
                <strong>Multiple reviewers:</strong> For critical quality dimensions, have 2-3 experts label the same traces to measure inter-rater agreement
              </li>
              <li>
                <strong>Iterate quickly:</strong> Don't wait to collect hundreds of labels—analyze after 20-30 traces, refine judges, then continue labeling
              </li>
              <li>
                <strong>Version your datasets:</strong> Export labeled traces as evaluation datasets in MLflow to track quality benchmarks over time
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  return (
    <StepLayout
      title="Collect Ground Truth Labels"
      description="Collect expert feedback to improve GenAI quality through structured labeling"
      intro={introSection}
      codeSection={codeSection}
      demoSection={demoSection}
    />
  );
}
