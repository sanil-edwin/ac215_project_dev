# AgriGuard - Agricultural Analytics Platform

A modern web-based agricultural analytics platform for Iowa corn farmers that provides comprehensive crop monitoring and yield prediction capabilities. This application integrates with GCP data sources and Vertex AI models to deliver real-time stress detection, environmental monitoring, and predictive analytics through an intuitive dashboard interface.

## Features

- **Dashboard with Key Metrics**: NDVI, ET, and LST values displayed in clean metric cards
- **Interactive Stress Detection Map**: Leaflet-based map showing Mild, Moderate, and Severe stress zones overlaying field boundaries
- **Time Series Analysis**: Track metric trends over time with interactive charts
- **Stress Drivers Panel**: Visual indicators for Low Vegetation, Water Deficiency, and Heat Stress
- **Yield Forecast Display**: Predicted bushels per acre with confidence intervals for selected field sections
- **AgriBot Chatbot**: Toggleable side panel interface (ready for RAG model integration)
- **Filter Controls**: County, Date range, and Field selection with persistent state

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Shadcn UI
- **Mapping**: Leaflet.js for interactive satellite imagery
- **Charts**: Recharts for data visualization
- **Backend**: Express.js (ready for integration)
- **Data**: Placeholder data (ready to connect to GCP and Vertex AI)

## Getting Started

```bash
npm install
npm run dev
```

The application will start on `http://localhost:5000`

---

## Integration Guide

### Overview

This application is built with a modular architecture that makes it easy to plug in your real GCP data sources and Vertex AI models. All placeholder data and integration points are clearly marked with `TODO` comments throughout the codebase.

### 1. GCP Data Source Integration

#### 1.1 Field Boundary Data (GeoJSON)

**File**: `client/src/components/StressMap.tsx`

**What to replace**: The sample field boundary polygon

```typescript
// CURRENT PLACEHOLDER (lines ~25-35):
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
```

**Replace with**:
```typescript
// Fetch your GeoJSON field boundaries from GCP
const response = await fetch('/api/fields/boundaries');
const fieldBoundaries = await response.json();

// Add each field boundary to the map
fieldBoundaries.features.forEach(feature => {
  L.geoJSON(feature, {
    style: {
      color: '#2E7D32',
      weight: 2,
      fillOpacity: 0
    }
  }).addTo(map);
});
```

**Data Format Expected**:
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {
      "fieldId": "field-001",
      "name": "North Field A",
      "acres": 120
    },
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[lon, lat], [lon, lat], ...]]
    }
  }]
}
```

#### 1.2 Metric Data (NDVI, ET, LST)

**File**: `client/src/pages/Dashboard.tsx`

**What to replace**: The sample metrics data (lines ~12-17)

```typescript
// CURRENT PLACEHOLDER:
const metricsData = [
  { title: "NDVI", value: "0.78", unit: "index", trend: 5.2, icon: Leaf },
  { title: "ET", value: "5.3", unit: "mm/day", trend: 2.1, icon: Droplets },
  { title: "LST", value: "28.5", unit: "°C", trend: -1.5, icon: Thermometer },
];
```

**Replace with**:
```typescript
// Fetch from your GCP data source
const { data: metricsData } = useQuery({
  queryKey: ['/api/metrics/current'],
});

// Expected data format from backend:
// [
//   { title: "NDVI", value: "0.78", unit: "index", trend: 5.2, icon: Leaf },
//   { title: "ET", value: "5.3", unit: "mm/day", trend: 2.1, icon: Droplets },
//   { title: "LST", value: "28.5", unit: "°C", trend: -1.5, icon: Thermometer }
// ]
```

**Backend Endpoint to Create** (`server/routes.ts`):
```typescript
app.get('/api/metrics/current', async (req, res) => {
  // Connect to your GCP data source
  const gcpData = await fetchFromGCP({
    dataset: 'satellite_metrics',
    table: 'current_values'
  });
  
  res.json([
    { 
      title: "NDVI", 
      value: gcpData.ndvi.toFixed(2), 
      unit: "index", 
      trend: gcpData.ndvi_trend,
      icon: "Leaf" 
    },
    // ... other metrics
  ]);
});
```

#### 1.3 Time Series Data

**File**: `client/src/components/TimeSeriesChart.tsx`

**What to replace**: The defaultData array (lines ~11-19)

```typescript
// CURRENT PLACEHOLDER:
const defaultData = [
  { date: "May 1", ndvi: 0.65, et: 4.2, lst: 22 },
  { date: "May 8", ndvi: 0.70, et: 4.5, lst: 24 },
  // ...
];
```

**Replace with**:
```typescript
// Use the data prop passed from parent, which should fetch from API
// In Dashboard.tsx, add:
const { data: timeSeriesData } = useQuery({
  queryKey: ['/api/metrics/timeseries', filters.dateRange],
});

