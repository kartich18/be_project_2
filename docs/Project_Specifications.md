# Quantum-Safe Banking Transaction System: Project Specifications

## 1. Executive Summary
The **Quantum-Safe Banking Transaction System** is a state-of-the-art Proof-of-Concept (PoC) designed to evaluate and demonstrate the transition of financial transaction systems from classical cryptographic standards to Post-Quantum Cryptography (PQC). The core objective is to protect financial architectures against the imminent threat of quantum computing and "Harvest Now, Decrypt Later" (HNDL) attacks by implementing next-generation, quantum-resistant algorithms side-by-side with classical counterparts. The project specifically integrates ML-KEM (Kyber) within a centralized client-server architecture.

## 2. Complete Project Specifications

### 2.1 Cryptographic Standards
- **Classical Suite (Baseline)**:
  - **Asymmetric**: RSA-2048 (OAEP padding for encryption, PSS for signing).
  - **Symmetric**: AES-256-GCM (used for bulk payload encryption).
  - **Hash Function**: SHA-256.
- **Post-Quantum Suite (FIPS 203 + FIPS 204)**:
  - **Key Encapsulation Mechanism (KEM)**: All three NIST security levels — ML-KEM-512, ML-KEM-768, and ML-KEM-1024 (aligned with NIST FIPS 203).
  - **Digital Signature Algorithm (DSA)**: ML-DSA-44, ML-DSA-65, and ML-DSA-87 (aligned with NIST FIPS 204 / Dilithium). Each KEM level is paired with the DSA scheme at the matching NIST security level (Option B — paired levels):
    - ML-KEM-512 ↔ ML-DSA-44 (Level 2)
    - ML-KEM-768 ↔ ML-DSA-65 (Level 3)
    - ML-KEM-1024 ↔ ML-DSA-87 (Level 5)
  - **Implementation**: Utilizes the `liboqs` C-library bound via `liboqs-python` for both KEM and DSA operations.
- **Quantum Simulation Framework**:
  - Utilizes **Qiskit** (IBM Quantum SDK) for classical, circuit-based simulations of Shor's algorithm (using simplified moduli like N=15) to statistically demonstrate the mathematical failure of RSA to quantum observation.

### 2.2 Telemetry & Benchmarking
- **Latency comparison**: Tracks sub-millisecond variations during dynamic execution for key generation, encapsulation, and decapsulation stages across all four pipelines.
- **Scalability**: Seamless transaction execution over SQLite with optimized transactional reads powering high-frequency analytical dashboards.

## 3. Implemented Features

### 3.1 Five-Pipeline Crypto Engine (Encryption + Signatures)
- Executes each banking transaction across four parallel encryption pipelines: Classical (RSA-2048), ML-KEM-512, ML-KEM-768, and ML-KEM-1024.
- **Every transaction is also digitally signed**: the classical pipeline signs with RSA-PSS / SHA-256; the three PQC pipelines sign with their paired ML-DSA algorithm (ML-DSA-44/65/87 respectively).
- Sign and verify timing, signature byte sizes, and DSA public key sizes are recorded per-transaction in the database and surfaced via the new `GET /api/v1/analytics/signature-health` endpoint.
- Extracts and visualizes exact payload size expansions, allowing systemic engineering decisions regarding transmission overhead.
- All three ML-KEM security levels run on every transaction, providing a direct side-by-side comparison of key sizes and latencies.

### 3.2 Client-Server Architecture & Real-Time Synchronization
- Centralized model with a trusted server authority holding all keys, running all crypto, validating transactions, and maintaining the master ledger.
- Users (Admin and Viewer roles) interact exclusively via the React SPA frontend — there are no separate thin client node processes.
- Real-time dashboard updates are delivered via Server-Sent Events (SSE) directly from the central `NotificationService`.

### 3.3 Role-Based Access Control & Authorization
- JWT (JSON Web Tokens) backed sessions providing role-based interactions over dynamic dashboards.
- **Two-token authentication pattern**: short-lived (15-minute) access tokens paired with long-lived refresh tokens persisted in the `sessions` table, enabling per-device revocation.
- Strict data siloing: Viewers can only read their own transactions; Admins have access to global system telemetry.

