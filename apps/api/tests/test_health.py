def test_health_reports_database_and_content(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["content"].startswith("ok")


def test_health_requires_no_authentication(client):
    # Deliberate: Docker healthchecks and uptime monitors need it.
    assert client.get("/api/health").status_code == 200
