cat > README.md << 'EOF'
# Iowa Agriculture RAG Pipeline

Retrieval-Augmented Generation system for Iowa agricultural data using LlamaIndex, ChromaDB, and Gemini.

## Features
- PDF document processing
- Three chunking strategies: Sentence Window, Auto-Merging, Semantic
- Gemini embeddings and LLM
- ChromaDB vector storage
- GCS artifact uploads

## Usage

Build and run:
```bash
./docker-shell.sh
