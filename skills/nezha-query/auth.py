"""Authentication module for Superset API access.

Manages browser sessions via playwright-cli. Uses a persistent Edge profile
with Microsoft SSO cookies for automatic re-authentication.

Usage:
    python auth.py [--refresh]

Outputs the browser session status on success.
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).parent
BROWSER_SESSION = "superset"

# Persistent Edge profile with MS SSO cookies
EDGE_PROFILE_DIR = Path(os.environ.get(
    "NEZHA_EDGE_PROFILE",
    os.path.expandvars(r"%LOCALAPPDATA%\NezhaAuth\EdgeProfile"),
))

BASE_URL = "https://www.microsoftnezha.com/nezha"
API_BASE = "https://www.microsoftnezha.com/api/v1"


def _pw(*args: str, timeout: int = 120) -> str:
    """Run a playwright-cli command. Returns combined stdout+stderr."""
    quoted_args = []
    for arg in args:
        if ' ' in arg or '"' in arg or "'" in arg or any(c in arg for c in '|&<>^'):
            quoted_args.append('"' + arg.replace('"', '\\"') + '"')
        else:
            quoted_args.append(arg)
    cmd = f'playwright-cli -s={BROWSER_SESSION} {" ".join(quoted_args)}'
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, shell=True,
    )
    return result.stdout + result.stderr


def _resolve_snapshot_content(snap: str) -> str:
    """If snap is metadata referencing a .yml file, read the actual file content."""
    m = re.search(r'\[[Ss]napshot\]\(([^)]+\.yml)\)', snap)
    if m:
        yml_path = Path(m.group(1))
        if not yml_path.is_absolute():
            yml_path = Path.cwd() / yml_path
        if yml_path.exists():
            return yml_path.read_text(encoding="utf-8", errors="replace")
    return snap


def _find_ref_in_snapshot(snap: str, role: str, name: str) -> str | None:
    """Find an element ref in a playwright-cli snapshot by role and name."""
    content = _resolve_snapshot_content(snap)
    pattern = rf'{role}\s+"{re.escape(name)}"\s+\[ref=(\w+)\]'
    m = re.search(pattern, content)
    return m.group(1) if m else None


def _is_session_active() -> bool:
    """Check if there's an active playwright-cli session."""
    output = _pw("session-list", timeout=10)
    return BROWSER_SESSION in output and "running" in output.lower()


def _is_authenticated() -> bool:
    """Check if current browser session can access the CSRF token endpoint."""
    try:
        _pw("open", f"{API_BASE}/security/csrf_token/")
        time.sleep(2)
        body = _pw("eval", "document.body.innerText")
        return '"result"' in body and "csrf" not in body.lower() or "result" in body
    except Exception:
        return False


def ensure_browser_session(force: bool = False) -> None:
    """Ensure a playwright-cli browser session is open and authenticated.

    If already authenticated, does nothing. If not, opens browser for SSO.
    """
    if not force:
        # Check if session is already active and authenticated
        try:
            output = _pw("snapshot", timeout=10)
            if "### Page" in output:
                # Session exists, check if auth works
                _pw("open", f"{API_BASE}/security/csrf_token/")
                time.sleep(2)
                body = _pw("eval", "document.body.innerText")
                if "result" in body:
                    print("Browser session authenticated.")
                    return
        except Exception:
            pass

    print("Opening browser for authentication...")
    EDGE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    profile_path = str(EDGE_PROFILE_DIR)

    # Open browser with persistent SSO profile
    _pw("open", f"{BASE_URL}/dashboard/list/",
        f"--browser=msedge",
        f"--profile={profile_path}")
    print(f"  Browser opened (profile: {profile_path}).")

    # Check if we're on the login page
    time.sleep(5)
    snap = _pw("snapshot")
    snap_content = _resolve_snapshot_content(snap)
    if "/login" in snap_content.lower() or "login required" in snap_content.lower():
        print("  Login page detected, finding Login button...")
        login_ref = _find_ref_in_snapshot(snap, "button", "Login")
        if not login_ref:
            raise RuntimeError(
                f"Could not find Login button in snapshot:\n{snap_content[:500]}"
            )
        print(f"  Clicking Login button (ref={login_ref})...")
        _pw("click", login_ref)

        # SSO should auto-complete via the persistent profile
        print("  Waiting for SSO to auto-complete...")
        sso_done = False
        for i in range(20):  # up to 60s
            time.sleep(3)
            snap = _pw("snapshot")
            snap_content = _resolve_snapshot_content(snap)
            snap_lower = snap_content.lower()
            # Success: no longer on login page
            if "login required" not in snap_lower and "/login" not in snap_lower:
                if ("dashboard" in snap_lower or "chart" in snap_lower or
                        "welcome" in snap_lower or "not found" in snap_lower or
                        "superset" in snap_lower):
                    sso_done = True
                    break
            if "stay signed in" in snap_lower:
                print("  Handling 'Stay signed in' prompt...")
                yes_ref = _find_ref_in_snapshot(snap, "button", "Yes")
                if yes_ref:
                    _pw("click", yes_ref)
            elif "pick an account" in snap_lower:
                print("  Handling 'Pick an account' prompt...")
                _pw("press", "Enter")
            if i % 5 == 4:
                print(f"    Still waiting... ({(i + 1) * 3}s elapsed)")
        if not sso_done:
            snap = _pw("snapshot")
            raise RuntimeError(
                f"SSO did not auto-complete. Page snapshot:\n{snap[:500]}"
            )

    # Verify auth by hitting CSRF endpoint
    _pw("open", f"{API_BASE}/security/csrf_token/")
    time.sleep(2)
    body = _pw("eval", "document.body.innerText")
    if "result" not in body:
        raise RuntimeError(f"Auth verification failed. CSRF response: {body[:300]}")

    print("  Authenticated successfully.")


# --- CLI entry point ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage Superset authentication.")
    parser.add_argument("--refresh", action="store_true", help="Force re-authentication")
    args = parser.parse_args()

    try:
        ensure_browser_session(force=args.refresh)
        print("\nReady. Browser session is authenticated.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
