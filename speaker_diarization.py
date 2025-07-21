"""
Speaker Diarization using pyannote-audio
This module provides speaker diarization functionality to identify different speakers in audio files.
"""

import os
import tempfile
try:
    import torch
except ImportError as e:
    print(f"Warning: PyTorch not available: {e}")
    torch = None
import numpy as np
from typing import List, Tuple, Dict, Optional
import logging

try:
    from pyannote.audio import Pipeline
    from pyannote.audio.pipelines import SpeakerDiarization
    from pyannote.core import Annotation, Segment
    import torchaudio
    PYANNOTE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: pyannote.audio not available: {e}")
    PYANNOTE_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeakerDiarizationWrapper:
    """Wrapper class for speaker diarization using pyannote-audio"""
    
    def __init__(self):
        self.pipeline = None
        self.is_initialized = False
        
    def initialize(self):
        """Initialize the diarization pipeline"""
        if not PYANNOTE_AVAILABLE:
            logger.error("pyannote.audio is not available")
            return False
            
        try:
            # Try to load the pretrained pipeline
            # Note: This requires a HuggingFace token for some models
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=os.getenv('HUGGINGFACE_TOKEN')
            )
            
            # Use GPU if available
            if torch.cuda.is_available():
                self.pipeline = self.pipeline.to(torch.device("cuda"))
                logger.info("Using GPU for speaker diarization")
            else:
                logger.info("Using CPU for speaker diarization")
                
            self.is_initialized = True
            logger.info("Speaker diarization pipeline initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize speaker diarization pipeline: {e}")
            # Try to initialize with a simpler approach
            try:
                # Alternative initialization without auth token - try older version
                self.pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization@2022.07")
                self.is_initialized = True
                logger.info("Speaker diarization pipeline initialized with fallback method")
                return True
            except Exception as e2:
                logger.error(f"Fallback initialization also failed: {e2}")
                # Try even simpler fallback
                try:
                    from pyannote.audio.pipelines import SpeakerDiarization
                    self.pipeline = SpeakerDiarization()
                    self.is_initialized = True
                    logger.info("Speaker diarization pipeline initialized with basic method")
                    return True
                except Exception as e3:
                    logger.error(f"Basic initialization also failed: {e3}")
                    return False
    
    def is_available(self) -> bool:
        """Check if speaker diarization is available"""
        return PYANNOTE_AVAILABLE and self.is_initialized
    
    def diarize_audio_file(self, audio_path: str) -> Optional[List[Dict]]:
        """
        Perform speaker diarization on an audio file
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            List of diarization segments with speaker labels and timestamps
        """
        if not self.is_available():
            if not self.initialize():
                return None
                
        try:
            # Perform diarization
            diarization = self.pipeline(audio_path)
            
            # Convert to list of segments
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': speaker,
                    'duration': turn.end - turn.start
                })
            
            # Improve diarization accuracy
            segments = self._improve_diarization_accuracy(segments)
            
            logger.info(f"Diarization completed: found {len(set([s['speaker'] for s in segments]))} speakers")
            return segments
            
        except Exception as e:
            logger.error(f"Error during diarization: {e}")
            return None
    
    def diarize_audio_bytes(self, audio_bytes: bytes, filename: str = "audio.wav") -> Optional[List[Dict]]:
        """
        Perform speaker diarization on audio bytes
        
        Args:
            audio_bytes: Audio data as bytes
            filename: Original filename (for format detection)
            
        Returns:
            List of diarization segments with speaker labels and timestamps
        """
        if not self.is_available():
            if not self.initialize():
                return None
        
        # Create temporary file with proper extension
        file_ext = os.path.splitext(filename)[1].lower()
        if not file_ext:
            file_ext = '.wav'
            
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name
        
        try:
            # If the file is not WAV, convert it first
            if file_ext not in ['.wav', '.wave']:
                wav_path = temp_path.replace(file_ext, '.wav')
                try:
                    # Try to convert using pydub (fallback to external tools if needed)
                    import subprocess
                    result = subprocess.run([
                        'ffmpeg', '-i', temp_path, '-ar', '16000', '-ac', '1', 
                        '-c:a', 'pcm_s16le', '-f', 'wav', '-y', wav_path
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        # Use converted WAV file
                        os.unlink(temp_path)
                        temp_path = wav_path
                    else:
                        logger.warning(f"Failed to convert audio: {result.stderr}")
                        # Try with original file anyway
                except Exception as e:
                    logger.warning(f"Audio conversion failed: {e}, trying with original format")
            
            return self.diarize_audio_file(temp_path)
        finally:
            # Clean up temporary files
            try:
                os.unlink(temp_path)
            except:
                pass
            # Also clean up any converted WAV file
            try:
                wav_path = temp_path.replace(file_ext, '.wav')
                if os.path.exists(wav_path) and wav_path != temp_path:
                    os.unlink(wav_path)
            except:
                pass
    
    def apply_diarization_to_transcription(self, transcription: str, segments: List[Dict]) -> str:
        """
        Apply speaker diarization to a transcription text using intelligent sentence-aware mapping
        
        Args:
            transcription: Original transcription text
            segments: Diarization segments with real timestamps from diarize_audio_file/diarize_audio_bytes
            
        Returns:
            Transcription with speaker labels based on actual timing and sentence boundaries
        """
        if not segments:
            return transcription
        
        # Split into sentences first to respect natural boundaries
        import re
        sentences = re.split(r'([.!?]+)', transcription)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return transcription
        
        # Calculate total audio duration from segments
        total_duration = max(seg['end'] for seg in segments) if segments else 0
        if total_duration <= 0:
            return transcription
        
        # Sort segments by start time for proper processing
        sorted_segments = sorted(segments, key=lambda x: x['start'])
        
        # Calculate total characters for timing approximation
        total_chars = sum(len(sentence) for sentence in sentences)
        
        # Map each sentence to a speaker based on timing
        sentence_segments = []
        char_offset = 0
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Calculate approximate timing for this sentence
            sentence_start_ratio = char_offset / total_chars if total_chars > 0 else 0
            sentence_end_ratio = (char_offset + len(sentence)) / total_chars if total_chars > 0 else 1
            
            sentence_start_time = sentence_start_ratio * total_duration
            sentence_end_time = sentence_end_ratio * total_duration
            sentence_mid_time = (sentence_start_time + sentence_end_time) / 2
            
            # Find the best matching speaker segment
            assigned_speaker = None
            best_overlap = 0
            
            for segment in sorted_segments:
                # Check if sentence midpoint falls within speaker segment
                if segment['start'] <= sentence_mid_time <= segment['end']:
                    overlap = min(sentence_end_time, segment['end']) - max(sentence_start_time, segment['start'])
                    if overlap > best_overlap:
                        best_overlap = overlap
                        assigned_speaker = segment['speaker']
            
            # If no overlap found, assign to closest segment by midpoint
            if assigned_speaker is None:
                closest_segment = min(sorted_segments, 
                                    key=lambda s: min(abs(sentence_mid_time - s['start']), 
                                                     abs(sentence_mid_time - s['end'])))
                assigned_speaker = closest_segment['speaker']
            
            sentence_segments.append({
                'sentence': sentence,
                'speaker': assigned_speaker,
                'start_time': sentence_start_time,
                'end_time': sentence_end_time
            })
            
            char_offset += len(sentence)
        
        # Group consecutive sentences by speaker
        result_parts = []
        current_speaker = None
        current_sentences = []
        
        for sent_seg in sentence_segments:
            if sent_seg['speaker'] != current_speaker:
                # Finish previous speaker segment
                if current_speaker is not None and current_sentences:
                    speaker_num = self._get_speaker_number(current_speaker, sorted_segments)
                    text = ' '.join(current_sentences).strip()
                    if text:
                        result_parts.append(f"[SPEAKER {speaker_num}] {text}")
                
                # Start new speaker segment
                current_speaker = sent_seg['speaker']
                current_sentences = [sent_seg['sentence']]
            else:
                current_sentences.append(sent_seg['sentence'])
        
        # Add the last segment
        if current_speaker is not None and current_sentences:
            speaker_num = self._get_speaker_number(current_speaker, sorted_segments)
            text = ' '.join(current_sentences).strip()
            if text:
                result_parts.append(f"[SPEAKER {speaker_num}] {text}")
        
        # Join with double newlines to ensure each speaker starts on a new line
        return '\n\n'.join(result_parts) if result_parts else transcription
    
    def _get_speaker_number(self, speaker_id: str, all_segments: List[Dict]) -> int:
        """Get a consistent speaker number for a speaker ID"""
        unique_speakers = sorted(list(set([seg['speaker'] for seg in all_segments])))
        try:
            return unique_speakers.index(speaker_id) + 1
        except ValueError:
            return 1
    
    def _improve_diarization_accuracy(self, segments: List[Dict]) -> List[Dict]:
        """
        Post-process diarization segments to improve accuracy
        by merging very short segments and smoothing speaker transitions
        """
        if not segments:
            return segments
        
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda x: x['start'])
        improved_segments = []
        
        # Merge segments that are very short (less than 0.5 seconds)
        # with adjacent segments from the same speaker
        min_segment_duration = 0.5
        
        i = 0
        while i < len(sorted_segments):
            current_segment = sorted_segments[i].copy()
            
            # Look ahead to merge consecutive segments from the same speaker
            j = i + 1
            while (j < len(sorted_segments) and 
                   sorted_segments[j]['speaker'] == current_segment['speaker'] and
                   sorted_segments[j]['start'] - current_segment['end'] < 1.0):  # Gap less than 1 second
                
                # Merge segments
                current_segment['end'] = sorted_segments[j]['end']
                current_segment['duration'] = current_segment['end'] - current_segment['start']
                j += 1
            
            # Only add segments that meet minimum duration or are the only segment for a speaker
            if (current_segment['duration'] >= min_segment_duration or 
                len([s for s in sorted_segments if s['speaker'] == current_segment['speaker']]) == 1):
                improved_segments.append(current_segment)
            
            i = j
        
        return improved_segments if improved_segments else segments

# Global instance
_speaker_diarization_wrapper = None

def get_speaker_diarization_wrapper():
    """Get the global speaker diarization wrapper instance"""
    global _speaker_diarization_wrapper
    if _speaker_diarization_wrapper is None:
        _speaker_diarization_wrapper = SpeakerDiarizationWrapper()
    return _speaker_diarization_wrapper

# Test function
def test_speaker_diarization():
    """Test speaker diarization functionality"""
    wrapper = get_speaker_diarization_wrapper()
    
    if not wrapper.is_available():
        print("Initializing speaker diarization...")
        if not wrapper.initialize():
            print("Failed to initialize speaker diarization")
            return False
    
    print("Speaker diarization is available and ready!")
    return True

if __name__ == "__main__":
    test_speaker_diarization()
