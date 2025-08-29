#!/usr/bin/env python3
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_streaming():
    """Test the streaming function directly"""
    try:
        # Import after adding path
        from main_sk import stream_agent_response, serialize_sse_event
        
        print("Testing streaming function...")
        
        # Test the serialize_sse_event function first
        test_data = {'content': 'Hello world', 'type': 'test'}
        serialized = serialize_sse_event(test_data)
        print(f"Serialized SSE: {repr(serialized)}")
        
        # Test the streaming function
        print("\nTesting stream_agent_response...")
        async for chunk in stream_agent_response("Hello, test message"):
            print(f"Chunk: {repr(chunk)}")
            if 'stream_end' in chunk:
                print("Found stream_end - ending")
                break
        
        print("Streaming test completed successfully")
        
    except Exception as e:
        print(f"Error during streaming test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_streaming())
