"""Lazy singletons for external services: LLM, embeddings, Pinecone, Tavily."""
from functools import lru_cache

from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from tavily import TavilyClient

from app.config import get_settings


@lru_cache
def get_llm():
    s = get_settings()
    if s.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=s.openai_model, api_key=s.openai_api_key, temperature=0)
    from langchain_groq import ChatGroq

    return ChatGroq(model=s.groq_model, api_key=s.groq_api_key, temperature=0)


@lru_cache
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(get_settings().embedding_model)


def embed(texts: list[str]) -> list[list[float]]:
    return get_embedder().encode(texts, normalize_embeddings=True).tolist()


@lru_cache
def get_pinecone() -> Pinecone:
    return Pinecone(api_key=get_settings().pinecone_api_key)


def get_index(create: bool = False):
    s = get_settings()
    pc = get_pinecone()
    if create and s.pinecone_index not in pc.list_indexes().names():
        pc.create_index(
            name=s.pinecone_index,
            dimension=s.embedding_dim,
            metric="cosine",
            spec=ServerlessSpec(cloud=s.pinecone_cloud, region=s.pinecone_region),
        )
    return pc.Index(s.pinecone_index)


@lru_cache
def get_tavily() -> TavilyClient:
    return TavilyClient(api_key=get_settings().tavily_api_key)
