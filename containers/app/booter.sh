#!/bin/sh

set -e

python3 <<END
import os
from urllib.parse import urlparse

from itsup import wait_for_port, wait_for_route, wait_for_model

ollama_url = urlparse(os.getenv("OLLAMA_API"))
ollama_host = ollama_url.hostname
ollama_port = ollama_url.port

typesense_host = os.getenv("TYPESENSE_HOST")
typesense_port = int(os.getenv("TYPESENSE_PORT"))

wait_for_route(f"http://{typesense_host}:{typesense_port}/health")
wait_for_model(f"http://{ollama_host}:{ollama_port}/api/tags")
END
