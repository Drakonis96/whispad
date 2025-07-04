#!/usr/bin/env python3
"""
WhisPad Whisper.cpp Wrapper
This module provides a Python wrapper for whisper.cpp local transcription
"""

import os
import subprocess
import tempfile
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Audio processing imports
try:
    from pydub import AudioSegment
    from pydub.utils import which
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Audio processing libraries not available: {e}")
    AUDIO_PROCESSING_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WhisperCppWrapper:
    """Wrapper class for whisper.cpp local transcription"""
    
    def __init__(self, model_path: str = None, whisper_cpp_path: str = None):
        """
        Initialize the whisper.cpp wrapper
        
        Args:
            model_path: Path to the whisper model file (e.g., ggml-tiny.bin)
            whisper_cpp_path: Path to the compiled whisper.cpp main executable
        """
        self.base_dir = Path(__file__).parent
        
        # Set default paths
        if model_path is None:
            self.model_path = self.base_dir / "whisper-cpp-models" / "ggml-tiny.bin"
        else:
            self.model_path = Path(model_path)
            
        if whisper_cpp_path is None:
            self.whisper_cpp_path = self.base_dir / "whisper.cpp-main" / "build" / "bin" / "whisper-cli"
        else:
            self.whisper_cpp_path = Path(whisper_cpp_path)
            
        # Check if paths exist
        self._check_prerequisites()
    
    def _check_prerequisites(self) -> bool:
        """Check if whisper.cpp is compiled and model exists"""
        issues = []
        
        if not self.model_path.exists():
            issues.append(f"Model file not found: {self.model_path}")
            
        if not self.whisper_cpp_path.exists():
            issues.append(f"Whisper.cpp executable not found: {self.whisper_cpp_path}")
            
        if issues:
            logger.error("Prerequisites not met:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
            
        return True
    
    def compile_whisper_cpp(self) -> bool:
        """Compile whisper.cpp if not already compiled"""
        try:
            whisper_dir = self.base_dir / "whisper.cpp-main"
            
            if not whisper_dir.exists():
                logger.error(f"Whisper.cpp source directory not found: {whisper_dir}")
                return False
            
            logger.info("Compiling whisper.cpp...")
            
            # Change to whisper.cpp directory and compile
            result = subprocess.run(
                ["make", "-j4"],  # Use 4 parallel jobs
                cwd=whisper_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("Whisper.cpp compiled successfully!")
                return True
            else:
                logger.error(f"Compilation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Compilation timed out")
            return False
        except Exception as e:
            logger.error(f"Error during compilation: {e}")
            return False
    
    def transcribe_audio(self, audio_file_path: str, language: str = None, 
                        output_format: str = "json") -> Dict[str, Any]:
        """
        Transcribe audio using whisper.cpp
        
        Args:
            audio_file_path: Path to the audio file
            language: Language code (e.g., 'en', 'es', 'fr') or None for auto-detect
            output_format: Output format ('json', 'txt', 'srt', 'vtt')
            
        Returns:
            Dictionary with transcription results
        """
        try:
            # Check if whisper.cpp is compiled
            if not self.whisper_cpp_path.exists():
                logger.info("Whisper.cpp not compiled, attempting to compile...")
                if not self.compile_whisper_cpp():
                    raise Exception("Failed to compile whisper.cpp")
            
            # Prepare command - simpler approach with direct stdout output
            cmd = [
                str(self.whisper_cpp_path),
                "-m", str(self.model_path),
                "-f", str(audio_file_path),
                "--no-timestamps",
                "--no-prints",  # Suppress debug prints to stderr
                "-t", "4"  # Use 4 threads
            ]
            
            # Add language if specified
            if language and language != 'auto':
                cmd.extend(["-l", language])
            
            logger.info(f"Running whisper.cpp with command: {' '.join(cmd)}")
            
            # Run whisper.cpp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )
            
            if result.returncode == 0:
                # With --no-prints and --no-timestamps, whisper.cpp outputs clean text to stdout
                transcription_text = result.stdout.strip()
                
                # If stdout is empty, try the output file approach as fallback
                if not transcription_text:
                    logger.info("No stdout transcription, checking for output file...")
                    
                    # Check if there's an output .txt file
                    audio_path = Path(audio_file_path)
                    txt_file = audio_path.with_suffix('.txt')
                    
                    if txt_file.exists():
                        try:
                            with open(txt_file, 'r', encoding='utf-8') as f:
                                transcription_text = f.read().strip()
                            logger.info(f"Found transcription in file: {txt_file}")
                            # Clean up the output file
                            txt_file.unlink()
                        except Exception as e:
                            logger.error(f"Error reading output file: {e}")
                
                # If still no transcription, try to extract from stderr (last resort)
                if not transcription_text:
                    logger.info("Attempting to extract transcription from stderr...")
                    stderr_lines = result.stderr.split('\n')
                    for line in stderr_lines:
                        line = line.strip()
                        # Look for lines that appear to be transcription text
                        if (line and 
                            len(line) > 10 and  # Reasonable length
                            not line.startswith('whisper_') and
                            not line.startswith('ggml_') and
                            not line.startswith('main:') and
                            not line.startswith('system') and
                            not 'load' in line.lower() and
                            not 'model' in line.lower() and
                            not 'time' in line.lower() and
                            not 'n_' in line.lower() and
                            not '=' in line):
                            transcription_text = line
                            break  # Take the first reasonable line
                
                # Debug logging
                logger.info(f"Command: {' '.join(cmd)}")
                logger.info(f"Return code: {result.returncode}")
                logger.info(f"Stdout: '{result.stdout}'")
                logger.info(f"Stderr first 200 chars: '{result.stderr[:200]}'")
                logger.info(f"Final transcription: '{transcription_text}'")
                
                # Check if we got any transcription
                if not transcription_text:
                    logger.error("No transcription text found in any output")
                    return {
                        "success": False,
                        "error": "No transcription text found in whisper.cpp output",
                        "transcription": "",
                        "debug_info": {
                            "stdout": result.stdout,
                            "stderr": result.stderr[:500],
                            "command": ' '.join(cmd)
                        }
                    }
                
                return {
                    "success": True,
                    "transcription": transcription_text,
                    "language": language or "auto",
                    "model": "whisper-tiny-local"
                }
            else:
                logger.error(f"Whisper.cpp failed: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "transcription": ""
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Transcription timed out")
            return {
                "success": False,
                "error": "Transcription timed out",
                "transcription": ""
            }
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcription": ""
            }
    
    def transcribe_audio_from_bytes(self, audio_bytes: bytes, filename: str = "audio.wav",
                                   language: str = None) -> Dict[str, Any]:
        """
        Transcribe audio from bytes data
        
        Args:
            audio_bytes: Audio data as bytes
            filename: Filename for the temporary file
            language: Language code or None for auto-detect
            
        Returns:
            Dictionary with transcription results
        """
        try:
            # Create temporary file for original audio
            with tempfile.NamedTemporaryFile(suffix=f".{filename.split('.')[-1]}", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                original_temp_path = temp_file.name
            
            # Convert to WAV format if needed
            wav_temp_path = self._convert_to_wav(original_temp_path, filename)
            
            # Transcribe using the WAV file
            result = self.transcribe_audio(wav_temp_path, language)
            
            # Clean up temporary files
            os.unlink(original_temp_path)
            if wav_temp_path != original_temp_path:
                os.unlink(wav_temp_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing from bytes: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcription": ""
            }
    
    def _convert_to_wav(self, input_path: str, original_filename: str) -> str:
        """
        Convert audio file to WAV format if needed
        
        Args:
            input_path: Path to the input audio file
            original_filename: Original filename to detect format
            
        Returns:
            Path to WAV file (same as input if already WAV, new path if converted)
        """
        try:
            # First, try using FFmpeg directly (most reliable for browser audio)
            logger.info(f"Converting audio to WAV format from {original_filename}")
            
            # Create new temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                wav_path = wav_file.name
            
            # Use FFmpeg to convert to WAV with whisper.cpp compatible settings
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ar', '16000',  # Sample rate 16kHz (whisper.cpp standard)
                '-ac', '1',      # Mono audio
                '-c:a', 'pcm_s16le',  # 16-bit PCM encoding
                '-f', 'wav',     # Force WAV format
                '-y',            # Overwrite output file
                wav_path
            ]
            
            logger.info(f"Running FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            result = subprocess.run(
                ffmpeg_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                # Verify the output file exists and has content
                if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                    logger.info(f"Successfully converted audio to WAV with FFmpeg: {wav_path} ({os.path.getsize(wav_path)} bytes)")
                    return wav_path
                else:
                    logger.error("FFmpeg conversion produced empty file")
            else:
                logger.error(f"FFmpeg conversion failed: {result.stderr}")
            
            # If FFmpeg failed, try pydub as fallback
            if AUDIO_PROCESSING_AVAILABLE:
                logger.info("Trying pydub conversion as fallback...")
                
                # Try different format loading methods
                audio = None
                
                # Try loading as WebM/OGG first (common for MediaRecorder)
                for fmt in ['webm', 'ogg', None]:  # None = auto-detect
                    try:
                        if fmt:
                            audio = AudioSegment.from_file(input_path, format=fmt)
                            logger.info(f"Successfully loaded as {fmt} format")
                        else:
                            audio = AudioSegment.from_file(input_path)
                            logger.info("Successfully loaded with auto-detection")
                        break
                    except Exception as e:
                        logger.debug(f"Failed to load as {fmt}: {e}")
                        continue
                
                if audio is None:
                    raise Exception("Could not load audio file with pydub")
                
                # Convert to WAV with proper settings for whisper.cpp
                audio = audio.set_frame_rate(16000).set_channels(1)
                
                # Remove the failed FFmpeg WAV file
                if os.path.exists(wav_path):
                    os.unlink(wav_path)
                
                # Create new WAV file for pydub
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
                    wav_path = wav_file.name
                
                # Export as WAV
                audio.export(wav_path, format="wav", parameters=["-acodec", "pcm_s16le"])
                
                if os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                    logger.info(f"Successfully converted audio to WAV with pydub: {wav_path} ({os.path.getsize(wav_path)} bytes)")
                    return wav_path
                else:
                    raise Exception("Pydub conversion produced empty file")
            
            # If both methods failed, raise an exception
            raise Exception("Both FFmpeg and pydub conversion methods failed")
            
        except Exception as e:
            logger.error(f"Error converting audio to WAV: {e}")
            # Clean up failed WAV file
            if 'wav_path' in locals() and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except:
                    pass
            # Return original path as last resort
            logger.warning("Using original file as-is (may not work with whisper.cpp)")
            return input_path
    
    def get_available_models(self) -> list:
        """Get list of available models in the models directory"""
        models_dir = self.base_dir / "whisper-cpp-models"
        if not models_dir.exists():
            return []
        
        models = []
        for file in models_dir.glob("*.bin"):
            models.append({
                "name": file.name,
                "path": str(file),
                "size": file.stat().st_size
            })
        
        return models
    
    def is_ready(self) -> bool:
        """Check if whisper.cpp is ready to use"""
        return self._check_prerequisites()


# Convenience function for easy usage
def transcribe_with_whisper_cpp(audio_file_path: str, language: str = None) -> str:
    """
    Simple function to transcribe audio using whisper.cpp
    
    Args:
        audio_file_path: Path to audio file
        language: Language code or None for auto-detect
        
    Returns:
        Transcribed text
    """
    wrapper = WhisperCppWrapper()
    result = wrapper.transcribe_audio(audio_file_path, language)
    return result.get("transcription", "")


if __name__ == "__main__":
    # Test the wrapper
    wrapper = WhisperCppWrapper()
    
    print("Checking whisper.cpp setup...")
    if wrapper.is_ready():
        print("✓ Whisper.cpp is ready!")
        
        # List available models
        models = wrapper.get_available_models()
        print(f"Available models: {len(models)}")
        for model in models:
            print(f"  - {model['name']} ({model['size']} bytes)")
    else:
        print("✗ Whisper.cpp needs setup")
        print("Attempting to compile...")
        if wrapper.compile_whisper_cpp():
            print("✓ Compilation successful!")
        else:
            print("✗ Compilation failed")