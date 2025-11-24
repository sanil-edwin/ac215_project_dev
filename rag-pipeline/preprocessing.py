"""
Handles PDF text extraction and document chunking using three strategies:
1. Sentence Window (LlamaIndex)
2. Auto-Merging / Hierarchical (LlamaIndex)
3. Semantic (Langchain-based custom splitter)
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Dict

import pdfplumber
from google.oauth2 import service_account
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
import vertexai
import re

from llama_index.core import Document
# Lazy imports for chunking methods - only import when needed
# from llama_index.core.node_parser import (
#     SentenceWindowNodeParser,
#     HierarchicalNodeParser,
#     get_leaf_nodes,
# )

# Custom semantic splitter
from semantic_splitter import SemanticChunker

# Setup
GCP_PROJECT = os.environ.get("GCP_PROJECT")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "768"))

# Initialize Vertex AI
creds = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
)
vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION, credentials=creds)

logger = logging.getLogger(__name__)

# Initialize embedding model
embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)


CHARS_PER_TOKEN_ESTIMATE = 4.0  # keep conservative
EMBED_TOKEN_LIMIT = 4000        # your Vertex per-input token budget
MAX_CHUNK_CHARS = int(EMBED_TOKEN_LIMIT * CHARS_PER_TOKEN_ESTIMATE)  # ~16,000

def approx_tokens(s: str) -> int:
    return int(len(s) / CHARS_PER_TOKEN_ESTIMATE)

def validate_chunk_size(text: str, chunk_id: str = "chunk") -> bool:
    tokens = approx_tokens(text)
    if tokens > EMBED_TOKEN_LIMIT:
        logger.warning(
            f"{chunk_id}: {tokens:,} tokens (~{len(text):,} chars) exceeds "
            f"limit ({EMBED_TOKEN_LIMIT:,} tokens)."
        )
        return False
    return True

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extract text from a PDF file using pdfplumber.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a single string
    """
    logger.info(f"Extracting text from PDF: {pdf_path.name}")
    
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text: #skips empty pages
                text += page_text + "\n\n" #new lines between pages
    
    logger.info(f"Extracted {len(text):,} characters from {len(pdf.pages)} pages")
    return text

# Called by semantic chunking
def generate_text_embeddings(
    chunks: List[str],
    dimensionality: int = None,
    batch_size: int = 50,
) -> List[List[float]]:
    """
    Generate embeddings for text chunks using Vertex AI.
    Assumes upstream chunking is token-aware (≤ EMBED_TOKEN_LIMIT).
    """
    if dimensionality is None:
        dimensionality = EMBEDDING_DIMENSION

    # Clamp to Vertex batch limits (max 250).
    batch_size = max(1, min(int(batch_size), 250))

    total = len(chunks)
    logger.info(f"Embedding {total} chunks (dim={dimensionality}, batch={batch_size})")

    # Quick sanity check (log-only). No truncation here.
    overs = [i for i, c in enumerate(chunks) if approx_tokens(c) > EMBED_TOKEN_LIMIT]
    if overs:
        logger.warning(f"{len(overs)} chunks exceed token budget; upstream should split further (indices: {overs[:5]}{'...' if len(overs)>5 else ''})")

    all_embeddings: List[List[float]] = []

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        try:
            inputs = [TextEmbeddingInput(text=t, task_type="RETRIEVAL_DOCUMENT") for t in batch]
            kwargs = {"output_dimensionality": dimensionality} if dimensionality else {}
            embs = embedding_model.get_embeddings(inputs, **kwargs)
            all_embeddings.extend([e.values for e in embs])
            logger.debug(f"Embedded {i + len(batch)}/{total}")
        except Exception as e:
            logger.error(f"Embedding batch {i//batch_size + 1} failed: {e}")
            # Re-raise in most pipelines so you don't silently drop context:
            raise

    logger.info(f"Generated {len(all_embeddings)} embeddings from {total} chunks")
    return all_embeddings

def chunk_with_sentence_window(
    text: str,
    window_size: int = 3,
    metadata: Optional[Dict] = None
) -> List[Document]:
    """
    Chunk text using LlamaIndex Sentence Window strategy.
    Each sentence becomes a node with surrounding context window.
    
    Args:
        text: Input text to chunk
        window_size: Number of sentences before/after to include as context
        metadata: Optional metadata to attach to documents
        
    Returns:
        List of LlamaIndex Document objects with sentence nodes
    """
    # Lazy import - only import when this method is actually used
    from llama_index.core.node_parser import SentenceWindowNodeParser
    
    logger.info(f"Chunking with Sentence Window (window_size={window_size})")
    
    parser = SentenceWindowNodeParser.from_defaults(
        window_size=window_size,
        window_metadata_key="window",
        original_text_metadata_key="original_sentence"
    )
    
    # Create a document
    doc = Document(text=text, metadata=metadata or {})
    
    # Parse into nodes
    nodes = parser.get_nodes_from_documents([doc])
    
    # Validate chunk sizes
    valid_nodes = []
    for i, node in enumerate(nodes):
        if validate_chunk_size(node.text, f"sentence-window-{i}"):
            valid_nodes.append(node)
        else:
            logger.warning(f"Skipping oversized sentence window chunk {i}")
    
    logger.info(f"Created {len(valid_nodes)} valid sentence window nodes (from {len(nodes)} total)")
    return valid_nodes

