from fastapi.testclient import TestClient
from agriguard.api.main import app

client = TestClient(app)

def test_health():
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'

def test_docs_redirect():
    r = client.get('/')
    assert 300 <= r.status_code < 400
