import pytest

from app import sql_tool


def test_only_allowlisted_aggregate_name_is_accepted():
    with pytest.raises(ValueError):
        sql_tool.execute_read_only_query("DELETE FROM reports", "C-01")


def test_aggregate_passes_client_id_to_entitlement_filtered_query(monkeypatch):
    observed = {}

    def aggregate(client_id):
        observed["client_id"] = client_id
        return ([{"sector": "water", "report_count": 1}], "WHERE e.client_id=:client_id")

    monkeypatch.setattr(sql_tool, "aggregate_report_count", aggregate)
    rows, query = sql_tool.execute_read_only_query("reports_by_sector", "C-02")

    assert rows == [{"sector": "water", "report_count": 1}]
    assert observed["client_id"] == "C-02"
    assert "client_id" in query
