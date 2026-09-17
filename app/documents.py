from pathlib import Path

import chromadb
from pypdf import PdfReader
from docx import Document

from app.llm import create_embedding


UPLOADS_DIR = Path("data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

CHROMA_DIR = Path("data/chroma")
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
collection = chroma_client.get_or_create_collection(name="documents")


def extract_text(file_path: Path) -> str:
    extension = file_path.suffix.lower()

    if extension == ".txt":
        return file_path.read_text(encoding="utf-8")

    if extension == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if extension == ".docx":
        document = Document(str(file_path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    raise ValueError(
        "Поддерживаются только файлы TXT, PDF и DOCX."
    )


def split_text(text: str, chunk_size: int = 1000) -> list[str]:
    text = text.strip()

    if not text:
        return []

    return [
        text[index:index + chunk_size]
        for index in range(0, len(text), chunk_size)
    ]


async def index_document(file_path: Path) -> int:
    text = extract_text(file_path)
    chunks = split_text(text)

    if not chunks:
        return 0

    embeddings = []

    for chunk in chunks:
        embedding = await create_embedding(chunk)
        embeddings.append(embedding)

    ids = [
        f"{file_path.stem}_{index}"
        for index in range(len(chunks))
    ]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=[
            {"filename": file_path.name}
            for _ in chunks
        ],
    )

    return len(chunks)