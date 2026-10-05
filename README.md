# Enterprise IT Support Agentic RAG Copilot

AI-powered IT support assistant that uses Agentic RAG (LangGraph) to decide how to answer each query:

```
User → Router (LLM) ─ direct ─────────────────────────────► Answer
          │
          └ kb → Pinecone retrieve → Grade KB ─ good ─► Answer from KB
                                        │ weak
                                        ▼
                                  Tavily web search → Grade web ─ good ─► Answer from web
                                                          │ weak
                                                          ▼
                                                  Fallback answer (states limitations)
```

Stack: FastAPI · LangGraph · Pinecone · Groq/OpenAI · Tavily · sentence-transformers (all-MiniLM-L6-v2) · Docker.

## Run locally
```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env                                 # fill in API keys
python -m app.ingest data/kb                         # chunk, embed, upsert to Pinecone
uvicorn app.main:app --reload                        # http://localhost:8000
```

Put your PDF/DOCX/TXT/MD files in `data/kb/` (a sample policy is included) and re-run ingest.

## API
`POST /api/chat` `{"question": "..."}` →
`{answer, source: kb|web|direct|fallback, confidence, sources[], trace[]}`; `GET /health`.

## Docker
```bash
docker compose up --build -d
```

## Deploy on DigitalOcean
1. Create a Droplet (Ubuntu, 2 GB RAM+) and install Docker, or use App Platform with the Dockerfile.
2. Clone the repo, create `.env` with production keys, run `docker compose up --build -d`.
3. Open port 8000 (or put Nginx/Caddy in front for HTTPS on port 443).
4. Run ingestion once: `docker compose exec copilot python -m app.ingest data/kb`.
