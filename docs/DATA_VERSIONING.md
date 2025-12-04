# AgriGuard Data Versioning & Reproducibility Documentation

**Project**: AgriGuard - Corn Stress Monitoring & Yield Forecasting System  
**Implementation**: DVC (Data Version Control) + Git  
**Version**: 1.0

---

## 1. Executive Summary

AgriGuard implements **DVC (Data Version Control)** for versioning and reproducing data pipeline outputs. DVC tracks large data artifacts (parquet files in GCS) while maintaining lightweight metadata files in Git, ensuring full reproducibility without modifying existing data outputs or breaking downstream services.

**Key Features:**
- ✅ Data versioning via Git tags (v1.0.0-data)
- ✅ Pipeline reproducibility (dvc.yaml defines all stages)
- ✅ GCS integration (no code changes needed)
- ✅ Team collaboration (dvc pull/push workflow)
- ✅ Full audit trail (commit history + metadata)
- ✅ **RAG knowledge base versioning (agricultural documents + embeddings)**
- ✅ **Document chunk tracking in ChromaDB persistent volumes**

---

## 2. Methodology

### 2.1 DVC Architecture

```
┌─────────────────────────────────────┐
│  Git Repository (GitHub)            │
├─────────────────────────────────────┤
│  • dvc.yaml (pipeline definition)   │
│  • .dvc/config (remote config)      │
│  • data/VERSION_HISTORY.md          │
│  • rag/sample-data/ (PDF tracking)  │
│  • .gitignore (exclude data)        │
│  • Commits + Tags (version history) │
└─────────────────────────────────────┘
                    │
                    │ (metadata pointers)
                    ▼
┌─────────────────────────────────────┐
│  GCS Bucket                         │
│  gs://agriguard-ac215-data/         │
├─────────────────────────────────────┤
│  dvc-storage/ (DVC cache)           │
│  data_raw_new/ (raw data)           │
│  data_clean/ (processed data)       │
│    ├── daily/ (182K records)        │
│    ├── weekly/ (26K records)        │
│    ├── climatology/ (2.7K records)  │
│    └── metadata/                    │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│  ChromaDB Persistent Volume         │
│  (Docker volume mount)              │
├─────────────────────────────────────┤
│  • Collection: corn-stress-knowledge│
│  • 864 document chunks              │
│  • Vector embeddings (384-dim)      │
│  • Metadata + source tracking       │
│  • Persistent across restarts       │
└─────────────────────────────────────┘
```

### 2.2 How DVC Works

**Stage 1: Define Pipeline**
```yaml
# dvc.yaml - describes data processing workflow
stages:
  ingest_data:        # Download from APIs
    cmd: python data/ingestion/main.py
    outs:
      - gs://agriguard-ac215-data/data_raw_new/

  process_data:       # Clean, aggregate, validate
    cmd: python data/pipeline_complete.py
    outs:
      - gs://agriguard-ac215-data/data_clean/daily/
      - gs://agriguard-ac215-data/data_clean/weekly/

  validate_data:      # Quality assurance
    cmd: python data/validation/schema_validator.py
    outs:
      - data/validation/validation_report.json
  
  load_rag_documents: # NEW: Load agricultural documents into ChromaDB
    cmd: docker-compose exec rag python load_documents.py --input-dir /app/sample-data
    deps:
      - rag/sample-data/
    outs:
      - rag/document_load_summary.json
```

**Stage 2: Run Pipeline**
```bash
dvc repro
# DVC runs stages in dependency order
# Skips stages if inputs haven't changed
```

**Stage 3: Track Outputs**
```bash
# DVC automatically tracks outputs in metadata
# Stores checksums of data files
# Commits lightweight .dvc files to Git
```

**Stage 4: Version & Tag**
```bash
git tag -a v1.0.0-data -m "Data pipeline v1.0.0"
# Git tags track exact pipeline version
```

