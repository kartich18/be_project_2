"""
run_server.py — Central server launcher.

Usage:
    python run_server.py [--port 5000]

This is functionally equivalent to the original run.py but explicitly named
to distinguish it from the client launcher in the new client-server topology.
"""
import argparse
import os
import socket

from dotenv import load_dotenv

# Load environment variables from .env before other imports
load_dotenv()

from app import create_app


def _get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Quantum-Safe Banking — Central Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("NODE_PORT", 5000)),
                        help="Port to listen on (default: 5000)")
    args = parser.parse_args()

    app = create_app()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    cert = os.path.join(BASE_DIR, "..", "infra", "certs", "cert.pem")
    key  = os.path.join(BASE_DIR, "..", "infra", "certs", "key.pem")

    lan_ip = _get_lan_ip()
    port   = args.port

    if os.path.exists(cert) and os.path.exists(key):
        ssl_ctx = (cert, key)
        scheme  = "https"
        print("\n┌─────────────────────────────────────────────────────────┐")
        print("│    Quantum-Safe Banking — Central Server [TLS ENABLED] │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│  Local  : https://127.0.0.1:{port}                        │")
        print(f"│  LAN    : https://{lan_ip}:{port}                    │")
        print("└─────────────────────────────────────────────────────────┘\n")
    else:
        ssl_ctx = None
        scheme  = "http"
        print(f"\n⚠️  TLS certs not found — running in HTTP mode.")
        print(f"   Local  : http://127.0.0.1:{port}")
        print(f"   LAN    : http://{lan_ip}:{port}\n")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=(os.environ.get("FLASK_ENV") == "development"),
        ssl_context=ssl_ctx,
    )


if __name__ == "__main__":
    main()
