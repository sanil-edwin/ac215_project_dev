'''
LlamaIndex wrapper for ChromaDB vector database and embedding model
Handles document loading, embedding, and retrieval.
'''

import logging
import os
import uuid
from typing import List, Tuple
import chromadb
from google.oauth2 import service_account

#LlamaIndex imports 
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.vertex import VertexTextEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

# Setup
GCP_PROJECT = os.environ.get("GCP_PROJECT")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "768"))
CHROMADB_HOST = os.environ.get("CHROMADB_HOST", "agri-rag-chromadb")
CHROMADB_PORT = int(os.environ.get("CHROMADB_PORT", "8000"))

logger = logging.getLogger(__name__)

creds = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
)


class LlamaIndexDB:
    """
    LlamaIndex wrapper for ChromaDB.
    
    Provides high-level interface for:
    - Loading documents with automatic embedding
    - Querying with semantic search
    - Managing collections
    """
    
    def __init__(self, collection_name: str):
        """
        Initialize LlamaIndexDB.
        
        Args:
            collection_name: Name of the ChromaDB collection
        """
        logger.info(f"Initializing LlamaIndexDB for collection: {collection_name}")
        
        self.collection_name = collection_name
        
        # Connect to ChromaDB
        self.chroma_client = chromadb.HttpClient(
            host=CHROMADB_HOST, 
            port=CHROMADB_PORT
        )
        
        # Get or create ChromaDB collection
        self.chroma_collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        # Wrap ChromaDB collection with LlamaIndex
        self.vector_store = ChromaVectorStore(
            chroma_collection=self.chroma_collection
        )
        
        # Initialize Vertex AI embedding model (wrapped by LlamaIndex)
        # Note: Vertex AI has a 20k token limit PER REQUEST
        # Even with small chunks, batching multiple together can exceed this
        self.embed_model = VertexTextEmbedding(
            model_name=EMBEDDING_MODEL,
            project=GCP_PROJECT,
            location=GCP_LOCATION,
            credentials=creds,
            embed_batch_size=1  # Process one at a time to avoid batching token limit errors
        )
        
        # Create storage context with wrapped ChromaDB
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
        
        logger.info(f"Connected to collection '{collection_name}' ({self.get_count()} chunks)")
    
    def load_documents(self, documents: List[Document]):
        """
        Load documents into the vector store.
        
        LlamaIndex will:
        1. Extract text from documents
        2. Generate embeddings using Vertex AI
        3. Store in ChromaDB
        
        Args:
            documents: List of LlamaIndex Document objects
        """
        logger.info(f"Loading {len(documents)} documents into vector store...")
        
        # Filter out documents that are too large for the embedding model
        # Vertex AI text-embedding-004 has a limit of 20,000 tokens
        # Using very conservative limit after observing actual token counts
        MAX_CHARS = 8000  # ~2000 tokens max to stay well under 20k token limit
        
        valid_documents = []
        oversized_documents = []
        
        for idx, doc in enumerate(documents):
            # Check actual text content
            doc_chars = len(doc.text)
            
            # Also check if there's window context (for sentence-window nodes)
            total_chars = doc_chars
            if hasattr(doc, 'metadata') and 'window' in doc.metadata:
                window_chars = len(doc.metadata.get('window', ''))
                total_chars += window_chars
                if idx < 3:  # Log first 3 for debugging
                    logger.info(
                        f"Doc {idx}: {doc_chars:,} chars + {window_chars:,} window chars "
                        f"= {total_chars:,} total"
                    )
            
            estimated_tokens = total_chars / 4  # Conservative estimate
            
            if total_chars <= MAX_CHARS:
                valid_documents.append(doc)
            else:
                oversized_documents.append(doc)
                logger.warning(
                    f"Skipping oversized document {idx}: {total_chars:,} total characters "
                    f"(~{estimated_tokens:.0f} tokens, max: {MAX_CHARS:,})"
                )
        
        if oversized_documents:
            logger.warning(
                f"Skipped {len(oversized_documents)} oversized documents. "
                f"Processing {len(valid_documents)} valid documents."
            )
        
        if not valid_documents:
            logger.error("No valid documents to load after filtering!")
            return None
        
        try:
            # Create index from valid documents only
            # LlamaIndex handles embedding and storage automatically of user query
            index = VectorStoreIndex.from_documents(
                valid_documents,
                storage_context=self.storage_context,
                embed_model=self.embed_model,
                show_progress=True
            )
            
            logger.info(f"✓ Successfully loaded {len(valid_documents)} documents")
            return index
            
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            logger.error("This may be due to oversized chunks. Try reducing chunk sizes or using a different chunking method.")
            raise
    
    def query(self, query_text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Query the vector store using semantic search.
        
        LlamaIndex will:
        1. Embed the query using Vertex AI
        2. Search ChromaDB for similar vectors
        3. Return top-k results with scores
        
        Args:
            query_text: Query string
            top_k: Number of results to return
            
        Returns:
            List of tuples: [(text, score), (text, score), ...]
        """
        logger.debug(f"Querying: '{query_text}' (top_k={top_k})")
        
        # Create index from existing vector store
        index = VectorStoreIndex.from_vector_store(
            vector_store=self.vector_store,
            embed_model=self.embed_model
        )
        
        # Create retriever
        retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=top_k
        )
        
        # Retrieve nodes
        # LlamaIndex automatically embeds query_text and searches
        nodes = retriever.retrieve(query_text)
        
        # Extract text and scores
        results = [(node.text, node.score) for node in nodes]
        
        logger.debug(f"Retrieved {len(results)} results")
        return results
    
    def get_count(self) -> int:
        """
        Get the number of chunks in the collection.
        
        Returns:
            Number of documents/chunks
        """
        return self.chroma_collection.count()
    
    @staticmethod
    def delete_collection(collection_name: str):
        """
        Delete a specific collection.
        
        Args:
            collection_name: Name of collection to delete
        """
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        try:
            client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise
    
    @staticmethod
    def delete_all_data():
        """
        Delete all collections (reset database).
        
        WARNING: This is destructive and cannot be undone!
        """
        client = chromadb.HttpClient(host=CHROMADB_HOST, port=CHROMADB_PORT)
        collections = client.list_collections()
        
        for collection in collections:
            client.delete_collection(name=collection.name)
            logger.info(f"Deleted collection: {collection.name}")
        
        logger.info(f"Deleted all {len(collections)} collections")


def main():
    """Test the vector store."""
    logging.basicConfig(level=logging.INFO)
    
    # Test basic functionality
    collection_name = "test-collection"
    
    logger.info("Creating test collection...")
    db = LlamaIndexDB(collection_name)
    
    # Create test documents
    test_docs = [
        Document(text="Corn yields in Iowa reached 200 bu/acre in 2024.", 
                metadata={"source": "test"}),
        Document(text="Weather conditions were favorable with adequate rainfall.",
                metadata={"source": "test"}),
        Document(text="Soybean production increased by 5% compared to last year.",
                metadata={"source": "test"}),
    ]
    
    # Load documents
    logger.info("Loading test documents...")
    db.load_documents(test_docs)
    
    # Query
    logger.info("\nQuerying...")
    results = db.query("What were the corn yields?", top_k=2)
    
    for i, (text, score) in enumerate(results, 1):
        print(f"\nResult {i} (Score: {score:.4f}):")
        print(text)
    
    # Cleanup
    logger.info("\nCleaning up...")
    LlamaIndexDB.delete_collection(collection_name)
    logger.info("Test complete!")


if __name__ == "__main__":
    main()