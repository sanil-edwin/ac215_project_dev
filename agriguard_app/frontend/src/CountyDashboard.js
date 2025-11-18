import React, { useEffect, useState } from "react";
import { getCountyMetrics, getCountyTrend } from "./api";

function CountyDashboard({ countyId }) {
  const [metrics, setMetrics] = useState(null);
  const [trend, setTrend] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
   
    if (!countyId) {
      setMetrics(null);
      setTrend([]);
      setError("");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    Promise.all([getCountyMetrics(countyId), getCountyTrend(countyId)])
      .then(([metricsData, trendData]) => {
        setMetrics(metricsData);
        setTrend(trendData || []);
      })
      .catch((err) => {
        console.error(err);
        setError("Failed to load county metrics.");
        setMetrics(null);
        setTrend([]);
      })
      .finally(() => setLoading(false));
  }, [countyId]);

  return (
    <div className="CountyDashboard">
      <h2>County Metrics</h2>

      <div style={{ marginBottom: "0.5rem" }}>
        <label>
          County FIPS:&nbsp;
          <input
            value={countyId || ""}
            readOnly
            style={{ width: "120px" }}
            placeholder="Select a county…"
          />
        </label>
      </div>

      {!countyId && (
        <div style={{ color: "#555" }}>
          Select a county to view stress, NDVI, and soil moisture metrics.
        </div>
      )}

      {countyId && loading && <div>Loading metrics…</div>}

      {countyId && error && (
        <div style={{ color: "red", marginTop: "0.5rem" }}>{error}</div>
      )}

      {countyId && metrics && !loading && !error && (
        <div className="metrics-card" style={{ marginTop: "0.5rem" }}>
          <div>
            <strong>{metrics.name}</strong> (FIPS {metrics.id})
          </div>
          <div>NDVI: {metrics.ndvi.toFixed(2)}</div>
          <div>Soil moisture: {metrics.soil_moisture.toFixed(2)}</div>
          <div>Stress index: {metrics.stress_index.toFixed(2)}</div>
        </div>
      )}

      {countyId && trend && trend.length > 0 && !loading && !error && (
        <div className="trend-section" style={{ marginTop: "0.75rem" }}>
          <div>
            <strong>Stress trend</strong>
          </div>
          <ul>
            {trend.map((t) => (
              <li key={t.date}>
                {t.date}: {t.stress_index.toFixed(2)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {countyId && !loading && !error && !metrics && (
        <div>No data available for this county.</div>
      )}
    </div>
  );
}

export default CountyDashboard;
