import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Send, ExternalLink, CheckCircle2, ThumbsUp, ThumbsDown } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { EmailService } from "@/fastapi_client";

// NFL Teams
const NFL_TEAMS = [
  "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills",
  "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns",
  "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers",
  "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs",
  "Las Vegas Raiders", "Los Angeles Chargers", "Los Angeles Rams", "Miami Dolphins",
  "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants",
  "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "San Francisco 49ers",
  "Seattle Seahawks", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders"
];

// Analysis types with their specific parameters
const ANALYSIS_TYPES = [
  {
    id: "3rd-down",
    label: "3rd Down Analysis",
    tool: "who_got_ball_by_down_distance",
    parameters: ["distance"],
    options: { distance: ["short", "medium", "long"] }
  },
  {
    id: "red-zone",
    label: "Red Zone Tendencies",
    tool: "red_zone_tendencies",
    parameters: ["zone"],
    options: { zone: ["inside_20", "inside_10", "goal_to_go"] }
  },
  {
    id: "personnel",
    label: "Personnel Packages",
    tool: "tendencies_by_personnel",
    parameters: ["package"],
    options: { package: ["11", "12", "21", "10", "13"] }
  },
  {
    id: "pass-rush",
    label: "Pass Rush & Coverage",
    tool: "success_by_pass_rush_and_coverage",
    parameters: [],
    options: {}
  },
  {
    id: "target-dist",
    label: "Target Distribution",
    tool: "target_share_by_down",
    parameters: ["down"],
    options: { down: ["1st", "2nd", "3rd", "any"] }
  },
  {
    id: "screen-plays",
    label: "Screen Play Tendencies",
    tool: "screen_play_tendencies",
    parameters: [],
    options: {}
  },
];

interface ToolCall {
  tool: string;
  arguments: Record<string, any>;
  status: "pending" | "success" | "error";
  result?: string;
}

interface DcTracingDemoProps {
  onTraceGenerated?: (traceId: string) => void;
}

