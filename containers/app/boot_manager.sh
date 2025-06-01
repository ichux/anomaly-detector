#!/bin/sh

set -e

python3 <<END
import os
import sys
import time
import logging
from urllib.parse import urlparse

from itsup import wait_for_model, wait_for_port, wait_for_route
from processor.database import AnomalySummary, SystemEventsDBHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_env_var(key: str, required: bool = True) -> str:
    value = os.getenv(key)
    if required and not value:
        logging.error(f"Missing required environment variable: {key}")
        sys.exit(1)
    return value

def main():
    # Load and validate environment variables
    ollama_url = urlparse(get_env_var("OLLAMA_API"))
    ollama_model = get_env_var("OLLAMA_MODEL")

    typesense_host = get_env_var("TYPESENSE_HOST")
    typesense_port = int(get_env_var("TYPESENSE_PORT"))

    ollama_host = ollama_url.hostname
    ollama_port = ollama_url.port

    if not ollama_host or not ollama_port:
        logging.error("OLLAMA_API must include a valid hostname and port")
        sys.exit(1)

    # Wait for Typesense to be ready
    typesense_health_url = f"http://{typesense_host}:{typesense_port}/health"
    logging.info(f"Waiting for Typesense at {typesense_health_url}")
    wait_for_route(typesense_health_url, timeout=5)
    time.sleep(2)

    # Create database collections
    logging.info("Creating database collections...")
    AnomalySummary().create_collection()
    SystemEventsDBHandler().create_collection()

    # Wait for Ollama model service to be ready
    ollama_model_url = f"http://{ollama_host}:{ollama_port}/api/tags"
    logging.info(f"Waiting for Ollama model: {ollama_model}")
    wait_for_model(ollama_model_url, timeout=5)

    logging.info("Initialization complete.")

main()

END

python3 -m processor.runner
