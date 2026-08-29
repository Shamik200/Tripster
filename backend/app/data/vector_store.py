import os
import json
from typing import Any, Dict
from app.core.config import settings

class SimpleVectorStore:
    def __init__(self):
        self.client = None
        self.collection = None
        self.trip_history_collection = None
        self._init_db()

    def _init_db(self):
        try:
            import chromadb
            os.makedirs(settings.CHROMA_DIR, exist_ok=True)
            self.client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
            self.collection = self.client.get_or_create_collection(name="travel_guides")
            self.trip_history_collection = self.client.get_or_create_collection(name="trip_history")
            self._index_existing_trips()
            print("ChromaDB initialized successfully")
        except Exception as error:
            print(f"ChromaDB init fallback: {error}")

    def add_guide(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        if self.collection:
            try:
                self.collection.add(documents=[content], metadatas=[metadata], ids=[doc_id])
                return True
            except Exception as error:
                print(f"Error adding guide: {error}")
        return False

    def query(self, query_text: str, n_results: int = 2) -> str:
        if self.collection:
            try:
                results = self.collection.query(query_texts=[query_text], n_results=n_results)
                documents = results.get("documents", [[]])[0]
                if documents:
                    return "\n---\n".join(documents)
            except Exception:
                pass
        return f"Local travel context for '{query_text}': Explore historic districts, local food markets, and cultural landmarks." 

    def add_trip_plan(self, trip_id: str, content: str, metadata: Dict[str, Any]) -> bool:
        if self.trip_history_collection:
            try:
                self.trip_history_collection.upsert(
                    documents=[content], metadatas=[metadata], ids=[trip_id]
                )
                return True
            except Exception as error:
                print(f"Error adding trip history: {error}")
        return False

    def _index_existing_trips(self) -> None:
        if not self.trip_history_collection or not os.path.exists(settings.DB_FILE):
            return
        try:
            with open(settings.DB_FILE, "r", encoding="utf-8") as file:
                trips = json.load(file).get("trips", {})
            for trip_id, trip in trips.items():
                self.add_trip_plan(
                    trip_id,
                    json.dumps(trip, ensure_ascii=False),
                    {"destination": trip.get("destination", ""), "created_at": trip.get("created_at", "")},
                )
        except Exception as error:
            print(f"Error indexing existing trip history: {error}")

    def query_trip_history(self, query_text: str, n_results: int = 3) -> str:
        if self.trip_history_collection:
            try:
                if self.trip_history_collection.count() == 0:
                    return ""
                results = self.trip_history_collection.query(
                    query_texts=[query_text],
                    n_results=min(n_results, self.trip_history_collection.count()),
                )
                documents = results.get("documents", [[]])[0]
                if documents:
                    return "\n---\n".join(documents)
            except Exception:
                pass
        return ""

vector_store = SimpleVectorStore()
