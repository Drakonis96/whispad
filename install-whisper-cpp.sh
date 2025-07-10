#!/bin/bash

# Script to download whisper medium model for whisper.cpp
# This downloads the pre-converted ggml model file

set -e  # Exit on any error

echo "Downloading whisper medium model..."

# Create the models directory if it doesn't exist
mkdir -p whisper-cpp-models

# Change to the models directory
cd whisper-cpp-models

# Download the whisper medium model
echo "Downloading ggml-medium.bin..."
curl -L -o ggml-medium.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin

# Verify the download
if [ -f "ggml-medium.bin" ]; then
    echo "✓ whisper medium model downloaded successfully!"
    echo "Model location: $(pwd)/ggml-medium.bin"
    echo "Model size: $(du -h ggml-medium.bin | cut -f1)"
else
    echo "✗ Failed to download whisper medium model"
    exit 1
fi

echo "Installation complete!"