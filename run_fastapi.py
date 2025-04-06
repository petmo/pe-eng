#!/usr/bin/env python
"""
Script to run the FastAPI pricing engine server.
Uses uvicorn with production settings.
"""
import os
import sys
import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Get configuration from environment variables
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    workers = int(os.environ.get("WORKERS", 1))
    log_level = os.environ.get("LOG_LEVEL", "info").lower()
    reload = os.environ.get("RELOAD", "false").lower() == "true"

    # Basic argument parsing
    if len(sys.argv) > 1:
        if sys.argv[1] == "--dev" or sys.argv[1] == "-d":
            reload = True
            log_level = "debug"
            workers = 1
            print("🚀 Running in development mode with auto-reload")
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(f"Usage: {sys.argv[0]} [options]")
            print("Options:")
            print("  --dev, -d    Run in development mode with auto-reload")
            print("  --help, -h   Show this help message")
            print("\nEnvironment variables:")
            print("  PORT         Port to listen on (default: 8000)")
            print("  HOST         Host to bind to (default: 0.0.0.0)")
            print("  WORKERS      Number of worker processes (default: 1)")
            print("  LOG_LEVEL    Logging level (default: info)")
            print("  RELOAD       Enable auto-reload (default: false)")
            print("  API_KEY      API key for authentication")
            print("  DEBUG        Enable debug mode")
            sys.exit(0)

    # Print startup info
    print(f"🔧 Configuration:")
    print(f"   Host:        {host}")
    print(f"   Port:        {port}")
    print(f"   Workers:     {workers}")
    print(f"   Log level:   {log_level}")
    print(f"   Auto-reload: {reload}")
    print(
        f"   API Key:     {'✓ Configured' if os.environ.get('API_KEY') else '✗ Not configured'}"
    )
    print(
        f"   Local data:  {'✓ Enabled' if os.environ.get('DATA_SOURCE_USE_LOCAL', '').lower() == 'true' else '✗ Using Supabase'}"
    )

    print(f"\n📚 API Documentation will be available at:")
    print(f"   http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs")

    # Start uvicorn server
    uvicorn.run(
        "main_fastapi:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=reload,
        workers=workers if not reload else 1,  # Workers must be 1 if reload=True
    )
