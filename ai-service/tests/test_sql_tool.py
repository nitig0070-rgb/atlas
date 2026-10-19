import pytest

from app.sql_tool import execute_read_only_query


def test_only_allowlisted_aggregate_name_is_accepted():
    with pytest.raises(ValueError):
        execute_read_only_query("DELETE FROM reports")
