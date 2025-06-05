#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &

# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "Retrieving model (llama3.1:8b-instruct-q2_K)"

ollama pull llama3.1:8b-instruct-q2_K

echo "Done."

# Wait for Ollama process to finish.
wait $pid
