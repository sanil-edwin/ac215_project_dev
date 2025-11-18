"""
Hybrid Retrieval with Reciprocal Rank Fusion (RRF).

RRF Formula: score(d) = Σ (1 / (k + rank(d)))
where k is typically 60 (default constant)
"""

import logging
from typing import List, Tuple, Dict
from dataclasses import dataclass
from collections import defaultdict

# BM25 implementation
from rank_bm25 import BM25Okapi

from vector_store import LlamaIndexDB

logger = logging.getLogger(__name__)


@dataclass
class FusedResult:
    """Container for RRF-fused search result."""
    text: str
    rrf_score: float
    vector_rank: int  # 0 if not in vector results
    bm25_rank: int    # 0 if not in BM25 results
    final_rank: int


class RRFHybridRetriever:
    """
    Hybrid retrieval using Reciprocal Rank Fusion (RRF).
    
    Usage:
        retriever = RRFHybridRetriever("iowa-agriculture")
        results = retriever.search("corn drought Iowa", top_k=5)
    """
    
    def __init__(
        self,
        collection_name: str,
        k: int = 60,  # RRF constant (standard is 60)
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75
    ):
        """
        Initialize RRF hybrid retriever.
        
        Args:
            collection_name: ChromaDB collection name
            k: RRF constant (larger = less weight on high ranks)
            bm25_k1: BM25 term frequency saturation
            bm25_b: BM25 document length normalization
        """
        self.collection_name = collection_name
        self.rrf_k = k
        self.bm25_k1 = bm25_k1
        self.bm25_b = bm25_b
        
        # Initialize vector store
        self.vector_db = LlamaIndexDB(collection_name)
        
        # BM25 index (lazy initialization)
        self.bm25_index = None
        self.corpus_texts = None
        
        logger.info(f"Initialized RRF HybridRetriever for '{collection_name}' (k={k})")
    
    def _initialize_bm25(self):
        """Initialize BM25 index (lazy - only on first search)."""
        if self.bm25_index is not None:
            return
        
        logger.info("Initializing BM25 index...")
        
        collection = self.vector_db.chroma_collection
        all_docs = collection.get()
        
        if not all_docs or not all_docs['documents']:
            logger.warning("No documents found in collection!")
            self.corpus_texts = []
            self.bm25_index = None
            return
        
        self.corpus_texts = all_docs['documents']
        tokenized_corpus = [doc.lower().split() for doc in self.corpus_texts]
        self.bm25_index = BM25Okapi(tokenized_corpus, k1=self.bm25_k1, b=self.bm25_b)
        
        logger.info(f"✓ BM25 index built with {len(self.corpus_texts)} documents")
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        vector_weight: float = 1.0,
        bm25_weight: float = 1.0
    ) -> List[FusedResult]:
        """
        Hybrid search using Reciprocal Rank Fusion.
        
        Args:
            query: Search query
            top_k: Number of results to return
            vector_weight: Weight for vector rankings (default: 1.0)
            bm25_weight: Weight for BM25 rankings (default: 1.0)
            
        Returns:
            List of FusedResult objects sorted by RRF score
        """
        # Initialize BM25 on first search
        if self.bm25_index is None:
            self._initialize_bm25()
        
        if not self.corpus_texts:
            logger.warning("Empty corpus, cannot perform hybrid search")
            return []
        
        logger.debug(f"RRF search: '{query}' (top_k={top_k})")
        
        # Step 1: Get vector search rankings (use vector_search to avoid circular dependency)
        vector_top_k = min(top_k * 3, len(self.corpus_texts))
        vector_results = self.vector_db.vector_search(query, top_k=vector_top_k)
        
        # Deduplicate vector results - keep first occurrence (best rank) of each unique text
        seen_texts = set()
        deduplicated_vector_results = []
        for text, score in vector_results:
            # Normalize text for comparison (strip whitespace)
            text_normalized = text.strip()
            if text_normalized not in seen_texts:
                seen_texts.add(text_normalized)
                deduplicated_vector_results.append((text, score))
        
        # Create ranking: text -> rank (1-indexed) using deduplicated results
        vector_rankings = {text.strip(): rank for rank, (text, _) in enumerate(deduplicated_vector_results, start=1)}
        
        # Step 2: Get BM25 rankings
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        
        # Sort by BM25 score to get rankings
        bm25_ranked_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:vector_top_k]  # Take same number as vector
        
        # Deduplicate BM25 rankings - keep first occurrence (best rank) of each unique text
        seen_bm25 = set()
        bm25_rankings = {}
        rank = 1
        for idx in bm25_ranked_indices:
            text = self.corpus_texts[idx].strip()
            if text not in seen_bm25:
                seen_bm25.add(text)
                bm25_rankings[text] = rank
                rank += 1
        
        # Step 3: Apply Reciprocal Rank Fusion
        rrf_scores = self._compute_rrf(
            vector_rankings,
            bm25_rankings,
            vector_weight,
            bm25_weight
        )
        
        # Step 4: Sort by RRF score and create results
        # Note: rrf_scores already has unique keys (from deduplicated vector_rankings and bm25_rankings)
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for rank, (text, rrf_score) in enumerate(sorted_docs, start=1):
            text_normalized = text.strip()
            results.append(FusedResult(
                text=text.strip(),
                rrf_score=rrf_score,
                vector_rank=vector_rankings.get(text_normalized, 0),
                bm25_rank=bm25_rankings.get(text_normalized, 0),
                final_rank=rank
            ))
        
        logger.debug(f"RRF complete. Top score: {results[0].rrf_score:.4f}")
        return results
    
    def _compute_rrf(
        self,
        vector_rankings: Dict[str, int],
        bm25_rankings: Dict[str, int],
        vector_weight: float,
        bm25_weight: float
    ) -> Dict[str, float]:
        """
        Compute Reciprocal Rank Fusion scores.
        
        RRF formula: score(d) = Σ w_i / (k + rank_i(d))
        
        Args:
            vector_rankings: {text: rank} from vector search
            bm25_rankings: {text: rank} from BM25
            vector_weight: Weight for vector contribution
            bm25_weight: Weight for BM25 contribution
            
        Returns:
            {text: rrf_score} for all documents
        """
        rrf_scores = defaultdict(float)
        
        # Add vector contributions
        for text, rank in vector_rankings.items():
            rrf_scores[text] += vector_weight / (self.rrf_k + rank)
        
        # Add BM25 contributions
        for text, rank in bm25_rankings.items():
            rrf_scores[text] += bm25_weight / (self.rrf_k + rank)
        
        return dict(rrf_scores)
    
    def search_with_breakdown(
        self,
        query: str,
        top_k: int = 5
    ) -> dict:
        """
        Search with detailed breakdown showing RRF fusion process.
        
        Returns:
            Dict with results, vector_only, bm25_only, and fusion details
        """
        # Get individual rankings (use vector_search to avoid circular dependency)
        vector_results = self.vector_db.vector_search(query, top_k=top_k*2)
        
        if self.bm25_index is None:
            self._initialize_bm25()
        
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        bm25_ranked_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True
        )[:top_k*2]
        
        bm25_results = [
            (self.corpus_texts[idx], bm25_scores[idx])
            for idx in bm25_ranked_indices
        ]
        
        # Get fused results
        fused_results = self.search(query, top_k=top_k)
        
        return {
            "fused": fused_results,
            "vector_only": vector_results[:top_k],
            "bm25_only": bm25_results[:top_k],
            "metadata": {
                "rrf_k": self.rrf_k,
                "query": query,
                "top_k": top_k
            }
        }


