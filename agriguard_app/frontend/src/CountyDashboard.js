import React, { useEffect, useState } from "react";

function CountyDashboard({ selectedCountyId }) {
  const [metrics, setMetrics] = useState(null);
  const [trend, setTrend] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | loading | error
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (!selectedCountyId) {
      setMetrics(null);
      setTrend([]);
      setStatus("idle");
      return;
    }

    async function fetchData() {
      try {
        setStatus("loading");
        setErrorMsg("");

        // Call FastAPI for metrics
        const metricsRes = await fetch(
          `/api/county-metrics?county_id=${selectedCountyId}`
        );
        if (!metricsRes.ok) {
          throw new Error("Failed to fetch county metrics");
        }
        const metricsJson = await metricsRes.json();

        // Call FastAPI for trend
        const trendRes = await fetch(
          `/api/county-trend?county_id=${selectedCountyId}`
        );
        if (!trendRes.ok) {
          throw new Error("Failed to fetch county trend");
        }
        const trendJson = await trendRes.json();

        setMetrics(metricsJson);
        setTrend(trendJson);
        setStatus("ok");
      } catch (err) {
        console.error(err);
        setStatus("error");
        setErrorMsg(err.message || "Unknown error");
      }
    }

    fetchData();
  }, [selectedCountyId]);

  if (!selectedCountyId) {
    return (
      <div className="card">
        <h2>County Dashboard</h2>
        <p>Select a county to view metrics.</p>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="card">
        <h2>County Dashboard</h2>
        <p>Loading metrics for county {selectedCountyId}…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="card">
        <h2>County Dashboard</h2>
        <p>Could not load data. {errorMsg}</p>
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  return (
    <div className="card">
      <h2>{metrics.name}</h2>

      <div className="metrics-grid">
        <div>
          <h3>NDVI</h3>
          <p>{metrics.ndvi.toFixed(2)}</p>
        </div>
        <div>
          <h3>Soil Moisture</h3>
          <p>{metrics.soil_moisture.toFixed(2)}</p>
        </div>
        <div>
          <h3>Stress Index</h3>
          <p>{metrics.stress_index.toFixed(2)}</p>
        </div>
      </div>

      <div className="trend-chart">
        <h3>Stress Trend Over Time</h3>
        {trend.length === 0 ? (
          <p>No trend data available.</p>
        ) : (
          <ul>
            {trend.map((point) => (
              <li key={point.date}>
                {point.date}: {point.stress_index.toFixed(2)}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default CountyDashboard;