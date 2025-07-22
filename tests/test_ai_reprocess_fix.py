#!/usr/bin/env python3
"""
Test script to verify the AI reprocessing fix
"""
import asyncio
from ai_reprocess import ai_reprocess_nodes

async def test_ai_reprocess_with_different_provider_formats():
    """Test that ai_reprocess_nodes handles different provider formats properly"""
    
    note_text = "This is a test note about machine learning and artificial intelligence."
    current_nodes = [
        {'id': 1, 'label': 'machine learning', 'size': 10, 'importance': 0.8},
        {'id': 2, 'label': 'artificial intelligence', 'size': 8, 'importance': 0.7},
        {'id': 3, 'label': 'test', 'size': 5, 'importance': 0.3}
    ]
    
    print("Testing AI reprocess with different provider formats...")
    
    # Test 1: String provider (should work)
    print("\nTest 1: String provider")
    try:
        result = await ai_reprocess_nodes(
            note_text, 
            current_nodes, 
            analysis_type='bridges',
            ai_provider='openai',  # String
            api_key=None  # No API key, should return original nodes
        )
        print(f"✓ String provider test passed. Result: {len(result)} nodes")
    except Exception as e:
        print(f"✗ String provider test failed: {e}")
    
    # Test 2: Dict provider (should be handled properly now)
    print("\nTest 2: Dict provider")
    try:
        result = await ai_reprocess_nodes(
            note_text, 
            current_nodes, 
            analysis_type='bridges',
            ai_provider={'provider': 'openai', 'name': 'openai'},  # Dict
            api_key=None  # No API key, should return original nodes
        )
        print(f"✓ Dict provider test passed. Result: {len(result)} nodes")
    except Exception as e:
        print(f"✗ Dict provider test failed: {e}")
    
    # Test 3: None provider (should return original nodes)
    print("\nTest 3: None provider")
    try:
        result = await ai_reprocess_nodes(
            note_text, 
            current_nodes, 
            analysis_type='bridges',
            ai_provider=None
        )
        print(f"✓ None provider test passed. Result: {len(result)} nodes")
    except Exception as e:
        print(f"✗ None provider test failed: {e}")
    
    # Test 4: Empty string provider (should return original nodes)
    print("\nTest 4: Empty string provider")
    try:
        result = await ai_reprocess_nodes(
            note_text, 
            current_nodes, 
            analysis_type='bridges',
            ai_provider=''
        )
        print(f"✓ Empty string provider test passed. Result: {len(result)} nodes")
    except Exception as e:
        print(f"✗ Empty string provider test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_reprocess_with_different_provider_formats())
    print("\n✅ All AI reprocess tests completed!")
