# AgriGuard: Corn Stress Monitoring & Yield Forecasting System

**AC215 Course Project - Harvard Extension School**

Team: BINH VU, SANIL EDWIN, MOODY FARRA, ARTEM BIRIUKOV

## Overview

AgriGuard is a production-ready agricultural intelligence platform that monitors corn stress across all 99 Iowa counties using satellite imagery, weather data, and machine learning. Built on microservices architecture and deployed on Google Cloud Platform, the system processes 770K+ agricultural observations to deliver real-time decision support for corn production.

**Key Capabilities:**
- Real-time multivariate corn stress monitoring (MCSI algorithm with 5 sub-indices)
- XGBoost-based yield forecasting with R² = 0.891 accuracy
- AI-powered AgriBot chatbot with RAG (Retrieval-Augmented Generation)
- Document-grounded recommendations using 864 agricultural knowledge chunks
- Automated weekly data pipeline from satellite and weather sources
- Interactive web dashboard with county-level visualization

## System Architecture

The system uses a six-service microservices architecture, each independently containerized and orchestrated via Docker Compose:

1. **MCSI Service (Port 8000)** - Calculate multivariate corn stress index
   - Technology: Python FastAPI
   - Data: 26,928 weekly records
   - Latency: <100ms per query

2. **Yield Forecast Service (Port 8001)** - Predict corn yields with uncertainty quantification
   - Technology: Python FastAPI + XGBoost
   - Model Accuracy: R² = 0.891, MAE = 8.32 bu/acre
   - Latency: <100ms per prediction

3. **API Orchestrator (Port 8002)** - Route requests and aggregate data
   - Technology: Python FastAPI
   - Features: Integrates live MCSI/yield data with RAG responses

4. **RAG Service (Port 8003)** - Conversational AI with document-grounded responses
   - Technology: Python FastAPI + Google Gemini 2.5-flash + ChromaDB
   - Knowledge Base: 864 document chunks from agricultural PDFs
   - Latency: ~1.5s for full RAG response

5. **ChromaDB (Port 8004)** - Vector database for semantic search
   - Technology: ChromaDB 0.4.24 with persistent storage
   - Embedding: sentence-transformers (all-MiniLM-L6-v2)

6. **Frontend (Port 3000)** - User interface and visualization
   - Technology: Next.js + React + TypeScript + Tailwind CSS
   - Features: Interactive AgriBot chat, county selection, time-series visualization

## Project Structure

```
ac215_agriguard/
├── README.md
├── docker-compose.yml
├── requirements.txt
│
├── api/
│   └── api_orchestrator.py
│
├── data_service/
│   ├── ingestion/
│   ├── processing/
│   └── validation/
│
├── frontend/
│   ├── components/
│   └── pages/
│
├── ml-models/
│   ├── mcsi/                    # Multi-source Crop Stress Index service
│   │   ├── mcsi_service.py
│   │   ├── Dockerfile
│   │   └── requirements_mcsi.txt
│   └── yield_forecast/          # XGBoost yield prediction service
│       ├── yield_forecast_service_light.py
│       ├── Dockerfile.yield
│       └── requirements_yield.txt
│
├── rag/                         # RAG service with ChromaDB
│   ├── rag_service.py
│   ├── load_documents.py
│   ├── Dockerfile.rag
│   ├── requirements.txt
│   └── sample-data/             # Agricultural knowledge base (18 PDFs)
│
├── docs/                        # Documentation
│   ├── APPLICATION_DESIGN.md
│   ├── DATA_VERSIONING.md
│   └── MODEL_TRAINING_SUMMARY.md
│
└── tests/                       # Test suite
    ├── test_api_orchestrator.py
    ├── test_data_processing.py
    └── test_rag_service.py
```

## Data Pipeline

The data pipeline operates in three automated stages:

**Stage 1: Ingestion**
- Satellite data (NASA MODIS): NDVI, LST (2016-2025)
- Weather data (gridMET): VPD, ETo, Precipitation (daily 4km grid)
- Yield data (USDA NASS): County-level corn yields
- Corn masks (USDA CDL): Year-specific field boundaries
- Agricultural documents: PDFs for RAG knowledge base

**Stage 2: Processing**
- Temporal alignment and spatial aggregation
- Corn mask application and county-level statistics
- Water deficit calculation (ETo - Precipitation)
- Document chunking (1000 chars, 200 overlap) and vector embedding

