"""
SenseVoice wrapper for WhisPad integration
Supports multilingual speech recognition with emotion and event detection
"""

import os
import sys
import tempfile
import json
import traceback
from typing import Dict, List, Optional, Union


class SenseVoiceWrapper:
    """Wrapper class for SenseVoice model integration"""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.supported_languages = {
            'auto': 'Auto-detect',
            'zh': 'Chinese (Mandarin)',
            'yue': 'Chinese (Cantonese)', 
            'en': 'English',
            'ja': 'Japanese',
            'ko': 'Korean',
            'nospeech': 'No Speech'
        }
        
        # Emotion labels supported by SenseVoice
        self.emotion_labels = {
            'HAPPY': '😊 Happy',
            'SAD': '😢 Sad',
            'ANGRY': '😠 Angry', 
            'NEUTRAL': '😐 Neutral',
            'FEARFUL': '😨 Fearful',
            'DISGUSTED': '🤢 Disgusted',
            'SURPRISED': '😲 Surprised'
        }
        
        # Event labels supported by SenseVoice
        self.event_labels = {
            'Speech': '🗣️ Speech',
            'BGM': '🎵 Background Music',
            'Applause': '👏 Applause',
            'Laughter': '😄 Laughter',
            'Cry': '😭 Crying',
            'Sneeze': '🤧 Sneeze',
            'Breath': '💨 Breathing',
            'Cough': '😷 Cough'
        }
        
    def is_available(self) -> bool:
        """Check if SenseVoice is available and model exists (always fresh check)"""
        try:
            # Always perform a fresh check - don't cache results
            # List of possible model locations to check
            possible_locations = [
                # Original location in whisper-cpp-models
                os.path.join(os.getcwd(), 'whisper-cpp-models', 'SenseVoiceSmall'),
                # FunASR cache locations (common cache directories)
                os.path.expanduser('~/.cache/funasr/iic/SenseVoiceSmall'),
                os.path.expanduser('~/.cache/funasr/FunAudioLLM/SenseVoiceSmall'),
                os.path.expanduser('~/.cache/huggingface/hub/models--FunAudioLLM--SenseVoiceSmall/snapshots'),
                os.path.expanduser('~/.cache/modelscope/iic/SenseVoiceSmall'),
                # Alternative local locations
                os.path.join(os.getcwd(), 'models', 'SenseVoiceSmall'),
                os.path.join(os.getcwd(), 'SenseVoiceSmall'),
            ]
            
            required_files = ['config.yaml', 'model.pt']
            
            for model_dir in possible_locations:
                if os.path.exists(model_dir):
                    # For huggingface cache, check subdirectories
                    if 'snapshots' in model_dir:
                        # Check all snapshot subdirectories
                        try:
                            for snapshot_dir in os.listdir(model_dir):
                                snapshot_path = os.path.join(model_dir, snapshot_dir)
                                if os.path.isdir(snapshot_path):
                                    if self._check_model_files(snapshot_path, required_files):
                                        print(f"SenseVoice model found at: {snapshot_path}")
                                        return True
                        except:
                            continue
                    else:
                        # Check the directory directly
                        if self._check_model_files(model_dir, required_files):
                            print(f"SenseVoice model found at: {model_dir}")
                            return True
            
            # If model not found locally, do not expose the provider
            # (behave like local Whisper models)
            print("SenseVoice model not found in any location")
            return False
        except Exception as e:
            print(f"Error checking SenseVoice availability: {e}")
            return False
    
    def _check_model_files(self, model_dir: str, required_files: list) -> bool:
        """Helper method to check if required model files exist in a directory"""
        try:
            for file in required_files:
                if not os.path.exists(os.path.join(model_dir, file)):
                    return False
            return True
        except:
            return False
    
    def _can_load_via_funasr(self) -> bool:
        """Check if SenseVoice can be loaded via FunASR using standard model identifiers"""
        try:
            # First check if all PyTorch dependencies are available
            try:
                import torch
                import torchaudio
                print("PyTorch dependencies available")
            except ImportError as e:
                print(f"Missing PyTorch dependency: {e}")
                return False
            
            # Check if FunASR is available
            try:
                from funasr import AutoModel
                print("FunASR import successful")
            except ImportError as e:
                print(f"FunASR not available: {e}")
                return False
            
            # Try common model identifiers without actually loading the full model
            model_identifiers = [
                "iic/SenseVoiceSmall", 
                "FunAudioLLM/SenseVoiceSmall"
            ]
            
            for model_id in model_identifiers:
                try:
                    # This is a lightweight check - just see if the model can be initialized
                    # without fully loading it by checking if the model exists remotely
                    print(f"Checking model availability: {model_id}")
                    # For now, we'll just return True if we can import FunASR successfully
                    # The actual model loading will happen when needed
                    return True
                except Exception as e:
                    print(f"Could not verify model {model_id}: {e}")
                    continue
            
            return False
        except Exception as e:
            print(f"Error checking FunASR availability: {e}")
            return False
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages"""
        return [
            {"code": code, "name": name} 
            for code, name in self.supported_languages.items()
        ]
    
    def _install_dependencies(self):
        """Install required dependencies for SenseVoice"""
        try:
            import subprocess
            import sys
            
            # Check if we're in Docker environment
            in_docker = os.path.exists('/.dockerenv')
            
            # Install PyTorch with all components (including torchaudio)
            try:
                import torch
                import torchaudio  # This is what's missing
                print("PyTorch and torchaudio already installed")
            except ImportError as e:
                print(f"Installing PyTorch components (missing: {e})...")
                if in_docker:
                    # Use CPU-only PyTorch in Docker for smaller size
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", 
                        "torch", "torchvision", "torchaudio", 
                        "--index-url", "https://download.pytorch.org/whl/cpu"
                    ])
                else:
                    # Install full PyTorch suite
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", 
                        "torch", "torchvision", "torchaudio"
                    ])
                
            # Install FunASR if not available
            try:
                import funasr
                print("FunASR already installed")
            except ImportError:
                print("Installing FunASR...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "funasr"])
                
            # Install additional dependencies
            required_packages = ["soundfile", "huggingface_hub"]
            for package in required_packages:
                try:
                    __import__(package.replace("-", "_"))
                    print(f"{package} already installed")
                except ImportError:
                    print(f"Installing {package}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                
            print("All SenseVoice dependencies installed successfully!")
            return True
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return False
    
    def _load_model(self):
        """Load the SenseVoice model"""
        if self.model_loaded:
            return True
            
        try:
            print("Starting SenseVoice model loading process...")
            
            # Install dependencies first
            if not self._install_dependencies():
                print("Failed to install SenseVoice dependencies")
                return False
                
            print("Dependencies installed, importing FunASR...")
            from funasr import AutoModel
            from funasr.utils.postprocess_utils import rich_transcription_postprocess
            
            # Set model directory
            models_dir = os.path.join(os.getcwd(), 'whisper-cpp-models')
            model_dir = os.path.join(models_dir, 'SenseVoiceSmall')
            
            print(f"Looking for SenseVoice model at: {model_dir}")
            if not os.path.exists(model_dir):
                print(f"SenseVoice model directory not found at {model_dir}")
                raise FileNotFoundError(f"SenseVoice model not found at {model_dir}")
            
            # Check for required model files with better error reporting
            required_files = ['config.yaml', 'model.pt']
            missing_files = []
            existing_files = []
            
            for file in required_files:
                file_path = os.path.join(model_dir, file)
                if not os.path.exists(file_path):
                    missing_files.append(file)
                else:
                    existing_files.append(file)
            
            if missing_files:
                print(f"Missing required model files in {model_dir}: {missing_files}")
                print(f"Existing files: {existing_files}")
                print(f"All files in directory: {os.listdir(model_dir) if os.path.exists(model_dir) else 'Directory does not exist'}")
                
                # Check if this looks like a Hugging Face download that might have different file names
                all_files = os.listdir(model_dir) if os.path.exists(model_dir) else []
                pytorch_files = [f for f in all_files if f.endswith('.pt') or f.endswith('.pth') or f.endswith('.bin')]
                
                if pytorch_files:
                    print(f"Found alternative PyTorch model files: {pytorch_files}")
                    # For now, we'll still consider it missing since we expect 'model.pt' specifically
                
                raise FileNotFoundError(f"Missing model files: {missing_files}")
            
            # Load model with VAD for better accuracy (less strict settings)
            print("Loading SenseVoice model with AutoModel...")
            self.model = AutoModel(
                model=model_dir,
                trust_remote_code=True,
                vad_model="fsmn-vad",
                vad_kwargs={
                    "max_single_segment_time": 30000,
                    "max_start_silence_time": 5000,
                    "max_end_silence_time": 800,
                    "min_speech_segment_time": 300,
                    "speech_threshold": 0.3,  # Lower threshold for detecting speech
                    "silence_threshold": 0.1   # Lower threshold for silence
                },
                device="cpu"  # Use CPU for compatibility
            )
            
            # Store postprocess function
            self.rich_transcription_postprocess = rich_transcription_postprocess
            
            self.model_loaded = True
            print("SenseVoice model loaded successfully!")
            return True
            
        except Exception as e:
            print(f"Error loading SenseVoice model: {e}")
            print(f"Exception type: {type(e).__name__}")
            traceback.print_exc()
            return False
    
    def transcribe_audio_from_bytes(self, audio_bytes: bytes, filename: str, 
                                  language: Optional[str] = None, 
                                  detect_emotion: bool = True,
                                  detect_events: bool = True,
                                  use_itn: bool = True) -> Dict:
        """
        Transcribe audio from bytes with SenseVoice
        
        Args:
            audio_bytes: Raw audio data
            filename: Original filename
            language: Language code (auto, zh, yue, en, ja, ko, nospeech)
            detect_emotion: Whether to detect emotions
            detect_events: Whether to detect audio events  
            use_itn: Whether to use inverse text normalization
            
        Returns:
            Dictionary with transcription results
        """
        try:
            # Load model if not already loaded
            if not self._load_model():
                return {
                    'success': False,
                    'error': 'Failed to load SenseVoice model'
                }
            
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_audio_path = temp_file.name
            
            try:
                # Set language
                if not language or language == 'auto':
                    language = "auto"
                elif language not in self.supported_languages:
                    language = "auto"
                
                # Perform transcription with less strict VAD settings
                print(f"Transcribing with SenseVoice: language={language}")
                res = self.model.generate(
                    input=temp_audio_path,
                    cache={},
                    language=language,
                    use_itn=use_itn,
                    batch_size_s=60,
                    merge_vad=False,  # Don't merge VAD segments for better detection
                    merge_length_s=0,  # Don't merge short segments
                )
                
                if not res or len(res) == 0:
                    return {
                        'success': False,
                        'error': 'No transcription result returned'
                    }
                
                # Process results
                result = res[0]
                
                # Get raw and processed text
                raw_text = result.get("text", "")
                processed_text = self.rich_transcription_postprocess(raw_text)
                
                # Extract emotion and event information if available
                emotion = None
                events = []
                
                # Parse rich transcription for emotion and events
                if detect_emotion or detect_events:
                    emotion, events = self._parse_rich_transcription(raw_text)
                
                # Clean text for final output (remove special tokens)
                clean_text = self._clean_transcription_text(processed_text)
                
                return {
                    'success': True,
                    'transcription': clean_text,
                    'raw_text': raw_text,
                    'processed_text': processed_text,
                    'language_detected': result.get("language", language),
                    'emotion': emotion if detect_emotion else None,
                    'events': events if detect_events else [],
                    'model': 'SenseVoiceSmall',
                    'provider': 'sensevoice'
                }
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_audio_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error in SenseVoice transcription: {e}")
            traceback.print_exc()
            return {
                'success': False,
                'error': f'Transcription failed: {str(e)}'
            }
    
    def _parse_rich_transcription(self, text: str) -> tuple:
        """Parse rich transcription to extract emotion and events"""
        emotion = None
        events = []
        
        try:
            # Look for emotion markers like <|HAPPY|>, <|SAD|>, etc.
            import re
            emotion_pattern = r'<\|(\w+)\|>'
            matches = re.findall(emotion_pattern, text)
            
            for match in matches:
                if match in self.emotion_labels:
                    emotion = {
                        'label': match,
                        'name': self.emotion_labels[match]
                    }
                elif match in self.event_labels:
                    events.append({
                        'label': match,
                        'name': self.event_labels[match]
                    })
                    
        except Exception as e:
            print(f"Error parsing rich transcription: {e}")
            
        return emotion, events
    
    def _clean_transcription_text(self, text: str) -> str:
        """Clean transcription text by removing special tokens"""
        try:
            import re
            # Remove emotion and event tokens
            clean_text = re.sub(r'<\|[^|]+\|>', '', text)
            # Remove extra whitespace
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            return clean_text
        except:
            return text
    
    def get_model_info(self) -> Dict:
        """Get information about the SenseVoice model"""
        return {
            'name': 'SenseVoiceSmall',
            'provider': 'sensevoice',
            'description': 'Multilingual speech recognition with emotion and event detection',
            'languages': self.get_supported_languages(),
            'features': [
                'Multilingual ASR (50+ languages)',
                'Speech emotion recognition',
                'Audio event detection', 
                'High efficiency (15x faster than Whisper-Large)',
                'Support for Chinese, Cantonese, English, Japanese, Korean'
            ],
            'emotions': list(self.emotion_labels.values()),
            'events': list(self.event_labels.values()),
            'available': self.is_available()
        }


# Global instance
sensevoice_wrapper = SenseVoiceWrapper()


def get_sensevoice_wrapper():
    """Get the global SenseVoice wrapper instance"""
    return sensevoice_wrapper
