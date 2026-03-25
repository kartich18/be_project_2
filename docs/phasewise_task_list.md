# Quantum-Safe Banking Transaction PoC — Phasewise Task List

> **Project Goal**: Build a Python PoC comparing **RSA-2048** (classical) vs **ML-KEM-768** (post-quantum) cryptography for banking transactions, with a Flask REST API, SQLite data layer, real-time dashboard, and comprehensive benchmarks.

---

## Phase 1: Foundation & Environment Setup

| # | Task | Details |
|---|------|---------|
| 1.1 | **Create project folder structure** | Set up the full directory tree as per the module decomposition (see below) |
| 1.2 | **Initialize Python virtual environment** | Python 3.11+, `venv` or `conda` |
| 1.3 | **Create `requirements.txt`** | `flask`, `sqlalchemy`, `cryptography`, `liboqs-python` (`python-oqs`), `pytest`, `flask-cors`, plus any charting/frontend deps |
| 1.4 | **Install and verify `liboqs`** | Build/install liboqs C library on macOS; verify `import oqs` works |
| 1.5 | **Configure [.gitignore](file:///Users/kartik/be_project/.gitignore), README, linting** | Standard Python ignores, project description, optional `black`/`ruff` config |
| 1.6 | **Create `config.py`** | Central config: DB URI, crypto algo names, key sizes, benchmark defaults |

### Target Folder Structure
```
be_project/
├── config.py
├── requirements.txt
├── run.py                  # App entry point
├── crypto/
│   ├── __init__.py
│   ├── classical.py        # RSA-2048 operations
│   ├── pqc.py              # ML-KEM-768 operations
│   └── benchmark.py        # Timing/comparison utilities
├── models/
│   ├── __init__.py
│   └── transaction.py      # SQLAlchemy models
├── routes/
│   ├── __init__.py
│   ├── transaction.py      # POST /api/transaction
│   └── metrics.py          # GET /metrics
├── services/
│   ├── __init__.py
│   └── transaction_service.py
├── static/                 # Dashboard frontend
│   ├── index.html
│   ├── css/
│   └── js/
├── templates/              # Jinja2 templates (if needed)
├── tests/
│   ├── __init__.py
│   ├── test_classical.py
│   ├── test_pqc.py
│   ├── test_routes.py
│   └── test_benchmark.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── helpers.py
└── docs/
    └── ...
```

---

## Phase 2: Cryptographic Core

| # | Task | Details |
|---|------|---------|
| 2.1 | **Implement `crypto/classical.py`** | RSA-2048 key generation, encryption (OAEP), decryption, signing (PSS), verification. Use Python `cryptography` library. Wrap each operation to return timing data. |
| 2.2 | **Implement `crypto/pqc.py`** | ML-KEM-768 key encapsulation/decapsulation using `liboqs-python`. AES-256-GCM for symmetric encryption with the shared secret. Wrap for timing. FIPS 203 alignment. |
| 2.3 | **Implement `crypto/benchmark.py`** | Functions to run N iterations of keygen, encrypt, decrypt for both classical & PQC. Collect min/max/avg/median timings. Return structured comparison dicts. |
| 2.4 | **Unit-test crypto modules** | `tests/test_classical.py`, `tests/test_pqc.py` — round-trip encrypt/decrypt, sign/verify, key sizes, error handling |

### Key Design Notes
- ML-KEM is a **KEM** (Key Encapsulation Mechanism), not direct encryption. Workflow: `keygen → encapsulate → shared_secret → AES-256-GCM encrypt payload`.
- All timing via `time.perf_counter_ns()` for nanosecond precision.
- Key sizes to compare: RSA-2048 public/private vs ML-KEM-768 public/ciphertext.

---

## Phase 3: Data Layer

| # | Task | Details |
|---|------|---------|
| 3.1 | **Implement `models/transaction.py`** | SQLAlchemy model: `Transaction` table with fields — `id`, `timestamp`, `amount`, `sender`, `receiver`, `crypto_method` (RSA/PQC), `key_gen_time_ms`, `encrypt_time_ms`, `decrypt_time_ms`, `total_time_ms`, `key_size_bytes`, `ciphertext_size_bytes`, `status` |
| 3.2 | **Database initialization** | SQLite with `flask_sqlalchemy` or standalone SQLAlchemy. Auto-create tables on first run. |
| 3.3 | **Implement `services/transaction_service.py`** | Business logic: accept transaction payload → run crypto (both classical & PQC) → store results → return comparison data |
| 3.4 | **Unit-test data layer** | Test model CRUD, service layer logic |

---

## Phase 4: REST API Routes

| # | Task | Details |
|---|------|---------|
| 4.1 | **Create Flask app factory (`run.py`)** | Initialize Flask app, register blueprints, configure CORS, set up DB |
| 4.2 | **Implement `POST /api/transaction`** | Accept JSON `{amount, sender, receiver}` → process via both crypto methods → return timing comparison + transaction IDs |
| 4.3 | **Implement `GET /api/metrics`** | Return aggregated benchmark data — avg times per method, key sizes, throughput stats. Support query params for filtering (`?last=100`, `?method=pqc`) |
| 4.4 | **Implement `GET /api/benchmark`** | Run on-demand benchmark of N iterations, return detailed comparison |
| 4.5 | **Error handling & validation** | Input validation, proper HTTP status codes, JSON error responses |
| 4.6 | **API tests** | `tests/test_routes.py` — test all endpoints with Flask test client |

### API Response Example (`POST /api/transaction`)
```json
{
  "transaction_id": "uuid",
  "classical": {
    "key_gen_ms": 45.2,
    "encrypt_ms": 1.8,
    "decrypt_ms": 3.1,
    "total_ms": 50.1,
    "key_size_bytes": 294
  },
  "pqc": {
    "key_gen_ms": 0.8,
    "encrypt_ms": 0.3,
    "decrypt_ms": 0.2,
    "total_ms": 1.3,
    "key_size_bytes": 1184
  }
}
```

---

## Phase 5: Dashboard Frontend

| # | Task | Details |
|---|------|---------|
| 5.1 | **Create `static/index.html`** | Main dashboard page with layout: header, charts area, transaction form, metrics table |
| 5.2 | **Implement comparison bar charts** | Chart.js or similar — side-by-side bars for keygen, encrypt, decrypt times (RSA vs ML-KEM) |
| 5.3 | **Implement real-time line chart** | Live-updating chart showing transaction processing times as new transactions are submitted |
| 5.4 | **Transaction form** | Form to submit a new transaction (amount, sender, receiver) → calls `POST /api/transaction` → updates charts |
| 5.5 | **Load generator UI** | Button to trigger N concurrent transactions for stress testing; show progress & results |
| 5.6 | **Metrics summary cards** | Cards showing avg latency, total transactions processed, key size comparisons, throughput |
| 5.7 | **Key size comparison visualization** | Visual comparison of RSA-2048 vs ML-KEM-768 public key, private key, and ciphertext sizes |
| 5.8 | **Responsive styling** | Clean, professional CSS. Dark-mode friendly. Suitable for academic presentation. |

---

## Phase 6: Testing, Documentation & Polish

| # | Task | Details |
|---|------|---------|
| 6.1 | **Complete unit test suite** | Achieve good coverage across crypto, models, services, routes |
| 6.2 | **Integration tests** | End-to-end: submit transaction via API → verify DB entry → verify metrics endpoint reflects it |
| 6.3 | **Performance benchmark script** | Standalone script to run 100/1000 iterations and generate comparison report (CSV/JSON) |
| 6.4 | **Documentation** | README with setup instructions, architecture diagram, API docs |
| 6.5 | **Academic deliverables** | Prepare benchmark result tables, comparison charts for SPPU report |
| 6.6 | **Risk mitigations** | Verify liboqs fallback strategy, handle edge cases (large payloads, concurrent requests) |
| 6.7 | **Final demo preparation** | End-to-end demo flow: start server → open dashboard → submit transactions → show comparison charts |

---

## Summary

| Phase | Focus | Est. Effort |
|-------|-------|-------------|
| 1 | Foundation & Environment | Day 1–2 |
| 2 | Cryptographic Core | Day 2–4 |
| 3 | Data Layer | Day 4–5 |
| 4 | REST API | Day 5–7 |
| 5 | Dashboard Frontend | Day 7–10 |
| 6 | Testing & Docs | Day 10–14 |

> **Total estimated timeline: 2–3 weeks**

---

## Quick Start Commands (for reference)

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run
python run.py

# Test
pytest tests/ -v

# Benchmark
python -m crypto.benchmark --iterations 100
```
