from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.graph import build_graph
from app.services import get_embedder

STATIC = Path(__file__).parent / "static"

@asynccontextmanager
async def lifespan(_: FastAPI):
    get_embedder()  # load the embedding model at startup so the first request isn't slow
    yield


app = FastAPI(title="Enterprise IT Support Agentic RAG Copilot", lifespan=lifespan)
graph = build_graph()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    answer: str
    source: str
    confidence: str
    sources: list[str]
    trace: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        out = graph.invoke({"question": req.question, "trace": []})
    except Exception as e:  # surface upstream (LLM/Pinecone/Tavily) failures cleanly
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}") from e
    docs = out.get("web_docs", []) if out["source"] == "web" else out.get("kb_docs", []) if out["source"] == "kb" else []
    return ChatResponse(
        answer=out["answer"],
        source=out["source"],
        confidence=out.get("confidence", "n/a"),
        sources=sorted({d["source"] for d in docs}),
        trace=out.get("trace", []),
    )


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
