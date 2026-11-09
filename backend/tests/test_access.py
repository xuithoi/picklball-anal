from fastapi.testclient import TestClient
from app import main


def test_auth_protects_homepage_api_and_downloads(monkeypatch):
    monkeypatch.setenv('APP_PASSWORD', 'test-secret-Đỗ')
    monkeypatch.setenv('APP_USERNAME', 'kun')
    client = TestClient(main.app)
    assert client.get('/api/health').status_code == 200
    for path in ['/', '/api/jobs/not-a-uuid', '/api/jobs/not-a-uuid/files/positions.json']:
        assert client.get(path).status_code == 401
    assert client.get('/api/jobs/not-a-uuid', auth=('kun', 'wrong')).status_code == 401
    import base64
    header = 'Basic ' + base64.b64encode('kun:test-secret-Đỗ'.encode()).decode()
    assert client.get('/api/jobs/not-a-uuid', headers={'Authorization': header}).status_code == 400
    assert client.get('/', headers={'Authorization':'Basic invalid-base64'}).status_code == 401


def test_public_deployment_fails_closed_without_password(monkeypatch):
    monkeypatch.setenv('REQUIRE_AUTH', '1')
    monkeypatch.delenv('APP_PASSWORD', raising=False)
    assert TestClient(main.app).get('/api/jobs/invalid').status_code == 503
