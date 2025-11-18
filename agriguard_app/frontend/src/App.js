import React, { useEffect, useState } from "react";
import "./App.css";
import CountyDashboard from "./CountyDashboard";
import ChatPanel from "./ChatPanel";
import CountyMap from "./CountyMap";
import { getHealth } from "./api";

function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState("");
  const [selectedCountyId, setSelectedCountyId] = useState(""); // no county initially

  useEffect(() => {
    getHealth()
      .then((data) => setHealth(data.status))
      .catch((err) => {
        console.error(err);
        setHealth("error");
        setHealthError("Backend health check failed.");
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>AgriGuard</h1>
        <div className="backend-status">
          <span>Backend status: </span>
          {health === null && <span>Loading…</span>}
          {health === "ok" && <span style={{ color: "green" }}>OK</span>}
          {health === "error" && (
            <span style={{ color: "red" }}>Error</span>
          )}
        </div>
        {healthError && (
          <div style={{ color: "red", marginTop: "0.25rem" }}>
            {healthError}
          </div>
        )}
      </header>

      <main className="App-main">
        <section className="App-left">
          <CountyMap
            selectedCountyId={selectedCountyId}
            onSelectCounty={setSelectedCountyId}
          />

          <CountyDashboard countyId={selectedCountyId} />
        </section>

        <section className="App-right">
          <ChatPanel countyId={selectedCountyId} />
        </section>
      </main>
    </div>
  );
}

export default App;
