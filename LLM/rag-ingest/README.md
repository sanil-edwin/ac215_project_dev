Data ingestion service with advanced chunking strategies for Iowa agronomy documents.

Features
1. Document Loading

Downloads PDFs from URLs
Uploads to GCS for archival
Uses LlamaIndex SimpleDirectoryReader

2. Advanced Chunking Strategies
a. Sentence Window Retrieval

What it does: Embeds small chunks (sentences) but retrieves with surrounding context
Parameters:
window_size=3: Retrieves 3 sentences before and after
Stores original text for context expansion

Best for: Precise retrieval with rich context
Index location: /app/indexes/sentence_window

b. Auto-Merging Retrieval
What it does: Creates hierarchical chunks that merge during retrieval
Chunk hierarchy:
Parent: 2048 tokens
Child: 512 tokens
Leaf: 128 tokens

Best for: Adaptive context based on query relevance
Index location: /app/indexes/automerging

Environment Variables
bash# Required
OPENAI_API_KEY=sk-xxx        # For LLM 
GCS_BUCKET=bucket-name      # For archival storage
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcs-key.json

Running Locally
Build the container:
run.sh

Adding More Documents
Edit main.py and add to the test_docs list:
pythontest_docs = [
    {
        "url": "https://example.com/document.pdf",
        "filename": "document.pdf",
        "metadata": {
            "source_type": "research_paper",
            "crop_focus": "corn",
            "state": "Iowa"
        }
    },
    # Add more...
]
How Chunking Strategies Work
Sentence Window
Original text: S1. S2. S3. S4. S5. S6. S7.

Embedded chunk: S4
Retrieved context: S1. S2. S3. [S4] S5. S6. S7.
                   └── window_size=3 ──┘
Auto-Merging
Document (2048 tokens)
├── Chunk 1 (512 tokens)
│   ├── Leaf 1a (128 tokens) ← Embedded
│   ├── Leaf 1b (128 tokens) ← Embedded
│   └── ...
└── Chunk 2 (512 tokens)
    └── ...

During retrieval:
- If leaf nodes are similar → merge to parent
- Returns appropriate context size

Next Steps

Query Engine (rag-api): Build query service to test retrieval
Vector-db: store vectors + matadata; provides fast k-NN search with filters; API will query here
Embeddings: embedding services for real time user queries (not offline docs) ==> scaling
Evaluation: Compare sentence window vs auto-merging performance
Scale: Add batch ingestion for multiple documents
Monitoring: Track chunk sizes and retrieval quality

Key Dependencies

llama-index: Core RAG framework
sentence-transformers: Local embeddings (bge-small-en-v1.5)
openai: LLM for query generation
google-cloud-storage: Document archival

Troubleshooting
OOM errors:

Reduce chunk sizes in HierarchicalNodeParser
Process documents one at a time

Slow embeddings:

First run downloads the embedding model (~120MB)
Subsequent runs use cached model

GCS upload fails:

Verify credentials are mounted correctly
Check bucket permissions (Storage Object Admin)