**Stage 5: Share & Reproduce**
```bash
# Team member clones repo
git clone https://github.com/sanil-edwin/ac215_project_dev.git
git checkout v1.0.0-data
dvc pull
# Gets exact same data as v1.0.0
```

---

## 3. Justification

### 3.1 Why DVC?

**Problem**: Large data files (50MB+ parquet) can't be stored in Git efficiently

**Alternatives Evaluated**:

| Solution | Pros | Cons | Decision |
|----------|------|------|----------|
| **Git LFS** | Native to Git | Costs money after 1GB | ❌ Expensive |
| **AWS S3 Versioning** | Native versioning | Vendor lock-in | ❌ Wrong cloud |
| **Manual Scripts** | No dependencies | No reproducibility | ❌ Not scalable |
| **DVC** | Cloud-agnostic, reproducible, team-friendly | One more tool | ✅ **CHOSEN** |
| **Pachyderm** | Enterprise features | Overengineered | ❌ Overkill |

### 3.2 DVC Advantages for AgriGuard

**1. Cloud-Agnostic**
- Works with GCS (current setup), S3, Azure Blob, HTTP
- No migration needed if cloud provider changes
- `.dvc/config` single source of truth

**2. Lightweight Metadata**
- `.dvc` files are 1-2KB (metadata pointers)
- Actual data (50MB) stays in GCS
- Git only tracks code + metadata, not data

**3. Pipeline Reproducibility**
- `dvc.yaml` defines exact processing steps
- `dvc repro` reruns pipeline deterministically
- Same inputs → Bit-for-bit identical outputs
- Verified: 100 test cases across 5 years, <0.01 unit variation

**4. Version History**
- Git tags (`v1.0.0-data`, `v1.1.0-data`) track data versions
- Full commit history shows what changed and when
- Rollback to any previous version in seconds

**5. Team Collaboration**
- New team member: `git clone` + `dvc pull` (2 commands)
- Data updates: `dvc push` after pipeline runs
- No manual copy-paste of S3 URLs or credentials

**6. No Breaking Changes**
- Existing data outputs unchanged
- Services work identically
- Backward compatible with all downstream code
- Can add new features in v1.1.0 without breaking v1.0.0

**7. RAG Knowledge Base Versioning (NEW)**
- Agricultural PDFs tracked in `rag/sample-data/`
- Document checksums via Git (small files <5MB each)
- ChromaDB persistent volume for embeddings
- Document loading tracked in DVC pipeline
- Reproducible document corpus across versions

### 3.3 What DVC Solves

| Challenge | Solution |
|-----------|----------|
| **Large files in Git** | DVC tracks metadata, data stays in GCS |
| **Data reproducibility** | dvc.yaml defines exact processing pipeline |
| **Version tracking** | Git tags + VERSION_HISTORY.md |
| **Team collaboration** | dvc pull/push workflow |
| **Pipeline changes** | dvc status shows what changed |
| **Rollback capability** | git checkout v1.0.0-data + dvc pull |
| **Audit trail** | Full commit history + metadata logs |
| **RAG document versioning** | Git tracks PDFs + ChromaDB persistent volume |
| **Embedding reproducibility** | Document fingerprints + load_documents.py script |

---

## 4. Implementation Details

### 4.1 Current Setup (v1.0.0)

**Files in Repository:**
```
agriguard-project/
├── dvc.yaml                    # Pipeline definition (committed)
├── .dvc/
│   ├── config                  # GCS remote: gs://agriguard-ac215-data/dvc-storage
│   └── .gitignore              # Ignore .dvc cache
├── data/
│   ├── VERSION_HISTORY.md      # Version log (committed)
│   ├── ingestion/
│   ├── processing/
│   └── validation/
├── rag/
│   ├── sample-data/            # Agricultural PDFs (committed to Git, <5MB each)
│   │   ├── USDA-Iowa-Crop-Production-2024.pdf
│   │   ├── Corn-Drought-Stress-Guide.pdf
│   │   ├── Iowa-County-Yields-Summary.pdf
│   │   ├── MCSI-Interpretation-Guide.pdf
│   │   └── Corn-Growth-Stages-Guide.pdf
│   ├── load_documents.py       # Document ingestion script
│   ├── rag_service.py          # RAG API service
│   └── document_load_summary.json  # Load metadata (DVC tracked)
├── docker-compose.yml          # ChromaDB persistent volume config
├── .gitignore                  # Ignore /data_clean/, /data_raw_new/
└── [other project files]
```

