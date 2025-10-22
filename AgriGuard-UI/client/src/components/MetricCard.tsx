import { Card } from "@/components/ui/card";
import { ArrowUp, ArrowDown, LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string;
  unit: string;
  trend: number;
  icon: LucideIcon;
  color?: "success" | "warning" | "error";
}

export default function MetricCard({
  title,
  value,
  unit,
  trend,
  icon: Icon,
  color = "success",
}: MetricCardProps) {
  const isPositive = trend >= 0;
  const trendColor = isPositive ? "text-green-600" : "text-red-600";

  return (
    <Card className="p-6" data-testid={`card-metric-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Icon className="w-5 h-5 text-primary" />
            <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-semibold" data-testid={`text-value-${title.toLowerCase().replace(/\s/g, '-')}`}>
              {value}
            </span>
            <span className="text-lg text-muted-foreground">{unit}</span>
          </div>
        </div>
        <div className={`flex items-center gap-1 text-sm font-medium ${trendColor}`} data-testid={`text-trend-${title.toLowerCase().replace(/\s/g, '-')}`}>
          {isPositive ? (
            <ArrowUp className="w-4 h-4" />
          ) : (
            <ArrowDown className="w-4 h-4" />
          )}
          <span>{Math.abs(trend)}%</span>
        </div>
      </div>
    </Card>
  );
}
