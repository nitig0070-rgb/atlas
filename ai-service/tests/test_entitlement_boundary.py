import pytest

from app import agent


def test_graph_rejects_unauthorized_evidence_before_writer(monkeypatch):
    monkeypatch.setattr(agent, "retrieve", lambda _question, _allowed, **_kwargs: [
        {"report_id": "R-101", "text": "private market value"}
    ])
    with pytest.raises(RuntimeError, match="unauthorized evidence"):
        agent.lookup({"question": "market size", "allowed": {"R-103"}, "client_id": "C-02"})


def test_explicit_report_query_is_filtered_to_that_entitled_report(monkeypatch):
    calls = {}
    def fake_retrieve(question, allowed, **kwargs):
        calls.update(question=question, allowed=allowed, **kwargs)
        return [{"report_id": "R-103", "text": "household filters", "page": 5}]
    monkeypatch.setattr(agent, "retrieve", fake_retrieve)
    state = agent.lookup({"question": "For report R-103, what products are included?",
                          "allowed": {"R-101", "R-103"}, "client_id": "C-01"})
    assert calls["report_filter"] == {"R-103"}
    assert state["evidence"][0]["report_id"] == "R-103"
