#!/usr/bin/env python3
"""
Test script to verify SenseVoice dependencies are working
"""

def test_pytorch_dependencies():
    """Test PyTorch and related dependencies"""
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__} available")
        
        import torchaudio
        print(f"✓ Torchaudio {torchaudio.__version__} available")
        
        import torchvision
        print(f"✓ Torchvision {torchvision.__version__} available")
        
        return True
    except ImportError as e:
        print(f"✗ PyTorch dependency missing: {e}")
        return False

def test_funasr_dependencies():
    """Test FunASR and related dependencies"""
    try:
        import funasr
        print(f"✓ FunASR available")
        
        from funasr import AutoModel
        print(f"✓ FunASR AutoModel can be imported")
        
        from funasr.utils.postprocess_utils import rich_transcription_postprocess
        print(f"✓ FunASR postprocess utils available")
        
        return True
    except ImportError as e:
        print(f"✗ FunASR dependency missing: {e}")
        return False

def test_other_dependencies():
    """Test other required dependencies"""
    dependencies = [
        'soundfile',
        'librosa', 
        'scipy',
        'numpy',
        'requests'
    ]
    
    all_available = True
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep} available")
        except ImportError:
            print(f"✗ {dep} missing")
            all_available = False
    
    return all_available

def test_sensevoice_wrapper():
    """Test SenseVoice wrapper functionality"""
    try:
        from sensevoice_wrapper import get_sensevoice_wrapper
        
        wrapper = get_sensevoice_wrapper()
        print(f"✓ SenseVoice wrapper created")
        
        is_available = wrapper.is_available()
        print(f"✓ SenseVoice availability check: {is_available}")
        
        model_info = wrapper.get_model_info()
        print(f"✓ SenseVoice model info: {model_info['name']}")
        
        return True
    except Exception as e:
        print(f"✗ SenseVoice wrapper error: {e}")
        return False

if __name__ == "__main__":
    print("Testing SenseVoice Dependencies")
    print("=" * 50)
    
    pytorch_ok = test_pytorch_dependencies()
    print()
    
    funasr_ok = test_funasr_dependencies()
    print()
    
    other_ok = test_other_dependencies()
    print()
    
    wrapper_ok = test_sensevoice_wrapper()
    print()
    
    print("=" * 50)
    if all([pytorch_ok, funasr_ok, other_ok, wrapper_ok]):
        print("✓ All dependencies are working correctly!")
        exit(0)
    else:
        print("✗ Some dependencies are missing or not working")
        exit(1)
