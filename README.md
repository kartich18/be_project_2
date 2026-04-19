# Quantum-Safe Banking Transaction System

A **production-grade Proof-of-Concept** evaluating the transition of financial transaction infrastructure from classical cryptography to Post-Quantum Cryptography (PQC). Built to demonstrate quantum-resistance against "Harvest Now, Decrypt Later" (HNDL) attacks using ML-KEM (Kyber) — fully aligned with **NIST FIPS 203**.

> Academic evaluation: SPPU | Industry demonstration: Sarvatra Technologies

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **Four-Pipeline Crypto Engine** | Every transaction is processed via RSA-2048, ML-KEM-512, ML-KEM-768, and ML-KEM-1024 |
| **ML-DSA Digital Signatures** | Every transaction is digitally signed — RSA-PSS on the classical path; ML-DSA-44/65/87 (FIPS 204) on PQC, paired by NIST security level |
| **Per-User Cryptographic Keys** | Each account gets dedicated ML-KEM + RSA key pairs, encrypted at rest via PBKDF2 |
| **Role-Based React SPA** | Admin Analytics (global telemetry + Signature Health panel) and Viewer Transaction Management (personal history + transfers) |
| **Two-Token Auth** | Short-lived JWT access tokens (15 min) + long-lived refresh tokens with per-device revocation |
| **Real-Time SSE Streams** | Live dashboard updates via Server-Sent Events — no polling |
| **Transaction State Machine** | `INITIATED → VALIDATED → CRYPTO_PROCESSED → COMMITTED → SETTLED` with append-only audit log |
| **HNDL Attack Simulator** | Three-phase simulation: intercept → Y2Q wait → Qiskit-powered Shor's algorithm attack on RSA |
| **Alembic Schema Management** | Full database migration history; one-command schema initialization |
| **NeonDB Ready** | SQLite for development, swap one env var for NeonDB (PostgreSQL) in production |

---

## 🏗️ Architecture

