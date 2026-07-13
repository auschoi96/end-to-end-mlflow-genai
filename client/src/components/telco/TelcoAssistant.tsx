import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import { TelcoChat } from "@/components/telco/TelcoChat";
import { TelcoIntelligentPanel } from "@/components/telco/TelcoIntelligentPanel";
import { TelcoChatMessage } from "@/components/telco/types";
import { getPathFromViewType } from "@/routes";

export function TelcoAssistant() {
  const [activeMessage, setActiveMessage] = useState<TelcoChatMessage | undefined>(
    undefined,
  );
  const navigate = useNavigate();

  return (
    <div className="w-full h-full flex flex-col gap-4 p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Telco Support Agent</h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            A production-style chat agent for telecom customer support — a simple
            example of an agent traced end-to-end by MLflow. For the full
            evaluation, alignment, and prompt optimization lifecycle, see the NFL
            Defensive Coordinator Assistant walkthrough.
          </p>
        </div>
        <Button
          variant="default"
          size="sm"
          onClick={() => navigate(getPathFromViewType("demo-overview"))}
        >
          Try the full MLflow walkthrough
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
        <div className="lg:col-span-8 min-h-0">
          <TelcoChat onActiveMessageChange={setActiveMessage} />
        </div>
        <div className="lg:col-span-4 min-h-0">
          <TelcoIntelligentPanel activeMessage={activeMessage} />
        </div>
      </div>
    </div>
  );
}
