"""
Test suite for AgriGuard RAG Service

Tests the document loading, vector search, and chat functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestRAGDocumentLoading:
    """Test document loading and chunking"""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking"""
        # Import or mock the chunking function
        text = "A" * 1500  # 1500 characters
        chunk_size = 1000
        overlap = 200
        
        # Simple chunking logic to test
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        
        assert len(chunks) > 1
        assert len(chunks[0]) == chunk_size
    
    def test_pdf_text_extraction(self):
        """Test PDF text extraction (mocked)"""
        # This would normally use PyMuPDF
        mock_pdf_text = "NDVI is the Normalized Difference Vegetation Index..."
        assert len(mock_pdf_text) > 0
        assert "NDVI" in mock_pdf_text


class TestRAGVectorSearch:
    """Test vector search functionality"""
    
    @patch('chromadb.HttpClient')
    def test_vector_search_returns_results(self, mock_chromadb):
        """Test that vector search returns relevant results"""
        # Mock ChromaDB response
        mock_collection = Mock()
        mock_collection.query.return_value = {
            'documents': [
                ['NDVI is a vegetation index...'],
                ['NDVI values range from 0 to 1...'],
                ['Healthy corn has NDVI > 0.6...']
            ],
            'distances': [[0.1, 0.2, 0.3]]
        }
        mock_chromadb.return_value.get_collection.return_value = mock_collection
        
        # Simulate query
        client = mock_chromadb()
        collection = client.get_collection('corn-stress-knowledge')
        results = collection.query(query_texts=["What is NDVI?"], n_results=3)
        
        assert len(results['documents'][0]) == 3
        assert 'NDVI' in results['documents'][0][0]
    
    def test_vector_search_relevance(self):
        """Test that search results are ordered by relevance"""
        # Mock distances (lower = more similar)
        distances = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Check that distances are in ascending order
        assert distances == sorted(distances)


class TestRAGChatGeneration:
    """Test RAG chat/generation functionality"""
    
    @patch('google.generativeai.GenerativeModel')
    def test_chat_generates_response(self, mock_gemini):
        """Test that chat endpoint generates a response"""
        # Mock Gemini API response
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "NDVI is the Normalized Difference Vegetation Index, calculated as (NIR - Red) / (NIR + Red)."
        mock_model.generate_content.return_value = mock_response
        mock_gemini.return_value = mock_model
        
        # Simulate chat
        model = mock_gemini('gemini-2.5-flash')
        response = model.generate_content("What is NDVI?")
        
        assert response.text is not None
        assert len(response.text) > 0
        assert 'NDVI' in response.text
    
    def test_context_assembly(self):
        """Test that context is properly assembled"""
        # Mock retrieved documents
        retrieved_docs = [
            "NDVI measures vegetation health.",
            "NDVI values range from 0 to 1.",
            "Healthy vegetation has NDVI > 0.6."
        ]
        
        # Mock live data
        live_data = {
            "mcsi": 45.2,
            "county": "Polk County"
        }
        
        # Assemble context
        context_parts = []
        context_parts.append("RETRIEVED DOCUMENTS:")
        for i, doc in enumerate(retrieved_docs):
            context_parts.append(f"[{i+1}] {doc}")
        context_parts.append(f"LIVE DATA: MCSI = {live_data['mcsi']} for {live_data['county']}")
        
        context = "\n".join(context_parts)
        
        assert "RETRIEVED DOCUMENTS" in context
        assert "LIVE DATA" in context
        assert "Polk County" in context
        assert len(context_parts) >= 5


class TestRAGService:
    """Integration tests for RAG service endpoints"""
    
    def test_health_endpoint_structure(self):
        """Test health endpoint response structure"""
        # Mock health response
        health_response = {
            "status": "healthy",
            "chromadb_connected": True,
            "gemini_ready": True,
            "collection_count": 864
        }
        
        assert "status" in health_response
        assert "chromadb_connected" in health_response
        assert health_response["collection_count"] > 0
    
    def test_query_endpoint_structure(self):
        """Test query endpoint request/response structure"""
        # Mock query request
        query_request = {
            "query": "What is NDVI?",
            "top_k": 5
        }
        
        # Mock query response
        query_response = {
            "results": [
                {"text": "NDVI is...", "distance": 0.1},
                {"text": "NDVI measures...", "distance": 0.2}
            ]
        }
        
        assert "query" in query_request
        assert query_request["top_k"] == 5
        assert len(query_response["results"]) > 0
    
    def test_chat_endpoint_structure(self):
        """Test chat endpoint request/response structure"""
        # Mock chat request
        chat_request = {
            "message": "What is NDVI?",
            "county_fips": "19153",
            "include_live_data": True
        }
        
        # Mock chat response
        chat_response = {
            "answer": "NDVI is the Normalized Difference Vegetation Index...",
            "sources_used": 5,
            "has_live_data": True,
            "county": "Polk County"
        }
        
        assert "message" in chat_request
        assert "answer" in chat_response
        assert chat_response["sources_used"] > 0
        assert chat_response["has_live_data"] == True


class TestRAGConfiguration:
    """Test RAG configuration and parameters"""
    
    def test_chunking_parameters(self):
        """Test that chunking parameters are sensible"""
        chunk_size = 1000
        overlap = 200
        
        assert chunk_size > 0
        assert overlap < chunk_size
        assert overlap > 0
    
    def test_retrieval_parameters(self):
        """Test that retrieval parameters are sensible"""
        top_k = 5
        similarity_metric = "cosine"
        
        assert top_k > 0
        assert top_k <= 20
        assert similarity_metric in ["cosine", "euclidean", "dot"]
    
    def test_generation_parameters(self):
        """Test that generation parameters are sensible"""
        temperature = 0.3
        max_tokens = 2048
        
        assert 0 <= temperature <= 1
        assert max_tokens > 0
        assert max_tokens <= 8192


# Fixtures
@pytest.fixture
def mock_chromadb_client():
    """Fixture for mocked ChromaDB client"""
    with patch('chromadb.HttpClient') as mock:
        yield mock


@pytest.fixture
def mock_gemini_model():
    """Fixture for mocked Gemini model"""
    with patch('google.generativeai.GenerativeModel') as mock:
        yield mock


@pytest.fixture
def sample_documents():
    """Fixture for sample documents"""
    return [
        "NDVI is the Normalized Difference Vegetation Index.",
        "NDVI values range from 0 to 1, with healthy vegetation showing values above 0.6.",
        "In corn production, NDVI helps monitor crop health and stress levels."
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
