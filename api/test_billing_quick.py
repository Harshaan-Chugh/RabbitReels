#!/usr/bin/env python3
"""
Quick start script for testing RabbitReels billing system
Starts necessary services and runs tests
"""
import os
import sys
import time
import subprocess
import signal
from threading import Thread

def run_redis():
    """Start Redis server."""
    print("🔴 Starting Redis...")
    try:
        # Try to start Redis (if not already running)
        result = subprocess.run(["redis-server", "--port", "6379"], 
                              capture_output=True, text=True, timeout=2)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Redis might already be running or not installed
        pass
    
    # Test Redis connection
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print(f"❌ Redis not available: {e}")
        return False

def run_rabbitmq():
    """Start RabbitMQ server."""
    print("🐰 Starting RabbitMQ...")
    
    # Test RabbitMQ connection
    try:
        import pika
        connection = pika.BlockingConnection(
            pika.URLParameters("amqp://guest:guest@localhost:5672/")
        )
        connection.close()
        print("✅ RabbitMQ is running")
        return True
    except Exception as e:
        print(f"❌ RabbitMQ not available: {e}")
        print("💡 Try running: docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
        return False

def start_api_server():
    """Start the API server in a subprocess."""
    print("🚀 Starting API server...")
    
    # Change to API directory
    api_dir = os.path.dirname(__file__)
    
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=api_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        time.sleep(3)
        
        # Check if it's running
        if process.poll() is None:
            print("✅ API server started")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ API server failed to start")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return None
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")
        return None

def test_api_health():
    """Test if API is responding."""
    print("🏥 Testing API health...")
    
    import requests
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ API health: {health.get('status')}")
            return True
        else:
            print(f"❌ API health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API not responding: {e}")
        return False

def run_billing_tests():
    """Run the billing system tests."""
    print("\n🧪 Running billing system tests...")
    
    try:
        # Run the end-to-end test
        result = subprocess.run(
            [sys.executable, "test_billing_e2e.py"],
            cwd=os.path.dirname(__file__),
            capture_output=False,  # Show output in real-time
            text=True
        )
        
        if result.returncode == 0:
            print("\n✅ All billing tests passed!")
            return True
        else:
            print(f"\n❌ Some billing tests failed (exit code: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main function to orchestrate the testing."""
    print("🐰 RabbitReels Billing System - Quick Test")
    print("=" * 50)
    
    api_process = None
    
    try:
        # Check prerequisites
        if not run_redis():
            print("💡 Install and start Redis: https://redis.io/download")
            return False
            
        if not run_rabbitmq():
            print("💡 Start RabbitMQ with Docker or install locally")
            return False
        
        # Start API server
        api_process = start_api_server()
        if not api_process:
            return False
            
        # Wait for API to be ready
        print("⏳ Waiting for API to be ready...")
        for i in range(10):
            if test_api_health():
                break
            time.sleep(1)
        else:
            print("❌ API failed to become ready")
            return False
        
        # Run tests
        success = run_billing_tests()
        
        if success:
            print("\n🎉 Billing system test completed successfully!")
            print("\n📋 Ready for production setup:")
            print("1. Add Stripe test keys to .env file")
            print("2. Start frontend: cd ../web && npm run dev")
            print("3. Test full flow at http://localhost:3001/billing")
        else:
            print("\n⚠️  Some tests failed. Check output above.")
            
        return success
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return False
        
    finally:
        # Clean up
        if api_process:
            print("\n🧹 Stopping API server...")
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_process.kill()
            print("✅ API server stopped")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
