from pathlib import Path
import re
from uuid import uuid5, NAMESPACE_URL

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from app.config import settings

REPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "reports"
COLLECTION = "atlas_reports"
_model: SentenceTransformer | None = None
_client = QdrantClient(url=settings.vector_db_url, timeout=5)


def vector_store_ready() -> bool:
    try:
        _client.get_collections()
        return True
    except Exception:
        return False


def embedder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def parse_report(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    report_id = path.stem.split("_")[0]
    lines = raw.splitlines()
    title = lines[0].removeprefix("# ").strip()
    headers = dict(re.findall(r"^(report_id|publisher|published|sector|access_level):\s*(.+)$", raw, re.M))
    pages = re.finditer(r"^## (.+?)\s*\n### Page (\d+)\s*\n(.*?)(?=^## |\Z)", raw, flags=re.M | re.S)
    chunks: list[dict] = []
    for page_match in pages:
        section_title, page_string, body = page_match.groups()
        page = int(page_string)
        content = body.strip()
        if not content:
            continue
        region = "APAC" if re.search(r"Asia-Pacific|\bAPAC\b", content, re.I) else "Global"
        step = max(1, settings.chunk_size_chars - settings.chunk_overlap_chars)
        start = 0
        chunk_number = 0
        while start < len(content):
            end = min(len(content), start + settings.chunk_size_chars)
            if end < len(content):
                boundary = content.rfind(" ", start + 1, end)
                if boundary > start:
                    end = boundary
            chunk_text = f"Section: {section_title}\n{content[start:end].strip()}"
            chunks.append({"id": str(uuid5(NAMESPACE_URL, f"{report_id}:{page}:{chunk_number}:{chunk_text[:120]}")),
                           "text": chunk_text, "report_id": report_id, "report_title": title,
                           "sector": headers.get("sector", "Unknown"), "region": region,
                           "year": int(headers.get("published", "2025")[:4]), "page": page,
                           "publisher": headers.get("publisher", "Unknown"),
                           "access_level": headers.get("access_level", "paid")})
            if end >= len(content):
                break
            start = max(start + 1, end - settings.chunk_overlap_chars)
            chunk_number += 1
    return chunks


def ingest_report(report_id: str) -> int:
    matches = list(REPORT_DIR.glob(f"{report_id}_*.md"))
    if not matches:
        raise FileNotFoundError(report_id)
    documents = parse_report(matches[0])
    vectors = embedder().encode([d["text"] for d in documents], normalize_embeddings=True).tolist()
    size = len(vectors[0])
    if not _client.collection_exists(COLLECTION):
        _client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=size, distance=models.Distance.COSINE))
    _client.upsert(COLLECTION, points=[models.PointStruct(id=d["id"], vector=v,
        payload={k: val for k, val in d.items() if k != "id"}) for d, v in zip(documents, vectors)])
    return len(documents)


def retrieve(question: str, allowed_report_ids: set[str], limit: int = 6,
             report_filter: str | set[str] | None = None) -> list[dict]:
    if not allowed_report_ids:
        return []
    if isinstance(report_filter, str):
        searched_report_ids = {report_filter}
    elif report_filter:
        searched_report_ids = set(report_filter)
    else:
        searched_report_ids = allowed_report_ids
    if report_filter is not None:
        searched_report_ids &= allowed_report_ids
        if not searched_report_ids:
            return []
    query = embedder().encode(question, normalize_embeddings=True).tolist()
    results = _client.query_points(COLLECTION, query=query, limit=limit,
        query_filter=models.Filter(must=[models.FieldCondition(key="report_id", match=models.MatchAny(any=sorted(searched_report_ids)))]),
        with_payload=True).points
    evidence = []
    for point in results:
        payload = point.payload or {}
        if payload.get("report_id") not in allowed_report_ids:
            raise RuntimeError("Entitlement post-filter rejected vector result")
        payload["chunk_id"] = str(point.id)
        payload["score"] = point.score
        evidence.append(payload)
    return evidence
