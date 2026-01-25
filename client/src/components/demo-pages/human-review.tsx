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
import {
  ExternalLink,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Shield,
  BarChart3,
  Clock,
  RefreshCw,
  Eye,
  Bell,
} from "lucide-react";
import { useQueryExperiment } from "@/queries/useQueryTracing";

const introContent = `
# Production Monitoring: Closing the Continuous Improvement Loop

You've built a complete quality system:
- ✅ Custom judges aligned to coaching expertise
- ✅ Optimized prompts from GEPA
- ✅ Labeled datasets from SME feedback

Now you need **continuous monitoring** to ensure quality stays high in production and to detect when it's time to iterate.

## Why Production Monitoring Matters

Deploying an optimized GenAI application isn't the end—it's the beginning of ongoing quality management:

### The Challenges
- **Quality drift**: Performance degrades over time as usage patterns change
- **New edge cases**: Production traffic reveals scenarios not covered in training data
- **Silent failures**: Bad outputs that don't crash but provide poor value
- **Scale**: Manual spot-checking doesn't scale to thousands of daily interactions
- **Feedback delay**: By the time users complain, you've served many bad responses

### What You Need
- **Automated quality scoring** on every production trace
- **Trend analysis** to detect gradual degradation before users notice
- **Alerting** when quality drops below thresholds
- **Root cause analysis** to understand why failures happen
- **Continuous loop** back to labeling/optimization when issues emerge

## Databricks Lakehouse Monitoring (Beta)

Databricks provides **Lakehouse Monitoring** for production GenAI traces. This beta feature enables:

### 1. **Automated Judge Evaluation on Production Traces**
- Your aligned judges run automatically on production traffic
- Smart sampling reduces cost (e.g., 10% of traces vs 100%)
- Quality scores stored with traces for analysis
- No additional inference infrastructure required

### 2. **Quality Dashboards & Analytics**
- Pre-built dashboards showing judge score trends over time
- Breakdown by judge dimension (football_language, data_grounded, etc.)
- Cohort analysis (performance by question type, time of day, user, etc.)
- Drill-down into failing traces for investigation

### 3. **Drift Detection & Alerting**
- Statistical tests for quality distribution changes
- Alerts when scores drop below historical baselines
- Configurable notification channels (email, Slack, PagerDuty)
- Early warning before users notice issues

### 4. **Continuous Feedback Loop**
- Flag low-scoring traces for expert review
- Add to labeling sessions for SME validation
- Re-run judge alignment and prompt optimization
- Close the loop: Monitor → Detect → Label → Align → Optimize → Deploy → Monitor

## How It Works Under the Hood

### Monitoring Infrastructure
\`\`\`
Production Trace → MLflow Tracking → Inference Table (Delta)
                                            ↓
                                   Lakehouse Monitor
                                            ↓
                          ┌─────────────────┴──────────────┐
                          ↓                                ↓
                    Profile Metrics                  Drift Metrics
                 (judge score stats)              (distribution changes)
                          ↓                                ↓
                    Monitor Dashboard              Alert Notifications
\`\`\`

### Smart Sampling Strategy
- **Sample rate**: Monitor 10-20% of traces to reduce cost
- **Stratified sampling**: Ensure coverage across question types
- **Priority sampling**: Always score traces with user thumbs-down feedback
- **Adaptive sampling**: Increase rate when drift detected

### Integration with MLflow Workflow
1. Production traces logged to MLflow Tracking
2. Traces written to inference table (Delta Lake)
3. Monitor configured with aligned judges and sampling rate
4. Judges run on sampled traces (async batch jobs)
5. Scores written back to inference table
6. Dashboard reflects updated quality metrics
7. Alerts fire if thresholds breached

## What This Enables

- **Proactive quality management**: Catch degradation before users complain
- **Data-driven optimization**: Know exactly when to re-tune prompts/judges
- **Confidence in production**: Visibility into real-world performance
- **Continuous improvement**: Systematic loop from monitoring → labeling → optimization
`;

