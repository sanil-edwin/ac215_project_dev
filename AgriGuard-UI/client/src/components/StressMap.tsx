import { Card } from "@/components/ui/card";
import { useEffect, useRef } from "react";

interface StressMapProps {
  className?: string;
}

export default function StressMap({ className }: StressMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const L = (window as any).L;
    if (!L) return;

    const map = L.map(mapRef.current).setView([42.0, -93.5], 10);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // TODO: Replace with real GCP field boundary data
    // Sample field boundaries (replace with your GeoJSON from GCP)
    const fieldBoundary = L.polygon([
      [42.01, -93.51],
      [42.01, -93.49],
      [42.03, -93.49],
      [42.03, -93.51]
    ], {
      color: '#2E7D32',
      weight: 2,
      fillOpacity: 0
    }).addTo(map);

    // TODO: Replace with stress zone data from Vertex AI model
    // Sample stress zones (replace with real model predictions)
    const severeLayers = [
      { coords: [[42.011, -93.505], [42.011, -93.495], [42.015, -93.495], [42.015, -93.505]], severity: 'severe' },
      { coords: [[42.020, -93.502], [42.020, -93.498], [42.024, -93.498], [42.024, -93.502]], severity: 'moderate' },
      { coords: [[42.025, -93.500], [42.025, -93.492], [42.029, -93.492], [42.029, -93.500]], severity: 'mild' }
    ];

    severeLayers.forEach(zone => {
      const color = zone.severity === 'severe' ? '#D32F2F' : 
                    zone.severity === 'moderate' ? '#FF9800' : '#FFE082';
      L.polygon(zone.coords, {
        color: color,
        fillColor: color,
        fillOpacity: 0.4,
        weight: 1
      }).addTo(map).bindPopup(`${zone.severity.charAt(0).toUpperCase() + zone.severity.slice(1)} Stress Zone`);
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  return (
    <Card className={`overflow-hidden ${className}`} data-testid="card-stress-map">
      <div className="p-4 border-b">
        <h3 className="font-semibold">Field Stress Detection</h3>
        <p className="text-sm text-muted-foreground">Real-time stress zones</p>
      </div>
      <div ref={mapRef} className="w-full h-[400px]" data-testid="map-stress-detection" />
      <div className="p-4 flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#FFE082' }}></div>
          <span>Mild</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#FF9800' }}></div>
          <span>Moderate</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#D32F2F' }}></div>
          <span>Severe</span>
        </div>
      </div>
    </Card>
  );
}
