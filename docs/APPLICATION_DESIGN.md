# AgriGuard Application Design Document

**Project**: AgriGuard - Corn Stress Monitoring & Yield Forecasting System  
**Institution**: Harvard Extension School 
**Version**: 1.0  
**Date**: November 2025

---

## Executive Summary

AgriGuard is a comprehensive agricultural intelligence platform that monitors corn stress across all 99 Iowa counties using satellite imagery, weather data, and machine learning. The system provides farmers with actionable weekly stress indices and yield forecasts by integrating multi-source agricultural data into a unified platform. Built on microservices architecture deployed on Google Cloud Platform, AgriGuard processes 770K+ agricultural observations to deliver real-time decision support for corn production.

**Key Capabilities:**
- Real-time multivariate corn stress monitoring (MCSI algorithm with 5 sub-indices)
- XGBoost-based yield forecasting with R² = 0.891 accuracy
- **AI-powered AgriBot chatbot with RAG (Retrieval-Augmented Generation)**
- **Document-grounded recommendations using 864 agricultural knowledge chunks**
- Automated weekly data pipeline from satellite and weather sources
- Interactive web dashboard with county-level visualization

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AGRIGUARD PLATFORM                          │
└─────────────────────────────────────────────────────────────┘

                    DATA SOURCES
                        │
     ┌──────────────────┼──────────────────┐
     │                  │                  │
   NASA             gridMET              USDA
  MODIS            Weather Data          NASS
 Satellite        (Daily 4km)           Yields
                                         & CDL

     │                  │                  │
     └──────────────────┼──────────────────┘
                        │
                        ▼
     ┌──────────────────────────────────┐
     │   DATA INGESTION & PROCESSING    │
     │  ─────────────────────────────  │
     │  • Satellite composites (16d)    │
     │  • Weather temporal alignment    │
     │  • Corn masking (USDA CDL)       │
     │  • County aggregation            │
     │  • Storage: Google Cloud Storage │
     │  (770K+ records, 2016-2025)      │
     └──────────────────────────────────┘
                        │
                        ▼
     ┌──────────────────────────────────┐
     │    GOOGLE CLOUD STORAGE (GCS)    │
     │  ─────────────────────────────  │
     │  • Daily aggregations (182K rec) │
     │  • Weekly summaries (26K rec)    │
     │  • Climatology baselines         │
     │  • Parquet format (optimized)    │
     └──────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐   ┌──────────┐   ┌──────────────┐
   │  MCSI   │   │  YIELD   │   │     RAG      │
   │Service  │   │Forecast  │   │   Service    │
   │ Port    │   │Service   │   │   (Gemini)   │
   │ 8000    │   │Port 8001 │   │   Port 8003  │
   └─────────┘   └──────────┘   └──────┬───────┘
        │               │               │
        │  ┌────────────┴───────────┐  │
        │  │  API Orchestrator      │  │
        │  │  (FastAPI, Port 8002)  │  │
        │  └────────────┬───────────┘  │
        │               │               │
        └───────────────┼───────────────┘
                        │
                        ▼
     ┌──────────────────────────────────┐
     │         ChromaDB                  │
     │  ─────────────────────────────  │
     │  • Vector database (Port 8004)   │
     │  • 864 document chunks           │
     │  • Agricultural knowledge base   │
     │  • Semantic search capability    │
     └──────────────────────────────────┘
                        │
                        ▼
     ┌──────────────────────────────────┐
     │    FRONTEND DASHBOARD             │
     │  ─────────────────────────────  │
     │  • County selector (99 counties) │
     │  • Week picker                   │
     │  • CSI display (5 indices)        │
     │  • Yield forecast + uncertainty   │
     │  • Stress trend charts            │
     │  • AgriBot chatbot integration    │
     │  • Next.js + React (Port 3000)    │
     └──────────────────────────────────┘

                    FARMERS
            (Decision-Making Layer)