const setupMonitoringCode = `import mlflow
from databricks import lakehouse_monitoring as lm
from mlflow.genai.scorers import get_scorer

# Get your production inference table (Delta table with traces)
INFERENCE_TABLE = f"{UC_CATALOG}.{UC_SCHEMA}.dc_assistant_inference_logs"

# Load aligned judges to run on production traces
football_language_judge = get_scorer("football_language_aligned")
data_grounded_judge = get_scorer("data_grounded_aligned")
strategic_soundness_judge = get_scorer("strategic_soundness_aligned")

# Configure Lakehouse Monitor for production traces
monitor = lm.create_monitor(
    table_name=INFERENCE_TABLE,
    profile_type=lm.InferenceLog(
        timestamp_col="timestamp",
        model_id_col="model_id",
        prediction_col="response",
        problem_type="llm/v1/chat",  # GenAI chat application
        label_col=None  # No ground truth in production (yet)
    ),
    baseline_table_name=None,  # Use historical data as baseline
    slicing_exprs=["question_type", "hour_of_day"],  # Analyze by cohorts
    custom_metrics=[
        # Run aligned judges on production traces
        lm.Metric(
            type="aggregate",
            name="avg_football_language_score",
            definition=f"AVG({football_language_judge.name})"
        ),
        lm.Metric(
            type="aggregate",
            name="avg_data_grounded_score",
            definition=f"AVG({data_grounded_judge.name})"
        ),
        lm.Metric(
            type="aggregate",
            name="avg_strategic_soundness",
            definition=f"AVG({strategic_soundness_judge.name})"
        ),
        # Track failure rate (low-scoring traces)
        lm.Metric(
            type="aggregate",
            name="failure_rate",
            definition=f"AVG(CASE WHEN {football_language_judge.name} < 0.5 THEN 1 ELSE 0 END)"
        )
    ],
    # Smart sampling: only score 15% of traces to reduce cost
    sample_percent=15,
    # Schedule: run monitoring every 6 hours
    schedule=lm.MonitorCronSchedule(
        quartz_cron_expression="0 0 */6 * * ?",  # Every 6 hours
        timezone_id="America/Los_Angeles"
    )
)

print(f"✅ Created Lakehouse Monitor: {monitor.monitor_id}")
print(f"📊 Dashboard URL: {monitor.dashboard_url}")`;

const configureAlertsCode = `from databricks.lakehouse_monitoring import Alert, AlertCondition

# Configure alerts for quality degradation
alerts = [
    Alert(
        name="football_language_degradation",
        condition=AlertCondition(
            metric="avg_football_language_score",
            op="<",  # Alert when score drops below
            threshold=0.65,  # 65% threshold (was 80% after optimization)
            lookback_days=7  # Compare to 7-day average
        ),
        actions=[
            lm.EmailAction(to=["dc-assistant-team@company.com"]),
            lm.SlackAction(channel="#dc-assistant-alerts")
        ],
        message="⚠️ Football language judge scores have degraded. Review recent traces and consider re-running prompt optimization."
    ),

    Alert(
        name="high_failure_rate",
        condition=AlertCondition(
            metric="failure_rate",
            op=">",
            threshold=0.10,  # Alert if >10% of traces score below 0.5
            lookback_days=1
        ),
        actions=[
            lm.PagerDutyAction(integration_key="<key>"),
            lm.EmailAction(to=["oncall@company.com"])
        ],
        severity="critical",
        message="🚨 CRITICAL: High failure rate detected. Immediate investigation required."
    ),

    Alert(
        name="drift_detected",
        condition=AlertCondition(
            metric="avg_strategic_soundness",
            op="drift",  # Statistical drift detection
            threshold=0.05,  # p-value threshold
            lookback_days=14  # Compare to 2-week baseline
        ),
        actions=[
            lm.EmailAction(to=["ml-team@company.com"])
        ],
        message="📊 Quality distribution drift detected. Consider collecting new labeled data and re-aligning judges."
    )
]

# Add alerts to monitor
for alert in alerts:
    monitor.add_alert(alert)
    print(f"✅ Configured alert: {alert.name}")`;

