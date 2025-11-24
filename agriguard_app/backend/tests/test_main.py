import sys
from pathlib import Path

# Ensure the backend directory (where main.py lives) is on the Python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200