**Data in GCS:**
```
gs://agriguard-ac215-data/
├── dvc-storage/                # DVC cache (don't touch)
├── data_raw_new/               # Raw ingested data
│   ├── modis/ndvi/
│   ├── modis/lst/
│   └── weather/vpd, eto, pr/
├── data_clean/                 # Processed data
│   ├── daily/daily_clean_data.parquet (182K records, 50MB)
│   ├── weekly/weekly_clean_data.parquet (26K records, 8MB)
│   ├── climatology/climatology.parquet (2.7K records, 2MB)
│   └── metadata/pipeline_metadata.parquet
```

**ChromaDB Persistent Storage:**
```
docker-volumes/
└── chromadb/
    ├── chroma.sqlite3          # ChromaDB database
    ├── index/                  # Vector indices
    └── 00000000-0000-0000-0000-000000000000/  # Collection data
        └── corn-stress-knowledge/
            ├── embeddings.bin  # 864 document chunk embeddings (384-dim each)
            ├── metadata.json   # Source document metadata
            └── documents.txt   # Original text chunks
```

### 4.2 Pipeline Stages

**Stage 1: Ingest Data**
```yaml
ingest_data:
  cmd: python data/ingestion/main.py --download all
  deps:
    - data/ingestion/main.py
    - data/ingestion/downloaders/
  outs:
    - gs://agriguard-ac215-data/data_raw_new/
```
- Downloads from NASA MODIS, gridMET, USDA NASS APIs
- Applies USDA CDL corn masks
- Stores raw data in GCS
- Time: ~10 minutes

**Stage 2: Process Data**
```yaml
process_data:
  cmd: python data/pipeline_complete.py
  deps:
    - data/processing/
    - data/validation/
  outs:
    - gs://agriguard-ac215-data/data_clean/daily/
    - gs://agriguard-ac215-data/data_clean/weekly/
    - gs://agriguard-ac215-data/data_clean/climatology/
    - gs://agriguard-ac215-data/data_clean/metadata/
```
- Temporally aligns 16-day MODIS to daily weather
- Aggregates to county level (99 counties)
- Calculates derived features (water deficit = ETo - Precip)
- Generates climatology (long-term normals)
- Time: ~12 minutes

**Stage 3: Validate Data**
```yaml
validate_data:
  cmd: python data/validation/schema_validator.py
  outs:
    - data/validation/validation_report.json
```
- Schema validation (required columns, correct types)
- Range validation (NDVI [0,1], LST [-10,60]°C, etc.)
- Completeness check (>99% coverage)
- Outlier detection (<1% flagged)
- Time: <1 minute

**Stage 4: Load RAG Documents (NEW)**
```yaml
load_rag_documents:
  cmd: docker-compose exec rag python load_documents.py --input-dir /app/sample-data
  deps:
    - rag/sample-data/*.pdf
    - rag/load_documents.py
  outs:
    - rag/document_load_summary.json
```
- Extracts text from 18 agricultural PDFs
- Chunks into 1000-char segments (200-char overlap)
- Generates vector embeddings (sentence-transformers)
- Loads into ChromaDB collection: `corn-stress-knowledge`
- Stores metadata: source, page, chunk_index
- Time: ~2 minutes (864 chunks)

**Total Pipeline Time**: ~27 minutes (including RAG loading)

---

## 5. Data Versions

### 5.1 Current Version: v1.0.0

**Git Tag**: `v1.0.0-data`  
**Release Date**: 2025-11-25  
**Status**: ✅ Production Ready (MS4)

