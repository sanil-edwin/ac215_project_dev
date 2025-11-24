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
    - RRF hybrid querying (BM25 + vector with rank fusion)
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
        
        # Use token-based validation - semantic chunking should produce chunks under this limit
        # MAX_CHUNK_CHARS from preprocessing is ~16,000 chars (4000 tokens * 4 chars/token)
        EMBED_TOKEN_LIMIT = 4000  # Vertex AI text-embedding-004 limit
        CHARS_PER_TOKEN_ESTIMATE = 4.0
        MAX_CHARS = int(EMBED_TOKEN_LIMIT * CHARS_PER_TOKEN_ESTIMATE)  # ~16,000 chars
        # Add small buffer (5%) to account for token estimation variance
        MAX_CHARS_WITH_BUFFER = int(MAX_CHARS * 1.05)  # ~16,800 chars
        BATCH_SIZE = 10  # Process only 10 documents at a time
        
        def approx_tokens(text: str) -> int:
            """Estimate token count from character count."""
            return int(len(text) / CHARS_PER_TOKEN_ESTIMATE)
        
        # Filter oversized documents (shouldn't happen if chunking worked correctly)
        # Semantic chunking should already ensure chunks are under EMBED_TOKEN_LIMIT
        valid_documents = []
        skipped_count = 0
        for idx, doc in enumerate(documents):
            total_chars = len(doc.text)
            if hasattr(doc, 'metadata') and 'window' in doc.metadata:
                total_chars += len(doc.metadata.get('window', ''))
            
            # Primary check: token limit (most accurate)
            est_tokens = approx_tokens(doc.text)
            # Secondary check: character limit with buffer (for safety)
            if est_tokens <= EMBED_TOKEN_LIMIT and total_chars <= MAX_CHARS_WITH_BUFFER:
                valid_documents.append(doc)
            else:
                skipped_count += 1
                logger.warning(
                    f"Skipping oversized document {idx}: {total_chars:,} chars "
                    f"(~{est_tokens:,} tokens, limit: {EMBED_TOKEN_LIMIT:,} tokens / {MAX_CHARS:,} chars)"
                )
        
        if skipped_count > 0:
            logger.warning(
                f"Skipped {skipped_count} oversized documents. "
                f"This suggests semantic chunking may need adjustment."
            )
        
        if not valid_documents:
            logger.error("No valid documents to load!")
            return None
        
        # Process in batches
        index = None  # Initialize index
        for i in range(0, len(valid_documents), BATCH_SIZE):
            batch = valid_documents[i:i + BATCH_SIZE]
            logger.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(valid_documents)-1)//BATCH_SIZE + 1}: {len(batch)} documents")
            
            try:
                if i == 0:
                    # First batch: create index
                    index = VectorStoreIndex.from_documents(
                        batch,
                        storage_context=self.storage_context,
                        embed_model=self.embed_model,
                        show_progress=True
                    )
                else:
                    # Subsequent batches: insert into existing index
                    if index is not None:  # Safety check
                        for doc in batch:
                            index.insert(doc)
                    else:
                        logger.error("Index not created, skipping batch")
                        continue
                
            except Exception as e:
                logger.error(f"Failed to process batch: {e}")
                continue
        
        logger.info(f"✓ Successfully loaded {len(valid_documents)} documents")
        return index
    
    def vector_search(self, query_text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Direct vector search (no RRF) - used internally by RRFHybridRetriever.
        
        Args:
            query_text: Query string
            top_k: Number of results to return
            
        Returns:
            List of tuples: [(text, similarity_score), ...]
        """
        logger.debug(f"Vector search: '{query_text}' (top_k={top_k})")
        
        try:
            # Load existing index from vector store
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
            nodes = retriever.retrieve(query_text)
            
            # Extract text and scores
            results = []
            for node in nodes:
                text = node.get_content()
                # Get similarity score from node
                # LlamaIndex nodes typically have score attribute (higher = more similar)
                # If not available, try to get from node metadata or default to 1.0
                if hasattr(node, 'score') and node.score is not None:
                    score = float(node.score)
                elif hasattr(node, 'node') and hasattr(node.node, 'score'):
                    score = float(node.node.score)
                else:
                    # Default score if not available (will be ranked by RRF anyway)
                    score = 1.0
                results.append((text, score))
            
            logger.debug(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise
    
    def query(
            self,
            query_text: str,
            top_k: int = 5,
            rrf_k: int = 60,
            vector_weight: float = 1.0,
            bm25_weight: float = 1.0
        ) -> List[Tuple[str, float]]:
            """
            Query using RRF hybrid search (BM25 + vector with rank fusion).
            
            Args:
                query_text: Query string
                top_k: Number of results to return
                rrf_k: RRF constant (default 60, standard value)
                vector_weight: Weight for vector rankings (default 1.0)
                bm25_weight: Weight for BM25 rankings (default 1.0)
                
            Returns:
                List of tuples: [(text, rrf_score), ...]
            """
            from rrf_hybrid import RRFHybridRetriever
            
            logger.debug(f"RRF hybrid query: '{query_text}' (top_k={top_k})")
            
            retriever = RRFHybridRetriever(
                collection_name=self.collection_name,
                k=rrf_k
            )
            
            results = retriever.search(
                query_text,
                top_k=top_k,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight
            )
            
            # Convert to (text, score) tuples
            return [(r.text, r.rrf_score) for r in results]
        
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