const analyzeMonitoringDataCode = `import pandas as pd
from databricks import sql

# Query monitoring metrics from Lakehouse Monitor
# (Monitor stores metrics in Delta tables for analysis)

# Get recent quality trends
quality_trends_query = f"""
SELECT
    DATE(window_start_time) as date,
    AVG(avg_football_language_score) as football_language,
    AVG(avg_data_grounded_score) as data_grounded,
    AVG(avg_strategic_soundness) as strategic_soundness,
    AVG(failure_rate) as failure_rate,
    COUNT(*) as trace_count
FROM {UC_CATALOG}.{UC_SCHEMA}.dc_assistant_monitoring_metrics
WHERE window_start_time >= CURRENT_DATE - INTERVAL 30 DAYS
GROUP BY DATE(window_start_time)
ORDER BY date DESC
"""

quality_df = spark.sql(quality_trends_query).toPandas()

# Identify degradation
baseline_avg = quality_df.iloc[-14:]['football_language'].mean()  # Last 2 weeks
recent_avg = quality_df.iloc[:7]['football_language'].mean()  # Last week

if recent_avg < baseline_avg * 0.95:
    print(f"⚠️  Quality degradation detected!")
    print(f"   Baseline (2 weeks ago): {baseline_avg:.3f}")
    print(f"   Recent (last week): {recent_avg:.3f}")
    print(f"   Change: {((recent_avg - baseline_avg) / baseline_avg * 100):.1f}%")
else:
    print(f"✅ Quality stable")
    print(f"   Recent avg: {recent_avg:.3f}")

# Find failing traces for investigation
failing_traces_query = f"""
SELECT
    trace_id,
    timestamp,
    question,
    response,
    football_language_score,
    data_grounded_score,
    strategic_soundness_score
FROM {INFERENCE_TABLE}
WHERE football_language_score < 0.5
    AND timestamp >= CURRENT_DATE - INTERVAL 7 DAYS
ORDER BY timestamp DESC
LIMIT 20
"""

failing_df = spark.sql(failing_traces_query).toPandas()

print(f"\\n🔍 Found {len(failing_df)} failing traces in last 7 days")
print(f"   Add these to a labeling session for SME review")

# Create labeling session for failing traces
if len(failing_df) > 0:
    failing_trace_ids = failing_df['trace_id'].tolist()

    # Load traces and create labeling session
    failing_traces = mlflow.search_traces(
        filter_string=f"trace_id IN ('{','.join(failing_trace_ids)}')"
    )

    labeling_session = mlflow.genai.create_labeling_session(
        name=f"failing_traces_review_{datetime.now().strftime('%Y%m%d')}",
        label_schemas=["football_language", "data_grounded", "strategic_soundness"],
        traces=failing_traces
    )

    print(f"\\n✅ Created labeling session: {labeling_session.name}")
    print(f"   Share Review App with coaching staff: {labeling_session.url}")
    print(f"   After SME review, re-run judge alignment and prompt optimization")`;

const continuousLoopCode = `# Continuous Improvement Loop Automation

def monitor_and_improve_pipeline():
    """
    Automated pipeline for continuous quality improvement.
    Run this weekly or when alerts fire.
    """

    # 1. Check monitoring metrics for degradation
    metrics = get_monitoring_metrics(days=7)

    if metrics['avg_score'] < QUALITY_THRESHOLD:
        print("📉 Quality degradation detected, starting improvement cycle...")

        # 2. Identify failing traces
        failing_traces = get_failing_traces(
            score_threshold=0.5,
            days=14,
            limit=50
        )

        # 3. Create labeling session for SME review
        session = mlflow.genai.create_labeling_session(
            name=f"degradation_review_{datetime.now().strftime('%Y%m%d')}",
            traces=failing_traces,
            label_schemas=["football_language", "data_grounded", "strategic_soundness"]
        )

        print(f"✅ Labeling session created: {session.url}")
        print(f"   Waiting for SME review...")

        # 4. Wait for labels (or run on schedule after SMEs complete)
        # In practice, this would be a separate scheduled job

        # 5. Re-align judges with new labeled data
        labeled_traces = session.get_labeled_traces()

        for judge_name in ["football_language", "data_grounded", "strategic_soundness"]:
            judge = get_scorer(judge_name)
            aligned_judge = judge.align(
                traces=labeled_traces,
                optimizer=MemAlignOptimizer()
            )
            aligned_judge.register(name=f"{judge_name}_aligned_v{VERSION + 1}")

        print("✅ Judges re-aligned with new feedback")

        # 6. Re-optimize prompts with updated judges
        result = optimize_prompts(
            predict_fn=dc_assistant_predict,
            train_data=labeled_traces,
            prompt_uris=[current_prompt.uri],
            optimizer=GepaPromptOptimizer(),
            scorers=[aligned_football_language, aligned_data_grounded, aligned_strategic]
        )

        if result.best_score > current_score:
            print(f"✅ Prompt improved: {current_score:.3f} → {result.best_score:.3f}")

            # 7. A/B test optimized prompt before full rollout
            ab_test_result = run_ab_test(
                control_prompt=current_prompt,
                treatment_prompt=result.best_prompt,
                duration_days=3,
                traffic_split=0.1  # 10% treatment traffic
            )

            if ab_test_result.treatment_better:
                # 8. Promote to production
                promote_to_production(result.best_prompt)
                print("🚀 New prompt promoted to production")
            else:
                print("⏸️  A/B test failed, keeping current prompt")
        else:
            print("⏸️  Optimization did not improve quality, investigating root cause")

    else:
        print("✅ Quality metrics healthy, no action needed")

# Schedule this pipeline to run weekly
# Or trigger via alerts when degradation detected`;