**Stage 3: Storage**
- Google Cloud Storage: Parquet files (daily, weekly, climatology)
- ChromaDB: 864 document chunks with metadata
- Total: 771,411 records (770,547 tabular + 864 document chunks)

## Getting Started

### Prerequisites
- Docker Desktop with Docker Compose
- Google Cloud Platform account with:
  - Service account with Earth Engine access
  - GCS bucket access
  - Gemini API key
- USDA NASS API key (for yield data)

### Quick Start

1. **Clone the repository:**
   ```sh
   git clone https://github.com/sanil-edwin/ac215_agriguard.git
   cd ac215_agriguard
   ```

2. **Configure environment variables:**
   Create a `.env` file in the root directory:
   ```env
   # Google Cloud
   GCP_PROJECT_ID=your-project-id
   GCS_BUCKET_NAME=your-bucket-name
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   
   # API Keys
   GEMINI_API_KEY=your-gemini-api-key
   NASS_API_KEY=your-nass-api-key
   
   # Service URLs (defaults for local development)
   MCSI_SERVICE_URL=http://mcsi_service:8000
   YIELD_SERVICE_URL=http://yield_service:8001
   RAG_SERVICE_URL=http://rag_service:8003
   CHROMADB_HOST=chromadb
   ```

3. **Build and launch all services:**
   ```sh
   docker-compose up --build
   ```

4. **Access the application:**
   - Frontend: `http://localhost:3000`
   - API Orchestrator: `http://localhost:8002`
   - MCSI Service: `http://localhost:8000`
   - Yield Service: `http://localhost:8001`
   - RAG Service: `http://localhost:8003`

### Running the Data Pipeline

Execute the complete data ingestion and processing pipeline:
```sh
cd data_service
python pipeline_complete.py
```

## RAG System Details

The RAG (Retrieval-Augmented Generation) system provides conversational AI grounded in agricultural knowledge:

**Knowledge Base:**
- 18 agricultural PDF documents (864 chunks total)
- USDA Iowa Crop Production reports
- Corn drought stress guides
- MCSI interpretation guides
- Growth stage documentation

**RAG Pipeline:**
1. User query → Vector search (ChromaDB, top-5 chunks)
2. Fetch live MCSI/yield data for selected county
3. Assemble context (documents + live data + system prompt)
4. LLM generation (Gemini 2.5-flash, temperature=0.3)
5. Return grounded response with source citations

**Performance:**
- Total latency: ~1.5s
- Vector search: 300ms
- LLM generation: 1000ms
- Retrieval accuracy: 5 relevant sources per query

## Performance Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| API Latency (p95) | <200ms | ~150ms |
| MCSI Query | <100ms | ~60ms |
| Yield Prediction | <100ms | ~80ms |
| RAG Full Response | <2s | ~1.5s |
| Frontend Load | <2s | ~1.8s |
| Data Pipeline | <30 min | ~25 min |

## Testing

Run the test suite:
```sh
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_api_orchestrator.py
pytest tests/test_data_processing.py
pytest tests/test_rag_service.py
```

**Test Coverage:**
- Unit tests: MCSI calculations, yield predictions, data processing
- Integration tests: API orchestrator coordination, RAG pipeline
- RAG tests: Document loading, vector search, retrieval accuracy

## Deployment

The application is deployed on Google Cloud Platform:
- **Cloud Run:** API services (orchestrator, MCSI, yield, RAG)
- **Cloud Run Jobs:** Data pipeline execution
- **Cloud Storage:** Data lake (Parquet files)
- **Artifact Registry:** Container images
- **Cloud Scheduler:** Automated weekly pipeline triggers

## Documentation

- `docs/APPLICATION_DESIGN.md` - Comprehensive system architecture and design decisions
- `docs/MODEL_TRAINING_SUMMARY.md` - ML model development and evaluation
- `docs/DATA_VERSIONING.md` - Data pipeline and versioning strategy
- Service READMEs in respective directories

## Team

- **Binh Vu** - Data Engineering & ML Infrastructure
- **Sanil Edwin** - Backend Development & API Design
- **Moody Farra** - Frontend Development & UX
- **Artem Biriukov** - ML Modeling & RAG Implementation

**Institution:** Harvard Extension School  
**Course:** AC215 - Applied MLOps  
**Date:** November 2025


