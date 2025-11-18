# AgriGuard RAG AI Chat - Complete Implementation Guide

## 📋 Overview

This guide provides step-by-step instructions to add a RAG-powered AI chat system to your AgriGuard application. The system combines:
- **Vector search** over agricultural knowledge base (PDFs, research papers)
- **Real-time MCSI data** for context-aware responses
- **Google Gemini** for natural language generation
- **Conversational memory** for multi-turn dialogues

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Frontend (Next.js)                       │
│  Component: <ChatInterface />                               │
│  - User message input                                       │
│  - Conversation display                                     │
│  - Source citations                                         │
└────────────────┬───────────────────────────────────────────┘
                 │ POST /api/chat
                 ↓
┌────────────────────────────────────────────────────────────┐
│              Backend API (FastAPI)                         │
│  Module: rag_chat.py                                        │
│  - Endpoint: POST /api/chat                                 │
│  - Integrates MCSI data + vector search                     │
│  - Returns: response + sources + context                    │
└────────┬────────────────┬──────────────────────────────────┘
         │                 │
         ↓                 ↓
┌─────────────────┐  ┌──────────────────────────────────────┐
│ MCSI Data (GCS) │  │  Vector Store (Chroma)               │
│ - Real-time     │  │  Module: ingest_documents.py          │
│ - County-level  │  │  - PDF embeddings                     │
│ - Stress scores │  │  - MCSI guides                        │
└─────────────────┘  └──────────┬───────────────────────────┘
                                 ↓
                      ┌──────────────────────────────────────┐
                      │  LangChain + Google Gemini           │
                      │  - Retrieval augmented generation    │
                      │  - Conversation memory               │
                      │  - Prompt engineering                │
                      └──────────────────────────────────────┘
```

---

## 📦 Step 1: Install Dependencies

### Backend Dependencies

Add to `backend-api/requirements.txt`:

```txt
# RAG System
langchain==0.1.20
langchain-community==0.0.38
langchain-google-genai==0.0.11
langchain-chroma==0.1.1

# Vector Store & Embeddings
chromadb==0.4.24
sentence-transformers==2.7.0

# Document Processing
pypdf==4.2.0
python-docx==1.1.0
unstructured==0.13.7
markdown==3.6

# Google AI
google-generativeai==0.5.4

# Utilities
tiktoken==0.7.0
tenacity==0.8.3
```

### Frontend Dependencies

The `ChatInterface` component uses standard React/Next.js with Lucide icons (already in your project).

---

## 📚 Step 2: Prepare Knowledge Base

### Create Directory Structure

```bash
cd backend-api
mkdir -p knowledge_base/{pdfs,guides,mcsi_docs}
mkdir -p chroma_db
```

### Add Documents

Place agricultural documents in `knowledge_base/`:

**Recommended Documents (10-15 PDFs):**

1. **Iowa State Extension Corn Guides**
   - Corn growth stages
   - Water stress management
   - Heat stress in corn
   - Yield prediction factors

2. **Research Papers**
   - NDVI and corn yield relationships
   - Remote sensing for crop stress
   - Drought impact on corn physiology
   - VPD effects on pollination

3. **USDA Resources**
   - Corn production handbook
   - Irrigation scheduling guides
   - Crop condition reports

4. **Custom Documentation**
   - Your MCSI calculation methodology (copy from README)
   - Historical yield data analysis
   - County-specific insights

### Sample Knowledge Base Document

Create `knowledge_base/guides/iowa_corn_stress_guide.md`:

```markdown
# Iowa Corn Stress Management Guide

## Understanding MCSI Scores

### Low Stress (0.0 - 0.3)
- Optimal growing conditions
- NDVI > 0.7 (healthy canopy)
- Adequate soil moisture
- Expected yield: 95-100% of average

### Moderate Stress (0.3 - 0.5)
- Minor vegetation stress
- NDVI 0.5-0.7
- Monitor closely
- Expected yield: 85-95% of average

### High Stress (0.5 - 0.7)
- Significant crop stress
- NDVI < 0.5
- Immediate action needed
- Expected yield: 70-85% of average

### Severe Stress (0.7 - 1.0)
- Critical conditions
- Irreversible damage possible
- Expected yield: < 70% of average

## Critical Growth Stages

### Vegetative (V6-V10)
- Rapid growth phase
- Early June in Iowa
- Establishes yield potential

