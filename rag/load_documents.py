"""
Document Loader for AgriGuard RAG Service

Usage:
    python load_documents.py --input-dir ./sample-data
    python load_documents.py --texts "Text 1" "Text 2"
    python load_documents.py --sample  # Load sample agricultural knowledge
"""

import argparse
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import chromadb

# Optional PDF processing
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "localhost")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8004"))  # External port
COLLECTION_NAME = os.environ.get("RAG_COLLECTION_NAME", "corn-stress-knowledge")


# ─────────────────────────────────────────────────────────────────────────────
# Sample Agricultural Knowledge Base
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_KNOWLEDGE = [
    # Corn Stress Overview
    """Corn stress monitoring is essential for Iowa farmers to maximize yields. The Multivariate Corn Stress Index (MCSI) combines multiple indicators: NDVI for vegetation health, LST for heat stress, VPD for atmospheric dryness, and water deficit for soil moisture balance. Each component is normalized to a 0-100 scale where higher values indicate healthier conditions.""",
    
    # NDVI Interpretation
    """NDVI (Normalized Difference Vegetation Index) measures vegetation greenness and photosynthetic activity. For corn, NDVI values above 0.7 indicate healthy, dense canopy. Values between 0.5-0.7 suggest moderate vegetation cover typical of early or late season. Values below 0.5 may indicate stress, sparse canopy, or bare soil. Peak NDVI typically occurs during silking stage (weeks 10-12 of the growing season).""",
    
    # Heat Stress (LST)
    """Land Surface Temperature (LST) is critical for detecting heat stress in corn. Temperatures above 32°C (90°F) during pollination can significantly reduce kernel set. Extended periods above 35°C cause pollen desiccation and silk damage. The LST index converts temperature readings to a stress scale where lower temperatures (cooler conditions) yield higher index values indicating less heat stress.""",
    
    # Water Stress
    """Water deficit is calculated as the difference between reference evapotranspiration (ETo) and precipitation. Positive values indicate water stress where crop demand exceeds supply. Corn requires approximately 20-25 inches of water during the growing season. Critical water needs occur during silking and grain fill stages. Deficit stress during these periods can reduce yields by 3-8% per day of severe stress.""",
    
    # VPD and Atmospheric Conditions
    """Vapor Pressure Deficit (VPD) measures atmospheric dryness affecting plant transpiration. High VPD (>2.5 kPa) forces plants to close stomata to conserve water, reducing photosynthesis and growth. Optimal VPD for corn is 0.8-1.5 kPa. VPD stress is particularly damaging when combined with high temperatures and low soil moisture.""",
    
    # Yield Forecasting
    """AgriGuard's yield forecasting model uses XGBoost regression trained on 10 years of Iowa county-level data. Key predictive features include: water deficit during grain fill, heat stress days during pollination, NDVI anomalies, and historical county yields. The model achieves R² of 0.89 and MAE of 8.3 bushels per acre.""",
    
    # Iowa Growing Season
    """Iowa's corn growing season typically runs from May 1 to October 31 (approximately 26 weeks). Planting occurs weeks 1-4, vegetative growth weeks 5-9, pollination weeks 10-12, grain fill weeks 13-20, and maturation weeks 21-26. Stress impacts vary by growth stage - early stress affects plant population, mid-season stress impacts kernel number, and late stress reduces kernel weight.""",
    
    # Stress Response Actions
    """When MCSI indicates severe stress (below 30): Check soil moisture immediately, consider irrigation if available, scout for pest damage that may compound stress. For moderate stress (30-50): Monitor closely, prepare contingency plans, document affected areas. For mild stress (50-70): Continue normal management, maintain regular scouting schedule.""",
    
    # Historical Context
    """Iowa is the leading corn producing state, averaging 180-200 bushels per acre in favorable years. The 2012 drought caused yields to drop to 137 bushels per acre statewide. Climate change is increasing frequency of extreme heat events and irregular precipitation patterns, making real-time stress monitoring increasingly valuable for farm management decisions.""",
    
    # County Variability
    """Iowa's 99 counties show significant yield variability based on soil types, drainage, and microclimates. Northwest Iowa counties generally have higher yield potential due to better soils. Southern Iowa counties face more frequent drought stress. Understanding county-specific patterns helps calibrate stress index interpretation.""",
]


def get_client():
    """Get ChromaDB client."""
    return chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)


