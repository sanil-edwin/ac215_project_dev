import React, { useState, useEffect } from "react";

function CountyMap({ selectedCountyId, onSelectCounty }) {
  const [manualFips, setManualFips] = useState(selectedCountyId || "");

  useEffect(() => {
    // keep the input in sync if selectedCountyId changes from outside
    setManualFips(selectedCountyId || "");
  }, [selectedCountyId]);

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = manualFips.trim();
    if (!trimmed) return;
    onSelectCounty(trimmed);
  }

  return (
    <div className="CountyMap">
      <h2>County Selection</h2>

      <div style={{ marginBottom: "0.5rem", fontSize: "0.9rem" }}>
        Enter any Iowa county FIPS code to update the dashboard and assistant.
      </div>

      <form onSubmit={handleSubmit} style={{ fontSize: "0.9rem" }}>
        <label>
          County FIPS:&nbsp;
          <input
            value={manualFips}
            onChange={(e) => setManualFips(e.target.value)}
            placeholder="e.g. 19015"
            style={{ width: "120px" }}
          />
        </label>
        <button type="submit" style={{ marginLeft: "0.5rem" }}>
          Go
        </button>
      </form>

      {selectedCountyId && (
        <div style={{ marginTop: "0.5rem", fontSize: "0.9rem" }}>
          Selected county: <strong>{selectedCountyId}</strong>
        </div>
      )}

      {!selectedCountyId && (
        <div style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "#555" }}>
          No county selected yet.
        </div>
      )}
    </div>
  );
}

export default CountyMap;