// Then pass to component:
<TimeSeriesChart data={timeSeriesData} />
```

**Backend Endpoint**:
```typescript
app.get('/api/metrics/timeseries', async (req, res) => {
  const { startDate, endDate, fieldId } = req.query;
  
  // Query your GCP BigQuery or Cloud Storage
  const data = await gcpClient.query({
    query: `
      SELECT date, ndvi, et, lst 
      FROM satellite_metrics 
      WHERE field_id = @fieldId 
      AND date BETWEEN @startDate AND @endDate
      ORDER BY date
    `,
    params: { fieldId, startDate, endDate }
  });
  
  res.json(data.map(row => ({
    date: format(row.date, "MMM d"),
    ndvi: row.ndvi,
    et: row.et,
    lst: row.lst
  })));
});
```

### 2. Vertex AI Model Integration

#### 2.1 Stress Detection Model

**File**: `client/src/components/StressMap.tsx`

**What to replace**: The sample stress zones (lines ~38-44)

```typescript
// CURRENT PLACEHOLDER:
const severeLayers = [
  { coords: [[42.011, -93.505], ...], severity: 'severe' },
  { coords: [[42.020, -93.502], ...], severity: 'moderate' },
  { coords: [[42.025, -93.500], ...], severity: 'mild' }
];
```

**Replace with**:
```typescript
// Fetch stress predictions from Vertex AI via your backend
const response = await fetch(`/api/predictions/stress?fieldId=${fieldId}&date=${date}`);
const stressZones = await response.json();

stressZones.forEach(zone => {
  const color = zone.severity === 'severe' ? '#D32F2F' : 
                zone.severity === 'moderate' ? '#FF9800' : '#FFE082';
  L.geoJSON(zone.geometry, {
    style: {
      color: color,
      fillColor: color,
      fillOpacity: 0.4,
      weight: 1
    }
  }).addTo(map).bindPopup(`${zone.severity} Stress Zone - Score: ${zone.score}`);
});
```

**Backend Endpoint** (`server/routes.ts`):
```typescript
import { VertexAI } from '@google-cloud/vertexai';

const vertexAI = new VertexAI({
  project: process.env.GCP_PROJECT_ID,
  location: process.env.GCP_REGION
});

app.get('/api/predictions/stress', async (req, res) => {
  const { fieldId, date } = req.query;
  
  // Fetch satellite data for the field
  const satelliteData = await fetchSatelliteData(fieldId, date);
  
  // Call your Vertex AI stress detection model
  const model = vertexAI.preview.getGenerativeModel({
    model: 'your-stress-detection-model-name'
  });
  
  const result = await model.generateContent({
    contents: [{
      role: 'user',
      parts: [{
        text: JSON.stringify({
          ndvi: satelliteData.ndvi,
          lst: satelliteData.lst,
          moisture: satelliteData.moisture,
          // ... other features
        })
      }]
    }]
  });
  
  // Parse model response and convert to GeoJSON zones
  const predictions = parseStressPredictions(result);
  
  res.json(predictions);
});