def compare_fusion_methods(
    collection_name: str,
    query: str,
    top_k: int = 3
):
    """
    Compare RRF vs weighted score fusion.
    
    Demonstrates why RRF is often better.
    """
    print(f"\n{'='*70}")
    print(f"FUSION COMPARISON: '{query}'")
    print(f"{'='*70}\n")
    
    retriever = RRFHybridRetriever(collection_name)
    breakdown = retriever.search_with_breakdown(query, top_k=top_k)
    
    print("VECTOR ONLY:")
    print("-" * 70)
    for i, (text, score) in enumerate(breakdown['vector_only'], 1):
        print(f"Rank {i}: Score {score:.4f}")
        print(f"  {text[:80]}...\n")
    
    print("\nBM25 ONLY:")
    print("-" * 70)
    for i, (text, score) in enumerate(breakdown['bm25_only'], 1):
        print(f"Rank {i}: Score {score:.4f}")
        print(f"  {text[:80]}...\n")
    
    print("\nRRF FUSION:")
    print("-" * 70)
    for result in breakdown['fused']:
        print(f"Rank {result.final_rank}: RRF Score {result.rrf_score:.4f}")
        print(f"  Vector Rank: {result.vector_rank}, BM25 Rank: {result.bm25_rank}")
        print(f"  {result.text[:80]}...\n")

def main():
    """Test RRF hybrid retrieval."""
    logging.basicConfig(level=logging.INFO)
    
    # test on real data
    collection_name = "iowa-agriculture"
    
    print("\n\n" + "="*70)
    print("TESTING RRF ON REAL DATA")
    print("="*70)
    
    queries = [
        "corn yield Iowa 2012",
        "drought stress mitigation",
        "NDMI irrigation timing"
    ]
    
    for query in queries:
        print(f"\n\nQuery: '{query}'")
        print("-" * 70)
        
        retriever = RRFHybridRetriever(collection_name)
        results = retriever.search(query, top_k=3)
        
        for r in results:
            print(f"\nRank {r.final_rank}: RRF={r.rrf_score:.4f}")
            print(f"  Vector Rank: {r.vector_rank}, BM25 Rank: {r.bm25_rank}")
            print(f"  {r.text[:100]}...")


if __name__ == "__main__":
    main()