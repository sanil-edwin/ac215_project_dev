import { Card } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface TimeSeriesChartProps {
  data?: Array<{ date: string; ndvi: number; et: number; lst: number }>;
}

export default function TimeSeriesChart({ data }: TimeSeriesChartProps) {
  // TODO: Replace with real time series data from GCP data sources
  const defaultData = [
    { date: "May 1", ndvi: 0.65, et: 4.2, lst: 22 },
    { date: "May 8", ndvi: 0.70, et: 4.5, lst: 24 },
    { date: "May 15", ndvi: 0.72, et: 4.8, lst: 26 },
    { date: "May 22", ndvi: 0.75, et: 5.1, lst: 25 },
    { date: "May 29", ndvi: 0.78, et: 5.3, lst: 27 },
    { date: "Jun 5", ndvi: 0.80, et: 5.5, lst: 28 },
    { date: "Jun 12", ndvi: 0.78, et: 5.2, lst: 30 },
  ];

  const chartData = data || defaultData;

  return (
    <Card className="p-6" data-testid="card-time-series">
      <h3 className="font-semibold mb-4">Metric Trends Over Time</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis dataKey="date" className="text-xs" />
          <YAxis className="text-xs" />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px'
            }}
          />
          <Legend />
          <Line type="monotone" dataKey="ndvi" stroke="#2E7D32" strokeWidth={2} name="NDVI" />
          <Line type="monotone" dataKey="et" stroke="#1565C0" strokeWidth={2} name="ET (mm/day)" />
          <Line type="monotone" dataKey="lst" stroke="#FF8F00" strokeWidth={2} name="LST (°C)" />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