def chunk_with_automerging(
    text: str,
    chunk_sizes: List[int] = None,
    metadata: Optional[Dict] = None
) -> List[Document]:
    """
    Chunk text using LlamaIndex Hierarchical (Auto-Merging) strategy.
    Creates parent-child-leaf hierarchy for context-aware retrieval.
    
    Args:
        text: Input text to chunk
        chunk_sizes: List of chunk sizes [parent, child, leaf] in characters
        metadata: Optional metadata to attach to documents
        
    Returns:
        List of leaf node Document objects (parents stored for merging)
    """
    # Lazy import - only import when this method is actually used
    from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
    
    if chunk_sizes is None:
        # Reduced chunk sizes to stay well under token limits
        # Vertex AI text-embedding-004 has ~20k token limit
        # Using conservative estimate: 4 chars per token = max 80k chars
        # But keeping chunks much smaller for better performance
        chunk_sizes = [4000, 1000, 250]  # large -> medium -> small
    
    logger.info(f"Chunking with Auto-Merging (sizes={chunk_sizes})")
    
    parser = HierarchicalNodeParser.from_defaults(chunk_sizes=chunk_sizes)
    
    # Create a document
    doc = Document(text=text, metadata=metadata or {})
    
    # Parse into hierarchical nodes
    all_nodes = parser.get_nodes_from_documents([doc])
    
    # Get only leaf nodes (these get embedded; parents are for context)
    leaf_nodes = get_leaf_nodes(all_nodes)
    
    # Validate chunk sizes
    valid_nodes = []
    for i, node in enumerate(leaf_nodes):
        if validate_chunk_size(node.text, f"automerging-{i}"):
            valid_nodes.append(node)
        else:
            logger.warning(f"Skipping oversized automerging chunk {i}")
    
    logger.info(
        f"Created {len(all_nodes)} total nodes "
        f"({len(valid_nodes)} valid leaf nodes for embedding from {len(leaf_nodes)} total)"
    )
    return valid_nodes


def chunk_with_semantic(
    text: str,
    metadata: Optional[Dict] = None,
    buffer_size: int = 1,
    breakpoint_threshold_type: str = "percentile",
    embedding_function=None
) -> List[Document]:
    """
    Efficient, token-aware semantic chunking:
    - Uses SemanticChunker for primary boundaries
    - Enforces EMBED_TOKEN_LIMIT via smart re-splitting (no truncation)
    - Logs major steps only
    """
    logger.info(f"Semantic chunking: {len(text):,} chars (~{approx_tokens(text):,} tokens)")

    if embedding_function is None:
        embedding_function = lambda texts, batch_size=50: generate_text_embeddings(texts, batch_size=batch_size)

    SENT_RE = r"(?<=[.?!])\s+|\n{2,}"     # sentence + paragraph
    CLAUSE_RE = r"(,|;|\s—\s|\s-\s)"      # clause delimiters

    def pack(piece: str, meta: Dict, out: List[Document]):
        """Token-safe packer; logs only when we must split deeply."""
        if approx_tokens(piece) <= EMBED_TOKEN_LIMIT:
            out.append(Document(text=piece.strip(), metadata=meta))
            return

        # Paragraph split
        for p in (x for x in re.split(r"\n{2,}", piece) if x.strip()):
            if approx_tokens(p) <= EMBED_TOKEN_LIMIT:
                out.append(Document(text=p.strip(), metadata=meta))
                continue

            # Greedy sentence packing
            buf = []
            def flush():
                if buf:
                    out.append(Document(text=" ".join(buf).strip(), metadata=meta))
                    buf.clear()

            sentences = [x for x in re.split(SENT_RE, p) if x.strip()]
            for s in sentences:
                cand = (" ".join(buf + [s])).strip()
                if approx_tokens(cand) <= EMBED_TOKEN_LIMIT:
                    buf.append(s)
                else:
                    if buf:
                        flush()
                    # Deep split by clauses if sentence itself is too large
                    logger.debug(f"Deep split (clauses) in oversize sentence (~{approx_tokens(s):,} tokens)")
                    cur = ""
                    for clause in re.split(CLAUSE_RE, s):
                        if not clause:
                            continue
                        nxt = (cur + (" " if cur and not re.match(CLAUSE_RE, clause) else "") + clause).strip()
                        if approx_tokens(nxt) <= EMBED_TOKEN_LIMIT:
                            cur = nxt
                        else:
                            if cur:
                                out.append(Document(text=cur, metadata=meta))
                            cur = clause.strip()
                    if cur:
                        out.append(Document(text=cur, metadata=meta))
            flush()

    try:
        # Step 1: semantic split
        est_chunks = max(2, int(len(text) / MAX_CHUNK_CHARS))
        splitter = SemanticChunker(
            embedding_function=embedding_function,
            buffer_size=buffer_size,
            breakpoint_threshold_type=breakpoint_threshold_type,
            number_of_chunks=est_chunks,
            sentence_split_regex=SENT_RE,
        )
        sem_chunks = splitter.split_text(text)
        logger.info(f"SemanticChunker created {len(sem_chunks)} primary chunks (target={est_chunks})")

        # Step 2: token-safe post-process
        docs: List[Document] = []
        oversized = 0
        for i, ch in enumerate(sem_chunks):
            base_meta = (metadata or {}).copy()
            base_meta["semantic_chunk_id"] = i
            if approx_tokens(ch) > EMBED_TOKEN_LIMIT:
                oversized += 1
                logger.debug(f"Chunk {i} oversized (~{approx_tokens(ch):,} tokens); re-splitting")
            pack(ch, base_meta, docs)

        logger.info(f"Final: {len(docs)} chunks created ({oversized} oversized re-split)")
        return docs

    except Exception as e:
        logger.error(f"Semantic chunking failed: {e}")
        logger.info("Falling back to token-aware paragraph-based splitting")

        docs: List[Document] = []
        pack(text, (metadata or {}) | {"fallback_chunking": True}, docs)
        logger.info(f"Fallback created {len(docs)} chunks")
        return docs