```
┌──────────────────────────────────┐
│   React SPA  (Vite + TypeScript) │
│   http://localhost:5173          │
│                                  │
│  ┌──────────┐  ┌───────────────┐ │
│  │  Login   │  │  Dashboard    │ │
│  └──────────┘  │  ├─ Admin     │ │
│                │  └─ Viewer    │ │
│  ┌──────────┐  └───────────────┘ │
│  │ Sessions │  ┌───────────────┐ │
│  └──────────┘  │    Harvest    │ │
│                └───────────────┘ │
└────────────┬─────────────────────┘
             │  REST + SSE  (proxied via Vite)
             ▼
┌──────────────────────────────────────────────────────────────┐
│                 Flask REST API  (port 5000)                   │
│                                                              │
│  /api/auth/*        /api/transactions/*   /api/analytics/*   │
│  /api/accounts/*    /api/harvest/*        /api/metrics/*      │
│  /api/stream/*      /api/keys/*           /api/clients/*      │
│                                                              │
│  ┌──────────────────┐  ┌─────────────────┐                   │
│  │ TransactionService│  │ CryptoKeyService│                   │
│  │  (4-pipeline)    │  │  (per-user KEMs)│                   │
│  └───────┬──────────┘  └────────┬────────┘                   │
│          │                      │                            │
│  ┌───────▼──────────────────────▼────────────────────────┐   │
│  │              crypto/                                  │   │
│  │  classical.py (RSA-2048 OAEP/PSS + AES-256-GCM)      │   │
│  │  pqc.py       (ML-KEM-512 / 768 / 1024 via liboqs)   │   │
│  │  benchmark.py (execution timing)                      │   │
│  └──────────────────────────┬────────────────────────────┘   │
│                             │                                │
│  ┌──────────────────────────▼────────────────────────────┐   │
│  │  SQLite / NeonDB (PostgreSQL) via SQLAlchemy ORM      │   │
│  │  Managed with Alembic migrations                      │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```text
be_project_2/
├── backend/                    # Python / Flask API server
│   ├── app/
│   │   ├── crypto/             # Cryptographic abstractions
│   │   │   ├── classical.py    # RSA-2048 OAEP/PSS + AES-256-GCM
│   │   │   ├── pqc.py          # ML-KEM-512/768/1024 via liboqs
│   │   │   └── benchmark.py    # Execution timing helpers
│   │   ├── models/             # SQLAlchemy ORM models
│   │   │   ├── user.py, session.py, account.py
│   │   │   ├── transaction.py, audit_log.py
│   │   │   ├── user_keys.py, key_metadata.py, key_rotation_audit.py
│   │   │   ├── anomaly.py, security_event.py
│   │   │   ├── daily_migration_snapshot.py, client.py
│   │   ├── routes/             # Flask REST API blueprints
│   │   │   ├── auth.py         # Login, register, refresh, session revocation
│   │   │   ├── transaction.py  # Transaction submission & history
│   │   │   ├── analytics.py    # KPI & dashboard metric endpoints
│   │   │   ├── accounts.py     # Account management
│   │   │   ├── stream.py       # Global & per-user SSE streams
│   │   │   ├── harvest.py      # HNDL attack simulator endpoints
│   │   │   ├── keys.py         # Key rotation health endpoints
│   │   │   ├── metrics.py      # Performance metrics endpoints
│   │   │   └── clients.py      # Client registry REST API
│   │   ├── services/           # Decoupled business logic
│   │   │   ├── transaction_service.py
│   │   │   ├── crypto_key_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── harvest_service.py
│   │   │   ├── notification_service.py
│   │   │   └── event_bus.py
│   │   └── utils/              # Decorators, loggers, helpers
│   ├── migrations/             # Alembic migration versions
│   ├── scripts/
│   │   ├── benchmark_cli.py    # Standalone algorithmic benchmark runner
│   │   ├── create_user.py      # CLI user creation utility
│   │   ├── generate_certs.py   # Dev TLS certificate generator
│   │   └── quantum_attack_demo.py
│   ├── tests/                  # Pytest test suite
│   ├── instance/               # SQLite database (dev only)
│   ├── liboqs/                 # liboqs C library submodule (PQC bindings)
│   ├── config.py               # App configuration & env loading
│   ├── run_server.py           # Server entry point
│   ├── alembic.ini
│   ├── pytest.ini
│   └── requirements.txt
│
├── frontend/                   # Vite + React + TypeScript SPA
│   ├── src/
│   │   ├── api/client.ts       # Axios API client with JWT auto-refresh
│   │   ├── hooks/useSSE.ts     # Custom React hook for SSE streams
│   │   └── pages/
│   │       ├── Login.tsx           # Authentication portal
│   │       ├── Dashboard.tsx       # Role-aware routing hub
│   │       ├── AdminAnalytics.tsx  # Admin global telemetry view
│   │       ├── ClientTransactions.tsx # Viewer transaction management
│   │       ├── Harvest.tsx         # HNDL attack simulation UI
│   │       └── Sessions.tsx        # Session management & revocation
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
├── infra/                      # Infrastructure & deployment
│   ├── certs/                  # TLS certificates (cert.pem, key.pem)
│   └── nginx.conf              # Nginx reverse proxy configuration
│
├── docs/
│   ├── Project_Specifications.md
│   ├── Working.md
│   └── DEPLOYMENT.md
│
├── logs/                       # Runtime logs (pytest.log, etc.)
├── output/                     # Simulation outputs (e.g. stolen_database.json)
└── README.md
```

---

## ⚡ Quick Start

> **All backend commands must be run from inside the `backend/` directory.**

### 1. Backend Setup

```bash
# Navigate to the backend
cd be_project_2/backend

# Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (includes liboqs-python, Flask, SQLAlchemy, Qiskit, etc.)
pip install -r requirements.txt
```

### 2. Configure Environment

Create / edit `backend/.env`:

```env
# Development (SQLite — default)
DATABASE_URL=sqlite:///instance/transactions.db

# Production (swap to NeonDB / PostgreSQL)
# DATABASE_URL=postgresql://user:password@ep-name.region.aws.neon.tech/dbname?sslmode=require

JWT_SECRET_KEY=super-secret-jwt-key
FLASK_ENV=development
CLIENT_REGISTRATION_SECRET=your-client-secret
```

### 3. Initialize the Database

```bash
# Apply all Alembic migrations (creates all tables)
alembic upgrade head
```

### 4. Launch the Application

Both services must run simultaneously in separate terminals.

**Terminal 1 — Flask API:**
```bash
cd backend
python run_server.py --port 5000
```
> API available at `http://localhost:5000/api/`

**Terminal 2 — React SPA:**
```bash
cd frontend
npm install
npm run dev
```
> Frontend available at `http://localhost:5173` — all `/api/*` calls are auto-proxied to Flask.

---

## 📚 API Reference

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/register` | `POST` | — | Register a new user account |
| `/api/auth/login` | `POST` | — | Obtain access + refresh tokens |
| `/api/auth/refresh` | `POST` | Refresh token | Rotate access token |
| `/api/auth/logout` | `POST` | JWT | Revoke current session |
| `/api/auth/sessions` | `GET` | JWT | List all active sessions |
| `/api/auth/sessions/<id>` | `DELETE` | JWT | Revoke a specific session |
| `/api/transaction` | `POST` | JWT (Viewer) | Submit a new transaction (4 pipelines + signatures) |
| `/api/transactions/history` | `GET` | JWT | Fetch transaction history (with resolved usernames) |
| `/api/directory/users` | `GET` | JWT | List all users and their account IDs |
| `/api/analytics/migration-status` | `GET` | JWT (Admin) | PQC migration progress |
| `/api/analytics/algorithm-comparison` | `GET` | JWT (Admin) | RSA vs ML-KEM latency comparison |
| `/api/analytics/security-health` | `GET` | JWT (Admin) | Failure rates and security status |
| `/api/analytics/anomalies` | `GET` | JWT (Admin) | Detected anomalies |
| `/api/v1/analytics/signature-health` | `GET` | JWT (Admin) | Digital signature telemetry (RSA-PSS vs ML-DSA) |
| `/api/metrics` | `GET` | JWT | Aggregated performance metrics |
| `/api/benchmark` | `GET` | JWT | On-demand crypto benchmark |
| `/api/stream/transactions` | `GET` | JWT (Admin) | Global SSE transaction stream |
| `/api/stream/my_transactions` | `GET` | JWT | Per-user SSE transaction stream |
| `/api/harvest/start` | `POST` | JWT | Trigger Phase 1 (intercept) |
| `/api/harvest/decrypt` | `POST` | JWT | Trigger Phase 3 (Shor's attack) |
| `/api/v1/keys/rotation-health` | `GET` | JWT (Admin) | Key rotation health |
| `/api/accounts` | `GET` | JWT | User account list |
| `/api/clients` | `GET` | JWT (Admin) | Connected client registry |

> See [`docs/Working.md`](docs/Working.md) for a detailed usage walkthrough.

---

## 🔐 Cryptographic Stack

### Classical Baseline (RSA-2048)
- **Encryption:** RSA-OAEP with SHA-256
- **Signing:** RSA-PSS with SHA-256 — signs the transaction payload on every transaction
- **Symmetric:** AES-256-GCM (FIPS 197) with HKDF-SHA256 key derivation
- **Library:** Python `cryptography`

### Post-Quantum Encryption Suite (ML-KEM — FIPS 203)
All three NIST security levels run on every transaction:

| Algorithm | Security Level | Library |
|---|---|---|
| ML-KEM-512 | Level 2 | `liboqs-python` |
| ML-KEM-768 | Level 3 | `liboqs-python` |
| ML-KEM-1024 | Level 5 | `liboqs-python` |

**Workflow:** `keygen → encapsulate → shared secret → AES-256-GCM encrypt payload`

### Post-Quantum Digital Signatures (ML-DSA — FIPS 204)
Every PQC transaction is also digitally signed. Each ML-KEM level is paired with the ML-DSA variant at the matching NIST security level (Option B — paired levels):

| KEM Pipeline | DSA Algorithm | NIST Level |
|---|---|---|
| ML-KEM-512 | **ML-DSA-44** | Level 2 |
| ML-KEM-768 | **ML-DSA-65** | Level 3 |
| ML-KEM-1024 | **ML-DSA-87** | Level 5 |

**Workflow:** `DSA keygen → sign(plaintext) → [KEM decrypt] → verify(signature)` — `dsa_verified` field stored per transaction row.

Sign/verify timing, signature size, and DSA public key size are exposed via `GET /api/v1/analytics/signature-health` and visualized in the Admin Dashboard **Digital Signature Health** panel.

### Quantum Simulation (Shor's Algorithm)
- **Library:** Qiskit (IBM Quantum SDK)
- Classical circuit-based simulation of Shor's algorithm (simplified moduli, e.g. N=15)
- Demonstrates the mathematical failure of RSA under quantum observation

---

## 🛡️ Security Model

- **No plaintext private keys at rest** — private keys encrypted via PBKDF2 derived from user credentials; decrypted only within a single request lifetime.
- **Two-token session pattern** — access tokens expire in 15 minutes; refresh tokens are stored server-side and can be revoked per-device.
- **Append-only audit log** — every transaction state transition writes an immutable record (algorithm, key ID, timing) to the `audit_log` table.
- **Digital signature on every transaction** — RSA-PSS (classical) and ML-DSA (PQC) sign each transaction payload; `dsa_verified` is stored in the DB and failure gates the SETTLED status.
- **Strict data siloing** — Viewers can only query their own transactions and see resolved usernames; Admins access global telemetry. Enforced server-side.

---

## 🛠️ Developer Tooling

> Run all scripts from inside `backend/` with the virtual environment active.

### Benchmark CLI
Run isolated end-to-end timing benchmarks across all four cryptographic pipelines:
```bash
python scripts/benchmark_cli.py
```

### Create User (CLI)
Manually create an account without the web UI:
```bash
python scripts/create_user.py <username> <password> [admin|viewer]
```

### Generate TLS Certificates (Dev)
Generate self-signed certs for local HTTPS testing:
```bash
python scripts/generate_certs.py
# Output: infra/certs/cert.pem + infra/certs/key.pem
```

### Run Test Suite
```bash
pytest
# Test logs written to: ../logs/pytest.log
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, TypeScript |
| **Backend** | Python 3.11+, Flask |
| **Database** | SQLite (dev) / NeonDB PostgreSQL (prod) |
| **ORM & Migrations** | SQLAlchemy, Alembic |
| **PQC Library** | `liboqs-python` (Open Quantum Safe) |
| **Classical Crypto** | Python `cryptography` (RSA-2048, AES-256-GCM) |
| **Quantum Simulation** | Qiskit (IBM Quantum SDK) |
| **Auth** | JWT (PyJWT), PBKDF2 key derivation |
| **Real-Time** | Server-Sent Events (SSE) |
| **Rate Limiting** | `flask-limiter` |
| **Testing** | pytest, pytest-cov |
| **Deployment** | Nginx reverse proxy, Certbot (TLS) |

---

## 📖 Documentation

| Document | Description |
|---|---|
| [`docs/Working.md`](docs/Working.md) | Full launch guide, UI walkthrough, and HNDL demo steps |
| [`docs/Project_Specifications.md`](docs/Project_Specifications.md) | Complete technical specification and architecture overview |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Production deployment guide (Nginx + Certbot) |