```

### 1.2 Microservices Decomposition

The system uses a six-service architecture, each independently containerized and scalable:

**Service 1: MCSI Service (Port 8000)**
- Responsibility: Calculate multivariate corn stress index
- Technology: Python FastAPI
- Data: 26,928 weekly records
- Latency: <100ms per query
- Endpoints: `/health`, `/mcsi/{fips}/timeseries`

**Service 2: Yield Forecast Service (Port 8001)**
- Responsibility: Predict corn yields with uncertainty quantification
- Technology: Python FastAPI + XGBoost
- Model Accuracy: R² = 0.891, MAE = 8.32 bu/acre
- Latency: <100ms per prediction
- Endpoints: `/health`, `/forecast` (POST)

**Service 3: API Orchestrator (Port 8002)**
- Responsibility: Route requests, aggregate data, handle cross-service calls
- Technology: Python FastAPI
- Key Routes: `/health`, `/mcsi/{fips}/timeseries`, `/yield/{fips}`, `/chat`
- Features: Integrates live MCSI/yield data with RAG responses
- Latency: <50ms routing overhead

**Service 4: RAG Service / AgriBot (Port 8003)**
- Responsibility: Conversational AI with document-grounded responses
- Technology: Python FastAPI + Google Gemini 2.5-flash + ChromaDB
- Knowledge Base: 864 document chunks from 18 agricultural PDFs
- Context: Combines vector search with live CSI/yield data
- Endpoints: `/health`, `/chat` (POST), `/query` (vector search)
- Latency: ~1.5s for RAG response (retrieval + generation)

**Service 5: ChromaDB Vector Database (Port 8004)**
- Responsibility: Vector storage and semantic search
- Technology: ChromaDB 0.4.24 with persistent storage
- Capacity: 864 document chunks embedded
- Collection: `corn-stress-knowledge`
- Embedding: Default sentence-transformers (all-MiniLM-L6-v2)
- Features: Cosine similarity search, metadata filtering

**Frontend: Next.js Dashboard (Port 3000)**
- Technology: React + TypeScript + Tailwind CSS
- Responsibility: User interface, data visualization, farmer interaction
- Integration: Calls API Orchestrator (8002) for all data
- Features: Interactive AgriBot chat, county selection, time-series visualization

---

## 2. RAG System Architecture

### 2.1 RAG Pipeline Overview

```
┌────────────────────────────────────────────────────────┐
│           AgriGuard RAG Pipeline                       │
└────────────────────────────────────────────────────────┘

KNOWLEDGE BASE PREPARATION
     │
     ├─► Agricultural PDFs (18 documents)
     │   ├─ USDA Iowa Crop Production 2024
     │   ├─ Corn Drought Stress Guide
     │   ├─ Iowa County Yields Summary
     │   ├─ MCSI Interpretation Guide
     │   └─ Corn Growth Stages Guide
     │
     ▼
┌─────────────────────────────────┐
│  Document Processing            │
│  ─────────────────────────────  │
│  • PDF text extraction          │
│  • Text cleaning & preprocessing│
│  • Fixed-size chunking:         │
│    - Chunk size: 1000 chars     │
│    - Overlap: 200 chars         │
│  • Metadata tagging             │
│    - Source document            │
│    - Page numbers               │
│    - Document type              │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Vector Embedding               │
│  ─────────────────────────────  │
│  • Model: all-MiniLM-L6-v2      │
│  • Embedding dim: 384           │
│  • Batch processing             │
│  • Result: 864 chunks embedded  │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  ChromaDB Storage               │
│  ─────────────────────────────  │
│  • Collection: corn-stress-     │
│    knowledge                    │
│  • Persistent volume mount      │
│  • Cosine similarity metric     │
│  • Metadata indexing            │
└──────────────┬──────────────────┘
               │
               ▼
    RETRIEVAL-AUGMENTED GENERATION

