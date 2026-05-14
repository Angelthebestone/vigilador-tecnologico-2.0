from uuid import UUID


def test_research_lifecycle_end_to_end(memory_repositories):
    client = memory_repositories["client"]

    start_response = client.post("/research/start", json={"user_query": "technology watch", "scope": {"geo": "global"}})
    assert start_response.status_code == 200
    session_id = UUID(start_response.json()["session_id"])
    assert start_response.json()["status"] == "clarifying"
    stream_response = client.get(f"/research/{session_id}/stream")
    assert "ClarificationRequested" in stream_response.text

    clarify_response = client.post(f"/research/{session_id}/clarify", json={"answers": {"scope-horizon": "mid-term", "scope-geo": "global"}})
    assert clarify_response.status_code == 200
    assert clarify_response.json()["status"] == "planning"
    assert clarify_response.json()["requires_approval"] is True

    approve_response = client.post(f"/research/{session_id}/approve", json={"approved": True})
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "completed"

    report_response = client.get(f"/research/{session_id}/report")
    assert report_response.status_code == 200
    assert "total_sources_consulted" in report_response.json()

    sources_response = client.get(f"/research/{session_id}/sources")
    assert sources_response.status_code == 200
    assert sources_response.json()["total"] > 0

    graph_response = client.get(f"/research/{session_id}/graph")
    assert graph_response.status_code == 200
    assert graph_response.json()["nodes"]
    assert graph_response.json()["edges"]

    providers_response = client.get(f"/research/{session_id}/providers")
    assert providers_response.status_code == 200
    assert providers_response.json()["providers"]

    iterations_response = client.get(f"/research/{session_id}/iterations")
    assert iterations_response.status_code == 200
    assert iterations_response.json()["items"]

    contracts_response = client.get(f"/research/{session_id}/agent-contracts")
    assert contracts_response.status_code == 200
    assert contracts_response.json()["skill_matrix"]

    evaluation_response = client.get(f"/research/{session_id}/evaluation")
    assert evaluation_response.status_code == 200
    assert evaluation_response.json()["by_branch"]

