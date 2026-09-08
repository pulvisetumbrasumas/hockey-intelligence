import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.schemas.common import AIQuestionIn, AIQuestionOut
from app.services.ai.service import OllamaAIService

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/ask", response_model=AIQuestionOut)
async def ask_ai(
    body: AIQuestionIn, db: AsyncSession = Depends(get_db)
):
    """Database-grounded natural-language hockey question.

    Ollama identifies intent, selects tools, and the tool layer resolves
    verified results from the database. Ollama only explains what the
    resolved data shows; it never invents numbers.
    """
    service = OllamaAIService()
    try:
        result = await service.ask(body.question, session=db)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI backend unavailable: {exc}. Is Ollama running?",
        ) from exc
    return AIQuestionOut(**result)


@router.post("/ask/stream")
async def ask_ai_stream(body: AIQuestionIn, db: AsyncSession = Depends(get_db)):
    """Server-sent events: live answer tokens + tool activity.

    Emits JSON events over text/event-stream: {"type":"delta","text":...},
    {"type":"tool","name":...,"status":...} and a final {"type":"done",...}.
    """
    service = OllamaAIService()

    async def gen():
        try:
            async for ev in service.ask_stream(body.question, session=db):
                yield "data: " + json.dumps(ev) + "\n\n"
            yield "data: " + json.dumps({"type": "end"}) + "\n\n"
        except Exception as exc:
            yield "data: " + json.dumps({"type": "error", "message": str(exc)}) + "\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
async def ai_health():
    service = OllamaAIService()
    return await service.health()