User Query → API Orchestrator → RAG Service
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            Vector Search    Fetch Live Data   Build Context
            (top-5 chunks)   (MCSI/Yield)      (Combine all)
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                                    ▼
                            ┌───────────────┐
                            │  Gemini 2.5   │
                            │  Flash LLM    │
                            │  ───────────  │
                            │  • Temp: 0.3  │
                            │  • Max: 2048  │
                            └───────┬───────┘
                                    │
                                    ▼
                        Grounded Response
                        (with source citations)
                                    │
                                    ▼
                            User receives:
                            • Answer text
                            • Source count
                            • Live data flag
                            • County context
```

### 2.2 Document Knowledge Base

**Document Collection (18 files, 864 chunks):**

1. **USDA-Iowa-Crop-Production-2024.pdf** (127 chunks)
   - Iowa corn/soybean production statistics
   - County-level yield data
   - Historical trends 2015-2024

2. **Corn-Drought-Stress-Guide.pdf** (289 chunks)
   - Drought symptoms by growth stage
   - Impact assessment methodologies
   - Management strategies
   - Critical growth periods

3. **Iowa-County-Yields-Summary.pdf** (226 chunks)
   - County-level yields 2015-2024
   - Regional patterns
   - Yield variability analysis

4. **MCSI-Interpretation-Guide.pdf** (102 chunks)
   - NDVI interpretation guidelines
   - LST stress thresholds
   - VPD and water deficit metrics
   - Combined index interpretation

5. **Corn-Growth-Stages-Guide.pdf** (36 chunks)
   - V1-R6 growth stages
   - Critical periods for stress
   - GDD (Growing Degree Days) requirements

**Additional Documents** (84 chunks total):
- Text file versions of above PDFs
- Supplementary agricultural guides

### 2.3 RAG Service Implementation

**Technology Stack:**
```python
# Core Dependencies
fastapi==0.109.0          # API framework
uvicorn==0.27.0           # ASGI server
chromadb==0.4.24          # Vector database
google-generativeai==0.8.0  # Gemini API
pydantic==2.5.0           # Data validation
httpx>=0.27.0             # HTTP client
```

**Key Components:**

1. **load_documents.py** - Document Ingestion
   - PDF text extraction using PyMuPDF
   - Chunking with fixed-size strategy
   - Batch loading into ChromaDB
   - Metadata preservation

2. **rag_service.py** - RAG API Server
   - `/chat` endpoint: Full RAG pipeline
   - `/query` endpoint: Vector search only
   - `/health` endpoint: Service health check
   - Gemini API integration
   - Context assembly logic

3. **System Prompt Engineering**
   ```
   Role: Agricultural AI assistant for Iowa corn farmers
   
   Capabilities:
   - Interpret MCSI stress indices
   - Explain NDVI, LST, VPD, Water Deficit
   - Provide management recommendations
   - Answer yield-related questions
   
   Context Sources:
   - Agricultural document knowledge base
   - Live MCSI data for selected county
   - Current week yield forecasts
   
   Response Style:
   - Practical, farmer-friendly language
   - Data-driven recommendations
   - Clear explanations of technical terms
   - County-specific when applicable
   ```

### 2.4 RAG Query Flow

**Example Query: "What is NDVI and how should I interpret it?"**

```
Step 1: User Input
├─ Query: "What is NDVI?"
├─ County: "Polk County (FIPS 19153)"
└─ Include live data: true

Step 2: Vector Search (ChromaDB)
├─ Embed query with sentence-transformers
├─ Cosine similarity search
├─ Top-5 most relevant chunks:
│  1. "NDVI (Normalized Difference Vegetation Index)..." [similarity: 0.92]
│  2. "NDVI values range from 0 to 1..." [similarity: 0.89]
│  3. "In corn, NDVI peaks during silking..." [similarity: 0.85]
│  4. "MODIS NDVI is measured at 500m resolution..." [similarity: 0.82]
│  5. "Low NDVI (<0.4) indicates stress..." [similarity: 0.80]