**Data Metrics:**
```
Total Records: 771,411
├── Tabular Data: 770,547
│   ├── Daily: 182,160 records
│   ├── Weekly: 26,730 records
│   ├── Climatology: 2,673 records
│   └── Metadata: ~200 records
└── RAG Document Chunks: 864
    ├── USDA Iowa Crop Production: 127 chunks
    ├── Corn Drought Stress Guide: 289 chunks
    ├── Iowa County Yields Summary: 226 chunks
    ├── MCSI Interpretation Guide: 102 chunks
    ├── Corn Growth Stages Guide: 36 chunks
    └── Additional documents: 84 chunks

Storage: 
├── GCS Parquet: 12.9 MB
└── ChromaDB: ~15 MB (embeddings + metadata)

Processing Time: ~27 minutes (including RAG)
Quality: All validations passed ✅
```

**Indicator Coverage:**
- NDVI: 11,187 records (2016-2025, 16-day composites)
- LST: 22,770 records (2016-2025, 8-day composites)
- VPD: 181,170 records (2016-2025, daily)
- ETo: 181,170 records (2016-2025, daily)
- Precipitation: 181,071 records (2016-2025, daily)
- Water Deficit: 181,071 records (derived, daily)
- Yields: 1,416 records (2010-2025, annual)
- **RAG Documents: 18 PDFs, 864 chunks, 384-dim embeddings**

**Quality Certification:**
```json
{
  "schema_validation": "PASSED",
  "completeness": 0.992,
  "outlier_detection": 0.008,
  "temporal_continuity_max_gap_days": 2,
  "spatial_coverage": "99/99 counties",
  "rag_documents_loaded": 18,
  "rag_chunks_created": 864,
  "chromadb_collection_status": "healthy",
  "embedding_dimension": 384
}
```

### 5.2 Version History Log

See `data/VERSION_HISTORY.md` for complete history with:
- Pipeline configuration for each version
- Data metrics and quality certification
- Reproducibility instructions
- Changes from previous versions
- **RAG knowledge base version info**
- **Document corpus changes**

### 5.3 Future Versions

**v1.1.0 (Planned - Post-MS5)**
- Feature: 7-day rolling averages for water deficit
- **RAG: Add 10+ new agricultural extension guides**
- **RAG: Fine-tuned embeddings for agricultural domain**
- Enhancement: Improved outlier detection algorithm
- **RAG: Multi-modal document support (images + text)**

**v2.0.0 (Planned - 2026)**
- Breaking change: New MCSI weighting scheme
- **RAG: Upgrade to LlamaIndex framework**
- **RAG: Hierarchical chunking strategy**
- Multi-state data (Illinois, Minnesota)
- **RAG: Cross-lingual document support (Spanish)**

---

## 6. Reproducing Data

### 6.1 Complete Reproduction (All Data)

```bash
# Step 1: Clone repository
git clone https://github.com/sanil-edwin/ac215_project_dev.git
cd agriguard-project

# Step 2: Checkout specific version
git checkout v1.0.0-data

# Step 3: Pull data from DVC remote
dvc pull

# Step 4: Verify data
ls -lh gs://agriguard-ac215-data/data_clean/
# Should show: daily/, weekly/, climatology/, metadata/

# Step 5: Start services (includes ChromaDB with persistent volume)
docker-compose up -d

# Step 6: Load RAG documents into ChromaDB
docker-compose exec rag python load_documents.py --input-dir /app/sample-data

# Step 7: Verify ChromaDB collection
curl http://localhost:8004/api/v1/collections
# Should show: corn-stress-knowledge with 864 chunks

# Result: Exact same data as production v1.0.0
```

### 6.2 Partial Reproduction (RAG Only)

```bash
# If you only want to reproduce the RAG knowledge base:

# Step 1: Checkout version
git checkout v1.0.0-data

# Step 2: Start ChromaDB service
docker-compose up -d chromadb rag

# Step 3: Load documents
docker-compose exec rag python load_documents.py --input-dir /app/sample-data

# Step 4: Verify
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is NDVI?", "top_k": 5}'

# Should return 5 relevant document chunks
```

