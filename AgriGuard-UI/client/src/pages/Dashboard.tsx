import { useState } from "react";
import { Leaf, Droplets, Thermometer, Bot, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import MetricCard from "@/components/MetricCard";
import StressMap from "@/components/StressMap";
import TimeSeriesChart from "@/components/TimeSeriesChart";
import StressDrivers from "@/components/StressDrivers";
import YieldForecast from "@/components/YieldForecast";
import CollapsibleFilterPanel from "@/components/CollapsibleFilterPanel";
import AgriBot from "@/components/AgriBot";

export default function Dashboard() {
  const [isChatbotOpen, setIsChatbotOpen] = useState(false);

  // TODO: Replace with real data from GCP data sources
  const metricsData = [
    { title: "NDVI", value: "0.78", unit: "index", trend: 5.2, icon: Leaf },
    { title: "ET", value: "5.3", unit: "mm/day", trend: 2.1, icon: Droplets },
    { title: "LST", value: "28.5", unit: "°C", trend: -1.5, icon: Thermometer },
  ];

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card sticky top-0 z-40">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Leaf className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-semibold" data-testid="text-app-title">AgriGuard</h1>
          </div>
          <div className="flex items-center gap-4">
            <nav className="flex gap-6">
              <Button variant="ghost" data-testid="link-dashboard">Dashboard</Button>
              <Button variant="ghost" data-testid="link-yield">Yield</Button>
              <Button variant="ghost" data-testid="link-reports">Reports</Button>
            </nav>
            <Button 
              onClick={() => setIsChatbotOpen(true)}
              className="gap-2"
              data-testid="button-open-agribot"
            >
              <MessageSquare className="w-4 h-4" />
              AgriBot
              <Badge variant="secondary" className="ml-1">AI</Badge>
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        <CollapsibleFilterPanel />

        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-4">Key Metrics</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {metricsData.map((metric, index) => (
                <MetricCard key={index} {...metric} />
              ))}
            </div>
          </div>

          <StressMap />

          <TimeSeriesChart />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <StressDrivers />
            <YieldForecast />
          </div>
        </div>
      </main>

      <AgriBot isOpen={isChatbotOpen} onClose={() => setIsChatbotOpen(false)} />
    </div>
  );
}
