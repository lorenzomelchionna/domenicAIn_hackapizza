#!/usr/bin/env python3
"""Run Hackapizza 2.0 multi-agent system. Execute from repo root: python run.py"""
import sys
sys.path.insert(0, ".")

if __name__ == "__main__":
    import asyncio
    from src.main import main
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        from src.sse import log
        log("INIT", "client stopped")
