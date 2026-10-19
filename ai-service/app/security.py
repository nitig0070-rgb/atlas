import hmac
import re

from fastapi import Header, HTTPException

from app.config import settings

INJECTION_PATTERNS = (
    r"ignore (all )?(previous|prior) instructions",
    r"disregard (all )?(previous|prior) instructions",
    r"reveal (the )?(system|developer) prompt",
    r"print (the )?(full )?contents of the clients table",
    r"reveal (all )?(client|customer) (emails|data)",
)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if not settings.api_key or not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def is_unsafe_request(text: str) -> bool:
    lowered = text.lower()
    sensitive = bool(re.search(r"\b(client|customer)\b.{0,50}\b(email|contact|purchase history|personal data)\b", lowered))
    email_exfiltration = bool(re.search(r"\b(all|every|list|show|give me)\b.{0,35}\b(client|customer)?\s*emails?\b", lowered))
    return sensitive or email_exfiltration or any(re.search(p, lowered) for p in INJECTION_PATTERNS) or bool(
        re.search(r"\b(delete|drop|truncate|update|insert)\b.*\b(table|rows|reports|clients)\b", lowered)
    )


def injection_detected(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in INJECTION_PATTERNS)

\n