### Reproductive (VT-R1)
- MOST CRITICAL PERIOD
- Mid-July in Iowa
- Tasseling and silking
- Stress here reduces yield 40-50%

### Grain Fill (R2-R4)
- August in Iowa
- Determines kernel weight
- Stress here reduces yield 15-25%

## Management Recommendations

### When MCSI Shows Moderate Stress:
1. Monitor soil moisture
2. Check weather forecast
3. Prepare irrigation if available
4. Scout for pests/diseases

### When MCSI Shows High Stress:
1. Irrigate immediately (1-1.5 inches)
2. Prioritize critical growth stages
3. Assess root health
4. Reduce crop competition

### When MCSI Shows Severe Stress:
1. Emergency irrigation if possible
2. Consider crop insurance assessment
3. May need salvage harvest
4. Document for records
```

---

## 🔧 Step 3: Set Up Vector Store

### Copy Ingestion Script

Copy `ingest_documents.py` to `backend-api/`:

```bash
cp /path/to/ingest_documents.py backend-api/
```

### Run Document Ingestion

```bash
cd backend-api

# Install dependencies first
pip install -r requirements.txt

# Run ingestion
python ingest_documents.py
```

**Expected Output:**
```
====================================================================
Starting AgriGuard RAG Document Ingestion
====================================================================

Loading PDF documents...
Loaded 25 PDF pages
Loading Markdown documents...
Loaded iowa_corn_stress_guide.md
Loaded MCSI_methodology.md
...
Total documents loaded: 35

Splitting documents into chunks...
Created 487 document chunks

Creating vector store...
Vector store created with 487 chunks
Persisted to: ./chroma_db

====================================================================
Testing vector store retrieval...
====================================================================

Query: What does an MCSI score of 0.6 mean?
  Result 1:
  Source: MCSI_Interpretation_Guide
  Content preview: High Stress (0.5 - 0.7): Significant stress
  ...

Document ingestion completed successfully!
====================================================================
```

---

## 🚀 Step 4: Integrate RAG into Backend API

### Add RAG Module

Copy `rag_chat.py` to `backend-api/`:

```bash
cp /path/to/rag_chat.py backend-api/
```

### Update `api_extended.py`

Add RAG initialization to your existing FastAPI startup:

```python
# Add imports at top
from rag_chat import (
    rag_system,
    initialize_rag_system,
    ChatRequest,
    ChatResponse
)

# In startup event
@app.on_event("startup")
async def startup():
    """Load models, data, and RAG system"""
    global models, mcsi_data, county_names
    
    logger.info("="*60)
    logger.info("AGRIGUARD API STARTUP")
    logger.info("="*60)
    
    # ... your existing startup code ...
    
    # Initialize RAG system (NEW)
    try:
        logger.info("Initializing RAG chat system...")
        rag_initialized = await initialize_rag_system()
        
        if rag_initialized:
            # Provide data sources to RAG system
            rag_system.set_data_sources(mcsi_data, county_names)
            logger.info("✓ RAG system ready")
        else:
            logger.warning("⚠ RAG system failed to initialize (chat will be unavailable)")
    
    except Exception as e:
        logger.error(f"RAG initialization error: {e}")
    
    logger.info("="*60)
    logger.info("STARTUP COMPLETE")
    logger.info("="*60)

