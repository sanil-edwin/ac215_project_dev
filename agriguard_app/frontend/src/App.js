import React, { useState } from "react";
import "./App.css";
import CountyDashboard from "./CountyDashboard";
import ChatPanel from "./ChatPanel";
import CountyMap from "./CountyMap";

function App() {
  const [selectedCountyId, setSelectedCountyId] = useState(null);

  return (
    <div className="App">
      <header className="app-header">
        <h1>AgriGuard</h1>
        <p>Iowa Corn Monitoring & Yield Insights</p>
      </header>

      <main className="app-main">
        <section className="left-column">
          <CountyMap
            selectedCountyId={selectedCountyId}
            onSelectCounty={setSelectedCountyId}
          />

          <CountyDashboard selectedCountyId={selectedCountyId} />
        </section>

        <section className="right-column">
          <ChatPanel />
        </section>
      </main>
    </div>
  );
}

export default App;