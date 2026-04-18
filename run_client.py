"""
run_client.py — Client node launcher.

Usage:
    python run_client.py --port 5001 --client-id C1
    python run_client.py --port 5002 --client-id C2

On startup this script:
  1. Reads --port and --client-id from CLI args (or env vars).
  2. Injects them into the client app's config.
  3. Auto-registers this client with the central server using
     CLIENT_REGISTRATION_SECRET from .env.
  4. Starts the Flask dev server.

Environment variables (from .env):
    SERVER_URL                  — e.g. http://127.0.0.1:5000
    CLIENT_REGISTRATION_SECRET  — shared secret
    JWT_SECRET_KEY              — same value as server (for token decode if needed)
"""
import argparse
import os
import socket
import sys
import time

import requests as http


def _get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _auto_register(server_url: str, client_id: str, port: int, secret: str) -> bool:
    """
    POST /api/clients/register to the central server.
    Retries up to 3 times (server may still be starting).
    Returns True on success.
    """
    payload = {
        "client_id":  client_id,
        "port":       port,
        "secret":     secret,
        "ip_address": _get_lan_ip(),
    }
    for attempt in range(1, 4):
        try:
            resp = http.post(
                f"{server_url}/api/clients/register",
                json=payload,
                timeout=5,
                verify=False,   # self-signed cert — skip TLS verification
            )
            if resp.status_code == 200:
                print(f"✓ Registered with server as '{client_id}'")
                return True
            else:
                print(f"  Registration attempt {attempt} failed: {resp.status_code} {resp.text[:80]}")
        except Exception as exc:
            print(f"  Registration attempt {attempt} error: {exc}")
        time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser(description="Quantum-Safe Banking — Client Node")
    parser.add_argument("--port",      type=int,  default=int(os.environ.get("CLIENT_PORT", 5001)),
                        help="Port for this client app (default: 5001)")
    parser.add_argument("--client-id", type=str,  default=os.environ.get("CLIENT_ID", "C1"),
                        help="Unique client identifier (default: C1)")
    args = parser.parse_args()

    client_id  = args.client_id
    port       = args.port
    server_url = os.environ.get("SERVER_URL", "https://127.0.0.1:5000")
    secret     = os.environ.get("CLIENT_REGISTRATION_SECRET", "")

    print(f"\n┌─────────────────────────────────────────────────────────┐")
    print(f"│    Quantum-Safe Banking — Client Node  [{client_id:<8}]    │")
    print(f"├─────────────────────────────────────────────────────────┤")
    print(f"│  Dashboard : http://127.0.0.1:{port}                      │")
    print(f"│  Server    : {server_url:<44} │")
    print(f"└─────────────────────────────────────────────────────────┘\n")

    # --- Auto-register with the server ------------------------------------
    if not _auto_register(server_url, client_id, port, secret):
        print("⚠️  Could not register with server. Continuing anyway — "
              "will retry on next restart.")

    # --- Inject config into app ------------------------------------------
    # Set env vars so create_client_app picks them up
    os.environ["CLIENT_ID"]     = client_id
    os.environ["CLIENT_PORT"]   = str(port)
    os.environ["SERVER_URL"]    = server_url

    # Import AFTER env vars are set so the factory sees them
    from client_app import create_client_app
    from client_app.client_state import state

    app = create_client_app({
        "CLIENT_ID":   client_id,
        "CLIENT_PORT": port,
        "SERVER_URL":  server_url,
    })

    # Initialise the module-level state so routes can read it immediately
    state.client_id  = client_id
    state.server_url = server_url

    app.run(
        host="0.0.0.0",
        port=port,
        debug=(os.environ.get("FLASK_ENV") == "development"),
    )


if __name__ == "__main__":
    main()