export function DcTracingDemo({ onTraceGenerated }: DcTracingDemoProps = {}) {
  const [selectedTeam, setSelectedTeam] = useState("");
  const [selectedSeasons, setSelectedSeasons] = useState<string[]>(["2024"]);
  const [selectedAnalysisType, setSelectedAnalysisType] = useState("");
  const [parameters, setParameters] = useState<Record<string, string>>({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [currentTraceId, setCurrentTraceId] = useState<string | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<"up" | "down" | null>(null);
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const selectedAnalysis = ANALYSIS_TYPES.find(a => a.id === selectedAnalysisType);

  const handleAnalysisTypeChange = (type: string) => {
    setSelectedAnalysisType(type);
    setParameters({});
  };

  // Generate question text based on selections
  const generateQuestionText = (): string => {
    if (!selectedTeam || !selectedAnalysisType) {
      return "Select team and analysis type to generate question...";
    }

    const seasonText = selectedSeasons.length > 0
      ? selectedSeasons.length === 1
        ? `in ${selectedSeasons[0]}`
        : `in ${selectedSeasons.join(" and ")}`
      : "";

    switch (selectedAnalysisType) {
      case "3rd-down":
        const distance = parameters.distance || "medium";
        return `What do the ${selectedTeam} do on 3rd and ${distance} ${seasonText}?`;
      case "red-zone":
        const zone = parameters.zone || "inside_20";
        const zoneText = zone === "inside_20" ? "inside the 20"
          : zone === "inside_10" ? "inside the 10"
          : "on goal-to-go";
        return `What are the ${selectedTeam}'s tendencies ${zoneText} ${seasonText}?`;
      case "personnel":
        const pkg = parameters.package || "11";
        return `What does the ${selectedTeam}'s ${pkg} personnel package look like ${seasonText}?`;
      case "pass-rush":
        return `How do the ${selectedTeam} attack the blitz ${seasonText}?`;
      case "target-dist":
        const down = parameters.down || "3rd";
        return `Who gets the ball for the ${selectedTeam} on ${down} down ${seasonText}?`;
      case "screen-plays":
        return `What are the ${selectedTeam}'s screen play tendencies ${seasonText}?`;
      default:
        return "Select analysis type to generate question...";
    }
  };

  const questionText = generateQuestionText();

  const handleAnalyze = async () => {
    if (!selectedTeam || !selectedAnalysisType) {
      setError("Please select a team and analysis type");
      return;
    }

    setLoading(true);
    setIsStreaming(true);
    setError(null);
    setStreamingContent("");
    setToolCalls([]);
    setCurrentTraceId(null);
    setFeedbackRating(null);
    setFeedbackComment("");
    setFeedbackSubmitted(false);

    const requestData = {
      question: questionText  // Use the generated question text
    };

    try {
      const response = await fetch('/api/dc-assistant/analyze-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = "";

      if (!reader) {
        throw new Error("No response body");
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === "token") {
                accumulatedContent += data.content;
                setStreamingContent(accumulatedContent);
              } else if (data.type === "tool_call") {
                // Add tool call to the list
                const toolCall: ToolCall = {
                  tool: data.tool.function_name || "Unknown",
                  arguments: data.tool.arguments ? JSON.parse(data.tool.arguments) : {},
                  status: "success"
                };
                setToolCalls(prev => [...prev, toolCall]);
              } else if (data.type === "done" && data.trace_id) {
                setCurrentTraceId(data.trace_id);
                // Process any tool calls from the done event
                if (data.tool_calls && Array.isArray(data.tool_calls)) {
                  const calls = data.tool_calls.map((tc: any) => ({
                    tool: tc.function_name || "Unknown",
                    arguments: tc.arguments ? JSON.parse(tc.arguments) : {},
                    status: "success" as const
                  }));
                  setToolCalls(calls);
                }
              } else if (data.type === "error") {
                setError(data.error);
                setToolCalls(prev => prev.map(tc => ({ ...tc, status: "error" as const })));
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e);
            }
          }
        }
      }
    } catch (err: any) {
      console.error("Error analyzing:", err);
      setError(err.message || "Failed to analyze");
      setToolCalls(prev => prev.map(tc => ({ ...tc, status: "error" as const })));
    } finally {
      setLoading(false);
      setIsStreaming(false);
    }
  };

  const handleFeedbackSubmit = async () => {
    if (!feedbackRating || !currentTraceId) return;

    try {
      const feedbackData = {
        trace_id: currentTraceId,
        rating: feedbackRating,
        comment: feedbackComment || undefined,
        sales_rep_name: "Coach",  // Could be dynamic based on user
      };

      const response = await EmailService.submitFeedbackApiFeedbackPost(feedbackData);

      if (response.success) {
        setFeedbackSubmitted(true);
      } else {
        setError(response.message);
      }
    } catch (err) {
      console.error("Error submitting feedback:", err);
      setError("Failed to submit feedback");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left Panel - Question Configuration */}
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Question Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Team Selector */}
            <div className="space-y-2">
              <Label htmlFor="team">Team</Label>
              <Select value={selectedTeam} onValueChange={setSelectedTeam}>
                <SelectTrigger>
                  <SelectValue placeholder="Select NFL team..." />
                </SelectTrigger>
                <SelectContent>
                  {NFL_TEAMS.map((team) => (
                    <SelectItem key={team} value={team}>
                      {team}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Season Selector */}
            <div className="space-y-2">
              <Label htmlFor="season">Season</Label>
              <div className="flex gap-2">
                <Button
                  variant={selectedSeasons.includes("2023") ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    if (selectedSeasons.includes("2023")) {
                      setSelectedSeasons(prev => prev.filter(s => s !== "2023"));
                    } else {
                      setSelectedSeasons(prev => [...prev, "2023"]);
                    }
                  }}
                >
                  2023
                </Button>
                <Button
                  variant={selectedSeasons.includes("2024") ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    if (selectedSeasons.includes("2024")) {
                      setSelectedSeasons(prev => prev.filter(s => s !== "2024"));
                    } else {
                      setSelectedSeasons(prev => [...prev, "2024"]);
                    }
                  }}
                >
                  2024
                </Button>
              </div>
            </div>

            {/* Analysis Type */}
            <div className="space-y-2">
              <Label htmlFor="analysis-type">Analysis Type</Label>
              <Select value={selectedAnalysisType} onValueChange={handleAnalysisTypeChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select analysis type..." />
                </SelectTrigger>
                <SelectContent>
                  {ANALYSIS_TYPES.map((type) => (
                    <SelectItem key={type.id} value={type.id}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedAnalysis && (
                <p className="text-xs text-muted-foreground">
                  UC Tool: <code className="bg-muted px-1 py-0.5 rounded">{selectedAnalysis.tool}</code>
                </p>
              )}
            </div>

            {/* Dynamic Parameters */}
            {selectedAnalysis && selectedAnalysis.parameters.map((param) => (
              <div key={param} className="space-y-2">
                <Label htmlFor={param}>{param.charAt(0).toUpperCase() + param.slice(1)}</Label>
                <Select
                  value={parameters[param] || ""}
                  onValueChange={(value) => setParameters(prev => ({ ...prev, [param]: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={`Select ${param}...`} />
                  </SelectTrigger>
                  <SelectContent>
                    {selectedAnalysis.options[param]?.map((option: string) => (
                      <SelectItem key={option} value={option}>
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}

            {/* Generated Question Display */}
            {selectedTeam && selectedAnalysisType && (
              <div className="p-4 bg-blue-50 dark:bg-blue-950/30 rounded-lg border border-blue-200 dark:border-blue-800">
                <Label className="text-xs text-blue-600 dark:text-blue-400 font-semibold mb-2 block">
                  Question to Agent
                </Label>
                <p className="text-sm text-blue-900 dark:text-blue-100 italic">
                  "{questionText}"
                </p>
              </div>
            )}

            <Button
              onClick={handleAnalyze}
              disabled={loading || !selectedTeam || !selectedAnalysisType}
              className="w-full"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Analyze
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      {/* Right Panel - Generated Response */}
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Generated Response</CardTitle>
          </CardHeader>
          <CardContent>
            {toolCalls.length > 0 && (
              <div className="mb-4 p-3 bg-muted/50 rounded-lg space-y-2">
                <p className="text-xs font-semibold text-muted-foreground mb-2">Tool Calls</p>
                {toolCalls.map((call, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 className={`h-4 w-4 mt-0.5 ${
                      call.status === "success" ? "text-green-600" :
                      call.status === "error" ? "text-red-600" :
                      "text-yellow-600 animate-pulse"
                    }`} />
                    <div className="flex-1">
                      <code className="text-xs bg-background px-1.5 py-0.5 rounded">
                        {call.tool}
                      </code>
                      <div className="text-xs text-muted-foreground mt-1">
                        {Object.entries(call.arguments).map(([k, v]) => (
                          <div key={k}>
                            {k}: {Array.isArray(v) ? `[${v.join(", ")}]` : JSON.stringify(v)}
                          </div>
                        ))}
                      </div>
                    </div>
                    <Badge variant={call.status === "success" ? "default" : "secondary"}>
                      {call.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}

            {isStreaming || streamingContent ? (
              <div className="space-y-4">
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <pre className="whitespace-pre-wrap font-sans text-sm">
                    {isStreaming ? streamingContent : streamingContent}
                  </pre>
                </div>

                {currentTraceId && (
                  <div className="pt-4 border-t space-y-4">
                    {/* Trace Link */}
                    <div>
                      <Label className="text-xs text-muted-foreground">
                        MLflow Trace
                      </Label>
                      <div className="mt-2 flex items-center gap-2">
                        <code className="text-xs bg-muted px-2 py-1 rounded flex-1 truncate">
                          {currentTraceId}
                        </code>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const experimentId = process.env.MLFLOW_EXPERIMENT_ID || '2517718719552044';
                            const traceUrl = `https://e2-demo-field-eng.cloud.databricks.com/ml/experiments/${experimentId}/traces?o=1444828305810485&sqlWarehouseId=4b9b953939869799&selectedEvaluationId=${currentTraceId}`;
                            window.open(traceUrl, '_blank');
                          }}
                        >
                          <ExternalLink className="h-3 w-3 mr-1" />
                          View Trace
                        </Button>
                      </div>
                    </div>

                    {/* Feedback Section */}
                    {!feedbackSubmitted && (
                      <div className="space-y-3">
                        <Label className="text-xs text-muted-foreground">
                          Submit Coaching Feedback
                        </Label>
                        <div className="flex items-center gap-2">
                          <Button
                            variant={feedbackRating === "up" ? "default" : "outline"}
                            size="sm"
                            onClick={() => setFeedbackRating("up")}
                          >
                            <ThumbsUp className="h-4 w-4" />
                          </Button>
                          <Button
                            variant={feedbackRating === "down" ? "default" : "outline"}
                            size="sm"
                            onClick={() => setFeedbackRating("down")}
                          >
                            <ThumbsDown className="h-4 w-4" />
                          </Button>
                        </div>
                        <Textarea
                          placeholder="Optional: Add your coaching feedback..."
                          value={feedbackComment}
                          onChange={(e) => setFeedbackComment(e.target.value)}
                          className="min-h-[80px]"
                        />
                        <Button
                          onClick={handleFeedbackSubmit}
                          disabled={!feedbackRating}
                          size="sm"
                        >
                          Submit Feedback
                        </Button>
                      </div>
                    )}

                    {feedbackSubmitted && (
                      <Alert>
                        <AlertDescription>
                          ✓ Feedback submitted successfully
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <p>Configure your question and click Analyze to see the agent in action</p>
                <p className="text-xs mt-2">Tool calls and streaming response will appear here</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
