# RAG Pipeline for AgriGuard

A **Retrieval-Augmented Generation (RAG)** pipeline designed for agricultural document analysis, focusing on Iowa crop/yield data. This system processes PDF documents, stores them in a vector database, and enables intelligent question-answering using Google's Gemini LLM.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Usage](#usage)
- [Chunking Methods](#chunking-methods)
- [Project Structure](#project-structure)
- [Commands Reference](#commands-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Overview

This RAG pipeline enables you to:
1. **Ingest** agricultural PDF documents (crop reports, yield data, etc.)
2. **Process** them using advanced chunking strategies
3. **Store** document embeddings in ChromaDB vector database
4. **Query** the knowledge base with natural language
5. **Chat** with an AI assistant powered by Gemini, grounded in your documents

The pipeline is containerized using Docker for consistent deployment and integrates with Google Cloud Platform for AI/ML services and storage.

## Architecture

```
┌─────────────────┐
│   PDF Documents │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Text Extraction (pdfplumber)   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Chunking Strategy (3 methods)  │
│  • Sentence Window              │
│  • Auto-Merging (Hierarchical)  │
│  • Semantic Splitting           │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Embedding (Vertex AI)          │
│  text-embedding-004             │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Vector Store (ChromaDB)        │
│  Persistent storage             │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Retrieval + Generation         │
│  (LlamaIndex + Gemini)          │
└─────────────────────────────────┘
```

## Features

### Core Functionality
- **PDF Processing**: Extracts text from agricultural PDF reports using `pdfplumber`
- **Multiple Chunking Strategies**: Choose from 3 research-backed chunking methods
- **Vector Search**: Semantic search powered by Vertex AI embeddings (768-dimensional)
- **LLM Integration**: Chat interface using Google's Gemini 2.0 Flash
- **Persistent Storage**: ChromaDB with persistent volumes for data retention
- **GCS Integration**: Optional upload of artifacts to Google Cloud Storage

### Advanced Features
- **LlamaIndex Framework**: High-level abstractions for RAG workflows
- **Metadata Tracking**: Comprehensive metadata for each document and chunk
- **Collection Management**: Create, query, and delete multiple collections
- **Batch Processing**: Efficient batch embedding (up to 100 documents at a time)
- **Interactive CLI**: User-friendly command-line interface

## Prerequisites

- **Docker** and **Docker Compose**
- **Google Cloud Project** with:
  - Vertex AI API enabled
  - Cloud Storage API enabled (optional, for GCS uploads)
  - Service account with appropriate permissions
- **Service Account Key**: JSON file with credentials

### GCP Permissions Required
You need to hava service account set up in GCP. Your service account needs to have these permissions:
 - Storage Admin
 - Vertex AI User

## Setup

### 1. Prepare Your Environment

```bash
# Clone the repository and navigate to the rag-pipeline directory
cd rag-pipeline

# Create a secrets directory (two levels up from current directory)
mkdir -p ../../secrets/

# Place your GCP service account key in the secrets directory
cp /path/to/your/service-account-key.json ../../secrets/agriguard-service-account.json
```

Make sure to name your file `agriguard-service-account.json`

### 2. Build and Run

```bash
# Create the container image
sh docker-shell.sh

```

This will:
- Create a Docker network (`agri-rag-network`)
- Build the RAG pipeline image
- Start ChromaDB and the CLI container
- Drop you into an interactive shell

## Usage

### Quick Start: Auto-Load Mode

To automatically load all PDFs from `sample-data/` using the sentence-window method:

If you haven't already, create the container image by running - 

```bash
# Create the container image
sh docker-shell.sh
```

### Interactive Mode (Default)

Once inside the container, you have access to several CLI commands:

#### 1. Load Documents

Process PDFs and load them into the vector database:

```bash
python rag_cli.py load \
    --collection-name "iowa-crops" \
    --method sentence-window \
    --input-dir sample-data
```

**Options:**
- `--collection-name`: Name for your collection (required)
- `--method`: Chunking method (`sentence-window`, `automerging`, or `semantic`)
- `--input-dir`: Directory containing PDFs (default: `sample-data`)

#### 2. Query Documents

Perform semantic search without LLM generation:

```bash
python rag_cli.py query \
    "What are the corn yield forecasts for Iowa?" \
    --collection-name "iowa-crops"
```

Returns top-5 most relevant document chunks with similarity scores.

#### 3. Chat with the AI Assistant

Ask questions and get AI-generated answers grounded in your documents:

```bash
python rag_cli.py chat \
    "What weather conditions affected corn yields this year?" \
    --collection-name "iowa-crops"
```

The system will:
1. Retrieve the top-5 most relevant chunks
2. Send them as context to Gemini
3. Generate a comprehensive, grounded response

#### 4. Database Management

**View collections:**
```bash
python rag_cli.py info
```

**Delete a specific collection:**
```bash
python rag_cli.py delete-collection "iowa-crops"
```

**Reset entire database (⚠️ DANGEROUS):**
```bash
python rag_cli.py reset
```

## Chunking Methods

The pipeline supports three advanced chunking strategies:

### 1. Sentence Window (Default)
- **Best for**: General-purpose retrieval
- **How it works**: Each sentence becomes a searchable node with surrounding context
- **Window size**: 3 sentences before/after (configurable)
- **Use case**: Balanced between precision and context

```python
# Example: Sentence becomes searchable but includes neighbors for context
"Corn yields reached 200 bu/acre."  # ← Main sentence
# Includes 3 sentences before and after for context
```

### 2. Auto-Merging (Hierarchical)
- **Best for**: Multi-scale retrieval (detailed + overview)
- **How it works**: Creates parent-child-leaf hierarchy
- **Chunk sizes**: [2048, 512, 128] characters (large → medium → small)
- **Use case**: When you need both fine-grained and broader context

```python
# Example hierarchy:
Parent (2048 chars): Entire section on corn yields
├─ Child (512 chars): Paragraph about Iowa yields  
│  └─ Leaf (128 chars): "Corn yields reached 200 bu/acre in Iowa"
└─ Child (512 chars): Another paragraph
```

### 3. Semantic Splitting
- **Best for**: Natural topic boundaries
- **How it works**: Uses embedding similarity to find semantic breaks
- **Threshold**: Percentile-based (95th percentile by default)
- **Use case**: When documents have clear topic shifts

```python
# Splits at semantic boundaries:
Chunk 1: "Corn planting and early growth... [topic A]"
Chunk 2: "Weather patterns in summer... [topic B]"  # ← Split here
Chunk 3: "Harvest forecasts show... [topic C]"
```

### Choosing a Method

| Method | Speed | Context Preservation | Best For |
|--------|-------|---------------------|----------|
| Sentence Window | Fast | Good | General Q&A |
| Auto-Merging | Medium | Excellent | Complex queries |
| Semantic | Slow | Very Good | Topic-specific queries |

## 📁 Project Structure

```
rag-pipeline/
├── README.md                    # This file
├── pyproject.toml              # Python dependencies (uv)
├── Dockerfile                  # Container image definition
├── docker-compose.yaml         # Multi-container orchestration
├── docker-shell.sh            # Build and run script
├── docker-entrypoint.sh       # Container startup script
│
├── rag_cli.py                 # Main CLI interface
├── preprocessing.py           # PDF extraction and chunking
├── vector_store.py           # LlamaIndex + ChromaDB wrapper
├── semantic_splitter.py      # Custom semantic chunking
├── gcs_manager.py            # GCS upload utilities
│
├── sample-data/              # Input PDF documents
│   ├── IA-Crop-Progress-09-29-25.pdf
│   └── iowa-corn-soybean-yield.pdf
│
├── outputs/                  # Generated summaries and logs
└── docker-volumes/          # Persistent ChromaDB storage
    └── chromadb/
```

## 📖 Commands Reference

### Load Command

```bash
python rag_cli.py load \
    --collection-name COLLECTION_NAME \
    [--method {sentence-window,automerging,semantic}] \
    [--input-dir INPUT_DIR]
```

**Workflow:**
1. Reads all PDFs from input directory
2. Extracts text using pdfplumber
3. Chunks text using selected method
4. Generates embeddings via Vertex AI
5. Stores in ChromaDB
6. Optionally uploads to GCS
7. Saves summary to `outputs/`

### Query Command

```bash
python rag_cli.py query "YOUR QUESTION" \
    --collection-name COLLECTION_NAME
```

**Output:** Top-5 most relevant chunks with similarity scores

### Chat Command

```bash
python rag_cli.py chat "YOUR QUESTION" \
    --collection-name COLLECTION_NAME
```

**Output:** AI-generated answer based on retrieved context

### Info Command

```bash
python rag_cli.py info
```

**Output:** Lists all collections with chunk counts

### Delete Collection Command

```bash
python rag_cli.py delete-collection COLLECTION_NAME
```

### Reset Command

```bash
python rag_cli.py reset
```

**⚠️ Warning:** Deletes ALL collections. Requires confirmation.

## ⚙️ Configuration

### Environment Variables

Set in `docker-shell.sh` or pass to Docker:

| Variable | Description | Default |
|----------|-------------|---------|
| `GCP_PROJECT` | Google Cloud project ID | Required |
| `GCP_LOCATION` | GCP region | `us-central1` |
| `GCS_BUCKET` | Cloud Storage bucket for artifacts | Optional |
| `EMBEDDING_MODEL` | Vertex AI embedding model | `text-embedding-004` |
| `EMBEDDING_DIMENSION` | Embedding vector size | `768` |
| `GENERATIVE_MODEL` | Gemini model for chat | `gemini-2.0-flash-001` |
| `CHROMADB_HOST` | ChromaDB hostname | `agri-rag-chromadb` |
| `CHROMADB_PORT` | ChromaDB port | `8000` |

### Model Configuration

Edit `rag_cli.py` to tune generation parameters:

```python
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0.1,      # Lower = more deterministic
    "top_p": 0.95,          # Nucleus sampling
}
```

### System Instruction

Customize the AI assistant's behavior by editing `SYSTEM_INSTRUCTION` in `rag_cli.py` (line ~227).


### Checking Logs

**Container logs:**
```bash
docker logs agri-rag-cli
docker logs agri-rag-chromadb
```

**Enable debug logging:**
Edit `rag_cli.py` and add:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```


## Future Enhancements

1. **Advanced RAG Techniques**
   - Reranking with cross-encoders
   - Query expansion/fusion
   - Hybrid search (dense + sparse)
   - Parent document retrieval

2. **API Server**
   - FastAPI REST endpoint
   - WebSocket for streaming responses
   - Authentication layer

3. **Monitoring**
   - Query analytics
   - Retrieval quality metrics
   - Cost tracking for Vertex AI calls

4. **UI/UX**
   - Web-based chat interface
   - Document management dashboard
   - Visualization of embeddings


**Questions or Issues?** Open an issue in the GitHub repository or contact the development team.
