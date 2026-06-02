#!/usr/bin/env python3
"""Verify Chat-Notes bridge API availability.

Checks whether the API has endpoints for:
- POST /api/v1/sessions/:id/notes (push chat to notes)
- GET /api/v1/notes/:id/chat-sessions (notes @mention chat)

Outputs: artifacts/walkthrough/v5_0/bridge_verification.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts" / "walkthrough" / "v5_0" / "bridge_verification.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check_bridge_endpoints() -> dict:
    """Check if bridge endpoints exist in the API codebase."""
    api_dir = ROOT / "apps" / "api" / "app" / "api"

    j6_available = False
    j7_available = False
    details = {}

    # Check for notes -> chat-session endpoint (J6: Notes -> @ Chat Session)
    # Look for GET /notes/:id/chat-sessions or similar
    notes_file = api_dir / "notes.py"
    if notes_file.exists():
        content = notes_file.read_text(encoding="utf-8")
        if "chat-session" in content.lower() or "chat_session" in content.lower():
            j6_available = True
            details["j6_endpoint"] = "found in notes.py"
        else:
            details["j6_endpoint"] = "not found in notes.py"

    # Check for chat -> push-to-notes endpoint (J7: Chat -> Push to Notes)
    # Look for POST /sessions/:id/notes or similar
    sessions_file = api_dir / "sessions.py"
    if not sessions_file.exists():
        # Check if sessions are handled elsewhere
        chat_file = api_dir / "chat.py"
        if chat_file.exists():
            content = chat_file.read_text(encoding="utf-8")
            if "push.*note" in content.lower() or "save.*note" in content.lower():
                j7_available = True
                details["j7_endpoint"] = "found in chat.py"
            else:
                details["j7_endpoint"] = "not found in chat.py"
        else:
            details["j7_endpoint"] = "sessions.py and chat.py not found"
    else:
        content = sessions_file.read_text(encoding="utf-8")
        if "/notes" in content or "push_note" in content:
            j7_available = True
            details["j7_endpoint"] = "found in sessions.py"
        else:
            details["j7_endpoint"] = "not found in sessions.py"

    return {
        "j6_bridge_available": j6_available,
        "j7_bridge_available": j7_available,
        "details": details,
        "checked_at": _now_iso(),
        "note": "Phase 5.0-6 closeout explicitly marked Chat-to-Notes bridge as out of scope"
    }


def main() -> int:
    result = check_bridge_endpoints()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[bridge-verify] j6_bridge_available={result['j6_bridge_available']}")
    print(f"[bridge-verify] j7_bridge_available={result['j7_bridge_available']}")
    print(f"[bridge-verify] output={OUTPUT}")

    if not result["j6_bridge_available"] or not result["j7_bridge_available"]:
        print("[bridge-verify] WARNING: Bridge endpoints not found. J6/J7 should be marked as skipped.",
              file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
