"""Load documents (PDF, DOCX, TXT, MD), chunk, embed and upsert into Pinecone.

Usage: python -m app.ingest [path-to-folder]   (default: data/kb)
"""
import sys
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services import embed, get_index


def read_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        return "\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    if ext == ".docx":
        from docx import Document

        return "\n".join(p.text for p in Document(str(path)).paragraphs)
    return path.read_text(encoding="utf-8", errors="ignore")


def ingest(folder: Path) -> int:
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    index = get_index(create=True)
    total = 0
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() not in {".pdf", ".docx", ".txt", ".md"}:
            continue
        chunks = splitter.split_text(read_file(path))
        if not chunks:
            continue
        vectors = embed(chunks)
        index.upsert(vectors=[
            {"id": f"{path.stem}-{i}", "values": v, "metadata": {"text": c, "source": path.name}}
            for i, (c, v) in enumerate(zip(chunks, vectors))
        ])
        total += len(chunks)
        print(f"{path.name}: {len(chunks)} chunks")
    print(f"Done. {total} chunks indexed.")
    return total


if __name__ == "__main__":
    ingest(Path(sys.argv[1] if len(sys.argv) > 1 else "data/kb"))
