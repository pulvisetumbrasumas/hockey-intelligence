#!/usr/bin/env python3
"""Run the Hockey Intelligence API server.

Usage:
    uvicorn app.main:app --reload
    python scripts/run.py
"""
import uvicorn

from app.core.config import get_settings

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.app_host,
        port=s.app_port,
        reload=s.app_debug,
    )
