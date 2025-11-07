import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { CalendarIcon, ChevronDown, ChevronUp, Filter } from "lucide-react";
import { format } from "date-fns";
import { useState } from "react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

interface CollapsibleFilterPanelProps {
  onFilterChange?: (filters: { county: string; field: string; dateRange: { from?: Date; to?: Date } }) => void;
}

export default function CollapsibleFilterPanel({ onFilterChange }: CollapsibleFilterPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [county, setCounty] = useState("Story County");
  const [field, setField] = useState("North Field A");
  const [dateRange, setDateRange] = useState<{ from?: Date; to?: Date }>({
    from: new Date(2024, 4, 1),
    to: new Date(2024, 5, 12)
  });

  const handleApply = () => {
    onFilterChange?.({ county, field, dateRange });
    console.log('Filters applied:', { county, field, dateRange });
    setIsOpen(false);
  };

  const handleReset = () => {
    setCounty("Story County");
    setField("North Field A");
    setDateRange({ from: new Date(2024, 4, 1), to: new Date(2024, 5, 12) });
    console.log('Filters reset');
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <Card className="mb-6">
        <CollapsibleTrigger asChild>
          <Button 
            variant="ghost" 
            className="w-full justify-between p-4 h-auto hover-elevate"
            data-testid="button-toggle-filters"
          >
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4" />
              <span className="font-semibold">Filters</span>
              <span className="text-sm text-muted-foreground">
                {county} • {field} • {dateRange.from && format(dateRange.from, "MMM d")} - {dateRange.to && format(dateRange.to, "MMM d")}
              </span>
            </div>
            {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <div className="p-4 pt-0 border-t">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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

              <div className="flex items-end gap-2">
                <Button onClick={handleApply} className="flex-1" data-testid="button-apply-filters">Apply</Button>
                <Button onClick={handleReset} variant="outline" data-testid="button-reset-filters">Reset</Button>
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}
