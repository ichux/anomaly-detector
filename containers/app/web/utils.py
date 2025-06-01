import os
import socket
from urllib.parse import urlparse


def llm_active() -> bool:
    ollama_url = urlparse(os.getenv("OLLAMA_API"))  # type: ignore
    host: str = ollama_url.hostname  # type: ignore
    port: int = ollama_url.port or 0  # type: ignore
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False
