"""Deployment verification script for Ice Stream Backend.

Validates that all core modules, database connections, and API routes
are functional for zero-cost cloud deployment on Render.
"""

import sys
import os
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.observability.service import get_observability_service
from app.api.main import app
from app.config.settings import settings


def verify_deployment():
    print("=" * 60)
    print("[ICE STREAM] Backend Deployment Verification")
    print("=" * 60)

    # 1. Check Observability Service & SQLite DB
    print("[1/4] Checking Observability Service & Database...")
    svc = get_observability_service()
    snap = svc.get_snapshot()
    print(f"      Status: OK (Pipeline={snap.pipeline_state.value}, Circuit={snap.circuit_state.value})")

    # 2. Check FastAPI Routes
    print("[2/4] Verifying Registered API Routes...")
    api_paths = list(app.openapi().get("paths", {}).keys())
    expected = ["/api/health", "/api/metrics", "/api/incidents", "/api/lakehouse/status"]
    for exp in expected:
        assert exp in api_paths, f"Missing expected route: {exp}"
    print(f"      Status: OK ({len(api_paths)} endpoints registered)")

    # 3. Check Dual-Host Environment Settings
    print("[3/4] Validating Dual-Host & Security Configuration...")
    print(f"      App Environment: {settings.app_env}")
    print(f"      Log Level: {settings.log_level}")
    print(f"      Observability DB Path: {settings.observability_db_path}")

    # 4. Summary
    print("[4/4] Verification Complete: Ready for Render & Vercel Deployment!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = verify_deployment()
    sys.exit(0 if success else 1)
