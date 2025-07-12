#!/usr/bin/env python3
"""
Direct test of SenseVoice with test.wav file
"""

import os
import sys
sys.path.append('/app')

def test_sensevoice_direct():
    """Test SenseVoice directly with test.wav"""
    try:
        print("Testing SenseVoice directly...")
        
        # Import the wrapper
        from sensevoice_wrapper import sensevoice_wrapper
        
        # Check if test file exists
        test_file = "/app/test/test.wav"
        if not os.path.exists(test_file):
            print(f"Test file not found: {test_file}")
            return False
            
        print(f"Found test file: {test_file}")
        
        # Read the audio file
        with open(test_file, 'rb') as f:
            audio_bytes = f.read()
            
        print(f"Audio file size: {len(audio_bytes)} bytes")
        
        # Test transcription
        print("Starting transcription...")
        result = sensevoice_wrapper.transcribe_audio_from_bytes(
            audio_bytes=audio_bytes,
            filename="test.wav",
            language="auto",
            detect_emotion=True,
            detect_events=True,
            speaker_diarization=True
        )
        
        print("Transcription result:")
        print(f"Success: {result.get('success', False)}")
        
        if result.get('success'):
            print(f"Transcription: '{result.get('transcription', '')}'")
            print(f"Language detected: {result.get('language_detected', 'N/A')}")
            if result.get('emotion'):
                print(f"Emotion: {result['emotion']}")
            if result.get('events'):
                print(f"Events: {result['events']}")
            if result.get("speaker_segments"):
                print("Speaker segments:")
                for seg in result["speaker_segments"]:
                    print(seg)
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            
        return result.get('success', False)
        
    except Exception as e:
        print(f"Error testing SenseVoice: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sensevoice_direct()
    sys.exit(0 if success else 1)