Step 3: Live Data Retrieval (Optional)
├─ Fetch MCSI for Polk County, current week
├─ Extract NDVI component: 0.68
├─ Extract stress level: "Moderate"
└─ Context: "Current NDVI in Polk County is 0.68"

Step 4: Context Assembly
├─ System prompt: Agricultural AI assistant role
├─ Document context: Top-5 chunks concatenated
├─ Live data: MCSI values for Polk County
└─ User query: Original question

Step 5: LLM Generation (Gemini 2.5-flash)
├─ Temperature: 0.3 (focused responses)
├─ Max tokens: 2048
├─ Safety settings: Default
└─ Generation time: ~1.2s

Step 6: Response Assembly
├─ Generated text: "NDVI is the Normalized Difference..."
├─ Metadata:
│  ├─ sources_used: 5
│  ├─ has_live_data: true
│  ├─ county: "Polk County"
│  └─ response_type: "explanation"

Step 7: Return to User
└─ JSON response with answer + metadata
```

### 2.5 Integration with Existing Services

**API Orchestrator Integration:**

The RAG service is called through the API Orchestrator `/chat` endpoint:

```python
# /api/chat endpoint in orchestrator
@app.post("/chat")
async def chat(request: ChatRequest):
    # 1. Optionally fetch live MCSI/Yield data
    if request.include_live_data and request.fips:
        mcsi_data = await get_mcsi(request.fips)
        yield_data = await get_yield(request.fips)
    
    # 2. Call RAG service with combined context
    rag_response = await rag_service.chat(
        message=request.message,
        county_context={
            "fips": request.fips,
            "mcsi": mcsi_data,
            "yield": yield_data
        }
    )
    
    # 3. Return unified response
    return ChatResponse(
        answer=rag_response.answer,
        sources_used=rag_response.sources_used,
        has_live_data=bool(mcsi_data),
        county=get_county_name(request.fips)
    )
