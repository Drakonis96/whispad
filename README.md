<p align="center">
  <img src="logos/logo.png" alt="WhisPad Logo" width="120"/>
</p>

# WhisPad

## Table of Contents
1. [Description](#description)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage Guide](#usage-guide)

## Description
WhisPad is a simple and powerful application for real-time speech-to-text transcription, note-taking, and audio analysis. It leverages advanced AI models to transcribe audio, manage notes, and visualize data, all in an intuitive interface.

## Features
- Real-time speech-to-text transcription
- Save and manage transcribed notes
- Audio file upload and transcription
- Simple and modern web interface
- Audio analysis and visualization
- API integration for advanced AI models

## Installation
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd WhisPad4
   ```
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **(Optional) Install Node.js dependencies:**
   If you use Node.js features, install dependencies:
   ```bash
   npm install
   ```
4. **(Optional) Build or run Docker container:**
   ```bash
   docker-compose up
   ```

## Usage Guide

### 1. Real-time Speech-to-Text Transcription
- Run the backend server:
  ```bash
  python backend.py
  ```
- Open `index.html` in your browser.
- Click the microphone button to start transcribing.

### 2. Save and Manage Notes
- After transcription, click the save button to store your note.
- Access saved notes in the `saved_notes/` folder.

### 3. Audio File Upload and Transcription
- Use the web interface to upload an audio file (e.g., `.wav`).
- The app will transcribe the audio and display the text.

### 4. Audio Analysis and Visualization
- Transcribed audio can be visualized using the chart features in the app.
- Open `chart_script.py` or `chart_script_1.py` for custom analysis.


### 5. API Integration
- Configure API keys and endpoints in the backend as needed.
- See `api_documentation/` for details on supported APIs.


### 6. API Keys Setup
- Speech-to-text features use the OpenAI Whisper-1 model and GPT-4o transcribe models. You must provide a valid OpenAI API key for these features to work.
- Some other features may require additional API keys (e.g., for Gemini or other AI services).
- Create a `.env` file in the project root directory.
- Add your API keys in the following format:
  ```env
  OPENAI_API_KEY=your_openai_key_here
  GEMINI_API_KEY=your_gemini_key_here
  # Add other keys as needed
  ```
- The backend will automatically load these keys if you use a library like `python-dotenv` (make sure it's in `requirements.txt`).
- Never share your `.env` file or API keys publicly.

---
For more information, see the code comments and documentation files in the `api_documentation/` folder.
