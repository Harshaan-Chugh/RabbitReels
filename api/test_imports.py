import sys
import os

# Add the repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from common.schemas import PromptJob, RenderJob, VideoStatus
    print("✅ Common schemas imported successfully")
except ImportError as e:
    print(f"❌ Error importing common schemas: {e}")

try:
    from config import GOOGLE_CLIENT_ID, JWT_SECRET
    print("✅ Config imported successfully")
    print(f"Google Client ID set: {'Yes' if GOOGLE_CLIENT_ID else 'No'}")
    print(f"JWT Secret set: {'Yes' if JWT_SECRET != 'super-secret-change-me' else 'No (using default)'}")
except ImportError as e:
    print(f"❌ Error importing config: {e}")

try:
    from auth import router
    print("✅ Auth router imported successfully")
except ImportError as e:
    print(f"❌ Error importing auth: {e}")

try:
    from main import app
    print("✅ Main app imported successfully")
    print(f"Available routes: {[route.path for route in app.routes]}")
except ImportError as e:
    print(f"❌ Error importing main app: {e}")