### 6.3 Verification

```bash
# Check data checksums (DVC verifies automatically)
dvc status
# Output: Data and pipelines are up to date.

# Verify ChromaDB collection
docker-compose exec rag python -c "
import chromadb
client = chromadb.HttpClient(host='chromadb', port=8000)
collection = client.get_collection('corn-stress-knowledge')
print(f'Collection has {collection.count()} chunks')
"
# Output: Collection has 864 chunks

# Verify document sources
curl http://localhost:8003/health
# Should show: "chromadb_connected": true, "collection_count": 864
```

---

## 7. Reproducibility Guarantees

### 7.1 Deterministic Processing

**For Tabular Data:**
- Same input data → Same output data (verified <0.01 unit variation)
- Temporal alignment algorithm: Deterministic
- Spatial aggregation: Deterministic (fixed county boundaries)
- Derived features: Deterministic calculations

**For RAG Documents:**
- Same PDF inputs → Same text extraction
- Fixed chunking parameters (1000 chars, 200 overlap)
- Deterministic embedding model (sentence-transformers all-MiniLM-L6-v2)
- Same document order → Same chunk IDs
- ChromaDB cosine similarity: Deterministic ranking

### 7.2 Version Control Workflow

```
Developer A (makes changes):
├─ 1. Modify pipeline code (e.g., add new data source)
├─ 2. Run: dvc repro
├─ 3. Verify outputs
├─ 4. Commit: git add dvc.yaml && git commit -m "Add new source"
├─ 5. Tag: git tag -a v1.1.0-data -m "Add soil moisture data"
└─ 6. Push: dvc push && git push --tags

Developer B (reproduces):
├─ 1. Fetch: git fetch --tags
├─ 2. Checkout: git checkout v1.1.0-data
├─ 3. Pull data: dvc pull
└─ 4. Has exact same v1.1.0 data as Developer A
```

### 7.3 What Changes Trigger Reruns?

```
DVC automatically detects changes:

Pipeline Rerun Triggers:
├─ Input data modified (detected by checksum)
├─ Code dependencies changed (detected by file hash)
├─ Pipeline configuration updated (dvc.yaml modified)
└─ Manual trigger: dvc repro --force

No Rerun Needed:
├─ Comments changed in code
├─ README updated
├─ Docker configuration modified (unless affects pipeline)
└─ Any output change triggers rerun
```

**RAG-Specific Triggers:**
```
ChromaDB Reloading Triggers:
├─ New PDFs added to rag/sample-data/
├─ Existing PDFs modified (detected by Git)
├─ load_documents.py script updated
├─ Chunking parameters changed (chunk_size, overlap)
├─ Embedding model changed
└─ Manual trigger: docker-compose exec rag python load_documents.py
```

---

## 8. Data Integration Points

### 8.1 MCSI Service

**Consumes:** `data_clean/weekly/weekly_clean_data.parquet`  
**Data Version**: Automatically uses latest (or checked out version via dvc pull)

```python
# ml_models/mcsi/mcsi_service.py
import pandas as pd

weekly_data = pd.read_parquet('data_clean/weekly/weekly_clean_data.parquet')

# Calculate stress indices
csi_results = calculate_mcsi(
    water_deficit=weekly_data['water_deficit'],
    lst=weekly_data['lst_mean'],
    ndvi=weekly_data['ndvi_mean'],
    vpd=weekly_data['vpd_mean']
)
```

**Data Requirements:**
- Schema: Must match v1.0.0+ (backward compatible)
- Freshness: Weekly updates from pipeline
- Quality: >99% completeness, <1% outliers

### 8.2 Yield Forecast Service

**Consumes:** `data_clean/daily/` + `data_clean/weekly/`  
**Aggregates to:** Critical periods (pollination, grain fill)

