@echo off
echo 🧹 Cleaning up RabbitReels for production deployment...

REM Delete test files
del /f api\test_*.py
del /f api\debug_server.py
del /f api\dev.py
del /f api\grant_test_credits.py

REM Delete development info files
del /f scripts-generator\info.txt
del /f BILLING_IMPLEMENTATION_COMPLETE.md

REM Clean up Python cache
rmdir /s /q api\__pycache__
rmdir /s /q common\__pycache__
rmdir /s /q video-creator\__pycache__

echo ✅ Cleanup complete!
echo.
echo 📋 Files remaining for production:
echo   - Keep: BILLING_SETUP.md (for future reference)
echo   - Keep: STRIPE_SETUP.md (for production setup)
echo   - Keep: OAUTH_SETUP.md (for OAuth configuration)
echo   - Keep: README.md files (documentation)
echo.
echo 🚀 Ready for production deployment!
