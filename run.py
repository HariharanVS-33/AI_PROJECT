#!/usr/bin/env python3
"""
run.py — Project entry point.
Run this file to start the Healthcare Lead Agent server.
"""
import os
import sys

# Ensure we run from project root so relative paths work
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Create data directories if they don't exist
os.makedirs("./data/chromadb", exist_ok=True)
os.makedirs("./data", exist_ok=True)

import uvicorn

if __name__ == "__main__":
    print("\n" + "="*55)
    print("  🏥 Healthcare Lead Agent — Starting Up")
    print("="*55)
    print("  📍 URL  : http://localhost:8000")
    print("  📚 Docs : http://localhost:8000/docs")
    print("  ⚠️  First run will scrape polymedicure.com (~2-3 min)")
    print("="*55 + "\n")

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend", "frontend"],
    )
