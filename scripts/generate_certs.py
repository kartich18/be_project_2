"""
Certificate generator for Quantum-Safe Banking PoC.

Generates a self-signed TLS certificate and private key for local development.
Run this once: python scripts/generate_certs.py

Output files:
    cert.pem  — self-signed X.509 certificate (valid 365 days)
    key.pem   — RSA-2048 private key
"""

import os
import datetime
import ipaddress

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:
    raise SystemExit(
        "ERROR: 'cryptography' package not installed.\n"
        "Run: pip install cryptography"
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT_PATH = os.path.join(BASE_DIR, "cert.pem")
KEY_PATH  = os.path.join(BASE_DIR, "key.pem")


def get_lan_ip() -> str:
    """Best-effort detection of the LAN IP address."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate():
    lan_ip = get_lan_ip()
    print(f"Detected LAN IP: {lan_ip}")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Build certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Quantum-Safe Banking PoC"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address(lan_ip)),
            ]),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Write private key
    with open(KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Write certificate
    with open(CERT_PATH, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"✅ cert.pem written to {CERT_PATH}")
    print(f"✅ key.pem  written to {KEY_PATH}")
    print(f"\nCertificate covers:")
    print(f"  - localhost")
    print(f"  - 127.0.0.1")
    print(f"  - {lan_ip}  ← your LAN IP")
    print(f"\nNOTE: Browsers will show a security warning for self-signed certs.")
    print(f"      Click 'Advanced' → 'Proceed' to accept it.")


if __name__ == "__main__":
    generate()
