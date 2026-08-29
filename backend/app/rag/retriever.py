from app.data.vector_store import vector_store

def retrieve_previous_trip_context(query_text: str) -> str:
    return vector_store.query_trip_history(query_text, n_results=3)

def retrieve_destination_context(destination: str) -> str:
    return vector_store.query(destination, n_results=2)
