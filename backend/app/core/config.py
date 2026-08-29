import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Tripster AI Travel Planner"
    VERSION: str = "4.0.0"

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "Tripster")

    # config.py is backend/app/core/config.py; four parents resolve to the project root.
    ROOT_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    DATA_DIR: str = os.path.join(ROOT_DIR, "data")
    CHROMA_DIR: str = os.path.join(DATA_DIR, "chroma")
    DB_FILE: str = os.path.join(DATA_DIR, "trips.json")
    MCP_CACHE_FILE: str = os.path.join(DATA_DIR, "mcp_cache.json")
    MCP_CACHE_TTL_SECONDS: int = 3600

    ALLOWED_ORIGINS: list = ["*"]

settings = Settings()
