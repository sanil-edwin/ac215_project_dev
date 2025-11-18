// frontend/src/api.js

const BACKEND_BASE_URL =
  process.env.REACT_APP_BACKEND_URL || "http://localhost:9000";

async function handleResponse(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Request failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function getHealth() {
  const res = await fetch(`${BACKEND_BASE_URL}/api/health`);
  return handleResponse(res);
}

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

export async function sendChat(question, countyId) {
  const res = await fetch(`${BACKEND_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      county_id: countyId || null,
    }),
  });

  return handleResponse(res);
}
