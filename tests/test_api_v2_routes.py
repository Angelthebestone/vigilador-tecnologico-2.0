from uuid import UUID


def test_api_v2_plan_and_graph_routes(memory_repositories):
    client = memory_repositories["client"]

    start_response = client.post("/api/v2/research/start", json={"user_query": "market watch"})
    assert start_response.status_code == 200
    session_id = UUID(start_response.json()["session_id"])

    clarify_response = client.post(
        f"/api/v2/research/{session_id}/clarify",
        json={"answers": {"scope-horizon": "short-term", "scope-geo": "latam"}},
    )
    assert clarify_response.status_code == 200

    plan_response = client.get(f"/api/v2/research/{session_id}/plan")
    assert plan_response.status_code == 200
    assert plan_response.json()["plan"]["version"] == 1

    modify_response = client.post(
        f"/api/v2/research/{session_id}/modify",
        json={"priority_weight": 80, "global_constraints": {"depth_limit": 4}},
    )
    assert modify_response.status_code == 200
    assert modify_response.json()["plan"]["version"] == 2

    approve_response = client.post(f"/api/v2/research/{session_id}/approve", json={"approved": True})
    assert approve_response.status_code == 200

    analytics_response = client.get(f"/api/v2/research/{session_id}/graph/analytics")
    assert analytics_response.status_code == 200
    assert analytics_response.json()["node_count"] > 0
    assert analytics_response.json()["clusters"]

    nodes_response = client.get(f"/api/v2/research/{session_id}/graph/nodes")
    assert nodes_response.status_code == 200
    assert nodes_response.json()["total"] > 0

    graph_response = client.get(f"/api/v2/research/{session_id}/graph")
    assert graph_response.status_code == 200
    graph_payload = graph_response.json()
    source_node_id = graph_payload["nodes"][0]["id"]
    target_node_id = graph_payload["nodes"][-1]["id"]

    path_response = client.get(
        f"/api/v2/research/{session_id}/graph/path",
        params={"source_node_id": source_node_id, "target_node_id": target_node_id},
    )
    assert path_response.status_code in (200, 404)

    search_response = client.get(
        f"/api/v2/research/{session_id}/graph/search",
        params={"query": "market"},
    )
    assert search_response.status_code == 200
    assert search_response.json()["items"]