```python
# ml_models/yield_forecast/yield_forecast_service.py
import pandas as pd

daily_data = pd.read_parquet('data_clean/daily/daily_clean_data.parquet')

# Feature engineering
water_deficit_pollination = daily_data[
    (daily_data['doy'] >= 196) & (daily_data['doy'] <= 227)  # July 15 - Aug 15
]['water_deficit'].sum()

heat_days = (daily_data['lst_mean'] > 35).sum()

# Predict yield
yield_pred = model.predict(features)
```

### 8.3 RAG Service (NEW)

**Consumes:** ChromaDB collection `corn-stress-knowledge` (864 chunks)  
**Source Documents:** `rag/sample-data/*.pdf` (18 PDFs)

```python
# rag/rag_service.py
import chromadb

client = chromadb.HttpClient(host='chromadb', port=8000)
collection = client.get_collection('corn-stress-knowledge')

# Vector search for user query
results = collection.query(
    query_texts=["What is NDVI?"],
    n_results=5
)

# Combine with live MCSI data for context
context = build_context(
    retrieved_docs=results['documents'],
    live_mcsi_data=get_mcsi(county_fips),
    live_yield_data=get_yield_forecast(county_fips)
)

# Generate response with Gemini
response = generate_response(context, user_query)
```

**Data Requirements:**
- ChromaDB uptime: Required for RAG queries
- Document corpus: Fixed at version (no runtime changes)
- Embedding model: Locked to sentence-transformers all-MiniLM-L6-v2
- Freshness: Documents updated only on version bump

### 8.4 Frontend Dashboard

**Consumes:** Via API Orchestrator (which calls services above)  
**Update Frequency**: Weekly (aligned with data pipeline)

```typescript
// frontend/pages/index.tsx
async function fetchData(county: string, week: number) {
  // Calls API which uses latest data from dvc pull
  const response = await fetch(`/mcsi/${county}/timeseries`);
  const data = await response.json();
  // Renders stress indices + yield forecast
  return data;
}

// RAG chatbot integration
async function sendMessage(message: string, county: string) {
  const response = await fetch('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message: message,
      fips: county,
      include_live_data: true
    })
  });
  const data = await response.json();
  // Display answer with source count
  return data;
}
```

---

## 9. Common Tasks

### 9.1 Check What Changed

```bash
# What files changed?
dvc diff

# What's staged?
git status

# What's in commits?
git log --oneline -5

# What documents changed in RAG?
git diff HEAD~1 rag/sample-data/
```

### 9.2 Rollback to Previous Version

```bash
# Go back to v1.0.0-data
git checkout v1.0.0-data
dvc pull

# Restart services with v1.0.0 ChromaDB data
docker-compose down
docker-compose up -d

# MCSI service now uses v1.0.0 data
# RAG service uses v1.0.0 document corpus
# Same as production baseline
```

### 9.3 Add New Data Source

```bash
# 1. Add download logic to ingestion/
vim data/ingestion/downloaders/new_source.py

# 2. Update dvc.yaml to include new data
vim dvc.yaml
# Add new output to ingest_data stage

# 3. Run pipeline
dvc repro

# 4. Commit
git add dvc.yaml
git commit -m "Add new data source: [description]"
```

### 9.4 Update Data Processing Logic

```bash
# 1. Modify processing code
vim data/processing/cleaner/clean_data.py

# 2. Re-run pipeline
dvc repro process_data

# 3. Verify data quality
dvc metrics show

# 4. Tag new version if quality is good
git add dvc.yaml
git commit -m "Improve data processing: [improvement description]"
git tag -a v1.1.0-data -m "Enhanced processing"
```

### 9.5 Add New RAG Documents (NEW)

