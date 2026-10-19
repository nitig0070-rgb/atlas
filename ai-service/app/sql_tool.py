from typing import Literal

from app.database import aggregate_report_count


def execute_read_only_query(query_name: Literal["reports_by_sector"]) -> tuple[list[dict], str]:
    """Only named, application-owned aggregates are exposed; caller text is never SQL."""
    if query_name != "reports_by_sector":
        raise ValueError("Unsupported read-only query")
    return aggregate_report_count()
