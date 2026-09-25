"""Fail a pull request that edits a protected path without owner-approved."""

from __future__ import annotations

import os
import sys

from protected_paths import protected_changes


def main() -> int:
    changed = protected_changes()
    event = os.environ.get("GITHUB_EVENT_NAME", "local")
    approved = os.environ.get("OWNER_APPROVED", "false") == "true"
    if not changed:
        print("protected-path check: pass (no protected paths changed)")
        return 0
    print("protected paths changed:")
    for path in changed:
        print(f"  {path}")
    if event == "pull_request" and not approved:
        print("protected-path check: fail")
        print("owner-approved label required")
        return 1
    if event == "pull_request" and approved:
        print("protected-path check: pass (owner-approved)")
        return 0
    print("protected-path check: pass")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — surface the check error, not a traceback-only fail
        print(f"protected-path check: fail ({exc})")
        sys.exit(1)
