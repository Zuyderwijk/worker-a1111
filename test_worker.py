#!/usr/bin/env python3
"""
Test script for RunPod worker functionality
"""
import requests
import json
import time

# Test configurations
ENDPOINT_URL = "YOUR_RUNPOD_ENDPOINT_URL"  # Replace with your actual endpoint
LOCAL_TEST_URL = "http://127.0.0.1:3000/sdapi/v1"

def test_basic_inference(endpoint_url):
    """Test basic txt2img generation"""
    payload = {
        "input": {
            "prompt": "a photo of an astronaut riding a horse on mars",
            "negative_prompt": "blurry, bad quality",
            "width": 512,
            "height": 512,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
            "seed": 42
        }
    }
    
    try:
        response = requests.post(endpoint_url, json=payload, timeout=120)
        print(f"Status Code: {response.status_code}")
        result = response.json()
        
        if "images" in result:
            print("✓ Basic inference test passed")
            print(f"Generated {len(result['images'])} images")
            return True
        else:
            print("✗ Basic inference test failed")
            print(f"Response: {result}")
            return False
            
    except Exception as e:
        print(f"✗ Basic inference test failed with error: {e}")
        return False

def test_worker_info(endpoint_url):
    """Test worker info endpoint"""
    payload = {
        "input": {
            "action": "get_info"
        }
    }
    
    try:
        response = requests.post(endpoint_url, json=payload, timeout=30)
        result = response.json()
        
        if "status" in result and result["status"] == "ready":
            print("✓ Worker info test passed")
            print(f"Available LoRAs: {len(result.get('available_loras', []))}")
            return True
        else:
            print("✗ Worker info test failed")
            print(f"Response: {result}")
            return False
            
    except Exception as e:
        print(f"✗ Worker info test failed with error: {e}")
        return False

def test_lora_functionality(endpoint_url):
    """Test LoRA functionality"""
    loras_to_test = [
        "picture_book",
        "soft_anime", 
        "whimsical_watercolor"
    ]
    
    passed = 0
    for lora in loras_to_test:
        payload = {
            "input": {
                "prompt": f"<lora:{lora}:1.0> a beautiful landscape",
                "negative_prompt": "blurry, bad quality",
                "width": 512,
                "height": 512,
                "num_inference_steps": 15,
                "guidance_scale": 7.5,
                "seed": 42
            }
        }
        
        try:
            response = requests.post(endpoint_url, json=payload, timeout=120)
            result = response.json()
            
            if "images" in result:
                print(f"✓ LoRA {lora} test passed")
                passed += 1
            else:
                print(f"✗ LoRA {lora} test failed: {result}")
                
        except Exception as e:
            print(f"✗ LoRA {lora} test failed with error: {e}")
    
    return passed == len(loras_to_test)

def test_local_webui_health():
    """Test local WebUI health (for development)"""
    try:
        response = requests.get(f"{LOCAL_TEST_URL}/options", timeout=10)
        if response.status_code == 200:
            print("✓ Local WebUI is healthy")
            return True
        else:
            print(f"✗ Local WebUI health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Local WebUI health check failed: {e}")
        return False

def main():
    print("RunPod Worker Test Suite")
    print("=" * 40)
    
    # Test local WebUI first (for development)
    print("\n1. Testing local WebUI health...")
    test_local_webui_health()
    
    # If you have a RunPod endpoint, update ENDPOINT_URL and uncomment these tests
    if ENDPOINT_URL != "YOUR_RUNPOD_ENDPOINT_URL":
        print(f"\n2. Testing RunPod endpoint: {ENDPOINT_URL}")
        
        print("\n2.1 Testing worker info...")
        test_worker_info(ENDPOINT_URL)
        
        print("\n2.2 Testing basic inference...")
        test_basic_inference(ENDPOINT_URL)
        
        print("\n2.3 Testing LoRA functionality...")
        test_lora_functionality(ENDPOINT_URL)
    else:
        print("\n2. Skipping RunPod tests (update ENDPOINT_URL to test)")
    
    print("\nTest suite completed!")

if __name__ == "__main__":
    main()