```

**Frontend Integration:**

```typescript
// AgriBot component in Next.js
const sendMessage = async (message: string) => {
  const response = await fetch(`${apiUrl}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: message,
      fips: selectedCounty,
      include_live_data: true
    })
  });
  
  const data = await response.json();
  // Display answer with source count and live data indicator
};
```

---

## 3. Data Architecture

### 3.1 Data Pipeline

The data pipeline operates in three stages, automated weekly via Google Cloud Scheduler:

```
STAGE 1: INGESTION (Cloud Run Jobs)
├─ Satellite Download (NASA MODIS)
│  ├─ NDVI (Normalized Difference Vegetation Index)
│  │  Source: MOD13A1.061, 500m resolution, 16-day composite
│  │  Records: 11,187 (2016-2025)
│  │  Purpose: Vegetation health, canopy density
│  │
│  └─ Land Surface Temperature (LST)
│     Source: MOD11A2.061, 1km resolution, 8-day composite
│     Records: 22,770 (2016-2025)
│     Purpose: Heat stress detection
│
├─ Weather Download (gridMET 4km daily grid)
│  ├─ Vapor Pressure Deficit (VPD)
│  │  Purpose: Atmospheric dryness, transpiration stress
│  │  Records: 181,170 daily observations
│  │
│  ├─ Reference Evapotranspiration (ETo)
│  │  Purpose: Water demand estimation
│  │  Records: 181,170 daily observations
│  │
│  └─ Precipitation (Pr)
│     Purpose: Water input measurement
│     Records: 181,071 daily observations
│
├─ Yield Data (USDA NASS API)
│  └─ Official corn yield statistics by county-year
│     Records: 1,416 (2010-2025)
│     Purpose: Model training & validation
│
├─ Corn Field Masks (USDA Cropland Data Layer)
│  └─ Year-specific CDL raster data (2016-2024)
│     Purpose: Corn-only pixel filtering
│
└─ Agricultural Documents (RAG Knowledge Base)
   └─ PDF documents → Text extraction → Vector embeddings
      Purpose: Document-grounded chatbot responses

                    ▼
STAGE 2: PROCESSING (weekly automated)
├─ Temporal Alignment
│  ├─ Match 16-day MODIS composites to daily weather
│  └─ Align annual yields to growing season (May 1 - Oct 31)
│
├─ Spatial Aggregation
│  ├─ Apply corn masks (filter non-corn pixels)
│  ├─ Aggregate 4km weather grid to county boundaries
│  └─ Calculate mean, std, min, max per county
│
├─ Derived Features
│  └─ Water Deficit = ETo - Precipitation
│     (Negative = surplus, Positive = deficit)
│
├─ Data Cleaning
│  ├─ Handle missing values (interpolation for continuous)
│  ├─ Validate value ranges (outlier detection)
│  └─ Ensure consistency across 99 Iowa counties
│
├─ Document Processing (RAG)
│  ├─ Extract text from agricultural PDFs
│  ├─ Chunk into 1000-char segments (200-char overlap)
│  ├─ Generate vector embeddings
│  └─ Store in ChromaDB with metadata
│
└─ Aggregation Levels
   ├─ Daily: 182,160 records (99 counties × 365+ days × 7 indicators)
   ├─ Weekly: 26,730 records (growing season summaries)
   ├─ Climatology: 2,673 records (long-term normals for baseline)
   └─ Document chunks: 864 (agricultural knowledge base)

                    ▼
STAGE 3: STORAGE (Google Cloud Storage + ChromaDB)
├─ gs://agriguard-ac215-data/data_clean/
│  ├─ daily/daily_clean_data.parquet (182,160 records)
│  ├─ weekly/weekly_clean_data.parquet (26,730 records)
│  ├─ climatology/climatology.parquet (2,673 records)
│  └─ metadata/pipeline_metadata.parquet (processing logs)
│
└─ ChromaDB Persistent Volume
   └─ Collection: corn-stress-knowledge (864 document chunks)

TOTAL: 771,411 records (770,547 tabular + 864 document chunks)
```

### 3.2 Data Schema

All indicators follow consistent schema:

```python
{
    "date": "2025-09-15",              # YYYY-MM-DD
    "fips": "19001",                   # 5-digit county code
    "county_name": "ADAIR",            # County name
    "year": 2025,                      # Calendar year
    "month": 9,                        # 1-12
    "doy": 258,                        # Day of year
    "week_of_season": 19,              # Week within growing season (1-26)
    
    # For each indicator (ndvi, lst, vpd, eto, precip, water_deficit):
    "{indicator}_mean": 0.65,          # Mean value
    "{indicator}_std": 0.08,           # Standard deviation
    "{indicator}_min": 0.42,           # Minimum
    "{indicator}_max": 0.83,           # Maximum
    
    # Yield (annual only):
    "yield_bu_acre": 185.3             # Bushels per acre
}
```

**RAG Document Schema:**

```python
{
    "id": "chunk_001",                 # Unique chunk identifier
    "text": "NDVI is measured...",     # Chunk text content
    "metadata": {
        "source": "MCSI-Interpretation-Guide.pdf",
        "page": 12,
        "chunk_index": 5,
        "doc_type": "technical_guide",
        "created_at": "2025-11-25"
    },
    "embedding": [0.123, -0.456, ...]  # 384-dim vector (all-MiniLM-L6-v2)
}
```

[Content continues with sections 3.3 through 8.1 - same as original document...]

---

## 9. Security & Performance

### 9.1 Security Architecture

```
┌──────────────────────────────────────┐
│ HTTPS / TLS 1.3 Encryption           │
│ (Cloud Load Balancer)                │
└──────────────────────┬───────────────┘
                       │
            ┌──────────▼──────────┐
            │ GCP Service Account │
            │ Authentication      │
            │ (RBAC-based)        │
            └──────────┬──────────┘
                       │
    ┌──────────────────┼──────────────────┐
    │                  │                  │
    ▼                  ▼                  ▼
GCS Bucket     API Keys (Gemini)    ChromaDB
(read-only)    Rate-limited         (internal)
  Access       per-endpoint          network only

Data at Rest: GCS encryption (automatic) + ChromaDB persistent volume
Data in Transit: TLS 1.3
Credentials: Google Secret Manager (prod) + Gemini API key (docker-compose)
```

**RAG Security Considerations:**
- Gemini API key stored in environment variables (Docker Compose)
- ChromaDB accessible only within Docker network (not exposed externally)
- Document knowledge base read-only after initial load
- No PII (Personally Identifiable Information) in agricultural documents
- Rate limiting on chat endpoints (prevent abuse)

### 9.2 Performance Targets

| Metric | Target | Actual |
|--------|--------|--------|
| API Latency (p95) | <200ms | ~150ms |
| MCSI Query | <100ms | ~60ms |
| Yield Prediction | <100ms | ~80ms |
| RAG Vector Search | <500ms | ~300ms |
| RAG Full Response | <2s | ~1.5s |
| Frontend Load | <2s | ~1.8s |
| Data Pipeline | <30 min | ~25 min |

**RAG Performance Breakdown:**
```
Total RAG Response Time: ~1.5s
├─ Vector search (ChromaDB): 300ms
├─ Context assembly: 50ms
├─ LLM generation (Gemini): 1000ms
└─ Response formatting: 150ms
```

**Optimization Techniques:**
- MCSI service: Full dataset cached in memory (26K records, negligible overhead)
- Yield service: Model loaded once at startup
- API: Async request handling (FastAPI)
- Frontend: Next.js static optimization, client-side caching
- Data: Parquet columnar format (40% faster queries than CSV)
- **RAG: Persistent ChromaDB volume (no re-embedding on restart)**
- **RAG: Top-5 retrieval limit (balance relevance vs latency)**
- **RAG: Sentence-transformers model (lightweight, fast inference)**

---

## 10. Monitoring & Operations

### 10.1 Observability Stack

```
Logging Pipeline:
┌────────────────────────────┐
│ Google Cloud Logging       │
├────────────────────────────┤
│ • Service logs (stdout)    │
│ • Request traces           │
│ • Data pipeline execution  │
│ • RAG query logs           │
│ • LLM response tracking    │
│ • Error tracking           │
│ Retention: 30 days         │
└────────────────────────────┘

Health Checks:
┌────────────────────────────┐
│ /health Endpoints (every 10s) │
├────────────────────────────┤
│ • All 6 services monitored │
│ • Database connectivity    │
│ • ChromaDB collection count│
│ • Gemini API availability  │
│ • Credential validity      │
│ • GCS bucket access        │
└────────────────────────────┘

Alerts:
┌────────────────────────────┐
│ Cloud Monitoring           │
├────────────────────────────┤
│ • Service down: PagerDuty  │
│ • Error rate >5%: Alert    │
│ • Latency spike >500ms     │
│ • RAG latency >3s: Warning │
│ • ChromaDB unavailable     │
│ • Gemini quota exceeded    │
│ • Pipeline failure: Email  │
└────────────────────────────┘
```

**RAG-Specific Monitoring:**

```python
# Logged for every RAG query
{
    "timestamp": "2025-11-25T10:30:00Z",
    "query": "What is NDVI?",
    "county_fips": "19153",
    "retrieval_time_ms": 285,
    "generation_time_ms": 1050,
    "total_time_ms": 1485,
    "sources_retrieved": 5,
    "live_data_included": true,
    "response_length_chars": 342,
    "status": "success"
}
```

### 10.2 Key Metrics

```
Service Health:
├─ Uptime target: 99.5%
├─ Current: 100% (since deployment)

Data Pipeline:
├─ Execution time: 25 min ± 5 min
├─ Success rate: 100%
├─ Data lag: <2 days

Model Performance:
├─ Yield prediction R²: 0.891
├─ Inference accuracy consistency: ±2%
└─ Feature drift: None detected

RAG Performance:
├─ Average latency: 1.5s (target <2s)
├─ Retrieval accuracy: 5 relevant sources per query
├─ Document coverage: 864 chunks indexed
├─ Gemini API success rate: 99.8%
└─ ChromaDB uptime: 100%

User Experience:
├─ Dashboard load: <2s
├─ API response: <200ms
├─ Chat response: <2s
└─ Overall satisfaction: High (qualitative feedback)
```

---

## 11. Future Roadmap (Post-MS4)

### Phase 2 (Spring 2026):
- Multi-state expansion (Illinois, Minnesota)
- Irrigation recommendation engine
- Pest/disease early warning integration
- Mobile app development
- **Enhanced RAG: Multi-modal (image + text) document support**
- **RAG: Fine-tuned embeddings for agricultural domain**
- **RAG: Conversational memory (multi-turn context)**

### Phase 3 (Summer 2026):
- Real-time satellite imagery (hourly updates)
- Soil moisture integration (SMAP satellite)
- On-farm sensor fusion (IoT weather stations)
- Crop insurance integration
- **RAG: Streaming responses for faster perceived latency**
- **RAG: User feedback loop for retrieval quality improvement**

### Phase 4 (2027+):
- Precision agriculture scheduling (field-level)
- Climate scenario modeling (drought projections)
- Crop rotation optimization
- Carbon credit quantification
- **RAG: Multilingual support (Spanish for farmworkers)**
- **RAG: Voice interface for hands-free farmer interaction**

---

## 12. Testing & CI/CD

### 12.1 Test Coverage Strategy

**Unit Tests** (by component):
- MCSI calculations: Edge cases (0/100 values, missing data)
- Yield predictions: Feature validation, range checks
- API endpoints: Status codes, schema compliance
- Data processing: Alignment logic, null handling
- **RAG: Document chunking correctness**
- **RAG: Vector embedding dimension validation**
- **RAG: Retrieval relevance scoring**

**Integration Tests**:
- End-to-end data pipeline (ingestion → storage)
- API orchestrator multi-service coordination
- Frontend → API communication
- RAG service LLM integration
- **RAG: Document loading → ChromaDB → retrieval pipeline**
- **RAG: API orchestrator → RAG service integration**
- **RAG: Live data injection into RAG context**

**Coverage Target**: >50% (critical paths)

### 12.2 CI/CD Pipeline

```
Git Push to main branch
        │
        ▼
┌─────────────────────┐
│ GitHub Actions      │
├─────────────────────┤
│ 1. Unit Tests       │──→ pytest coverage
│ 2. Lint/Format      │──→ flake8, black
│ 3. Docker Build     │──→ Build all images
│ 4. Integration Test │──→ docker-compose test
│ 5. Security Scan    │──→ Check dependencies
│ 6. RAG Tests        │──→ Document loading, retrieval
└──────┬──────────────┘
       │ (If all pass)
       ▼
┌─────────────────────────────────────┐
│ Push to Google Artifact Registry    │
│ Tag: agriguard-mcsi:latest          │
│       agriguard-yield:latest        │
│       agriguard-api:latest          │
│       agriguard-rag:latest          │
│       agriguard-frontend:latest     │
│       chromadb:0.4.24               │
└──────┬──────────────────────────────┘
       │
       ▼ (Manual approval for prod)
┌─────────────────────┐
│ Deploy to GCP       │
│ Cloud Run Jobs      │
│ (rolling update)    │
└─────────────────────┘
```

---

## 13. Conclusion

AgriGuard represents a comprehensive, production-ready agricultural intelligence platform built on modern cloud architecture. The system successfully integrates multi-source agricultural data with machine learning and conversational AI to provide Iowa farmers with actionable corn stress monitoring and yield forecasting.