# Add chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    AI chat endpoint for corn stress interpretation and guidance
    
    - **message**: User's question or message
    - **county_fips**: Optional county FIPS for context
    - **conversation_id**: Optional conversation ID for history
    
    Returns AI response with sources and context
    """
    return await rag_system.chat(request)
```

### Set Environment Variable

Add your Google API key:

```bash
export GOOGLE_API_KEY="your-gemini-api-key-here"
```

Get your API key at: https://makersuite.google.com/app/apikey

---

## 🎨 Step 5: Add Chat UI to Frontend

### Copy Chat Component

Copy `ChatInterface.tsx` to `frontend-app/src/components/`:

```bash
cp /path/to/ChatInterface.tsx frontend-app/src/components/
```

### Integrate into Main Page

Update your main dashboard page (`app/page.tsx` or wherever):

```tsx
import ChatInterface from '@/components/ChatInterface';

export default function Dashboard() {
  const [selectedCounty, setSelectedCounty] = useState<string>('');
  const [countyName, setCountyName] = useState<string>('');
  
  // API URL from environment or default
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 
                 'https://agriguard-api-ms4-723493210689.us-central1.run.app';

  return (
    <div className="container mx-auto p-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column - County Selector, MCSI Display, etc. */}
        <div className="lg:col-span-2 space-y-6">
          {/* Your existing components */}
          <CountySelector onSelect={handleCountySelect} />
          <MCSIDisplay county={selectedCounty} />
          <YieldPredictor county={selectedCounty} />
        </div>

        {/* Right Column - AI Chat */}
        <div className="lg:col-span-1">
          <ChatInterface
            selectedCounty={selectedCounty}
            countyName={countyName}
            apiUrl={apiUrl}
          />
        </div>
      </div>
    </div>
  );
}
```

---

## 🐳 Step 6: Update Docker Configuration

### Update Backend Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./
COPY models/ ./models/

# Copy RAG components (NEW)
COPY knowledge_base/ ./knowledge_base/
COPY chroma_db/ ./chroma_db/

# Expose port
EXPOSE 8080

# Start server
CMD ["uvicorn", "api_extended:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Update `.dockerignore`

```
# Keep RAG components in build
!knowledge_base/
!chroma_db/

# Exclude large files if any
knowledge_base/**/*.zip
*.pyc
__pycache__/
```

---

## 🚢 Step 7: Deploy to Cloud Run

### Build and Push Backend

```bash
cd backend-api

# Build image
docker build -t us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-rag:latest .

# Push to registry
docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-rag:latest

# Deploy to Cloud Run
gcloud run deploy agriguard-api-ms4 \
  --image=us-central1-docker.pkg.dev/agriguard-ac215/agriguard/api-rag:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --timeout=300 \
  --set-env-vars GOOGLE_API_KEY=your-key-here
```

**Note:** Increased memory (4Gi) and CPU (2) needed for embeddings model.

### Build and Deploy Frontend

```bash
cd frontend-app

# Build
npm run build

# Build Docker image
docker build -t us-central1-docker.pkg.dev/agriguard-ac215/agriguard/frontend-rag:latest .

# Push and deploy
docker push us-central1-docker.pkg.dev/agriguard-ac215/agriguard/frontend-rag:latest

gcloud run deploy agriguard-frontend-ms4 \
  --image=us-central1-docker.pkg.dev/agriguard-ac215/agriguard/frontend-rag:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars NEXT_PUBLIC_API_URL=https://agriguard-api-ms4-*.run.app
```

---

## 🧪 Step 8: Test the System

### Test Backend API Locally

```bash
# Start backend
cd backend-api
uvicorn api_extended:app --reload --host 0.0.0.0 --port 8080
```

Test chat endpoint:

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What does an MCSI score of 0.65 mean for my corn?",
    "county_fips": "19153"
  }'
```

**Expected Response:**
```json
{
  "response": "An MCSI score of 0.65 indicates High Stress in your corn crop...",
  "sources": [
    {
      "source": "MCSI_Interpretation_Guide",
      "content": "High Stress (0.5 - 0.7): Significant stress..."
    }
  ],
  "context": {
    "county_name": "Polk",
    "mcsi_score": 0.65,
    "stress_level": "High"
  },
  "conversation_id": "conv_1234567890",
  "timestamp": "2025-11-17T21:30:00Z"
}
```

### Test Frontend Locally

```bash
cd frontend-app
npm run dev
```

Navigate to `http://localhost:3000` and:
1. Select a county
2. Open the AI chat interface
3. Ask questions like:
   - "What does my current MCSI score mean?"
   - "How will stress affect my yield?"
   - "What should I do about high stress?"

---

## 📊 Step 9: Monitor and Optimize

### Check Logs

```bash
# Cloud Run logs
gcloud run services logs read agriguard-api-ms4 --region=us-central1 --limit=50

# Look for:
# - "✓ RAG system initialized successfully"
# - "Processing chat query..."
# - "Generated response"
```

### Monitor Performance

- **Response Time:** Target < 5 seconds
- **Token Usage:** Monitor Gemini API usage
- **Memory:** Should stay under 4Gi
- **Cold Starts:** Consider min-instances=1 if needed

### Common Issues

**Issue 1: "RAG system not initialized"**
- Solution: Check `chroma_db` directory exists in container
- Solution: Verify GOOGLE_API_KEY is set

**Issue 2: Slow responses**
- Solution: Reduce retrieval k from 3 to 2
- Solution: Use smaller embedding model
- Solution: Increase Cloud Run CPU/memory

**Issue 3: Generic responses**
- Solution: Add more specific documents to knowledge base
- Solution: Improve prompt engineering in `rag_chat.py`
- Solution: Ensure MCSI context is being passed correctly

---

## 🎯 Step 10: Enhance Knowledge Base

### Add More Documents

**Research Papers (Google Scholar):**
```
site:scholar.google.com corn stress NDVI Iowa
site:scholar.google.com yield prediction remote sensing
site:scholar.google.com VPD corn pollination
```

**Iowa State Extension:**
- https://crops.extension.iastate.edu/corn
- Download PDF guides on corn management

**USDA Resources:**
- https://www.nass.usda.gov/
- Corn production reports and statistics

### Re-run Ingestion

```bash
# After adding new documents
python ingest_documents.py

# Rebuild and deploy
docker build ...
```

---

## 🎓 MS4 Demonstration

### Required Deliverables

1. **Screenshot of Chat Interface**
   - Show conversation with MCSI interpretation
   - Include source citations visible
   - Show county context

2. **API Documentation**
   - Document `/api/chat` endpoint
   - Include example requests/responses

3. **Knowledge Base Inventory**
   - List all documents in `knowledge_base/`
   - Note: 10-15 documents minimum

4. **Demo Conversation Examples**
   - MCSI interpretation query
   - Yield prediction explanation
   - Management recommendation
   - Show RAG retrieval working (sources)

### Sample Demo Script

```
Conversation 1: MCSI Interpretation
User: "My MCSI score is 0.58 in Polk County. What does this mean?"
AI: [Explains High Stress with specific recommendations]

Conversation 2: Yield Impact
User: "How will this stress level affect my expected yield?"
AI: [References historical data and predicts impact]

Conversation 3: Action Items
User: "What should I do right now?"
AI: [Provides specific management actions based on growth stage]
```

---

## 📞 Support and Troubleshooting

### Quick Diagnostics

```bash
# Check if vector store was created
ls -lh backend-api/chroma_db/

# Test document ingestion
cd backend-api
python -c "from ingest_documents import AgriGuardDocumentIngestion; ing = AgriGuardDocumentIngestion(); docs = ing.load_documents(); print(f'Loaded {len(docs)} documents')"

# Test RAG initialization
python -c "import asyncio; from rag_chat import initialize_rag_system; asyncio.run(initialize_rag_system())"
```

### Environment Variables Checklist

```bash
# Required for backend
export GOOGLE_API_KEY="your-key"
export GCP_PROJECT="agriguard-ac215"
export BUCKET_NAME="agriguard-mcsi-data"

# Required for frontend
export NEXT_PUBLIC_API_URL="https://agriguard-api-ms4-*.run.app"
```

---

## ✅ Success Checklist

- [ ] Dependencies installed (backend + frontend)
- [ ] Knowledge base created with 10+ documents
- [ ] Vector store created (`chroma_db/` exists)
- [ ] RAG system initializes without errors
- [ ] `/api/chat` endpoint responds correctly
- [ ] Frontend chat interface displays
- [ ] Conversations work with context
- [ ] Sources are cited correctly
- [ ] Deployed to Cloud Run
- [ ] Documentation screenshots taken
- [ ] Ready for MS4 submission

---

## 🚀 Next Steps

1. **Expand Knowledge Base**
   - Add more Iowa-specific documents
   - Include historical drought case studies
   - Add hybrid selection guides

2. **Improve Prompts**
   - Fine-tune system prompts
   - Add persona/tone controls
   - Improve source citation format

3. **Add Features**
   - Voice input/output
   - Multi-language support
   - Export conversation history
   - Share chat sessions

4. **Optimize Performance**
   - Cache common queries
   - Implement streaming responses
   - Add rate limiting

---

**Implementation Time Estimate:**
- Setup + Document Collection: 2 hours
- Backend Integration: 2 hours
- Frontend Integration: 1.5 hours
- Testing + Debugging: 1.5 hours
- **Total: 7 hours**

**Deadline:** November 25, 2025 (8 days remaining)

**Priority:** HIGH - Core MS4 requirement

---

**Questions?** Check logs, test each component independently, and ensure all environment variables are set!

Good luck with your RAG implementation! 🌽🤖
