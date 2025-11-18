'''
Command-line interface for the RAG pipeline.

Commands:
- load: Process PDFs and load into vector store (Llama Index))
- query: Query the vector store
- chat: Interactive chat with retrieved context
- info: Show collection information
- delete-collection: Delete a collection
- reset: Delete all collections
'''
import argparse
import os
import chromadb
import logging
import warnings
from pathlib import Path
from pprint import pprint
from datetime import datetime
warnings.filterwarnings("ignore")
# import our custom modules
from preprocessing import process_pdf
from vector_store import LlamaIndexDB
from gcs_manager import GCSStorageManager

logger = logging.getLogger(__name__)

# Set up
INPUT_FOLDER = "sample-data"
OUTPUT_FOLDER = "outputs"
CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "agri-rag-chromadb")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))
GCS_BUCKET = os.environ.get("GCS_BUCKET")

CHUNK_METHODS = ["sentence-window", "automerging", "semantic"]
DEFAULT_CHUNKING_METHOD = "semantic"
DEFAULT_TOP_K = 5

def load_command(args):
    """
    Load PDFs from a directory into the vector store.
    
    Process:
    1. Read PDFs from input directory
    2. Extract text and chunk using specified method
    3. Load chunks into ChromaDB collection
    4. Upload artifacts to GCS
    """
    logger.info("-" * 70)
    logger.info(f"LOAD COMMAND: {args.collection_name}")
    logger.info(f"Method: {args.method}")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info("-" * 70)
    
    # Initialize vector_store.py instance
    db = LlamaIndexDB(args.collection_name)
    
    # Get list of PDFs
    pdf_files = list(Path(args.input_dir).glob("*.pdf"))
    
    if not pdf_files:
        logger.error(f"No PDF files found in {args.input_dir}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Initialize GCS manager if bucket is configured
    gcs = None
    if GCS_BUCKET:
        try:
            gcs = GCSStorageManager(GCS_BUCKET)
            logger.info(f"GCS uploads enabled to bucket: {GCS_BUCKET}")
        except Exception as e:
            logger.warning(f"Could not initialize GCS: {e}")
            logger.warning("Continuing without GCS uploads")
    
    # Process each PDF
    all_chunks = []
    successful_docs = []
    failed_docs = []
    
    # iterate each pdf in pdf files
    for pdf_path in pdf_files:
        try:
            logger.info(f"\nProcessing: {pdf_path.name}")
            
            # Add metadata
            metadata = {
                "file_name": pdf_path.name,
                "source": args.input_dir,
                "chunking_method": args.method,
                "ingested_at": datetime.now().isoformat(),
            }
            
            # pass into full pipelien (extract + chunk)
            chunks = process_pdf(
                pdf_path,
                method=args.method,
                metadata=metadata
            )
            
            if not chunks:
                logger.warning(f"No chunks created from {pdf_path.name}")
                failed_docs.append(pdf_path.name)
                continue
            
            # Log chunk size statistics
            chunk_sizes = [len(chunk.text) for chunk in chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes)
            max_size = max(chunk_sizes)
            min_size = min(chunk_sizes)
            
            logger.info(
                f"  Chunk stats: {len(chunks)} chunks, "
                f"avg={avg_size:.0f}, min={min_size}, max={max_size:,} chars"
            )
            
            all_chunks.extend(chunks)
            successful_docs.append(pdf_path.name)
            
            # Upload to GCS if enabled
            if gcs:
                try:
                    # Upload raw PDF
                    gcs.upload_file(str(pdf_path), "raw", pdf_path.name)
                    
                    # Upload metadata
                    doc_metadata = {
                        "file_name": pdf_path.name,
                        "num_chunks": len(chunks),
                        "chunking_method": args.method,
                        "collection_name": args.collection_name,
                        "ingested_at": metadata["ingested_at"]
                    }
                    gcs.upload_json(
                        doc_metadata,
                        "metadata",
                        f"{pdf_path.stem}_metadata.json"
                    )
                    
                except Exception as e:
                    logger.warning(f"GCS upload failed for {pdf_path.name}: {e}")
            
            logger.info(f"✓ Processed {pdf_path.name}: {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {e}")
            failed_docs.append(pdf_path.name)
            continue
    
    # Load all chunks into vector store
    if all_chunks:
        # Log overall chunk statistics before loading
        total_chars = sum(len(chunk.text) for chunk in all_chunks)
        avg_chars = total_chars / len(all_chunks)
        max_chars = max(len(chunk.text) for chunk in all_chunks)
        min_chars = min(len(chunk.text) for chunk in all_chunks)
        
        logger.info(f"\nOverall chunk statistics:")
        logger.info(f"  Total chunks: {len(all_chunks)}")
        logger.info(f"  Total characters: {total_chars:,}")
        logger.info(f"  Average size: {avg_chars:.0f} characters")
        logger.info(f"  Size range: {min_chars} - {max_chars:,} characters")
        
        logger.info(f"\nLoading {len(all_chunks)} chunks into ChromaDB...")
        try:
            # tell db to load documents
            db.load_documents(all_chunks)
            logger.info(f"✓ Successfully loaded chunks into vector store")
        except Exception as e:
            logger.error(f"Failed to load chunks into vector store: {e}")
            return
    else:
        logger.error("No chunks to load!")
        return
    
    # Save summary to outputs/
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    summary = {
        "collection_name": args.collection_name,
        "method": args.method,
        "input_dir": str(args.input_dir),
        "total_pdfs": len(pdf_files),
        "successful": len(successful_docs),
        "failed": len(failed_docs),
        "total_chunks": len(all_chunks),
        "successful_docs": successful_docs,
        "failed_docs": failed_docs,
        "timestamp": datetime.now().isoformat()
    }
    
    summary_file = Path(OUTPUT_FOLDER) / f"load_summary_{args.collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\n{'-' * 70}")
    logger.info("LOAD COMPLETE")
    logger.info(f"Successful: {len(successful_docs)}/{len(pdf_files)}")
    logger.info(f"Total chunks: {len(all_chunks)}")
    logger.info(f"Collection: {args.collection_name}")
    logger.info(f"Summary saved to: {summary_file}")
    logger.info("-" * 70)