### 3.4 Per-User Cryptographic Key Architecture
- Each user account is assigned dedicated ML-KEM and RSA key pairs upon registration, stored encrypted in the database.
- Private keys are encrypted using a key derived from the user's credentials (PBKDF2) — the server never holds plaintext private keys in memory beyond a single request.
- This makes the HNDL simulation meaningful: the attacker targets genuine per-user ciphertexts, not synthetic data.

### 3.5 Transaction State Machine & Audit Log
- Transactions follow an explicit state machine:
  `INITIATED → VALIDATED → CRYPTO_PROCESSED → COMMITTED → SETTLED` (or `FAILED`)
- Every state transition writes an entry to the append-only `audit_log` table, recording algorithm, key ID, and timing data permanently.

### 3.6 Operational Interactive Dashboard Layer
- Sophisticated "Glassmorphism" React SPA with real-time KPI overviews natively coupled to the API via Server-Sent Events (SSE). No manual polling is utilized.
- Renders advanced security insights visually: Latency Percentiles (p50, p95, p99), ML-KEM Migration Status thresholds, algorithmic ratio costs, and Anomaly Detections.
- **Admin Analytics Dashboard**: Global system telemetry, live registrations, algorithmic comparisons, key rotation health, security events, full transaction history, and the **Digital Signature Health** panel showing RSA-PSS vs ML-DSA-44/65/87 sign/verify timing and signature sizes.
- **Viewer Transaction Management**: Isolated user-specific transaction history (with resolved usernames, not raw account IDs) updated live via SSE, plus a directory-aware form to execute client-to-client transfers.
- **Sessions Management**: Users can review and revoke individual active login sessions.
- **Load Generator**: Admin dashboard includes a traffic generator that cycles through real registered account pairs — no synthetic IDs are sent to the backend.

### 3.7 "Harvest Now, Decrypt Later" (HNDL) Sandbox
- Live simulation illustrating a phased Threat Actor approach targeting legacy banking traffic.
- Phase 1: Cryptographic metadata is harvested in transit. Phase 2: Simulates timeline stagnation until Y2Q (Year-to-Quantum). Phase 3: Evaluates Shor's algorithm logic across Qiskit quantum registers directly extracting encoded banking payloads.
- Targets real, per-user ciphertext captured from live transactions.

## 4. Architecture

### 4.1 System Topology
1. **Frontend Layer (React SPA)**
   - Built with **Vite + TypeScript + React**.
   - Communicates with the Flask API exclusively via REST and SSE.
   - Secures session context via JWT stored in memory, with auto-refresh logic.
2. **Flask REST API (Backend Control Plane)**
   - Pure JSON API server — no Jinja templates or server-side rendering.
   - Handles authentication, transactions, analytics, streaming, key management, and the HNDL harvest simulator.
3. **Core Services Layer**
   - **TransactionService**: Formats structured data, routes cryptographic execution across all 4 encryption pipelines (Classical + 3 ML-KEM levels), and orchestrates ML-DSA signing and verification on each PQC pipeline. Writes all timing and signature telemetry to the DB.
   - **CryptoKeyService**: Manages per-user key generation, storage, and retrieval.
   - **AnalyticsService**: Processes latencies, computes rolling SLA compliance percentiles, exposes security metric heuristics, and provides the signature health comparison endpoint.
   - **HarvestService**: Converts logical mathematical endpoints into executable IBM Qiskit Quantum instructions.
   - **NotificationService / EventBus**: Maintains real-time SSE push streams and updates the server dashboard internally.
4. **Data Persistence**
   - Implemented over **SQLite** (development), interfaced via **SQLAlchemy ORM**.
   - Designed to target **NeonDB (PostgreSQL)** in production via a connection string swap in `.env`.
   - Schema managed by **Alembic** migrations.

## 5. Codebase Structure

