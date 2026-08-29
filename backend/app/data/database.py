import json
import os
from typing import Any, Dict
from app.core.config import settings

def ensure_database() -> None:
    os.makedirs(os.path.dirname(settings.DB_FILE), exist_ok=True)
    if not os.path.exists(settings.DB_FILE):
        with open(settings.DB_FILE, "w", encoding="utf-8") as file:
            json.dump({"trips": {}}, file)

def read_database() -> Dict[str, Any]:
    ensure_database()
    try:
        with open(settings.DB_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {"trips": {}}

def write_database(data: Dict[str, Any]) -> None:
    ensure_database()
    with open(settings.DB_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

def read_mcp_cache() -> Dict[str, Any]:
    os.makedirs(os.path.dirname(settings.MCP_CACHE_FILE), exist_ok=True)
    if not os.path.exists(settings.MCP_CACHE_FILE):
        return {}
    try:
        with open(settings.MCP_CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}

def write_mcp_cache(cache: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(settings.MCP_CACHE_FILE), exist_ok=True)
    with open(settings.MCP_CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=2, ensure_ascii=False)
