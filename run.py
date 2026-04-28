"""
ScanVD — Video Content Scanner
Run this script to start the server.
Usage: python run.py
"""

import os
import sys
import uvicorn

# Ensure working directory is the project root (where this file lives)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

if __name__ == "__main__":
    print("=" * 50)
    print("  ScanVD — Video Content Scanner")
    print("  Starting server at http://localhost:8000")
    print("=" * 50)
    print()

    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[PROJECT_ROOT],
    )