The project is organized as a **Monorepo** cleanly separating the backend API, React frontend, deployment infrastructure, and documentation:

```text
be_project_2/
├── backend/                  # Python / Flask API server
│   ├── app/                  # Main application logic hub
│   │   ├── crypto/           # Cryptographic abstractions
│   │   │   ├── classical.py  # RSA-2048 / AES-256-GCM handling
│   │   │   ├── pqc.py        # liboqs ML-KEM-512/768/1024 methods
│   │   │   └── benchmark.py  # Execution timing logic
│   │   ├── models/           # SQLAlchemy data models
│   │   │   ├── account.py, anomaly.py, audit_log.py, client.py
│   │   │   ├── daily_migration_snapshot.py, key_metadata.py
│   │   │   ├── key_rotation_audit.py, security_event.py
│   │   │   ├── session.py, transaction.py, user.py, user_keys.py
│   │   ├── routes/           # REST API route handlers
│   │   │   ├── accounts.py   # Account management endpoints
│   │   │   ├── analytics.py  # Dashboard KPI endpoints
│   │   │   ├── auth.py       # Login, register, token refresh, sessions
│   │   │   ├── clients.py    # Client registry REST API
│   │   │   ├── harvest.py    # HNDL simulator endpoints
│   │   │   ├── keys.py       # Key rotation health endpoints
│   │   │   ├── metrics.py    # Performance metrics endpoints
│   │   │   ├── stream.py     # Global & per-user SSE streams
│   │   │   └── transaction.py# Transaction submission & history
│   │   ├── services/         # Decoupled business logic
│   │   │   ├── analytics_service.py
│   │   │   ├── crypto_key_service.py
│   │   │   ├── event_bus.py
│   │   │   ├── harvest_service.py
│   │   │   ├── notification_service.py
│   │   │   └── transaction_service.py
│   │   └── utils/            # Decorators, loggers, helpers
│   ├── migrations/           # Alembic schema migration versions
│   ├── scripts/              # Developer tooling
│   │   ├── benchmark_cli.py  # Standalone algorithmic benchmark runner
│   │   ├── create_user.py    # CLI user creation utility
│   │   ├── generate_certs.py # Dev-environment TLS cert generator
│   │   └── quantum_attack_demo.py
│   ├── tests/                # Pytest test suite
│   ├── instance/             # SQLite database storage (dev only)
│   ├── liboqs/               # liboqs C library submodule (PQC bindings)
│   ├── alembic.ini           # Alembic configuration
│   ├── config.py             # Application configuration & env loading
│   ├── pytest.ini            # Pytest configuration (logs → ../logs/)
│   ├── requirements.txt      # Python dependency manifest
│   ├── run_server.py         # Central server launch script
│   └── .env                  # Environment variable overrides
│
├── frontend/                 # Vite + React + TypeScript SPA
│   ├── src/
│   │   ├── api/client.ts     # Axios API client with JWT auto-refresh
│   │   ├── hooks/useSSE.ts   # Custom React hook for SSE streams
│   │   └── pages/
│   │       ├── AdminAnalytics.tsx  # Admin-only global analytics view
│   │       ├── ClientTransactions.tsx # Viewer transaction management
│   │       ├── Dashboard.tsx       # Role-aware routing hub
│   │       ├── Harvest.tsx         # HNDL attack simulation UI
│   │       ├── Login.tsx           # Authentication portal
│   │       └── Sessions.tsx        # Session management & revocation
│   ├── index.html
│   ├── package.json
│   └── tsconfig.json
│
├── infra/                    # Infrastructure & deployment config
│   ├── certs/                # TLS certificates (cert.pem, key.pem)
│   └── nginx.conf            # Nginx reverse proxy configuration
│
├── docs/                     # Project documentation
│   ├── Project_Specifications.md
│   ├── Working.md
│   └── DEPLOYMENT.md
│
├── logs/                     # Generated runtime logs (pytest.log, etc.)
├── output/                   # Simulation outputs (e.g. stolen_database.json)
├── .gitignore
└── README.md
```
