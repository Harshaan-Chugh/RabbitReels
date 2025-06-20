#!/usr/bin/env python3
"""
Development startup script for RabbitReels API
"""
import os
import sys
import subprocess
import uvicorn

def main():
    """Start the API server with development settings."""
    print("🚀 Starting RabbitReels API...")
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found. Run this script from the api/ directory.")
        sys.exit(1)
    
    # Check environment variables
    required_vars = ["RABBIT_URL", "REDIS_URL", "VIDEO_OUT_DIR"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Using default values. Consider setting these in your .env file.")
    
    # Start the server
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 API server stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