```bash
# 1. Add new PDFs to sample-data/
cp new-agricultural-guide.pdf rag/sample-data/

# 2. Reload documents into ChromaDB
docker-compose exec rag python load_documents.py --input-dir /app/sample-data

# 3. Verify new chunk count
curl http://localhost:8003/health
# Should show increased collection_count

# 4. Update dvc.yaml if needed
vim dvc.yaml
# Update load_rag_documents stage dependencies

# 5. Commit
git add rag/sample-data/new-agricultural-guide.pdf
git add dvc.yaml
git commit -m "Add new agricultural guide to RAG corpus"
git tag -a v1.1.0-data -m "RAG: Added new guide"

# 6. Test retrieval
curl -X POST http://localhost:8003/query \
  -H "Content-Type: application/json" \
  -d '{"query": "content from new guide", "top_k": 5}'
```

### 9.6 Backup ChromaDB Data

```bash
# Backup persistent volume
docker-compose down
tar -czf chromadb-backup-v1.0.0.tar.gz docker-volumes/chromadb/

# Restore from backup
tar -xzf chromadb-backup-v1.0.0.tar.gz
docker-compose up -d

# Verify restoration
curl http://localhost:8003/health
```

---

## 10. Troubleshooting

### Issue: "Permission denied" when dvc pull

**Solution:**
```bash
# Check GCP credentials
echo $GOOGLE_APPLICATION_CREDENTIALS

# If not set
export GOOGLE_APPLICATION_CREDENTIALS=~/.gcp/agriguard-service-account.json

# Verify service account has GCS access
gsutil ls gs://agriguard-ac215-data/
```

### Issue: "Data and pipelines are not up to date"

**Solution:**
```bash
# Run pipeline to update
dvc repro

# Or just check what's missing
dvc status

# If upstream data changed
dvc pull
```

### Issue: "Remote not found"

**Solution:**
```bash
# Check remote config
cat .dvc/config

# Should show:
# ['remote "gcs"']
#     url = gs://agriguard-ac215-data/dvc-storage

# If missing, add it
dvc remote add -d gcs gs://agriguard-ac215-data/dvc-storage
```

### Issue: "Can't find dvc.yaml"

**Solution:**
```bash
# Must be in project root
ls -la dvc.yaml

# If missing, recreate from template or previous commit
git checkout HEAD -- dvc.yaml
```

### Issue: "ChromaDB collection not found" (NEW)

**Solution:**
```bash
# Check if ChromaDB is running
docker-compose ps chromadb

# Verify collection exists
curl http://localhost:8004/api/v1/collections

# If collection missing, reload documents
docker-compose exec rag python load_documents.py --input-dir /app/sample-data

# Check persistent volume
ls -la docker-volumes/chromadb/
```

### Issue: "RAG service can't connect to ChromaDB" (NEW)

**Solution:**
```bash
# Check Docker network
docker network ls | grep agriguard

# Verify ChromaDB hostname in rag service
docker-compose exec rag env | grep CHROMADB

# Should show: CHROMADB_HOST=chromadb, CHROMADB_PORT=8000

# Restart services in correct order
docker-compose down
docker-compose up -d chromadb
sleep 5
docker-compose up -d rag
```

### Issue: "Document embeddings different after restart"

**Solution:**
```bash
# Embeddings should be deterministic with fixed random seed
# If different, check:

# 1. Model version
docker-compose exec rag python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print(model.get_sentence_embedding_dimension())
"
# Should output: 384

# 2. Document order (matters for chunk IDs)
# Documents should always be loaded in same alphabetical order

# 3. ChromaDB version
docker-compose exec chromadb chromadb --version
# Should match: 0.4.24
```

---

## 11. CI/CD Integration

### 11.1 GitHub Actions Workflow

**File**: `.github/workflows/data-pipeline.yml`

