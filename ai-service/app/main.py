import logging
import json
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text

from app.agent import workflow
from app.config import settings
from app.database import create_escalation, engine, entitled_reports, record_security_event, persist_turn, record_request
from app.rag import ingest_report, REPORT_DIR, vector_store_ready
from app.schemas import ChatRequest, ChatResponse, IngestRequest
from app.security import is_unsafe_request, require_api_key
from app.writer import LLMProviderError

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {"level": record.levelname, "logger": record.name, "message": record.getMessage()}
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[_handler])
logger = logging.getLogger("atlas")
app = FastAPI(title="Project Atlas Report Copilot", version="0.1.0")


@app.on_event("startup")
def initialize_knowledge_base():
    """Idempotently embed the bundled corpus before serving chat traffic."""
    for path in sorted(REPORT_DIR.glob("R-*.md")):
        report_id = path.stem.split("_")[0]
        count = ingest_report(report_id)
        logger.info("corpus_ingested report_id=%s chunks=%d", report_id, count)


@app.get("/health")
def health():
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    vector_ok = vector_store_ready()
    return {"status": "ok" if db_ok and vector_ok else "degraded", "mysql": db_ok, "qdrant": vector_ok}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
def chat(request: ChatRequest):
    started = time.perf_counter()
    request_id = str(uuid.uuid4())
    if len(request.message) > settings.max_input_chars:
        raise HTTPException(status_code=413, detail="Message exceeds configured size limit")
    if is_unsafe_request(request.message):
        record_security_event(request.client_id, "UNSAFE_REQUEST_BLOCKED", {"request_id": request_id, "kind": "destructive_or_exfiltration"})
        return ChatResponse(answer="I can't execute destructive database requests or disclose client data. No SQL was executed.",
            confidence=0.99, escalated=False, request_id=request_id)
    try:
        allowed = entitled_reports(request.client_id)
    except Exception as exc:
        logger.exception("entitlement lookup failed request_id=%s", request_id)
        raise HTTPException(status_code=503, detail="The copilot is temporarily unavailable") from exc
    if allowed is None:
        raise HTTPException(status_code=404, detail="Unknown client")
    conv_id = request.conversation_id or str(uuid.uuid4())
    with engine.connect() as conn:
        conversation_owner = conn.execute(text("SELECT client_id FROM conversations WHERE id=:id"), {"id": conv_id}).scalar()
    if conversation_owner is not None and conversation_owner != request.client_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    explicit_reports = set(__import__('re').findall(r"\bR-\d{3}\b", request.message.upper()))
    inaccessible_reports = sorted(explicit_reports - allowed)
    for report_id in inaccessible_reports:
        with engine.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM reports WHERE id=:id"), {"id": report_id}).scalar()
        if exists:
            response_text = f"Report {report_id} exists but is not included in your current access. I can't provide its figures. You can request access from your account team."
            message_id = persist_turn(conv_id, request.client_id, request.message, response_text)
            return ChatResponse(answer=response_text, confidence=0.99, conversation_id=conv_id,
                                request_id=request_id, message_id=message_id)
    try:
        result = workflow.invoke({"question": request.message, "allowed": allowed, "client_id": request.client_id})
    except LLMProviderError as exc:
        logger.warning("llm_provider_failure request_id=%s provider=%s model=%s category=%s retrieved_chunk_count=%s",
                       request_id, getattr(exc, "provider", settings.llm_provider),
                       getattr(exc, "model", settings.model_name), exc.category,
                       getattr(exc, "retrieved_chunk_count", 0))
        raise HTTPException(status_code=exc.status_code, detail=exc.public_message) from None
    except Exception as exc:
        logger.exception("agent request failed request_id=%s", request_id)
        raise HTTPException(status_code=503, detail="The copilot is temporarily unavailable") from exc
    escalated = bool(result.get("escalation_reason"))
    if escalated:
        result["answer"] = "I don't have enough reliable evidence to answer this confidently. I've escalated the question to an analyst."
    message_id = persist_turn(conv_id, request.client_id, request.message, result.get("answer", ""))
    if escalated:
        create_escalation(request.client_id, conv_id, request.message, result["escalation_reason"], result["confidence"])
    elapsed = int((time.perf_counter() - started) * 1000)
    logger.info("request_id=%s route=%s latency_ms=%d escalated=%s provider=%s model=%s generation_outcome=%s retrieved_chunk_count=%s source_pages=%s retrieved_chunks=%s confidence=%s confidence_components=%s escalation_reason=%s",
                request_id, result.get("route", "guard"), elapsed, escalated,
                result.get("provider", settings.llm_provider), result.get("model", settings.model_name),
                result.get("generation_outcome", "not_attempted"),
                result.get("retrieved_chunk_count", 0), result.get("source_pages", []), result.get("retrieved_chunks", []),
                result.get("confidence"), result.get("confidence_components", {}),
                result.get("escalation_reason", "none"))
    token_usage = result.get("token_usage") or None
    record_request(request.client_id, request_id, elapsed, result.get("route", "guard"),
                   token_usage=token_usage, estimated_cost=result.get("estimated_cost"),
                   input_tokens=result.get("input_tokens"), output_tokens=result.get("output_tokens"))
    return ChatResponse(answer=result.get("answer", ""), citations=result.get("citations", []),
        confidence=result.get("confidence", 0.0), conflicts=result.get("conflicts", []),
        derived_values=result.get("derived_values", []), escalated=escalated,
        conversation_id=conv_id, request_id=request_id, message_id=message_id,
        token_usage=token_usage, estimated_cost=result.get("estimated_cost"))


@app.post("/ingest", dependencies=[Depends(require_api_key)])
def ingest(request: IngestRequest):
    try:
        count = ingest_report(request.report_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Report source not found") from exc
    except Exception as exc:
        logger.exception("ingestion failed report_id=%s", request.report_id)
        raise HTTPException(status_code=503, detail="Ingestion service unavailable") from exc
    return {"report_id": request.report_id, "chunks_upserted": count}


@app.get("/escalations", dependencies=[Depends(require_api_key)])
def escalations():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id,client_id,conversation_id,question,reason,confidence,status,created_at FROM escalations WHERE status='open' ORDER BY created_at LIMIT 100")).mappings().all()
        return [dict(row) for row in rows]


@app.get("/conversations/{conversation_id}/messages", dependencies=[Depends(require_api_key)])
def conversation_messages(conversation_id: str, client_id: str):
    with engine.connect() as conn:
        owner = conn.execute(text("SELECT 1 FROM conversations WHERE id=:id AND client_id=:client"),
                             {"id": conversation_id, "client": client_id}).scalar()
        if not owner:
            raise HTTPException(status_code=404, detail="Conversation not found")
        rows = conn.execute(text("SELECT id,role,content,created_at FROM conversation_messages WHERE conversation_id=:id ORDER BY created_at,id"),
                            {"id": conversation_id}).mappings().all()
        return [dict(row) for row in rows]