def get_collection(client, name: Optional[str] = None):
    """Get or create collection."""
    collection_name = name or COLLECTION_NAME
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF file."""
    if not HAS_PDF:
        raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")
    
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Simple text chunking with overlap."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end
            for sep in ['. ', '.\n', '! ', '? ']:
                pos = text.rfind(sep, start, end)
                if pos > start + chunk_size // 2:
                    end = pos + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks


def load_texts(texts: List[str], collection_name: Optional[str] = None, 
               metadatas: Optional[List[dict]] = None):
    """Load text chunks into ChromaDB."""
    client = get_client()
    collection = get_collection(client, collection_name)
    
    # Generate IDs
    timestamp = datetime.now().timestamp()
    ids = [f"doc_{i}_{timestamp}" for i in range(len(texts))]
    
    # Add to collection
    collection.add(
        documents=texts,
        ids=ids,
        metadatas=metadatas
    )
    
    logger.info(f"Loaded {len(texts)} chunks into '{collection.name}'")
    logger.info(f"Total documents in collection: {collection.count()}")
    
    return len(texts)


def load_text_file(file_path: Path) -> str:
    """Load text from a .txt or .md file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_documents_from_dir(input_dir: Path, collection_name: Optional[str] = None,
                           chunk_size: int = 1000):
    """Load all documents (PDFs and text files) from directory."""
    
    # Find all supported files
    pdf_files = list(input_dir.glob("*.pdf")) if HAS_PDF else []
    txt_files = list(input_dir.glob("*.txt"))
    md_files = list(input_dir.glob("*.md"))
    
    all_files = pdf_files + txt_files + md_files
    
    if not all_files:
        logger.warning(f"No supported files found in {input_dir}")
        logger.info("Supported formats: .pdf, .txt, .md")
        return 0
    
    logger.info(f"Found {len(all_files)} files: {len(pdf_files)} PDFs, {len(txt_files)} TXT, {len(md_files)} MD")
    
    all_chunks = []
    all_metadatas = []
    
    for file_path in all_files:
        logger.info(f"Processing: {file_path.name}")
        try:
            # Extract text based on file type
            if file_path.suffix.lower() == '.pdf':
                text = extract_text_from_pdf(file_path)
            else:
                text = load_text_file(file_path)
            
            if not text.strip():
                logger.warning(f"  Empty file: {file_path.name}")
                continue
                
            chunks = chunk_text(text, chunk_size=chunk_size)
            
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadatas.append({
                    "source": file_path.name,
                    "file_type": file_path.suffix,
                    "chunk_index": i,
                    "loaded_at": datetime.now().isoformat()
                })
            
            logger.info(f"  Created {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"  Failed: {e}")
    
    if all_chunks:
        return load_texts(all_chunks, collection_name, all_metadatas)
    return 0


def load_pdfs(input_dir: Path, collection_name: Optional[str] = None,
              chunk_size: int = 1000):
    """Load all PDFs from directory (legacy function, use load_documents_from_dir)."""
    if not HAS_PDF:
        raise ImportError("pdfplumber not installed")
    
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return 0
    
    all_chunks = []
    all_metadatas = []
    
    for pdf_path in pdf_files:
        logger.info(f"Processing: {pdf_path.name}")
        try:
            text = extract_text_from_pdf(pdf_path)
            chunks = chunk_text(text, chunk_size=chunk_size)
            
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadatas.append({
                    "source": pdf_path.name,
                    "chunk_index": i,
                    "loaded_at": datetime.now().isoformat()
                })
            
            logger.info(f"  Created {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"  Failed: {e}")
    
    if all_chunks:
        return load_texts(all_chunks, collection_name, all_metadatas)
    return 0


def load_sample_knowledge(collection_name: Optional[str] = None):
    """Load sample agricultural knowledge base."""
    logger.info("Loading sample agricultural knowledge...")
    
    metadatas = [
        {"source": "sample_knowledge", "topic": "overview", "index": i}
        for i in range(len(SAMPLE_KNOWLEDGE))
    ]
    
    return load_texts(SAMPLE_KNOWLEDGE, collection_name, metadatas)


def show_info(collection_name: Optional[str] = None):
    """Show collection information."""
    client = get_client()
    
    print("\n" + "=" * 60)
    print("CHROMADB COLLECTIONS")
    print("=" * 60)
    
    collections = client.list_collections()
    print(f"\nTotal collections: {len(collections)}\n")
    
    for col in collections:
        marker = " ← default" if col.name == COLLECTION_NAME else ""
        print(f"  • {col.name}: {col.count()} documents{marker}")
    
    print()


def main():
    parser = argparse.ArgumentParser(description="Load documents into AgriGuard RAG")
    parser.add_argument("--input-dir", type=Path, help="Directory with PDF files")
    parser.add_argument("--texts", nargs="+", help="Text strings to load")
    parser.add_argument("--sample", action="store_true", help="Load sample knowledge")
    parser.add_argument("--collection", type=str, default=None, help="Collection name")
    parser.add_argument("--info", action="store_true", help="Show collection info")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size for PDFs")
    
    args = parser.parse_args()
    
    try:
        if args.info:
            show_info(args.collection)
            return
        
        if args.sample:
            count = load_sample_knowledge(args.collection)
            print(f"\n✓ Loaded {count} sample knowledge chunks")
            return
        
        if args.input_dir:
            if not args.input_dir.exists():
                print(f"Error: Directory not found: {args.input_dir}")
                return
            count = load_documents_from_dir(args.input_dir, args.collection, args.chunk_size)
            print(f"\n✓ Loaded {count} chunks from documents")
            return
        
        if args.texts:
            count = load_texts(args.texts, args.collection)
            print(f"\n✓ Loaded {count} text chunks")
            return
        
        parser.print_help()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
