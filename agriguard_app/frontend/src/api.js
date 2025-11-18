const BACKEND_BASE_URL =
  process.env.REACT_APP_BACKEND_URL || "http://localhost:9000";

async function handleResponse(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed: ${res.status} ${text}`);
  }
  return res.json();
}

// Health

export async function getHealth() {
  const res = await fetch(`${BACKEND_BASE_URL}/api/health`);
  return handleResponse(res);
}

// County metrics + trend

export async function getCountyMetrics(countyId) {
  const res = await fetch(
    `${BACKEND_BASE_URL}/api/county-metrics?county_id=${encodeURIComponent(
      countyId
    )}`
  );
  return handleResponse(res);
}

export async function getCountyTrend(countyId) {
  const res = await fetch(
    `${BACKEND_BASE_URL}/api/county-trend?county_id=${encodeURIComponent(
      countyId
    )}`
  );
  return handleResponse(res);
}

// Yield forecast

export async function getYieldForecast(countyId, asOfDate) {
  const body = {
    county_id: countyId,
    as_of_date: asOfDate || null,
  };

  const res = await fetch(`${BACKEND_BASE_URL}/api/yield-forecast`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return handleResponse(res);
}


// Chat

export async function sendChat(question, countyId) {
  const body = {
    question,
    county_id: countyId || null,
  };

  const res = await fetch(`${BACKEND_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return handleResponse(res);
}

// Query transform + embeddings

export async function transformQuery(question, countyId) {
  const body = {
    question,
    county_id: countyId || null,
  };

  const res = await fetch(`${BACKEND_BASE_URL}/api/query/transform`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return handleResponse(res);
}

export async function getQueryEmbeddings(queries) {
  const body = { queries };

  const res = await fetch(`${BACKEND_BASE_URL}/api/query/embeddings`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return handleResponse(res);
}