def query_command(args):
    """
    Query the vector store and return top-k results (query ChromaDB through LlamaIndex).
    """
    logger.info("=" * 70)
    logger.info(f"QUERY: {args.query}")
    logger.info(f"Collection: {args.collection_name}")
    logger.info(f"Top-K: {DEFAULT_TOP_K}")
    logger.info("=" * 70)
    # Create instance
    db = LlamaIndexDB(args.collection_name)
    
    if db.get_count() == 0:
        logger.error(f"Collection '{args.collection_name}' is empty!")
        return
    # Calls query (vector_store.py)
    results = db.query(args.query, top_k=DEFAULT_TOP_K)
    
    logger.info(f"\nFound {len(results)} results:\n")
    
    for i, (text, score) in enumerate(results, 1):
        print(f"\n{'-' * 70}")
        print(f"Result {i} (Score: {score:.4f})")
        print(f"{'-' * 70}")
        print(text[:500] + "..." if len(text) > 500 else text)


def chat_command(args):
    """
    Chat with the LLM using retrieved context.
    Simple RAG: retrieve top-k chunks, concat, send to Gemini.
    Should be enhanced with other techniques: reranker + fusion
    """
    logger.info("-" * 70)
    logger.info(f"CHAT: {args.query}")
    logger.info(f"Collection: {args.collection_name}")
    logger.info("-" * 70)
    
    from google.oauth2 import service_account
    from vertexai.generative_models import GenerativeModel
    import vertexai
    
    # Initialize Gemini
    GCP_PROJECT = os.environ.get("GCP_PROJECT")
    GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
    GENERATIVE_MODEL = os.environ.get("GENERATIVE_MODEL", "gemini-2.0-flash-001")
    
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    )
    vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION, credentials=creds)
    
    # System instruction for agriculture (!!! EDIT WITH AN EXAMPLE FOR GEMINI)
    SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in Iowa agriculture and corn crop management. Your responses are based mainly on the information provided in the retrieved document chunks given to you. Do not use any external knowledge or make assumptions beyond what is explicitly stated in these chunks.

When answering a query:
1. Carefully read all the retrieved document chunks provided.
2. Identify the most relevant information from these chunks to address the user's question about Iowa crops, yields, weather conditions, stress dection, and reasoning or farming practices.
3. Formulate your response using only the information found in the given chunks.
4. If the provided chunks do not contain sufficient information to answer the query, state that you don't have enough information to provide a complete answer based on the available documents.
5. Always maintain a professional and knowledgeable tone, befitting an agricultural expert.
6. When discussing yields, weather conditions, or crop progress and stress, always include relevant context such as dates, counties, or comparison to averages when available in the chunks.

