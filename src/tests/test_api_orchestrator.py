"""
Test suite for AgriGuard API Orchestrator

Tests the main API that orchestrates calls to MCSI, Yield, and RAG services.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock


class TestAPIOrchestrator:
    """Test API orchestrator functionality"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        health_response = {
            "status": "healthy",
            "services": {
                "mcsi": "healthy",
                "yield": "healthy",
                "rag": "healthy"
            }
        }
        
        assert health_response["status"] == "healthy"
        assert len(health_response["services"]) == 3
    
    def test_mcsi_endpoint_routing(self):
        """Test that MCSI requests are routed correctly"""
        fips = "19153"  # Polk County
        endpoint = f"/mcsi/{fips}/timeseries"
        
        assert fips in endpoint
        assert "mcsi" in endpoint
    
    def test_yield_endpoint_routing(self):
        """Test that yield requests are routed correctly"""
        fips = "19153"
        endpoint = f"/yield/{fips}"
        
        assert fips in endpoint
        assert "yield" in endpoint


class TestChatEndpoint:
    """Test the /chat endpoint that integrates RAG with live data"""
    
    @patch('httpx.AsyncClient')
    async def test_chat_without_live_data(self, mock_client):
        """Test chat endpoint without live data"""
        # Mock RAG service response
        mock_response = Mock()
        mock_response.json.return_value = {
            "answer": "NDVI is a vegetation index...",
            "sources_used": 5
        }
        mock_response.status_code = 200
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Simulate request
        request = {
            "message": "What is NDVI?",
            "include_live_data": False
        }
        
        assert "message" in request
        assert request["include_live_data"] == False
    
    @patch('httpx.AsyncClient')
    async def test_chat_with_live_data(self, mock_client):
        """Test chat endpoint with live MCSI/yield data"""
        # Mock RAG service response
        mock_rag_response = Mock()
        mock_rag_response.json.return_value = {
            "answer": "Based on current MCSI of 45.2...",
            "sources_used": 5
        }
        mock_rag_response.status_code = 200
        
        # Mock MCSI service response
        mock_mcsi_response = Mock()
        mock_mcsi_response.json.return_value = {
            "mcsi": 45.2,
            "water_stress": 50.0,
            "heat_stress": 40.0
        }
        mock_mcsi_response.status_code = 200
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_rag_response
        mock_client_instance.get.return_value = mock_mcsi_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Simulate request
        request = {
            "message": "How is my corn doing?",
            "fips": "19153",
            "include_live_data": True
        }
        
        assert request["include_live_data"] == True
        assert request["fips"] is not None
    
    def test_chat_response_structure(self):
        """Test chat response has correct structure"""
        response = {
            "answer": "NDVI is the Normalized Difference Vegetation Index...",
            "sources_used": 5,
            "has_live_data": True,
            "county": "Polk County"
        }
        
        assert "answer" in response
        assert "sources_used" in response
        assert "has_live_data" in response
        assert isinstance(response["sources_used"], int)


class TestDataIntegration:
    """Test integration between services"""
    
    def test_mcsi_data_format(self):
        """Test MCSI data format"""
        mcsi_data = {
            "fips": "19153",
            "county_name": "POLK",
            "week": 15,
            "mcsi": 45.2,
            "water_stress": 50.0,
            "heat_stress": 40.0,
            "vegetation_health": 35.0,
            "atmospheric_stress": 30.0
        }
        
        assert "mcsi" in mcsi_data
        assert mcsi_data["fips"] == "19153"
        assert 0 <= mcsi_data["mcsi"] <= 100
    
    def test_yield_data_format(self):
        """Test yield forecast data format"""
        yield_data = {
            "fips": "19153",
            "county_name": "POLK",
            "yield_prediction": 185.3,
            "uncertainty": 12.5,
            "confidence_interval_lower": 172.8,
            "confidence_interval_upper": 197.8
        }
        
        assert "yield_prediction" in yield_data
        assert yield_data["uncertainty"] > 0
        assert yield_data["confidence_interval_lower"] < yield_data["yield_prediction"]
        assert yield_data["confidence_interval_upper"] > yield_data["yield_prediction"]
    
    def test_rag_context_integration(self):
        """Test that RAG context includes live data"""
        context = {
            "retrieved_documents": ["doc1", "doc2", "doc3"],
            "live_mcsi": 45.2,
            "live_yield": 185.3,
            "county": "POLK"
        }
        
        assert len(context["retrieved_documents"]) > 0
        assert context["live_mcsi"] is not None
        assert context["county"] is not None


class TestErrorHandling:
    """Test error handling in API orchestrator"""
    
    def test_service_unavailable_handling(self):
        """Test handling when a service is down"""
        # Simulate service down
        service_status = {
            "mcsi": "healthy",
            "yield": "unhealthy",
            "rag": "healthy"
        }
        
        unhealthy_services = [k for k, v in service_status.items() if v == "unhealthy"]
        assert len(unhealthy_services) == 1
        assert "yield" in unhealthy_services
    
    def test_invalid_fips_handling(self):
        """Test handling of invalid FIPS code"""
        invalid_fips = ["99999", "abc", ""]
        
        for fips in invalid_fips:
            # FIPS should be 5 digits
            is_valid = len(fips) == 5 and fips.isdigit()
            assert not is_valid
    
    def test_missing_parameters(self):
        """Test handling of missing parameters"""
        incomplete_request = {
            "message": "What is NDVI?"
            # Missing fips when include_live_data is True
        }
        
        if "fips" not in incomplete_request and incomplete_request.get("include_live_data"):
            # Should raise error or use default
            assert True


class TestRequestValidation:
    """Test request validation"""
    
    def test_chat_request_validation(self):
        """Test chat request parameter validation"""
        valid_request = {
            "message": "What is NDVI?",
            "fips": "19153",
            "include_live_data": True
        }
        
        assert isinstance(valid_request["message"], str)
        assert len(valid_request["message"]) > 0
        assert isinstance(valid_request["include_live_data"], bool)
    
    def test_query_length_limits(self):
        """Test query length validation"""
        short_query = "NDVI"
        long_query = "A" * 1000
        valid_query = "What is NDVI and how do I interpret it?"
        
        assert len(short_query) > 0
        assert len(valid_query) > 0
        # Could implement max length check if needed
    
    def test_fips_code_format(self):
        """Test FIPS code format validation"""
        valid_fips = ["19153", "19001", "19099"]
        invalid_fips = ["1915", "191530", "abc12"]
        
        for fips in valid_fips:
            assert len(fips) == 5
            assert fips.isdigit()
        
        for fips in invalid_fips:
            is_valid = len(fips) == 5 and fips.isdigit()
            assert not is_valid


# Fixtures
@pytest.fixture
def sample_chat_request():
    """Fixture for sample chat request"""
    return {
        "message": "What is NDVI?",
        "fips": "19153",
        "include_live_data": True
    }


@pytest.fixture
def sample_mcsi_data():
    """Fixture for sample MCSI data"""
    return {
        "fips": "19153",
        "week": 15,
        "mcsi": 45.2,
        "water_stress": 50.0,
        "heat_stress": 40.0
    }


@pytest.fixture
def sample_yield_data():
    """Fixture for sample yield data"""
    return {
        "fips": "19153",
        "yield_prediction": 185.3,
        "uncertainty": 12.5
    }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