// Expected response format:
// [
//   {
//     severity: "severe" | "moderate" | "mild",
//     score: 0.85,
//     geometry: {
//       type: "Polygon",
//       coordinates: [[[lon, lat], ...]]
//     }
//   }
// ]
```

#### 2.2 Stress Driver Analysis

**File**: `client/src/components/StressDrivers.tsx`

**What to replace**: The defaultDrivers array (lines ~17-21)

**Backend Endpoint**:
```typescript
app.get('/api/predictions/drivers', async (req, res) => {
  const { fieldId, date } = req.query;
  
  // Call Vertex AI model for stress driver analysis
  const model = vertexAI.preview.getGenerativeModel({
    model: 'your-driver-analysis-model'
  });
  
  const fieldData = await fetchFieldMetrics(fieldId, date);
  const result = await model.generateContent({
    contents: [{
      role: 'user',
      parts: [{ text: JSON.stringify(fieldData) }]
    }]
  });
  
  res.json([
    { name: "Low Vegetation", severity: "medium", value: 45, icon: "Sprout" },
    { name: "Water Deficiency", severity: "high", value: 72, icon: "Droplet" },
    { name: "Heat Stress", severity: "low", value: 28, icon: "Thermometer" }
  ]);
});
```

#### 2.3 Yield Prediction Model

**File**: `client/src/components/YieldForecast.tsx`

**Props to fetch from API**: `predictedYield`, `confidenceInterval`

**Backend Endpoint**:
```typescript
app.get('/api/predictions/yield', async (req, res) => {
  const { fieldId, date } = req.query;
  
  // Call Vertex AI yield prediction model
  const model = vertexAI.preview.getGenerativeModel({
    model: 'your-yield-prediction-model-v2.1'
  });
  
  const historicalData = await fetchHistoricalYields(fieldId);
  const currentMetrics = await fetchCurrentMetrics(fieldId);
  const weatherData = await fetchWeatherForecast(fieldId);
  
  const result = await model.generateContent({
    contents: [{
      role: 'user',
      parts: [{
        text: JSON.stringify({
          historical: historicalData,
          current: currentMetrics,
          weather: weatherData
        })
      }]
    }]
  });
  
  const prediction = parseYieldPrediction(result);
  
  res.json({
    fieldName: "North Field Section A",
    predictedYield: prediction.mean,
    confidenceInterval: {
      low: prediction.lower_95,
      high: prediction.upper_95
    },
    modelVersion: "v2.1"
  });
});
```

### 3. AgriBot RAG Model Integration

**File**: `client/src/components/AgriBot.tsx`

**What to replace**: The placeholder response (lines ~35-41)

```typescript
// CURRENT PLACEHOLDER:
setTimeout(() => {
  setMessages(prev => [...prev, {
    role: "assistant",
    content: "This is a placeholder response..."
  }]);
}, 500);
```

**Replace with**:
```typescript
const handleSend = async () => {
  if (!input.trim()) return;
  
  const newMessage: Message = { role: "user", content: input };
  setMessages([...messages, newMessage]);
  setInput("");
  
  try {
    // Call your RAG-enabled chatbot backend
    const response = await fetch('/api/chat/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: input,
        context: {
          fieldId: selectedField,
          conversationHistory: messages
        }
      })
    });
    
    const data = await response.json();
    
    setMessages(prev => [...prev, {
      role: "assistant",
      content: data.response
    }]);
  } catch (error) {
    console.error('Chat error:', error);
    setMessages(prev => [...prev, {
      role: "assistant",
      content: "Sorry, I encountered an error. Please try again."
    }]);
  }
};
```

**Backend Endpoint**:
```typescript
app.post('/api/chat/message', async (req, res) => {
  const { message, context } = req.body;
  
  // Retrieve relevant agricultural knowledge from vector database
  const relevantDocs = await vectorSearch(message, {
    collection: 'agricultural_knowledge',
    topK: 5
  });
  
  // Get current field data for context
  const fieldData = await fetchFieldData(context.fieldId);
  
  // Call Vertex AI with RAG context
  const model = vertexAI.preview.getGenerativeModel({
    model: 'gemini-pro' // or your custom RAG model
  });
  
  const prompt = `
You are AgriBot, an agricultural assistant. Use the following context to answer the farmer's question.

Field Data: ${JSON.stringify(fieldData)}
Relevant Knowledge: ${relevantDocs.map(doc => doc.content).join('\n\n')}
Conversation History: ${JSON.stringify(context.conversationHistory)}

Question: ${message}

Provide a helpful, accurate response based on the data and agricultural best practices.
  `;
  
  const result = await model.generateContent({
    contents: [{ role: 'user', parts: [{ text: prompt }] }]
  });
  
  res.json({
    response: result.response.text()
  });
});
```

### 4. Environment Variables Setup

Create a `.env` file in the project root:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_CREDENTIALS_PATH=/path/to/service-account-key.json

# Vertex AI Model Endpoints
VERTEX_AI_STRESS_MODEL=your-stress-detection-model
VERTEX_AI_YIELD_MODEL=your-yield-prediction-model-v2.1
VERTEX_AI_CHAT_MODEL=gemini-pro

# BigQuery/Cloud Storage
GCP_DATASET_ID=agricultural_data
GCP_BUCKET_NAME=agriguard-satellite-data

# Vector Database (for RAG)
VECTOR_DB_URL=your-vector-db-url
VECTOR_DB_API_KEY=your-api-key
```

