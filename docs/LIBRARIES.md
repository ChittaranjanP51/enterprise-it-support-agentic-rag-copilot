# Libraries and Services Used

Everything here is listed in `requirements.txt`. "Must-have" means the app will not run without it; "Optional" means it can be swapped out or dropped.

## Must-have libraries
| Library | Purpose in this project |
|---|---|
| **fastapi** | Web framework for the `/api/chat` and `/health` endpoints and for serving the chat page |
| **uvicorn** | ASGI server that runs the FastAPI app |
| **pydantic** | Validates request and response data (e.g. question length) |
| **pydantic-settings** | Loads configuration from `.env` into a typed settings object |
| **langgraph** | Builds the agent as a graph of nodes and conditional edges (router, grading, fallback) |
| **langchain-core** | Message types and the common chat-model interface used by the nodes |
| **pinecone** | Vector database client: stores and searches document embeddings |
| **sentence-transformers** | Runs the `all-MiniLM-L6-v2` model locally to turn text into 384-dimension embeddings |
| **tavily-python** | Real-time web search used when the knowledge base is not enough |
| **langchain-text-splitters** | Splits documents into overlapping chunks before embedding |
| **One LLM provider package** | **langchain-groq** (Groq) *or* **langchain-openai** (OpenAI) for routing, grading and answer generation |

## Needed for loading documents
| Library | Purpose |
|---|---|
| **pypdf** | Reads text from PDF files |
| **python-docx** | Reads text from Word (.docx) files |

TXT and MD files need no extra library.

## Optional / convenience
| Library | Purpose |
|---|---|
| **python-dotenv** | Loads `.env` files (also handled by pydantic-settings) |
| **python-multipart** | Needed only if you add file-upload endpoints later |
| **langchain-groq / langchain-openai** | Keep only the one you use; the other can be removed |

## Infrastructure and external services
| Service | Role | Needed? |
|---|---|---|
| **OpenAI or Groq** | The LLM brain (API key required) | One of the two |
| **Pinecone** | Hosted vector database for the knowledge base | Yes |
| **Tavily** | Web search API | Needed for web fallback |
| **Hugging Face Hub** | Downloads the embedding model the first time | First run only |
| **Docker** | Packages the app for deployment | For production |
| **DigitalOcean** | Cloud host for the container | Deployment target |

## Minimal install for development
```
fastapi uvicorn pydantic pydantic-settings langgraph langchain-core
langchain-text-splitters pinecone sentence-transformers tavily-python
pypdf python-docx
+ langchain-openai   (or langchain-groq)
```
