#!/usr/bin/env python3
import http.client
import json
import logging
import os
import socket
import time
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def wait_for_port(host: str, port: int):
    while True:
        try:
            with socket.create_connection((host, port), timeout=1):
                logging.info(f"✅ Connected to {host}:{port}")
                break
        except (socket.timeout, ConnectionRefusedError, OSError):
            logging.info(f"⏳ Waiting for {host}:{port}...")
            time.sleep(1)


def wait_for_route(url: str, interval: int = 1, timeout: int = 2):
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"

    conn_class = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )

    while True:
        try:
            conn = conn_class(host, port, timeout=timeout)
            conn.request("GET", path)
            response = conn.getresponse()
            if response.status == 200:
                logging.info(f"✅ Service is ready at {url}")
                break
            else:
                logging.info(f"⚠️ Got status {response.status} from {url}")
        except (ConnectionRefusedError, http.client.HTTPException, OSError) as e:
            logging.info(f"⏳ Waiting for {url}... ({type(e).__name__})")
        time.sleep(interval)


def wait_for_model(url: str, interval: int = 1, timeout: int = 30):
    target_name = os.getenv("OLLAMA_MODEL")

    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or ""

    conn_class = (
        http.client.HTTPSConnection
        if parsed.scheme == "https"
        else http.client.HTTPConnection
    )

    start_time = time.time()

    while True:
        try:
            conn = conn_class(host, port, timeout=timeout)
            conn.request("GET", path)
            response = conn.getresponse()
            data = response.read()

            if response.status == 200:
                try:
                    models = json.loads(data).get("models")
                    if any(m.get("name") == target_name for m in models):
                        logging.info(f"✅ Model '{target_name}' exists")
                        break
                    else:
                        logging.info(
                            f"⏳ Waiting for model '{target_name}' to be downloaded..."
                        )
                except json.JSONDecodeError:
                    logging.warning(f"⚠️ Invalid JSON from {url}")
            else:
                logging.info(f"⚠️ Got status {response.status} from {url}")
        except (ConnectionRefusedError, http.client.HTTPException, OSError) as e:
            logging.info(f"⏳ Waiting for {url}... ({type(e).__name__})")

        if timeout is not None and (time.time() - start_time) > timeout:
            raise TimeoutError(
                f"❌ Timed out waiting for model '{target_name}' at {url}"
            )

        time.sleep(interval)
