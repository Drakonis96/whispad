#!/bin/bash

# Install dependencies for speaker diarization
echo "Installing speaker diarization dependencies..."

# Install pyannote.audio and its dependencies
pip install pyannote.audio

# Install additional dependencies if not already installed
pip install torch torchaudio numpy

echo "Speaker diarization dependencies installed!"
echo ""
echo "Note: To use speaker diarization, you may need a HuggingFace token for some models."
echo "You can get a token at: https://huggingface.co/settings/tokens"
echo "Then set it as an environment variable: export HUGGINGFACE_TOKEN=your_token_here"
echo "Or add it to your .env file: HUGGINGFACE_TOKEN=your_token_here"
