import React from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const countiesGeoJson = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: { id: "19015", name: "Boone" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-93.9, 42.2],
            [-93.6, 42.2],
            [-93.6, 42.0],
            [-93.9, 42.0],
            [-93.9, 42.2]
          ]
        ]
      }
    },
    {
      type: "Feature",
      properties: { id: "19017", name: "Bremer" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-92.6, 42.9],
            [-92.2, 42.9],
            [-92.2, 42.6],
            [-92.6, 42.6],
            [-92.6, 42.9]
          ]
        ]
      }
    },
    {
      type: "Feature",
      properties: { id: "19021", name: "Carroll" },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-94.9, 42.2],
            [-94.5, 42.2],
            [-94.5, 41.9],
            [-94.9, 41.9],
            [-94.9, 42.2]
          ]
        ]
      }
    }
  ]
};

const IOWA_CENTER = [42.2, -93.6]; // lat, lng

function CountyMap({ selectedCountyId, onSelectCounty }) {
  const styleFeature = (feature) => {
    const isSelected = feature.properties.id === selectedCountyId;
    return {
      color: isSelected ? "#2563eb" : "#6b7280",
      weight: isSelected ? 3 : 1,
      fillColor: isSelected ? "#bfdbfe" : "#e5e7eb",
      fillOpacity: 0.6
    };
  };

  const onEachFeature = (feature, layer) => {
    const id = feature.properties.id;
    const name = feature.properties.name;

    layer.bindTooltip(name, { sticky: true });

    layer.on({
      click: () => onSelectCounty(id)
    });
  };

  return (
    <div className="card map-card">
      <h2>Iowa County Map</h2>
      <p className="map-subtitle">
        Click a highlighted county to view current stress metrics.
      </p>
      <div className="map-wrapper">
        <MapContainer
          center={IOWA_CENTER}
          zoom={7}
          scrollWheelZoom={false}
          className="leaflet-map-container"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <GeoJSON
            data={countiesGeoJson}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
        </MapContainer>
      </div>
      {selectedCountyId ? (
        <p className="map-selected-label">
          Selected county: <strong>{selectedCountyId}</strong>
        </p>
      ) : (
        <p className="map-selected-label map-selected-label--empty">
          No county selected.
        </p>
      )}
    </div>
  );
}

export default CountyMap;