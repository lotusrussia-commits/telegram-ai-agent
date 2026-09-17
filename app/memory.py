from collections import defaultdict, deque
from pathlib import Path

import chromadb


MAX_HISTORY_MESSAGES = 10

memory: dict[int, deque[dict[str, str]]] = defaultdict(
    lambda: deque(maxlen=MAX_HISTORY_MESSAGES)
)


def add_message(user_id: int, role: str, content: str) -> None:
    memory[user_id].append(
        {
            "role": role,
            "content": content,
        }
    )


def get_history(user_id: int) -> list[dict[str, str]]:
    return list(memory[user_id])


def clear_history(user_id: int) -> None:
    memory[user_id].clear()


# ---------- Долгосрочная память ----------

CHROMA_DIR = Path("data/chroma")
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

collection = chroma_client.get_or_create_collection(
    name="documents"
)


def save_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    source: str,
) -> None:
    if not chunks:
        return

    ids = [
        f"{source}-{index}"
        for index in range(len(chunks))
    ]

    metadatas = [
        {
            "source": source,
        }
        for _ in chunks
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search_memory(
    embedding: list[float],
    top_k: int = 3,
) -> list[str]:
    if collection.count() == 0:
        return []

    result = collection.query(
        query_embeddings=[embedding],
        n_results=top_k,
    )

    documents = result.get("documents", [[]])[0]

    return documents