import React from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Headphones, Trophy, ArrowRight, Check } from "lucide-react";
import { getPathFromViewType } from "@/routes";

export function Landing() {
  const navigate = useNavigate();

  return (
    <div className="w-full h-full flex flex-col">
      <div className="border-b bg-background/95 p-6">
        <h1 className="text-3xl font-bold tracking-tight">MLflow GenAI Demo</h1>
        <p className="text-muted-foreground mt-2">
          Two examples of the same idea — building AI agents you can observe, evaluate, and
          improve with MLflow. Pick where you want to start.
        </p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="grid md:grid-cols-2 gap-6 max-w-4xl w-full">
          <Card className="hover:shadow-md transition-shadow flex flex-col border-t-4 border-t-blue-500">
            <CardHeader>
              <div className="flex items-center justify-between mb-2">
                <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center">
                  <Headphones className="h-6 w-6 text-blue-600" />
                </div>
                <Badge variant="secondary" className="font-normal">
                  ~2 min · single-turn
                </Badge>
              </div>
              <CardTitle>Telco Support Agent</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col">
              <p className="text-muted-foreground mb-4">
                A quick, simple example: chat with a production-style customer support agent
                and see each response traced by MLflow.
              </p>
              <p className="text-xs font-semibold text-muted-foreground mb-2">
                Best if you want:
              </p>
              <ul className="space-y-2 mb-6 flex-1">
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                  <span>A fast look at what tracing actually captures</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                  <span>A live chat interface backed by real Unity Catalog tools</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-blue-600 mt-0.5 shrink-0" />
                  <span>No setup — one conversation, one trace, done</span>
                </li>
              </ul>
              <Button
                onClick={() => navigate(getPathFromViewType("telco"))}
              >
                Start with Telco
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow flex flex-col border-t-4 border-t-orange-500">
            <CardHeader>
              <div className="flex items-center justify-between mb-2">
                <div className="w-12 h-12 rounded-full bg-orange-500/10 flex items-center justify-center">
                  <Trophy className="h-6 w-6 text-orange-600" />
                </div>
                <Badge variant="secondary" className="font-normal">
                  ~15 min · 6-step lifecycle
                </Badge>
              </div>
              <CardTitle>NFL Defensive Coordinator Assistant</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col">
              <p className="text-muted-foreground mb-4">
                The full, detailed walkthrough: tracing, LLM judges, ground-truth labeling,
                judge alignment, and automatic prompt optimization.
              </p>
              <p className="text-xs font-semibold text-muted-foreground mb-2">
                Best if you want:
              </p>
              <ul className="space-y-2 mb-6 flex-1">
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-orange-600 mt-0.5 shrink-0" />
                  <span>MLflow's complete self-optimizing lifecycle, end to end</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-orange-600 mt-0.5 shrink-0" />
                  <span>Multi-modal, multi-tool, and multi-turn tracing examples</span>
                </li>
                <li className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-orange-600 mt-0.5 shrink-0" />
                  <span>How judges get calibrated to expert (coach) feedback and drive prompt gains</span>
                </li>
              </ul>
              <Button
                onClick={() => navigate(getPathFromViewType("demo-overview"))}
              >
                Start the full walkthrough
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