def chunk_text(
    text: str,
    method: str = "semantic",
    metadata: Optional[Dict] = None,
    **kwargs
) -> List[Document]:
    """
    Main chunking dispatcher function.
    
    Args:
        text: Input text to chunk
        method: Chunking method ('sentence-window', 'automerging', 'semantic')
        metadata: Optional metadata to attach to chunks
        **kwargs: Additional arguments for specific chunking methods
        
    Returns:
        List of Document objects (chunks)
    """
    if method == "sentence-window":
        return chunk_with_sentence_window(text, metadata=metadata, **kwargs)
    
    elif method == "automerging":
        return chunk_with_automerging(text, metadata=metadata, **kwargs)
    
    elif method == "semantic":
        return chunk_with_semantic(text, metadata=metadata, **kwargs)
    
    else:
        raise ValueError(
            f"Unknown chunking method: {method}. "
            f"Choose from: 'sentence-window', 'automerging', 'semantic'"
        )


def process_pdf(
    pdf_path: Path,
    method: str = "semantic",
    metadata: Optional[Dict] = None
) -> List[Document]:
    """
    Full pipeline: Extract text from PDF and chunk it.
    
    Args:
        pdf_path: Path to PDF file
        method: Chunking method
        metadata: Optional metadata to attach
        
    Returns:
        List of chunked Document objects
    """
    logger.info(f"Processing PDF: {pdf_path.name} with method: {method}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    
    if not text.strip():
        logger.warning(f"No text extracted from {pdf_path.name}")
        return []
    
    # Add file info to metadata
    if metadata is None:
        metadata = {}
    metadata["file_name"] = pdf_path.name
    metadata["file_path"] = str(pdf_path)
    
    # Chunk text
    chunks = chunk_text(text, method=method, metadata=metadata)
    
    logger.info(f"Processed {pdf_path.name}: {len(chunks)} chunks created")
    return chunks


def main():
    """Test preprocessing functions."""
    logging.basicConfig(level=logging.INFO)
    
    # Test with a sample PDF (you'd need to provide this)
    test_pdf = Path("sample-data/IA-Crop-Progress-09-29-25.pdf")
    
    if not test_pdf.exists():
        logger.error(f"Test PDF not found: {test_pdf}")
        return
    
    # Test all three methods
    for method in ["sentence-window", "automerging", "semantic"]:
        logger.info(f"\n{'-'*60}")
        logger.info(f"Testing {method} method")
        logger.info(f"{'-'*60}")
        
        chunks = process_pdf(test_pdf, method=method)
        
        # Show sample chunks
        logger.info(f"\nSample chunks (first 2):")
        for i, chunk in enumerate(chunks[:2], 1):
            logger.info(f"\nChunk {i}:")
            logger.info(f"Text preview: {chunk.text[:200]}...")
            logger.info(f"Metadata: {chunk.metadata}")


if __name__ == "__main__":
    main()

