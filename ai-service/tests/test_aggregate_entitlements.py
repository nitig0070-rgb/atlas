from app import agent


def test_natural_language_my_reports_aggregate_uses_client_scoped_query(monkeypatch):
    state = {"question": "Which sectors are represented in my reports?", "client_id": "C-02"}
    routed = agent.route_question(state)
    seen = {}

    def aggregate(query_name, client_id):
        seen["query_name"] = query_name
        seen["client_id"] = client_id
        return ([{"sector": "water", "report_count": 1}], "WHERE e.client_id=:client_id")

    monkeypatch.setattr(agent, "execute_read_only_query", aggregate)
    result = agent.answer({**state, **routed})

    assert routed["route"] == "aggregate"
    assert seen == {"query_name": "reports_by_sector", "client_id": "C-02"}
    assert "water: 1" in result["answer"]
    assert "other client" not in result["answer"].lower()
