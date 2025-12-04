"""
pytest configuration for AgriGuard test suite

This file configures pytest settings and provides shared fixtures.
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Shared fixtures
@pytest.fixture(scope="session")
def iowa_counties():
    """Fixture providing list of Iowa county FIPS codes"""
    return [
        "19001",  # ADAIR
        "19153",  # POLK
        "19169",  # STORY
        "19113",  # LINN
        # Add more as needed
    ]


@pytest.fixture(scope="session")
def sample_dates():
    """Fixture providing sample dates for testing"""
    return [
        "2024-05-01",  # Start of season
        "2024-07-15",  # Mid-season (pollination)
        "2024-10-31",  # End of season
    ]


@pytest.fixture
def mock_environment_variables(monkeypatch):
    """Fixture to set mock environment variables"""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-12345")
    monkeypatch.setenv("GCP_PROJECT", "test-project")
    monkeypatch.setenv("CHROMADB_HOST", "chromadb")
    monkeypatch.setenv("CHROMADB_PORT", "8000")


@pytest.fixture
def sample_ndvi_timeseries():
    """Fixture providing sample NDVI timeseries"""
    return {
        "dates": ["2024-05-01", "2024-05-17", "2024-06-02"],
        "values": [0.45, 0.68, 0.82]
    }


@pytest.fixture
def sample_mcsi_response():
    """Fixture providing sample MCSI API response"""
    return {
        "fips": "19153",
        "county_name": "POLK",
        "week": 15,
        "mcsi": 45.2,
        "water_stress": 50.0,
        "heat_stress": 40.0,
        "vegetation_health": 35.0,
        "atmospheric_stress": 30.0,
        "timestamp": "2024-07-15T12:00:00Z"
    }


@pytest.fixture
def sample_yield_response():
    """Fixture providing sample yield forecast response"""
    return {
        "fips": "19153",
        "county_name": "POLK",
        "year": 2024,
        "yield_prediction": 185.3,
        "uncertainty": 12.5,
        "confidence_interval_lower": 172.8,
        "confidence_interval_upper": 197.8,
        "model_version": "xgboost_v1.0"
    }


@pytest.fixture
def sample_rag_query():
    """Fixture providing sample RAG query"""
    return {
        "query": "What is NDVI and how do I interpret it?",
        "top_k": 5
    }


@pytest.fixture
def sample_rag_response():
    """Fixture providing sample RAG response"""
    return {
        "results": [
            {
                "text": "NDVI is the Normalized Difference Vegetation Index...",
                "distance": 0.12,
                "source": "MCSI-Interpretation-Guide.pdf"
            },
            {
                "text": "NDVI values range from 0 to 1...",
                "distance": 0.18,
                "source": "MCSI-Interpretation-Guide.pdf"
            }
        ]
    }


@pytest.fixture
def sample_chat_request():
    """Fixture providing sample chat request"""
    return {
        "message": "How is my corn doing this week?",
        "fips": "19153",
        "include_live_data": True
    }


@pytest.fixture
def sample_chat_response():
    """Fixture providing sample chat response"""
    return {
        "answer": "Based on the current MCSI of 45.2 for Polk County...",
        "sources_used": 5,
        "has_live_data": True,
        "county": "Polk County",
        "timestamp": "2024-07-15T12:00:00Z"
    }


# Pytest options
def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run slow tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on command line options"""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)