Your goal is to provide accurate, helpful information about Iowa agriculture based mainly on the content of the document chunks you receive.
"""
    
    model = GenerativeModel(
        GENERATIVE_MODEL,
        system_instruction=[SYSTEM_INSTRUCTION]
    )
    
    # Manual use LlamaIndex for RETRIEVAL
    db = LlamaIndexDB(args.collection_name)
    
    if db.get_count() == 0:
        logger.error(f"Collection '{args.collection_name}' is empty!")
        return
    
    logger.info(f"Retrieving top {DEFAULT_TOP_K} chunks...")
    # Calls query() in vector_store.py
    results = db.query(args.query, top_k=DEFAULT_TOP_K)
    
    if not results:
        logger.warning("No results found for query")
        return
    
    # Concatenate retrieved chunks
    retrieved_text = "\n\n".join([text for text, score in results])
    
    logger.info(f"Retrieved {len(results)} chunks ({len(retrieved_text)} characters)")
    
    # Build prompt
    prompt = f"""Query: {args.query}

Retrieved Context:
{retrieved_text}

Please answer the query based on the context above."""
    
    # Generate response
    logger.info("Generating response with Gemini...")
    
    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 0.1, # currrently minimal creativity (0.1) means top 1-2 tokens already makes up 95%
        "top_p": 0.95,
    }
    
    response = model.generate_content(
        [prompt],
        generation_config=generation_config,
        stream=False
    )
    
    # Display response
    print(f"\n{'-' * 70}")
    print("AGRIBOT RESPONSE:")
    print(f"{'-' * 70}\n")
    print(response.text)
    print(f"\n{'-' * 70}")


def info_command(args):
    """QC: Show information about all collections in ChromaDB."""
    logger.info("-" * 70)
    logger.info("CHROMADB INFORMATION")
    logger.info("-" * 70)
    
    client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
    collections = client.list_collections()
    
    print(f"\nTotal collections: {len(collections)}\n")
    
    for idx, collection in enumerate(collections, 1):
        print(f"{idx}. Name: {collection.name}")
        print(f"   Count: {collection.count():,} chunks") #count of embeddings chunks
        print()


def delete_collection_command(args):
    """QC: Delete a specific collection."""
    logger.info(f"Deleting collection: {args.collection_name}")
    
    try:
        LlamaIndexDB.delete_collection(args.collection_name)
        logger.info(f"✓ Deleted collection: {args.collection_name}")
    except Exception as e:
        logger.error(f"Failed to delete collection: {e}")


def reset_command(args):
    """QC: Delete all collections (reset database)."""
    logger.warning("WARNING: This will delete ALL collections!")
    
    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() != "yes":
        logger.info("Reset cancelled")
        return
    
    try:
        LlamaIndexDB.delete_all_data()
        logger.info("Reset complete - all collections deleted")
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Iowa Agriculture RAG Pipeline CLI"
    )
    
    subparsers = parser.add_subparsers(help="Available commands", dest="command")
    
    # LOAD command
    load_parser = subparsers.add_parser(
        "load",
        help="Process PDFs and load into vector store"
    )
    load_parser.add_argument(
        "--collection-name",
        type=str,
        required=True,
        help="Name for the ChromaDB collection"
    )
    load_parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(INPUT_FOLDER),
        help=f"Directory containing PDFs (default: {INPUT_FOLDER})"
    )
    load_parser.add_argument(
        "--method",
        type=str,
        choices=CHUNK_METHODS,
        default=DEFAULT_CHUNKING_METHOD, #semantic search
        help="Chunking method to use"
    )
    
    # QUERY command
    query_parser = subparsers.add_parser(
        "query",
        help="Query the vector store"
    )
    query_parser.add_argument(
        "query",
        type=str,
        help="Query text"
    )
    query_parser.add_argument(
        "--collection-name",
        type=str,
        required=True,
        help="Collection to query"
    )
    
    # CHAT command
    chat_parser = subparsers.add_parser(
        "chat",
        help="Chat with LLM using retrieved context"
    )
    chat_parser.add_argument(
        "query",
        type=str,
        help="Your question"
    )
    chat_parser.add_argument(
        "--collection-name",
        type=str,
        required=True,
        help="Collection to use for context"
    )
    
    # INFO command
    info_parser = subparsers.add_parser(
        "info",
        help="Show database information"
    )
    
    # DELETE-COLLECTION command
    delete_parser = subparsers.add_parser(
        "delete-collection",
        help="Delete a collection"
    )
    delete_parser.add_argument(
        "collection_name",
        type=str,
        help="Collection to delete"
    )
    
    # RESET command
    reset_parser = subparsers.add_parser(
        "reset",
        help="Delete all collections (DANGEROUS!)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to appropriate command
    if args.command == "load":
        load_command(args)
    elif args.command == "query":
        query_command(args)
    elif args.command == "chat":
        chat_command(args)
    elif args.command == "info":
        info_command(args)
    elif args.command == "delete-collection":
        delete_collection_command(args)
    elif args.command == "reset":
        reset_command(args)


if __name__ == "__main__":
    main()