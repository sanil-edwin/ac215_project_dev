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

from llama_index.core import Document
from llama_index.core.node_parser import (
    SentenceWindowNodeParser,
    HierarchicalNodeParser,
    get_leaf_nodes,
)

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
    batch_size: int = 50
) -> List[List[float]]:
    """
    Generate embeddings for text chunks using Vertex AI.
    
    Args:
        chunks: List of text strings to embed
        dimensionality: Output embedding dimension (default from env)
        batch_size: Number of texts to embed per batch (max 250)
        
    Returns:
        List of embedding vectors
    """
    if dimensionality is None:
        dimensionality = EMBEDDING_DIMENSION
    
    all_embeddings = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # Create inputs with task type
        inputs = [
            TextEmbeddingInput(text=text, task_type="RETRIEVAL_DOCUMENT") 
            for text in batch
        ]
        
        # Get embeddings
        kwargs = dict(output_dimensionality=dimensionality) if dimensionality else {}
        embeddings = embedding_model.get_embeddings(inputs, **kwargs)
        
        all_embeddings.extend([embedding.values for embedding in embeddings])
        
        logger.debug(f"Embedded batch {i//batch_size + 1}: {len(batch)} chunks")
    
    logger.info(f"Generated {len(all_embeddings)} embeddings")
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
    
    logger.info(f"Created {len(nodes)} sentence window nodes")
    return nodes


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
    if chunk_sizes is None:
        chunk_sizes = [2048, 512, 128]  # large -> medium -> small
    
    logger.info(f"Chunking with Auto-Merging (sizes={chunk_sizes})")
    
    parser = HierarchicalNodeParser.from_defaults(chunk_sizes=chunk_sizes)
    
    # Create a document
    doc = Document(text=text, metadata=metadata or {})
    
    # Parse into hierarchical nodes
    all_nodes = parser.get_nodes_from_documents([doc])
    
    # Get only leaf nodes (these get embedded; parents are for context)
    leaf_nodes = get_leaf_nodes(all_nodes)
    
    logger.info(
        f"Created {len(all_nodes)} total nodes "
        f"({len(leaf_nodes)} leaf nodes for embedding)"
    )
    return leaf_nodes


def chunk_with_semantic(
    text: str,
    embedding_function=None,
    buffer_size: int = 1,
    breakpoint_threshold_type: str = "percentile",
    metadata: Optional[Dict] = None
) -> List[Document]:
    """
    Chunk text using Semantic Chunking strategy.
    Splits at semantic boundaries based on embedding similarity.
    
    Args:
        text: Input text to chunk
        embedding_function: Function to generate embeddings (uses default if None)
        bbuffer_size: Number of sentences to combine for context
        breakpoint_threshold_type: Method to determine split points
        metadata: Optional metadata to attach to documents
        
    Returns:
        List of Document objects with semantically coherent chunks
    """
    logger.info(f"Chunking with Semantic Splitting (threshold={breakpoint_threshold_type})")
    
    # Use default embedding function if not provided
    if embedding_function is None:
        embedding_function = lambda texts, batch_size=50: generate_text_embeddings(
            texts, batch_size=batch_size
        )
    
    # Create semantic splitter
    splitter = SemanticChunker(
        embedding_function=embedding_function,
        buffer_size=buffer_size,
        breakpoint_threshold_type=breakpoint_threshold_type
    )
    
    # Split text
    chunks = splitter.split_text(text)
    
    # Convert to LlamaIndex Document objects
    documents = [
        Document(text=chunk, metadata=metadata or {})
        for chunk in chunks
    ]
    
    logger.info(f"Created {len(documents)} semantic chunks")
    return documents


def chunk_text(
    text: str,
    method: str = "sentence-window",
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
    method: str = "sentence-window",
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

