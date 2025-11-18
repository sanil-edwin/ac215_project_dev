from fastapi.testclient import TestClient
from agriguard.api.main import app

client = TestClient(app)

def test_reject_non_iowa_list():
    r = client.get('/stress', params={'date': '2024-07-16', 'fips': '17001,55001'})
    assert r.status_code == 400
    assert 'Non-Iowa FIPS' in r.json()['detail']

def test_reject_non_iowa_single():
    r = client.get('/stress/prob', params={'date': '2024-07-16', 'fips': '55001'})
    assert r.status_code == 400
