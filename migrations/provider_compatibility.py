"""
WhisPad Provider Compatibility Layer
Version: 0.7.12.0
Date: August 9, 2025
Purpose: Provide backward compatibility for provider name changes
"""

import json
import logging

# Provider migration mapping
PROVIDER_MIGRATION_MAP = {
    # Old provider names -> New provider names
    'openai': 'openai-api',
    'local': 'whisper-cpp', 
    'sensevoice': 'funasr',
    
    # New names (no change needed)
    'openai-api': 'openai-api',
    'whisper-cpp': 'whisper-cpp',
    'funasr': 'funasr'
}

# Reverse mapping for rollback scenarios
REVERSE_MIGRATION_MAP = {
    'openai-api': 'openai',
    'whisper-cpp': 'local',
    'funasr': 'sensevoice'
}

# Display names for UI
PROVIDER_DISPLAY_NAMES = {
    'openai-api': 'OpenAI Whisper API',
    'whisper-cpp': 'Local Whisper.cpp',
    'funasr': 'FunASR (SenseVoice)',
    
    # Legacy support (for any remaining old names)
    'openai': 'OpenAI Whisper API',
    'local': 'Local Whisper.cpp', 
    'sensevoice': 'FunASR (SenseVoice)'
}

# Model compatibility mapping
MODEL_MIGRATION_MAP = {
    # Models that need provider context adjustment
    'whisper-1': 'whisper-1',  # OpenAI model (no change)
    'gpt-4o-transcribe': 'gpt-4o-transcribe',  # OpenAI model (no change)
    'gpt-4o-mini-transcribe': 'gpt-4o-mini-transcribe',  # OpenAI model (no change)
    
    # Local whisper.cpp models (no change needed)
    'tiny': 'tiny',
    'base': 'base', 
    'small': 'small',
    'medium': 'medium',
    'large': 'large',
    
    # FunASR models
    'SenseVoiceSmall': 'SenseVoiceSmall'  # Keep model name but provider changes
}


def migrate_provider_name(old_provider: str) -> str:
    """
    Convert old provider names to new ones.
    
    Args:
        old_provider (str): Original provider name
        
    Returns:
        str: New provider name
    """
    migrated = PROVIDER_MIGRATION_MAP.get(old_provider, old_provider)
    if migrated != old_provider:
        logging.info(f"Migrated provider: {old_provider} -> {migrated}")
    return migrated


def rollback_provider_name(new_provider: str) -> str:
    """
    Convert new provider names back to old ones (for rollback).
    
    Args:
        new_provider (str): New provider name
        
    Returns:
        str: Old provider name
    """
    rolled_back = REVERSE_MIGRATION_MAP.get(new_provider, new_provider)
    if rolled_back != new_provider:
        logging.info(f"Rolled back provider: {new_provider} -> {rolled_back}")
    return rolled_back


def migrate_user_config(config: dict) -> dict:
    """
    Migrate user configuration object to new provider names.
    
    Args:
        config (dict): User configuration dictionary
        
    Returns:
        dict: Updated configuration with new provider names
    """
    updated_config = config.copy()
    
    # Migrate transcription provider
    if 'transcriptionProvider' in updated_config:
        old_provider = updated_config['transcriptionProvider']
        new_provider = migrate_provider_name(old_provider)
        updated_config['transcriptionProvider'] = new_provider
        
        if old_provider != new_provider:
            logging.info(f"Updated transcriptionProvider: {old_provider} -> {new_provider}")
    
    # Migrate postprocess provider (only openai changes)
    if 'postprocessProvider' in updated_config:
        old_provider = updated_config['postprocessProvider']
        new_provider = migrate_provider_name(old_provider) if old_provider == 'openai' else old_provider
        updated_config['postprocessProvider'] = new_provider
        
        if old_provider != new_provider:
            logging.info(f"Updated postprocessProvider: {old_provider} -> {new_provider}")
    
    return updated_config


def migrate_provider_arrays(providers: list) -> list:
    """
    Migrate arrays of provider names (used for user permissions).
    
    Args:
        providers (list): List of provider names
        
    Returns:
        list: Updated list with new provider names
    """
    if not providers:
        return []
        
    migrated_providers = [migrate_provider_name(p) for p in providers]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_providers = []
    for provider in migrated_providers:
        if provider not in seen:
            seen.add(provider)
            unique_providers.append(provider)
    
    if migrated_providers != providers:
        logging.info(f"Migrated provider array: {providers} -> {unique_providers}")
    
    return unique_providers


def get_provider_display_name(provider: str) -> str:
    """
    Get user-friendly display name for a provider.
    
    Args:
        provider (str): Provider internal name
        
    Returns:
        str: Display name for UI
    """
    return PROVIDER_DISPLAY_NAMES.get(provider, provider.title())


def validate_provider(provider: str) -> bool:
    """
    Check if a provider name is valid (either old or new).
    
    Args:
        provider (str): Provider name to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    all_valid_providers = set(PROVIDER_MIGRATION_MAP.keys()) | set(PROVIDER_MIGRATION_MAP.values())
    return provider in all_valid_providers


def migrate_request_data(request_data: dict) -> dict:
    """
    Migrate API request data to use new provider names.
    
    Args:
        request_data (dict): Request data from API call
        
    Returns:
        dict: Updated request data
    """
    updated_data = request_data.copy()
    
    if 'provider' in updated_data:
        old_provider = updated_data['provider']
        new_provider = migrate_provider_name(old_provider)
        updated_data['provider'] = new_provider
        
        if old_provider != new_provider:
            logging.info(f"Migrated request provider: {old_provider} -> {new_provider}")
    
    return updated_data


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test provider migration
    test_providers = ['openai', 'local', 'sensevoice', 'unknown']
    print("Provider Migration Test:")
    for provider in test_providers:
        migrated = migrate_provider_name(provider)
        print(f"  {provider} -> {migrated}")
    
    # Test config migration
    test_config = {
        'transcriptionProvider': 'openai',
        'postprocessProvider': 'openai',
        'model': 'whisper-1',
        'other_setting': 'value'
    }
    print(f"\nConfig Migration Test:")
    print(f"  Before: {test_config}")
    migrated_config = migrate_user_config(test_config)
    print(f"  After:  {migrated_config}")
    
    # Test provider arrays
    test_arrays = [
        ['openai', 'local'],
        ['openai', 'sensevoice'],
        ['openai', 'local', 'sensevoice'],
        []
    ]
    print(f"\nProvider Array Migration Test:")
    for array in test_arrays:
        migrated = migrate_provider_arrays(array)
        print(f"  {array} -> {migrated}")