export function HumanReview() {
  const { data: experiment, isLoading: experimentIsLoading } = useQueryExperiment();

  const [mockMetrics] = React.useState({
    avgFootballLanguage: 0.78,
    avgDataGrounded: 0.82,
    avgStrategicSoundness: 0.75,
    failureRate: 0.08,
    tracesMonitored: 1247,
    alertsActive: 2,
    trendDirection: "stable" as "up" | "down" | "stable",
  });

  const introSection = <MarkdownContent content={introContent} />;

  const codeSection = (
    <div className="space-y-6">
      <CollapsibleSection
        title="1. Configure Lakehouse Monitor for production traces"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/lakehouse-monitoring/"
      >
        <div className="space-y-4">
          <MarkdownContent content="Set up automated monitoring on your production inference table. Configure aligned judges to run on a sample of traces, reducing cost while maintaining quality coverage." />
          <CodeSnippet
            code={setupMonitoringCode}
            title="Create Lakehouse Monitor"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="2. Configure alerts for quality degradation"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/lakehouse-monitoring/alerts"
      >
        <div className="space-y-4">
          <MarkdownContent content="Set up alerts to notify your team when quality drops below thresholds or statistical drift is detected. Integrate with email, Slack, or PagerDuty for timely notifications." />
          <CodeSnippet
            code={configureAlertsCode}
            title="Configure Quality Alerts"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="3. Analyze monitoring data & identify issues"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/lakehouse-monitoring/monitor-output"
      >
        <div className="space-y-4">
          <MarkdownContent content="Query monitoring metrics to analyze trends, identify failing traces, and create labeling sessions for SME review. Metrics are stored in Delta tables for flexible analysis." />
          <CodeSnippet
            code={analyzeMonitoringDataCode}
            title="Analyze Monitoring Metrics"
          />
        </div>
      </CollapsibleSection>

      <CollapsibleSection
        title="4. Automate the continuous improvement loop"
        variant="simple"
        docsUrl="https://docs.databricks.com/aws/en/workflows/"
      >
        <div className="space-y-4">
          <MarkdownContent content="Close the loop by automating the cycle: monitoring detects degradation → failing traces flagged for SME review → judges re-aligned → prompts re-optimized → new version deployed. This creates a self-improving system." />
          <CodeSnippet
            code={continuousLoopCode}
            title="Continuous Improvement Pipeline"
          />
        </div>
      </CollapsibleSection>

      <NotebookReference
        notebookPath="mlflow_demo/notebooks/6_production_monitoring.ipynb"
        notebookName="6_production_monitoring"
        description="Set up Lakehouse Monitoring for continuous quality tracking in production"
      />
    </div>
  );

  const demoSection = (
    <div className="space-y-6">
      <MarkdownContent content="See how production monitoring provides continuous visibility into GenAI quality. This demo shows pre-configured monitoring metrics and alerts for the DC Assistant application." />

      {/* Monitoring Overview */}
      <Card className="border-2 border-blue-200 bg-blue-50/30 dark:border-blue-800 dark:bg-blue-950/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
            <Activity className="h-5 w-5" />
            Production Monitoring Overview
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center p-4 border rounded-lg bg-white dark:bg-gray-900">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Eye className="h-4 w-4 text-blue-600" />
                <div className="text-2xl font-bold text-blue-600">{mockMetrics.tracesMonitored}</div>
              </div>
              <div className="text-xs text-muted-foreground">Traces Monitored (7d)</div>
            </div>

            <div className="text-center p-4 border rounded-lg bg-white dark:bg-gray-900">
              <div className="flex items-center justify-center gap-2 mb-2">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <div className="text-2xl font-bold text-green-600">
                  {(mockMetrics.avgFootballLanguage * 100).toFixed(0)}%
                </div>
              </div>
              <div className="text-xs text-muted-foreground">Avg Football Language</div>
            </div>

            <div className="text-center p-4 border rounded-lg bg-white dark:bg-gray-900">
              <div className="flex items-center justify-center gap-2 mb-2">
                <Shield className="h-4 w-4 text-purple-600" />
                <div className="text-2xl font-bold text-purple-600">
                  {(mockMetrics.avgDataGrounded * 100).toFixed(0)}%
                </div>
              </div>
              <div className="text-xs text-muted-foreground">Avg Data Grounded</div>
            </div>

            <div className="text-center p-4 border rounded-lg bg-white dark:bg-gray-900">
              <div className="flex items-center justify-center gap-2 mb-2">
                <AlertTriangle className="h-4 w-4 text-orange-600" />
                <div className="text-2xl font-bold text-orange-600">
                  {(mockMetrics.failureRate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-xs text-muted-foreground">Failure Rate</div>
            </div>
          </div>

          <div className="p-4 bg-white dark:bg-gray-900 rounded-lg border">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-sm">Quality Trends (30 days)</h4>
              <Badge variant="outline" className="text-green-600 border-green-600">
                {mockMetrics.trendDirection === "up" && <TrendingUp className="h-3 w-3 mr-1" />}
                {mockMetrics.trendDirection === "down" && <TrendingDown className="h-3 w-3 mr-1" />}
                {mockMetrics.trendDirection === "stable" && <Activity className="h-3 w-3 mr-1" />}
                {mockMetrics.trendDirection.toUpperCase()}
              </Badge>
            </div>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Football Language Score</span>
                  <span className="font-medium">{(mockMetrics.avgFootballLanguage * 100).toFixed(0)}%</span>
                </div>
                <Progress value={mockMetrics.avgFootballLanguage * 100} className="h-2" />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Data Grounded Score</span>
                  <span className="font-medium">{(mockMetrics.avgDataGrounded * 100).toFixed(0)}%</span>
                </div>
                <Progress value={mockMetrics.avgDataGrounded * 100} className="h-2 bg-green-100" />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Strategic Soundness Score</span>
                  <span className="font-medium">{(mockMetrics.avgStrategicSoundness * 100).toFixed(0)}%</span>
                </div>
                <Progress value={mockMetrics.avgStrategicSoundness * 100} className="h-2 bg-purple-100" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Active Alerts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Active Alerts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="p-4 border-l-4 border-orange-500 bg-orange-50 dark:bg-orange-950/20 rounded-r-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-semibold text-orange-900 dark:text-orange-100">
                      Football Language Score Degradation
                    </p>
                    <Badge variant="outline" className="text-orange-600">Warning</Badge>
                  </div>
                  <p className="text-sm text-orange-800 dark:text-orange-200 mb-2">
                    Average score dropped to 78% (down from 82% baseline). Review recent traces for incorrect terminology usage.
                  </p>
                  <div className="flex gap-2">
                    <Badge variant="secondary" className="text-xs">
                      <Clock className="h-3 w-3 mr-1" />
                      2 hours ago
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      47 failing traces
                    </Badge>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 border-l-4 border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20 rounded-r-lg">
              <div className="flex items-start gap-3">
                <TrendingDown className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-semibold text-yellow-900 dark:text-yellow-100">
                      Strategic Soundness Drift Detected
                    </p>
                    <Badge variant="outline" className="text-yellow-600">Info</Badge>
                  </div>
                  <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-2">
                    Quality distribution has shifted compared to 14-day baseline (p=0.04). Consider re-collecting labeled data.
                  </p>
                  <div className="flex gap-2">
                    <Badge variant="secondary" className="text-xs">
                      <Clock className="h-3 w-3 mr-1" />
                      1 day ago
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      Statistical drift
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Continuous Improvement Loop */}
      <Card className="border-2 border-green-200 bg-green-50/30 dark:border-green-800 dark:bg-green-950/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-green-900 dark:text-green-100">
            <RefreshCw className="h-5 w-5" />
            The Continuous Improvement Loop
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-green-900/90 dark:text-green-100/90">
            Production monitoring completes the self-improving quality system. When degradation is detected:
          </p>

          <div className="space-y-3">
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center text-sm font-semibold text-green-700 dark:text-green-300 flex-shrink-0">
                1
              </div>
              <div>
                <p className="font-semibold text-sm text-green-900 dark:text-green-100">Monitor Detects Issue</p>
                <p className="text-xs text-green-800 dark:text-green-200">
                  Alerts fire when quality drops or drift occurs
                </p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center text-sm font-semibold text-green-700 dark:text-green-300 flex-shrink-0">
                2
              </div>
              <div>
                <p className="font-semibold text-sm text-green-900 dark:text-green-100">Flag Failing Traces</p>
                <p className="text-xs text-green-800 dark:text-green-200">
                  Low-scoring traces added to labeling session for SME review
                </p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center text-sm font-semibold text-green-700 dark:text-green-300 flex-shrink-0">
                3
              </div>
              <div>
                <p className="font-semibold text-sm text-green-900 dark:text-green-100">Collect Expert Feedback</p>
                <p className="text-xs text-green-800 dark:text-green-200">
                  Coaching staff label traces to provide ground truth
                </p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center text-sm font-semibold text-green-700 dark:text-green-300 flex-shrink-0">
                4
              </div>
              <div>
                <p className="font-semibold text-sm text-green-900 dark:text-green-100">Re-align Judges</p>
                <p className="text-xs text-green-800 dark:text-green-200">
                  Run SIMBA/MemAlign with updated labeled dataset
                </p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center text-sm font-semibold text-green-700 dark:text-green-300 flex-shrink-0">
                5
              </div>
              <div>
                <p className="font-semibold text-sm text-green-900 dark:text-green-100">Re-optimize Prompts</p>
                <p className="text-xs text-green-800 dark:text-green-200">
                  Run GEPA with refined judges to improve prompt
                </p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center text-sm font-semibold text-green-700 dark:text-green-300 flex-shrink-0">
                6
              </div>
              <div>
                <p className="font-semibold text-sm text-green-900 dark:text-green-100">Deploy & Monitor</p>
                <p className="text-xs text-green-800 dark:text-green-200">
                  Promote optimized prompt to production, cycle repeats
                </p>
              </div>
            </div>
          </div>

          <div className="p-3 bg-green-100 dark:bg-green-950/40 rounded-lg border border-green-300 dark:border-green-700 mt-4">
            <p className="text-xs font-semibold text-green-900 dark:text-green-100 mb-1">
              Result: Self-Improving Quality System
            </p>
            <p className="text-xs text-green-800 dark:text-green-200">
              Instead of manual, reactive quality management, you have an automated loop that continuously monitors production, detects issues early, collects expert feedback, and optimizes prompts/judges. Quality improves over time without constant manual intervention.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* View in MLflow UI */}
      <Card>
        <CardHeader>
          <CardTitle>View Monitoring Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Access the Lakehouse Monitoring dashboard to view detailed quality trends, drill into failing traces, and configure additional alerts.
          </p>
          <Button
            variant="open_mlflow_ui"
            size="lg"
            onClick={() =>
              window.open(
                experiment?.monitoring_url || (experimentIsLoading ? "#" : ""),
                "_blank"
              )
            }
          >
            <ExternalLink className="h-4 w-4 mr-2" />
            View Monitoring Dashboard
          </Button>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <StepLayout
      title="Production Monitoring & Continuous Improvement"
      description="Close the loop with automated quality monitoring and continuous optimization"
      intro={introSection}
      codeSection={codeSection}
      demoSection={demoSection}
    />
  );
}
