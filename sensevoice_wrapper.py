import os
import sys
from io import BytesIO
from typing import Optional, Dict, Any

try:
    import torchaudio
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
    AUDIO_AVAILABLE = True
except Exception as e:
    print(f"Warning loading SenseVoice dependencies: {e}")
    AUDIO_AVAILABLE = False

class SenseVoiceWrapper:
    """Wrapper for the SenseVoice Small model"""

    def __init__(self, model_dir: str = "iic/SenseVoiceSmall", device: Optional[str] = None):
        self.model_dir = model_dir
        self.device = device or os.getenv("SENSEVOICE_DEVICE", "cpu")
        self.model = None
        self.kwargs = None
        self._loaded = False
        # add repo path for local code
        repo_path = os.path.join(os.path.dirname(__file__), "SenseVoice-main")
        if repo_path not in sys.path:
            sys.path.append(repo_path)
        try:
            from model import SenseVoiceSmall
            self.ModelClass = SenseVoiceSmall
        except Exception as e:
            print(f"Error importing SenseVoiceSmall: {e}")
            self.ModelClass = None

    def load_model(self) -> bool:
        if not AUDIO_AVAILABLE or not self.ModelClass:
            return False
        if self._loaded:
            return True
        try:
            self.model, self.kwargs = self.ModelClass.from_pretrained(model=self.model_dir, device=self.device)
            self.model.eval()
            self._loaded = True
            return True
        except Exception as e:
            print(f"Error loading SenseVoice model: {e}")
            return False

    def is_ready(self) -> bool:
        return self._loaded

    def transcribe_audio_from_bytes(self, audio_bytes: bytes, language: Optional[str] = "auto") -> Dict[str, Any]:
        if not self._loaded:
            if not self.load_model():
                return {"success": False, "error": "Model not loaded"}
        try:
            bio = BytesIO(audio_bytes)
            waveform, fs = torchaudio.load(bio)
            waveform = waveform.mean(0)
            res = self.model.inference(
                data_in=waveform,
                language=language or "auto",
                use_itn=False,
                ban_emo_unk=False,
                fs=fs,
                **self.kwargs,
            )
            if not res or not res[0]:
                return {"success": False, "error": "No result"}
            text = res[0][0]["text"]
            text = rich_transcription_postprocess(text)
            return {"success": True, "transcription": text, "model": "SenseVoice Small"}
        except Exception as e:
            return {"success": False, "error": str(e)}
