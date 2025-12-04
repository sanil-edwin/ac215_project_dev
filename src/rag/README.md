# AgriGuard RAG Service Integration Guide

## Overview

This guide explains how to integrate the RAG (Retrieval-Augmented Generation) service into your AgriGuard project.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Port 3000)                      │
│                    Next.js Dashboard                         │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               API ORCHESTRATOR (Port 8002)                   │
│  Routes: /mcsi, /yield, /chat, /query, /health              │
└───────┬─────────────────┬─────────────────┬─────────────────┘
        │                 │                 │
        ▼                 ▼                 ▼
   ┌─────────┐      ┌──────────┐      ┌──────────┐
   │  MCSI   │      │  Yield   │      │   RAG    │
   │ Service │      │ Service  │      │ Service  │
   │  :8000  │      │  :8001   │      │  :8003   │
   └─────────┘      └──────────┘      └────┬─────┘
                                           │
                              ┌────────────┼────────────┐
                              │            │            │
                              ▼            ▼            ▼
                         ┌─────────┐  ┌─────────┐  ┌─────────┐
                         │ChromaDB │  │ Gemini  │  │Knowledge│
                         │  :8004  │  │  API    │  │  Base   │
                         └─────────┘  └─────────┘  └─────────┘
```

## Files to Add/Update

### 1. Add RAG Service Directory

Copy the `rag/` directory to your project root:

```
E:\project\agriguard-project\
├── rag/                          # ← NEW DIRECTORY
│   ├── Dockerfile.rag           # Docker configuration
│   ├── requirements.txt         # Python dependencies
│   ├── rag_service.py          # Main FastAPI service
│   └── load_documents.py       # Document loader utility
├── api_service/
│   └── api/
│       └── api_orchestrator.py     # ← UPDATED with /chat endpoint
├── ml-models/
├── frontend/
└── docker-compose.yml          # Already has RAG service defined
```

### 2. Update API Orchestrator

Replace `api_service/api/api_orchestrator.py` with the updated version that includes:
- `/chat` endpoint - Chat with AgriBot
- `/query` endpoint - Direct vector search
- RAG service health checks

## Quick Start

### Step 1: Start All Services

```bash
# From project root
docker-compose up -d
```

This starts:
- MCSI service (8000)
- Yield service (8001)
- API orchestrator (8002)
- RAG service (8003)
- ChromaDB (8004)
- Frontend (3000)

### Step 2: Load Knowledge Base (First Time)

```bash
# Load sample agricultural knowledge
docker-compose exec rag python load_documents.py --sample

# Or load from PDF files
docker-compose exec rag python load_documents.py --input-dir /app/sample-data
```

### Step 3: Test the Chat

```bash
# Simple chat
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What factors affect corn yield in Iowa?"}'

# Chat with live county data
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How is the corn crop doing?",
    "fips": "19001",
    "include_live_data": true
  }'
```

## API Endpoints

### Chat with AgriBot
```
POST /chat
```

Request:
```json
{
  "message": "What are the signs of heat stress in corn?",
  "fips": "19001",           // Optional: include live data for this county
  "include_live_data": true  // Optional: default true
}
```

Response:
```json
{
  "response": "Heat stress in corn shows several key symptoms...",
  "sources_used": 5,
  "has_live_data": true,
  "county": "Adair",
  "mcsi_summary": { ... },
  "yield_summary": { ... }
}
```

### Direct Knowledge Search
```
POST /query
```

Request:
```json
{
  "query": "drought stress mitigation",
  "top_k": 5
}
```

## Frontend Integration

Add chat component to your React frontend:

```tsx
// Example chat hook
const useAgriBot = () => {
  const [loading, setLoading] = useState(false);
  
  const sendMessage = async (message: string, fips?: string) => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8002/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          fips,
          include_live_data: !!fips
        })
      });
      return await response.json();
    } finally {
      setLoading(false);
    }
  };
  
  return { sendMessage, loading };
};
```

## Environment Variables

The RAG service uses these environment variables (already in docker-compose.yml):

| Variable | Value | Description |
|----------|-------|-------------|
| `GEMINI_API_KEY` | Your API key | Google Gemini API key |
| `CHROMADB_HOST` | `chromadb` | ChromaDB hostname |
| `CHROMADB_PORT` | `8000` | ChromaDB port (internal) |
| `RAG_COLLECTION_NAME` | `corn-stress-knowledge` | Default collection |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model to use |

## Loading Custom Documents

### From Python Code:

```python
import httpx

# Load text chunks via API
response = httpx.post(
    "http://localhost:8003/load",
    json={
        "texts": [
            "Corn requires 20-25 inches of water during growing season.",
            "Heat stress occurs when temps exceed 95°F for multiple days.",
        ],
        "collection_name": "corn-stress-knowledge"
    }
)
```

### From CLI:

```bash
# Load PDFs
python load_documents.py --input-dir ./documents

# Load specific texts
python load_documents.py --texts "Text 1" "Text 2"

# View collections
python load_documents.py --info
```

## Troubleshooting

### ChromaDB Not Connecting
```bash
# Check if ChromaDB is running
docker-compose logs chromadb

# Restart ChromaDB
docker-compose restart chromadb
```

### Gemini API Errors
```bash
# Verify API key is set
docker-compose exec rag env | grep GEMINI

# Test Gemini directly
docker-compose exec rag python -c "
import google.generativeai as genai
import os
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.0-flash')
print(model.generate_content('Hello').text)
"
```

### Empty Knowledge Base
```bash
# Load sample knowledge
docker-compose exec rag python load_documents.py --sample

# Verify loading
curl http://localhost:8003/collections
```

## Service Health Check

```bash
# Check all services
curl http://localhost:8002/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "mcsi": "healthy",
    "yield": "healthy",
    "rag": "healthy"
  }
}
```

## Production Deployment

For Cloud Run deployment, update the service URLs in environment variables:

```yaml
# Cloud Run environment
RAG_URL: https://agriguard-rag-xxxxx.run.app
MCSI_URL: https://agriguard-mcsi-xxxxx.run.app
YIELD_URL: https://agriguard-yield-xxxxx.run.app
```

---

**Version**: 1.0.0  
**Last Updated**: November 2025
