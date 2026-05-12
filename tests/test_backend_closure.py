def test_health_endpoint_reports_runtime_metadata(memory_repositories):
    client = memory_repositories["client"]

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["ready"] is True
    assert payload["database"] == "initialized"
    assert payload["runtime"]["service"] == "Vigilancia Tecnologica Multiagente"
    assert payload["runtime"]["api_base"] == "/api/v2"
    assert payload["runtime"]["closure_status"]["api_v2"] == "ready"
