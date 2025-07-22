#!/usr/bin/env python3
"""
Test script for SenseVoice model download
"""

import os
import requests
import time
from pathlib import Path

def download_model_pt_with_progress():
    """Download model.pt with progress tracking"""
    repo_id = "FunAudioLLM/SenseVoiceSmall"
    model_url = f"https://huggingface.co/{repo_id}/resolve/main/model.pt"
    
    # Create models directory
    models_dir = Path("whisper-cpp-models/SenseVoiceSmall")
    models_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = models_dir / "model.pt"
    
    print(f"Downloading from: {model_url}")
    print(f"Saving to: {model_path}")
    
    # Set headers for better compatibility
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; WhisPad/1.0)',
        'Accept': 'application/octet-stream, */*',
    }
    
    try:
        response = requests.get(model_url, stream=True, headers=headers, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        print(f"Total size: {total_size // (1024*1024)} MB")
        
        start_time = time.time()
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        mb_downloaded = downloaded // (1024*1024)
                        mb_total = total_size // (1024*1024)
                        
                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed / (1024*1024) if elapsed > 0 else 0
                        
                        print(f"\rProgress: {progress:.1f}% ({mb_downloaded}/{mb_total} MB) - {speed:.1f} MB/s", end='', flush=True)
        
        print(f"\nDownload completed!")
        
        # Verify file
        if model_path.exists():
            file_size = model_path.stat().st_size
            print(f"File size: {file_size // (1024*1024)} MB")
            return True
        else:
            print("Error: File doesn't exist after download")
            return False
            
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def download_remaining_files():
    """Download remaining files using huggingface_hub"""
    try:
        from huggingface_hub import snapshot_download
        
        models_dir = "whisper-cpp-models/SenseVoiceSmall"
        repo_id = "FunAudioLLM/SenseVoiceSmall"
        
        print("Downloading remaining files...")
        
        snapshot_download(
            repo_id=repo_id,
            local_dir=models_dir,
            repo_type="model",
            local_files_only=False,
            allow_patterns=None,
            ignore_patterns=["model.pt"]  # Skip model.pt since we already have it
        )
        
        print("Remaining files downloaded successfully!")
        return True
        
    except Exception as e:
        print(f"Failed to download remaining files: {e}")
        return False

def verify_download():
    """Verify that all required files exist"""
    models_dir = Path("whisper-cpp-models/SenseVoiceSmall")
    required_files = ['config.yaml', 'model.pt']
    
    print("\nVerifying downloaded files:")
    all_present = True
    
    for file in required_files:
        file_path = models_dir / file
        if file_path.exists():
            size = file_path.stat().st_size
            size_mb = size / (1024 * 1024)
            print(f"✓ {file}: {size_mb:.1f} MB")
        else:
            print(f"✗ {file}: Missing")
            all_present = False
    
    # List all files in directory
    if models_dir.exists():
        print(f"\nAll files in {models_dir}:")
        for file in models_dir.iterdir():
            if file.is_file():
                size = file.stat().st_size
                size_mb = size / (1024 * 1024)
                print(f"  - {file.name}: {size_mb:.1f} MB")
    
    return all_present

if __name__ == "__main__":
    print("SenseVoice Model Download Test")
    print("=" * 40)
    
    # Step 1: Download model.pt
    print("Step 1: Downloading model.pt...")
    if download_model_pt_with_progress():
        print("✓ model.pt download successful")
    else:
        print("✗ model.pt download failed")
        exit(1)
    
    # Step 2: Download remaining files
    print("\nStep 2: Downloading remaining files...")
    if download_remaining_files():
        print("✓ Remaining files download successful")
    else:
        print("✗ Remaining files download failed")
    
    # Step 3: Verify everything
    print("\nStep 3: Verification...")
    if verify_download():
        print("✓ All files present and verified!")
        print("\nDownload completed successfully!")
    else:
        print("✗ Some files are missing")
        exit(1)
