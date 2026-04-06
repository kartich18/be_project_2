"""
Application entry point for the Quantum-Safe Banking Transaction PoC.

Usage:
    python run.py

TLS:
    Generate certs first:  python scripts/generate_certs.py
    The server then starts on https://0.0.0.0:5000 using self-signed TLS.
    Peer nodes connect via: https://<this-machine-LAN-IP>:5000
"""
import os
import socket

from app import create_app

app = create_app()


def _get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    cert = os.path.join(BASE_DIR, "cert.pem")
    key  = os.path.join(BASE_DIR, "key.pem")

    lan_ip = _get_lan_ip()
    port   = int(os.environ.get("NODE_PORT", 5000))

    if os.path.exists(cert) and os.path.exists(key):
        ssl_ctx = (cert, key)
        scheme  = "https"
        print("\n┌─────────────────────────────────────────────────────────┐")
        print("│       Quantum-Safe Banking Node  [TLS ENABLED]          │")
        print("├─────────────────────────────────────────────────────────┤")
        print(f"│  Local    : https://127.0.0.1:{port}                      │")
        print(f"│  LAN URL  : https://{lan_ip}:{port}                  │")
        print(f"│  Share the LAN URL with peer nodes on the same network  │")
        print("└─────────────────────────────────────────────────────────┘\n")
    else:
        ssl_ctx = None
        scheme  = "http"
        print("\n⚠️  TLS certs not found — running in HTTP mode.")
        print("   Generate certs with:  python scripts/generate_certs.py\n")
        print(f"   Local  : http://127.0.0.1:{port}")
        print(f"   LAN    : http://{lan_ip}:{port}\n")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=(os.environ.get("FLASK_ENV") == "development"),
        ssl_context=ssl_ctx,
    )

