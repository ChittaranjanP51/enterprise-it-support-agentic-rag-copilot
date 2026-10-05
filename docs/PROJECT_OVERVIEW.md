# Enterprise IT Support Agentic RAG Copilot: Project Overview

## What it is
An AI-powered IT support assistant that helps employees resolve technical and policy questions quickly. Instead of always searching the same way, it **decides for itself** how to answer each question. This is called *Agentic RAG* (Retrieval-Augmented Generation).

## What it does
1. **Understands the question (Router).** An LLM decides whether the message is small talk (answered directly) or needs a knowledge lookup.
2. **Searches the company knowledge base.** The question is converted to an embedding and matched against private documents (IT and HR policies) stored in Pinecone. Weak matches are filtered out.
3. **Grades the evidence.** An LLM checks whether the retrieved text actually answers the question.
4. **Falls back to the web if needed.** If the knowledge base is not enough, Tavily searches the web, and the results are graded the same way.
5. **Answers honestly.** If neither source is good enough, it still gives the best possible answer, but clearly states it is unverified.

Every response includes the **source** (knowledge base / web / direct / fallback), a **confidence** value, the **documents cited**, and a **step trace** of the decisions made.

```
User -> Router -> KB (Pinecone) -> Grade -> Answer from KB
                        | weak
                        v
                  Web (Tavily) -> Grade -> Answer from web
                        | weak
                        v
                  Fallback answer (states limitations)
```

## How the pieces fit
| Layer | What it does | Where |
|---|---|---|
| Web UI | Simple chat page showing answer, source and confidence | `app/static/index.html` |
| API | `POST /api/chat`, `GET /health` | `app/main.py` |
| Agent flow | LangGraph state machine (router, retrieve, grade, web, generate, fallback) | `app/graph.py` |
| Ingestion | Reads PDF/DOCX/TXT/MD, chunks, embeds, stores in Pinecone | `app/ingest.py` |
| Services | LLM, embeddings, Pinecone and Tavily clients | `app/services.py` |
| Deployment | Docker image and compose file; deployable on DigitalOcean | `Dockerfile`, `docker-compose.yml` |

## Why it is useful
- **Faster resolution.** Employees get step-by-step answers in seconds instead of waiting for a ticket.
- **Less load on the service desk.** Repetitive questions (VPN, passwords, leave, Wi-Fi) are handled automatically.
- **Company-specific answers.** Answers come from your own private policies first, not generic internet advice.
- **Never stuck.** If the internal documents are silent, it searches the web, so employees still get help.
- **Honest about uncertainty.** Grading plus the fallback disclaimer reduces made-up answers and shows how much to trust each reply.
- **Transparent.** Each answer shows its source, citations and decision trace, which makes it easy to audit and debug.
- **Easy to keep current.** Drop new documents into `data/kb` and re-run ingestion; no model retraining.
- **Flexible and portable.** Switch between OpenAI and Groq with one setting; runs anywhere via Docker.
- **Low cost to start.** Local embeddings are free, and Pinecone, Tavily and Groq have free tiers.

## Known limitations
- Answer quality depends on the quality and coverage of the documents in the knowledge base.
- The relevance cutoff (`MIN_KB_SCORE = 0.25`) was tuned on the two sample documents and may need adjusting for a larger knowledge base.
- Sample HR and IT policies are placeholders; replace them with real documents.
- No user login, chat history or access control yet; add these before wide production use.
