import os
from app.core.config import settings
from app.data.vector_store import vector_store

def ingest_documents() -> int:
    documents_dir = os.path.join(settings.DATA_DIR, "documents")
    os.makedirs(documents_dir, exist_ok=True)
    count = 0
    for filename in os.listdir(documents_dir):
        path = os.path.join(documents_dir, filename)
        if os.path.isfile(path) and filename.endswith(".txt"):
            with open(path, "r", encoding="utf-8") as file:
                if vector_store.add_guide(filename, file.read(), {"source": filename}):
                    count += 1
    return count