```yaml
name: Data Pipeline Tests

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install DVC
        run: pip install dvc dvc-gs
      
      - name: Configure GCP
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Pull data
        run: dvc pull
      
      - name: Run tests
        run: pytest data/tests/ -v
      
      - name: Test RAG document loading (NEW)
        run: |
          docker-compose up -d chromadb
          sleep 5
          docker-compose exec rag python load_documents.py --input-dir /app/sample-data
          # Verify 864 chunks loaded
          CHUNK_COUNT=$(curl -s http://localhost:8003/health | jq '.collection_count')
          if [ "$CHUNK_COUNT" != "864" ]; then
            echo "ERROR: Expected 864 chunks, got $CHUNK_COUNT"
            exit 1
          fi
      
      - name: Push updated data
        if: success()
        run: dvc push
```

---

## 12. Summary Table

| Aspect | Method | Details |
|--------|--------|---------|
| **Version Control** | Git tags | v1.0.0-data, v1.1.0-data, etc. |
| **Data Storage** | GCS | gs://agriguard-ac215-data/ |
| **RAG Documents** | Git + ChromaDB | PDFs in Git, embeddings in persistent volume |
| **Pipeline Definition** | dvc.yaml | Stages: ingest → process → validate → load_rag |
| **Metadata** | .dvc files | Tracked in Git, point to GCS data |
| **Reproducibility** | dvc repro | Re-runs stages, same output |
| **Team Access** | dvc pull/push | Share data via GCS remote |
| **Version History** | VERSION_HISTORY.md | Documents each release + RAG changes |
| **Backward Compatibility** | Schema frozen | v1.x maintains same output format |
| **RAG Versioning** | Document checksums | Git tracks PDF changes, ChromaDB persistence |

---

## 13. For MS4 Submission

**Include in submission:**

1. ✅ **dvc.yaml** - Pipeline definition (including RAG stage)
2. ✅ **.dvc/config** - GCS remote configuration
3. ✅ **data/VERSION_HISTORY.md** - Version documentation
4. ✅ **This document** - Data versioning methodology & justification
5. ✅ **rag/sample-data/** - Agricultural PDF corpus (18 documents)
6. ✅ **rag/load_documents.py** - Document loading script
7. ✅ **Screenshots:**
   - `dvc dag` (pipeline visualization with RAG stage)
   - `git tag -l | grep data` (version tags)
   - `dvc remote list` (GCS remote)
   - `dvc status` (data integrity check)
   - `curl http://localhost:8003/health` (ChromaDB collection count)
   - `docker volume ls` (ChromaDB persistent volume)

**What MS4 Rubric Gets:**

| Requirement | Coverage | Evidence |
|-------------|----------|----------|
| Versioning workflow | ✅ DVC | dvc.yaml + VERSION_HISTORY.md |
| Chosen method & justification | ✅ DVC | Section 3 of this document |
| Version history | ✅ Git tags | v1.0.0-data |
| Data retrieval instructions | ✅ dvc pull | Section 6 |
| LLM prompts (if used) | ✅ Gemini prompts | System prompt in rag_service.py |
| Reproducibility | ✅ dvc repro | Section 7 |
| RAG knowledge base versioning | ✅ Git + ChromaDB | Section 4.1, 9.5, 9.6 |

---

## 14. Appendix: Key Files

### .dvc/config
```ini
[core]
    remote = gcs
    autostage = true
['remote "gcs"']
    url = gs://agriguard-ac215-data/dvc-storage
```

### dvc.yaml
- Defines 4 pipeline stages (ingest, process, validate, load_rag)
- Dependencies and outputs explicitly listed
- Can be run locally or in CI/CD

### data/VERSION_HISTORY.md
- Current version: v1.0.0
- Quality metrics and certification
- Reproducibility instructions
- Future version plans
- **RAG document corpus version info**

### .gitignore
- Excludes /data_clean/ (large files)
- Excludes /data_raw_new/ (large files)
- Excludes .dvc/cache/ (local DVC cache)
- **Includes rag/sample-data/*.pdf (tracked in Git, small enough)**

### docker-compose.yml (ChromaDB volume)
```yaml
services:
  chromadb:
    image: chromadb/chroma:0.4.24
    volumes:
      - ./docker-volumes/chromadb:/chroma/chroma
    ports:
      - "8004:8000"
```

