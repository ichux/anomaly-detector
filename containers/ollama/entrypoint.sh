#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &

# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "Retrieving model (llama3.2:3b-instruct-fp16) ~6.6GB"

ollama pull llama3.2:3b-instruct-fp16

echo "Done."

# Wait for Ollama process to finish.
wait $pid
