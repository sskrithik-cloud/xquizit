"""
Quick start script for running the backend server.
Handles basic environment checks before starting.
"""

import os
import sys
import signal
import time
from pathlib import Path


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    if not shutdown_requested:
        shutdown_requested = True
        print("\n\n" + "=" * 60)
        print("  Shutdown signal received. Stopping server...")
        print("=" * 60)
        sys.exit(0)


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print("ERROR: .env file not found!")
        print("\nPlease create a .env file with your API keys:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your Gemini and DeepInfra API keys to the .env file")
        print("\nExample .env content:")
        print("  GEMINI_API_KEY=your_gemini_api_key_here")
        print("  DEEPINFRA_API_KEY=your_deepinfra_api_key_here")
        return False

    # Check if API keys are set
    from dotenv import load_dotenv
    load_dotenv(env_path)

    gemini_key = os.getenv("GEMINI_API_KEY")
    deepinfra_key = os.getenv("DEEPINFRA_API_KEY")

    missing_keys = []
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        missing_keys.append("GEMINI_API_KEY")
    if not deepinfra_key or deepinfra_key == "your_deepinfra_api_key_here":
        missing_keys.append("DEEPINFRA_API_KEY")

    if missing_keys:
        print(f"ERROR: {', '.join(missing_keys)} not properly configured in .env file!")
        print("\nPlease set valid API keys in your .env file:")
        print("  - Gemini API Key: https://aistudio.google.com/app/apikey")
        print("  - DeepInfra API Key: https://deepinfra.com/dash/api_keys")
        return False

    print("✓ Environment configuration looks good")
    return True


def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        "fastapi",
        "uvicorn",
        "langchain",
        "langgraph",
        "langchain_google_genai",
        "requests",
        "PyPDF2",
        "docx"
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"ERROR: Missing required packages: {', '.join(missing)}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        return False

    print("✓ All dependencies are installed")
    return True


def main():
    """Main entry point."""
    print("=" * 60)
    print("  Screening Interview Chatbot - Backend Server")
    print("=" * 60)
    print()

    # Run checks
    if not check_dependencies():
        sys.exit(1)

    if not check_env_file():
        sys.exit(1)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check for development mode reload option
    enable_reload = os.getenv("UVICORN_RELOAD", "false").lower() == "true"

    print()
    print("Starting server...")
    print()
    print("API will be available at:")
    print("  - http://localhost:8000")
    print("  - API docs: http://localhost:8000/docs")
    print("  - ReDoc: http://localhost:8000/redoc")
    print()
    if enable_reload:
        print("NOTE: Auto-reload is ENABLED (UVICORN_RELOAD=true)")
        print("      This may cause issues on Windows. Use CTRL+C to stop.")
    else:
        print("NOTE: Auto-reload is DISABLED for stability on Windows")
        print("      Set UVICORN_RELOAD=true to enable auto-reload")
    print()
    print("Press CTRL+C to stop the server")
    print("=" * 60)
    print()

    # Start the server
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=enable_reload,
        log_level="info",
        timeout_graceful_shutdown=5
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("  Server stopped by user (CTRL+C)")
        print("=" * 60)
        # Give a moment for cleanup
        time.sleep(0.5)
        sys.exit(0)
    except SystemExit:
        # Allow clean exits from signal handler
        pass
    except Exception as e:
        print("\n\n" + "=" * 60)
        print(f"  ERROR: {str(e)}")
        print("=" * 60)
        sys.exit(1)