Load environment variables in `server/index.ts`:
```typescript
import dotenv from 'dotenv';
dotenv.config();
```

### 5. GCP Authentication

Install the required packages:
```bash
npm install @google-cloud/vertexai @google-cloud/bigquery @google-cloud/storage
```

Initialize GCP clients in `server/services/gcp.ts`:
```typescript
import { VertexAI } from '@google-cloud/vertexai';
import { BigQuery } from '@google-cloud/bigquery';
import { Storage } from '@google-cloud/storage';

export const vertexAI = new VertexAI({
  project: process.env.GCP_PROJECT_ID!,
  location: process.env.GCP_REGION!
});

export const bigquery = new BigQuery({
  projectId: process.env.GCP_PROJECT_ID,
  keyFilename: process.env.GCP_CREDENTIALS_PATH
});

export const storage = new Storage({
  projectId: process.env.GCP_PROJECT_ID,
  keyFilename: process.env.GCP_CREDENTIALS_PATH
});
```

### 6. Data Format Specifications

#### Satellite Metrics Table (BigQuery)
```sql
CREATE TABLE agricultural_data.satellite_metrics (
  id STRING,
  field_id STRING,
  date DATE,
  ndvi FLOAT64,
  et FLOAT64,
  lst FLOAT64,
  moisture FLOAT64,
  timestamp TIMESTAMP
);
```

#### Field Boundaries Table
```sql
CREATE TABLE agricultural_data.field_boundaries (
  field_id STRING,
  name STRING,
  county STRING,
  acres FLOAT64,
  geometry GEOGRAPHY,
  owner_id STRING
);
```

#### Stress Predictions Table
```sql
CREATE TABLE agricultural_data.stress_predictions (
  id STRING,
  field_id STRING,
  date DATE,
  severity STRING, -- 'mild', 'moderate', 'severe'
  confidence FLOAT64,
  geometry GEOGRAPHY,
  drivers JSON, -- { vegetation: 0.45, water: 0.72, heat: 0.28 }
  model_version STRING
);
```

### 7. Quick Start Integration Checklist

- [ ] Set up GCP project and enable Vertex AI API
- [ ] Create service account and download credentials
- [ ] Set up BigQuery datasets and tables
- [ ] Upload field boundary GeoJSON to Cloud Storage or BigQuery
- [ ] Deploy Vertex AI models (stress detection, yield prediction)
- [ ] Configure environment variables in `.env`
- [ ] Install GCP packages: `npm install @google-cloud/vertexai @google-cloud/bigquery`
- [ ] Create backend service layer in `server/services/gcp.ts`
- [ ] Implement API endpoints in `server/routes.ts`
- [ ] Update frontend components to use real API calls (remove TODO placeholders)
- [ ] Set up vector database for RAG model (Pinecone, Weaviate, or Vertex AI Vector Search)
- [ ] Test each integration point individually
- [ ] Deploy to production

### 8. Finding All Integration Points

Search for TODO comments in the codebase:
```bash
grep -r "TODO" client/src/components/
grep -r "TODO" client/src/pages/
```

All placeholder data and integration points are marked with comments like:
- `// TODO: Replace with real GCP field boundary data`
- `// TODO: Replace with stress zone data from Vertex AI model`
- `// TODO: Connect to your RAG model for intelligent responses`

---

## Architecture Overview

```
┌─────────────────┐
│   React UI      │
│  (Dashboard)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Express API    │
│   (Routes)      │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│   GCP   │ │  Vertex AI   │
│BigQuery │ │   Models     │
│ Storage │ │              │
└─────────┘ └──────────────┘
```

## Support

For questions or issues with integration, review the TODO comments in the code which provide context-specific guidance.

## License

MIT
