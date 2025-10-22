import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Sprout, Droplet, Thermometer } from "lucide-react";

interface StressDriver {
  name: string;
  severity: "low" | "medium" | "high";
  value: number;
  icon: typeof Sprout;
}

interface StressDriversProps {
  drivers?: StressDriver[];
}

export default function StressDrivers({ drivers }: StressDriversProps) {
  // TODO: Replace with real stress driver data from Vertex AI model
  const defaultDrivers: StressDriver[] = [
    { name: "Low Vegetation", severity: "medium", value: 45, icon: Sprout },
    { name: "Water Deficiency", severity: "high", value: 72, icon: Droplet },
    { name: "Heat Stress", severity: "low", value: 28, icon: Thermometer },
  ];

  const driverData = drivers || defaultDrivers;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "low": return "text-green-600";
      case "medium": return "text-orange-600";
      case "high": return "text-red-600";
      default: return "text-gray-600";
    }
  };

  const getProgressColor = (severity: string) => {
    switch (severity) {
      case "low": return "[&>div]:bg-green-600";
      case "medium": return "[&>div]:bg-orange-600";
      case "high": return "[&>div]:bg-red-600";
      default: return "";
    }
  };

  return (
    <Card className="p-6" data-testid="card-stress-drivers">
      <h3 className="font-semibold mb-4">Stress Drivers</h3>
      <div className="space-y-6">
        {driverData.map((driver, index) => {
          const Icon = driver.icon;
          return (
            <div key={index} data-testid={`driver-${driver.name.toLowerCase().replace(/\s/g, '-')}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium">{driver.name}</span>
                </div>
                <span className={`text-sm font-semibold ${getSeverityColor(driver.severity)}`}>
                  {driver.severity.charAt(0).toUpperCase() + driver.severity.slice(1)}
                </span>
              </div>
              <Progress value={driver.value} className={getProgressColor(driver.severity)} />
            </div>
          );
        })}
      </div>
    </Card>
  );
}
