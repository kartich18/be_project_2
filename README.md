# Quantum-Safe Banking Transaction PoC

A proof-of-concept comparing **RSA-2048** (classical) vs **ML-KEM-768** (post-quantum, FIPS 203) cryptography for banking transactions. Built for academic evaluation (SPPU) and industry demonstration (Sarvatra Technologies).

---

## 🚀 Latest Features

- **Dual Crypto Engine:** Side-by-side processing using RSA-2048 (OAEP/PSS) and ML-KEM-768 alongside AES-256-GCM.
- **Interactive Dashboard:** Real-time visualisations using Chart.js to compare metrics like encryption time, decryption time, and key generation times.
- **Harvest Now, Decrypt Later (HNDL) Simulation:** A dedicated module demonstrating the threat of quantum computing using Shor's algorithm on intercepted classical data.
- **REST API Integration:** Fully functional Flask endpoints handling cryptographic operations and the HNDL workflow.
- **Persistence Layer:** SQLite database integration via SQLAlchemy capturing transaction run times and parameters.
- **Benchmarking CLI:** A standalone CLI tool (`benchmark_cli.py`) for generating detailed JSON and CSV comparison reports.
- **Comprehensive Testing:** End-to-end integration tests, route tests, and automated module benchmarking.
- **NIST Aligned:** Fully compliant with FIPS 203 (ML-KEM) and FIPS 197 (AES-256-GCM) standards.

---

## 🏗 Architecture

```text
┌─────────────┐      ┌──────────────────────────────────────────┐      ┌──────────────────────────┐
│  Dashboard  │◄────►│              Flask REST API              │◄────►│  HNDL Attack Simulation  │
│  (Chart.js) │      │  POST /api/transaction                   │      │  (Shor's Algorithm)      │
└─────────────┘      │  GET  /api/metrics                       │      └──────────────────────────┘
                     │  GET  /api/benchmark                     │
                     └──────────────┬───────────────────────────┘
                                    │
                     ┌──────────────▼───────────────────────────┐
                     │         Transaction Service              │
                     │  (orchestrates both crypto pipelines)    │
                     └──────┬──────────────────┬────────────────┘
                            │                  │
                ┌───────────▼──────┐  ┌────────▼─────────┐
                │  classical.py    │  │     pqc.py        │
                │  RSA-2048 OAEP   │  │  ML-KEM-768 +     │
                │  RSA-PSS sign    │  │  AES-256-GCM      │
                └───────────┬──────┘  └────────┬──────────┘
                            │                  │
                     ┌──────▼──────────────────▼────────────────┐
                     │         SQLite (via SQLAlchemy)          │
                     │         transactions table               │
                     └──────────────────────────────────────────┘
```

---

## ⚙️ Quick Start & Steps to Run

For detailed environment setup (including the `liboqs` C library installation), see the [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) guide.

### 1. Setup

```bash
# Clone the repository
git clone <repo-url> && cd be_project

# Create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
*(Ensure `liboqs` is installed on your system for Post-Quantum features. See setup guide for details.)*

### 2. Run the Application

```bash
# Start the Flask web server
python run.py
```

- **Dashboard:** Open your browser and navigate to `http://localhost:5000/`
- **API Base URL:** `http://localhost:5000/api/`

### 3. Run Benchmark CLI

```bash
# Generate 100 benchmark iterations and output to docs/
python benchmark_cli.py

# Specify custom iterations
python benchmark_cli.py --iterations 500
```

### 4. Run Tests

```bash
# Execute the full pytest suite
pytest tests/ -v
```

---

## 📚 API Reference (Summary)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/transaction` | `POST` | Process a transaction through both crypto methods |
| `/api/metrics` | `GET` | Aggregated performance metrics |
| `/api/benchmark` | `GET` | On-demand benchmark comparison |
| `/api/harvest/start` | `POST` | Trigger Phase 1 of HNDL simulation |
| `/api/harvest/decrypt` | `POST` | Trigger Phase 3 of HNDL simulation |
| `/` | `GET` | Dashboard frontend |
| `/harvest` | `GET` | Harvest simulation frontend |

> Full API documentation is available in [docs/API.md](docs/API.md)

---

## 🔐 Cryptographic Methods

### RSA-2048 (Classical Baseline)
- **Key generation:** 2048-bit RSA key pair
- **Encryption:** RSA-OAEP with SHA-256
- **Signing:** RSA-PSS with SHA-256
- **Library:** Python `cryptography`

### ML-KEM-768 (Post-Quantum)
- **KEM:** ML-KEM-768 (FIPS 203, formerly Kyber-768)
- **Symmetric:** AES-256-GCM (FIPS 197) with HKDF-SHA256 key derivation
- **Workflow:** keygen → encapsulate → shared secret → AES-GCM encrypt payload
- **Library:** `liboqs-python` (backed by the Open Quantum Safe `liboqs` C library)

---

## 🛠 Tech Stack

- **Backend:** Python 3.9+, Flask, SQLAlchemy
- **Database:** SQLite
- **Crypto Libraries:** `cryptography`, `liboqs-python`
- **Frontend:** HTML5, CSS3, Vanilla JS, Chart.js
- **Testing:** pytest, pytest-cov