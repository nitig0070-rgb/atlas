from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    client_id: str = Field(min_length=4, max_length=16, pattern=r"^C-[0-9]{2}$")
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


class Citation(BaseModel):
    report_id: str
    report_title: str
    page: int
    quote: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    confidence: float = Field(ge=0, le=1)
    conflicts: list[str] = []
    derived_values: list[dict] = []
    escalated: bool = False
    conversation_id: str | None = None
    request_id: str
    message_id: int | None = None
    token_usage: int | None = None
    estimated_cost: float | None = None


class IngestRequest(BaseModel):
    report_id: str = Field(pattern=r"^R-[0-9]{3}$")

\n