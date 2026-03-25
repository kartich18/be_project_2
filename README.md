# Quantum-Safe Banking Transaction PoC

A proof-of-concept comparing **RSA-2048** (classical) vs **ML-KEM-768** (post-quantum, FIPS 203) cryptography for banking transactions.

## Features
- Side-by-side cryptographic benchmarking (keygen, encrypt, decrypt)
- Flask REST API with transaction processing
- Real-time dashboard with Chart.js visualizations
- SQLite data persistence with SQLAlchemy
- Load generator for stress testing

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py

# Run tests
pytest tests/ -v
```

## Tech Stack
- **Backend**: Python 3.11+, Flask, SQLAlchemy
- **Classical Crypto**: `cryptography` library (RSA-2048, OAEP, PSS)
- **PQC Crypto**: `liboqs-python` (ML-KEM-768, FIPS 203) + AES-256-GCM
- **Frontend**: HTML/CSS/JS, Chart.js
- **Database**: SQLite

## Project Structure
```
be_project/
├── config.py           # Central configuration
├── run.py              # App entry point
├── requirements.txt    # Dependencies
├── app/
│   ├── __init__.py     # Flask app factory
│   ├── crypto/         # Cryptographic modules
│   ├── models/         # SQLAlchemy models
│   ├── routes/         # API blueprints
│   ├── services/       # Business logic
│   └── utils/          # Logger, helpers
├── static/             # Dashboard frontend
├── tests/              # Test suite
└── docs/               # Documentation
```