"""Agentic RAG flow orchestrated with LangGraph.

router -> (direct | retrieve_kb) -> grade_kb -> (generate_kb | web_search)
web_search -> grade_web -> (generate_web | fallback)
"""
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.services import embed, get_index, get_llm, get_tavily


class State(TypedDict, total=False):
    question: str
    route: str
    kb_docs: list[dict]
    web_docs: list[dict]
    answer: str
    source: str  # kb | web | direct | fallback
    confidence: str
    trace: list[str]


MIN_KB_SCORE = 0.25  # cosine similarity below this is treated as irrelevant


def _log(state: State, step: str) -> list[str]:
    return [*state.get("trace", []), step]


def _ask(system: str, user: str) -> str:
    resp = get_llm().invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return str(resp.content).strip()


def _verdict(system: str, user: str) -> str:
    out = _ask(
        system + "\nReply 'good' if the text contains the information needed to answer the question "
        "(even if it also contains unrelated material or is not exhaustive). Reply 'weak' only if "
        "the answer is missing or the text is off-topic. Reply with exactly one word: good or weak.",
        user,
    ).lower()
    return "good" if out.startswith("good") else "weak"


def _fmt(docs: list[dict]) -> str:
    return "\n\n".join(f"[{i + 1}] ({d['source']}) {d['text']}" for i, d in enumerate(docs))


# ---- nodes -----------------------------------------------------------------
def router(state: State) -> State:
    out = _ask(
        "You route messages for an enterprise IT support copilot. Reply with exactly one word: "
        "'kb' if the message is an IT/technical/company-policy question that needs knowledge lookup, "
        "'direct' if it is greeting, thanks or general chit-chat.",
        state["question"],
    ).lower()
    route = "direct" if out.startswith("direct") else "kb"
    return {"route": route, "trace": _log(state, f"router -> {route}")}


def direct_answer(state: State) -> State:
    answer = _ask(
        "You are a friendly enterprise IT support assistant. Reply briefly to the conversational message.",
        state["question"],
    )
    return {"answer": answer, "source": "direct", "confidence": "n/a",
            "trace": _log(state, "direct answer")}


def retrieve_kb(state: State) -> State:
    s = get_settings()
    res = get_index().query(
        vector=embed([state["question"]])[0], top_k=s.top_k, include_metadata=True
    )
    docs = [
        {"text": m.metadata.get("text", ""), "source": m.metadata.get("source", "kb"), "score": m.score}
        for m in res.matches
        if m.score >= MIN_KB_SCORE
    ]
    return {"kb_docs": docs, "trace": _log(state, f"retrieve_kb ({len(docs)} chunks)")}


def grade_kb(state: State) -> State:
    docs = state.get("kb_docs", [])
    verdict = "weak" if not docs else _verdict(
        "Is the retrieved context sufficient to answer the question?",
        f"Question: {state['question']}\n\nContext:\n{_fmt(docs)}",
    )
    return {"confidence": verdict, "trace": _log(state, f"grade_kb -> {verdict}")}


def web_search(state: State) -> State:
    res = get_tavily().search(query=state["question"], max_results=get_settings().top_k)
    docs = [{"text": r["content"], "source": r["url"]} for r in res.get("results", [])]
    return {"web_docs": docs, "trace": _log(state, f"web_search ({len(docs)} results)")}


def grade_web(state: State) -> State:
    docs = state.get("web_docs", [])
    verdict = "weak" if not docs else _verdict(
        "Is the web evidence sufficient to answer the question?",
        f"Question: {state['question']}\n\nEvidence:\n{_fmt(docs)}",
    )
    return {"confidence": verdict, "trace": _log(state, f"grade_web -> {verdict}")}


_GEN = (
    "You are an enterprise IT support assistant. Answer using ONLY the numbered context. "
    "Give clear step-by-step instructions and cite sources like [1]."
)


def generate_kb(state: State) -> State:
    ans = _ask(_GEN, f"Question: {state['question']}\n\nContext:\n{_fmt(state['kb_docs'])}")
    return {"answer": ans, "source": "kb", "trace": _log(state, "generate from KB")}


def generate_web(state: State) -> State:
    ans = _ask(_GEN, f"Question: {state['question']}\n\nContext:\n{_fmt(state['web_docs'])}")
    return {"answer": ans, "source": "web", "trace": _log(state, "generate from web")}


def fallback(state: State) -> State:
    ctx = _fmt([*state.get("kb_docs", []), *state.get("web_docs", [])]) or "(none)"
    ans = _ask(
        "You are an enterprise IT support assistant. Neither the company knowledge base nor the web "
        "gave sufficient information. Give the best possible general answer and CLEARLY state at the "
        "start that this is not verified by company docs or web sources and may be incomplete.",
        f"Question: {state['question']}\n\nPartial context:\n{ctx}",
    )
    return {"answer": ans, "source": "fallback", "confidence": "low",
            "trace": _log(state, "fallback answer")}


# ---- edges -----------------------------------------------------------------
def after_router(state: State) -> Literal["direct_answer", "retrieve_kb"]:
    return "direct_answer" if state["route"] == "direct" else "retrieve_kb"


def after_grade_kb(state: State) -> Literal["generate_kb", "web_search"]:
    return "generate_kb" if state["confidence"] == "good" else "web_search"


def after_grade_web(state: State) -> Literal["generate_web", "fallback"]:
    return "generate_web" if state["confidence"] == "good" else "fallback"


def build_graph():
    g = StateGraph(State)
    for name, fn in [
        ("router", router), ("direct_answer", direct_answer), ("retrieve_kb", retrieve_kb),
        ("grade_kb", grade_kb), ("web_search", web_search), ("grade_web", grade_web),
        ("generate_kb", generate_kb), ("generate_web", generate_web), ("fallback", fallback),
    ]:
        g.add_node(name, fn)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", after_router)
    g.add_edge("retrieve_kb", "grade_kb")
    g.add_conditional_edges("grade_kb", after_grade_kb)
    g.add_edge("web_search", "grade_web")
    g.add_conditional_edges("grade_web", after_grade_web)
    for end_node in ("direct_answer", "generate_kb", "generate_web", "fallback"):
        g.add_edge(end_node, END)
    return g.compile()
