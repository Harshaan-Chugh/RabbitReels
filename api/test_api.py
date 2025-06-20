#!/usr/bin/env python3
"""
Test script for the Shorts-Generator API
"""
import requests
import time
import json
import uuid

# Configuration
API_BASE = "http://localhost:8080"
TEST_JOB_ID = f"test-{uuid.uuid4().hex[:8]}"

def test_api():
    """Test the complete API workflow."""
    print("🧪 Testing Shorts-Generator API")
    print(f"API Base: {API_BASE}")
    print(f"Test Job ID: {TEST_JOB_ID}")
    print()
    
    # Test 1: Get available themes
    print("1️⃣ Testing GET /themes")
    try:
        response = requests.get(f"{API_BASE}/themes")
        response.raise_for_status()
        themes = response.json()
        print(f"✅ Available themes: {themes}")
    except Exception as e:
        print(f"❌ Error getting themes: {e}")
        return
    
    # Test 2: Submit a new job
    print("\n2️⃣ Testing POST /videos")
    job_data = {
        "job_id": TEST_JOB_ID,
        "prompt": "Explain hash tables in simple terms",
        "character_theme": "family_guy"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/videos", 
            json=job_data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Job submitted: {result}")
    except Exception as e:
        print(f"❌ Error submitting job: {e}")
        return
    
    # Test 3: Poll job status
    print(f"\n3️⃣ Testing GET /videos/{TEST_JOB_ID}")
    max_polls = 20
    poll_interval = 5
    
    for i in range(max_polls):
        try:
            response = requests.get(f"{API_BASE}/videos/{TEST_JOB_ID}")
            response.raise_for_status()
            status = response.json()
            
            print(f"📊 Poll #{i+1}: Status = {status.get('status')}")
            
            if status.get('status') == 'done':
                print("✅ Job completed!")
                break
            elif status.get('status') == 'error':
                print(f"❌ Job failed: {status.get('error_msg')}")
                return
            
            time.sleep(poll_interval)
            
        except Exception as e:
            print(f"❌ Error polling status: {e}")
            time.sleep(poll_interval)
    else:
        print("⏰ Timeout waiting for job completion")
        return
    
    # Test 4: Download the video
    print(f"\n4️⃣ Testing GET /videos/{TEST_JOB_ID}/file")
    try:
        response = requests.get(f"{API_BASE}/videos/{TEST_JOB_ID}/file")
        
        if response.status_code == 200:
            filename = f"{TEST_JOB_ID}.mp4"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"✅ Video downloaded: {filename} ({len(response.content)} bytes)")
        else:
            print(f"❌ Download failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error downloading video: {e}")
    
    print("\n🎉 API test completed!")

def test_health():
    """Test health endpoint."""
    print("🏥 Testing health endpoint")
    try:
        response = requests.get(f"{API_BASE}/health")
        response.raise_for_status()
        health = response.json()
        print(f"✅ Health check: {health}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    # First test health
    test_health()
    print()
    
    # Run full API test
    test_api()
