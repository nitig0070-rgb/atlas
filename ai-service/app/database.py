from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.config import settings

_db_timeouts = {"connect_timeout": 3, "read_timeout": 8, "write_timeout": 8}
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=1800, connect_args=_db_timeouts)
readonly_engine = create_engine(settings.readonly_database_url, pool_pre_ping=True, pool_recycle=1800,
                                connect_args=_db_timeouts) if settings.readonly_database_url else None


def persist_turn(conversation_id: str, client_id: str, question: str, answer: str) -> int:
    with engine.begin() as conn:
        existing = conn.execute(text("SELECT id FROM conversations WHERE id=:id AND client_id=:client"),
                                {"id": conversation_id, "client": client_id}).scalar()
        if existing is None:
            conn.execute(text("INSERT INTO conversations (id,client_id) VALUES (:id,:client)"),
                         {"id": conversation_id, "client": client_id})
        conn.execute(text("INSERT INTO conversation_messages (conversation_id,role,content) VALUES (:id,'user',:q)"),
                     {"id": conversation_id, "q": question})
        return int(conn.execute(text("INSERT INTO conversation_messages (conversation_id,role,content) VALUES (:id,'assistant',:a)"),
                     {"id": conversation_id, "a": answer}).lastrowid)


def entitled_reports(client_id: str) -> set[str] | None:
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT id FROM clients WHERE id=:id"), {"id": client_id}).scalar()
        if exists is None:
            return None
        rows = conn.execute(
            text("SELECT report_id FROM client_report_entitlements WHERE client_id=:id"), {"id": client_id}
        ).scalars()
        return set(rows)


def record_security_event(client_id: str | None, event_type: str, details: dict) -> None:
    import json

    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO security_events (client_id,event_type,severity,details) VALUES (:client,:type,'high',:details)"),
            {"client": client_id, "type": event_type, "details": json.dumps(details)},
        )


def create_escalation(client_id: str, conversation_id: str, question: str, reason: str, confidence: float) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO escalations (client_id,conversation_id,question,reason,confidence)
            VALUES (:client,:conversation,:question,:reason,:confidence)
        """), {"client": client_id, "conversation": conversation_id, "question": question,
               "reason": reason, "confidence": confidence})


def record_request(client_id: str, request_id: str, latency_ms: int, route: str,
                   token_usage: int | None = None, estimated_cost: float | None = None,
                   input_tokens: int | None = None, output_tokens: int | None = None) -> None:
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO request_logs (client_id,request_id,latency_ms,token_usage,estimated_cost,route) VALUES (:client,:request,:latency,:tokens,:cost,:route)"),
                     {"client": client_id, "request": request_id, "latency": latency_ms,
                      "tokens": token_usage, "cost": estimated_cost, "route": route[:40]})
        if token_usage is not None:
            conn.execute(text("INSERT INTO cost_logs (request_id,provider,model,input_tokens,output_tokens,estimated_cost) VALUES (:request,:provider,:model,:input,:output,:cost)"),
                         {"request": request_id, "provider": settings.llm_provider, "model": settings.model_name,
                          "input": input_tokens, "output": output_tokens, "cost": estimated_cost})


def aggregate_report_count() -> tuple[list[dict], str]:
    query = "SELECT /*+ MAX_EXECUTION_TIME(3000) */ sector, COUNT(*) AS report_count FROM reports GROUP BY sector ORDER BY report_count DESC, sector LIMIT 20"
    if readonly_engine is None:
        raise RuntimeError("READONLY_DATABASE_URL must be configured for aggregate SQL")
    with readonly_engine.connect() as conn:
        rows = conn.execute(text(query)).mappings().all()
        return [dict(row) for row in rows], query


def get_metric(report_id: str, metric: str, period: str):
    query = text("SELECT `value`, unit, scope_note FROM market_metrics WHERE report_id=:report AND metric=:metric AND period=:period LIMIT 1")
    if readonly_engine is None:
        raise RuntimeError("READONLY_DATABASE_URL must be configured for report metric reads")
    with readonly_engine.connect() as conn:
        row = conn.execute(query, {"report": report_id, "metric": metric, "period": period}).mappings().first()
        return dict(row) if row else None
