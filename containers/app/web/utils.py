import os
import socket
from urllib.parse import urlparse


def llm_active():
    ollama_url = urlparse(os.getenv("OLLAMA_API"))
    host = ollama_url.hostname
    port = ollama_url.port
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False
