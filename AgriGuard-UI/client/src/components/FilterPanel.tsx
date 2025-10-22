import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon } from "lucide-react";
import { format } from "date-fns";
import { useState } from "react";

interface FilterPanelProps {
  onFilterChange?: (filters: { county: string; field: string; dateRange: { from?: Date; to?: Date } }) => void;
}

export default function FilterPanel({ onFilterChange }: FilterPanelProps) {
  const [county, setCounty] = useState("Story County");
  const [field, setField] = useState("North Field A");
  const [dateRange, setDateRange] = useState<{ from?: Date; to?: Date }>({
    from: new Date(2024, 4, 1),
    to: new Date(2024, 5, 12)
  });

  const handleApply = () => {
    onFilterChange?.({ county, field, dateRange });
    console.log('Filters applied:', { county, field, dateRange });
  };

  const handleReset = () => {
    setCounty("Story County");
    setField("North Field A");
    setDateRange({ from: new Date(2024, 4, 1), to: new Date(2024, 5, 12) });
    console.log('Filters reset');
  };

  return (
    <Card className="p-6" data-testid="card-filter-panel">
      <h3 className="font-semibold mb-4">Filters</h3>
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium mb-2 block">County</label>
          <Select value={county} onValueChange={setCounty}>
            <SelectTrigger data-testid="select-county">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Story County">Story County</SelectItem>
              <SelectItem value="Polk County">Polk County</SelectItem>
              <SelectItem value="Dallas County">Dallas County</SelectItem>
              <SelectItem value="Boone County">Boone County</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">Field</label>
          <Select value={field} onValueChange={setField}>
            <SelectTrigger data-testid="select-field">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="North Field A">North Field A</SelectItem>
              <SelectItem value="North Field B">North Field B</SelectItem>
              <SelectItem value="South Field A">South Field A</SelectItem>
              <SelectItem value="East Field">East Field</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <label className="text-sm font-medium mb-2 block">Date Range</label>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="w-full justify-start text-left" data-testid="button-date-range">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {dateRange.from && dateRange.to ? (
                  `${format(dateRange.from, "MMM d")} - ${format(dateRange.to, "MMM d, yyyy")}`
                ) : (
                  "Select date range"
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="range"
                selected={{ from: dateRange.from, to: dateRange.to }}
                onSelect={(range) => setDateRange(range || {})}
                numberOfMonths={2}
              />
            </PopoverContent>
          </Popover>
        </div>

        <div className="flex gap-2 pt-2">
          <Button onClick={handleApply} className="flex-1" data-testid="button-apply-filters">Apply</Button>
          <Button onClick={handleReset} variant="outline" data-testid="button-reset-filters">Reset</Button>
        </div>
      </div>
    </Card>
  );
}
