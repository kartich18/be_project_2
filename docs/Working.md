# Quantum-Safe Banking System: Working & Functional Guide

This document functions as a comprehensive usage guide showing exactly how to launch, operate, and review the live functionality of the implemented PQC capabilities. This allows any engineer to independently run the project with zero external instructions.

## 1. System Set up & Boot Sequence

### 1.1 Prerequisites Requirements
- Ensure **Python 3.11** or greater is available.
- Ensure **Node.js** (v18+) and **npm** are installed for the React SPA frontend.
- Ensure standard C compilation tools are available, which are utilized under the hood by the bundled `liboqs` Post-Quantum libraries.
- A **NeonDB** account (for production) or local SQLite for development (default).

### 1.2 Initializing The Backend Environment

> All backend commands must be run from inside the **`backend/`** directory.

1. Clone the project and navigate to the `backend/` directory:
   ```bash
   cd be_project_2/backend
   ```
2. Initialize and activate the Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `backend/.env`:
   ```
   # Development (SQLite — default)
   DATABASE_URL=sqlite:///instance/transactions.db

   # Production (NeonDB / PostgreSQL)
   # DATABASE_URL=postgresql://user:password@ep-name.region.aws.neon.tech/dbname?sslmode=require

   JWT_SECRET_KEY=super-secret-jwt-key
   FLASK_ENV=development
   CLIENT_REGISTRATION_SECRET=your-client-secret
   ```
5. Apply Database Migrations (schema initialization using Alembic):
   ```bash
   alembic upgrade head
   ```
   *This initializes user schemas, refresh token sessions, audit logs, account models, user key stores, and the digital signature telemetry columns (`sign_time_ms`, `verify_time_ms`, `dsa_algorithm`, etc.).*

### 1.3 Launching the Application

The architecture splits into an independent Flask API server and a React SPA frontend. Both must run simultaneously.

**Terminal 1 — Flask API Server:**
```bash
cd backend
python run_server.py --port 5000
```
*The server acts strictly as a JSON API, serving REST endpoints and SSE streams on `http://localhost:5000`.*

**Terminal 2 — React Frontend:**
```bash
cd frontend
npm install
npm run dev
```
*The Vite dev server starts at `http://localhost:5173` and automatically proxies all `/api/*` calls to the Flask server at port 5000.*

---

## 2. Navigating The Front-End Architecture

### 2.1 The Login & Session Infrastructure
1. Open your browser to **`http://localhost:5173`**.
2. The initial view renders the React Login component. Register a new account or sign in with an existing one.
3. Authentication uses a **two-token pattern**: a short-lived access token (15 min) for API calls and a long-lived refresh token stored in the server's `sessions` table. Tokens are auto-refreshed transparently by the API client.

### 2.2 Role-Based Dashboards
Upon authentication, the application routes the user based on their internal role:

- **Admin (`role=admin`)**: Routed to the **Admin Analytics Dashboard** — full global system telemetry, real-time transaction stream, ML-KEM migration status, algorithm comparison, key rotation health, anomaly detection, security events, and the **Digital Signature Health** panel (see §2.3).
- **Viewer (`role=viewer`)**: Routed to the **Client Transactions Dashboard** — isolated personal transaction history (showing usernames, not raw account IDs) updated live via SSE, plus a directory-aware form to send transfers to other registered accounts.

### 2.3 Live Transaction Tracking, Per-User Crypto & Digital Signatures
1. Log in via a Viewer account.
2. Submit a transaction using the send form — select the recipient from the user directory and enter an amount.
3. Under the hood, the platform runs a **five-pipeline transaction engine**:
   - **Encryption**: Classical RSA-2048, ML-KEM-512, ML-KEM-768, and ML-KEM-1024 simultaneously.
   - **Digital Signatures**: Each pipeline signs the payload — RSA-PSS for classical; ML-DSA-44 (Level 2), ML-DSA-65 (Level 3), and ML-DSA-87 (Level 5) for each PQC level respectively (NIST FIPS 204 / Dilithium).
4. The transaction is committed to the ledger, transitions through the state machine (`INITIATED → SETTLED`), and sign/verify timing is stored in the DB.
5. Both the sender and recipient dashboards update live via SSE — no page refresh needed.
6. The Sender → Receiver column in all tables shows **usernames**, not raw account numbers.

### 2.4 Admin Digital Signature Health Panel
The Admin Analytics Dashboard includes a dedicated **Digital Signature Health** section:
- **Four algorithm cards**: RSA-PSS, ML-DSA-44, ML-DSA-65, ML-DSA-87 — each showing avg sign time, avg verify time, signature size, public key size, verified%, and quantum-safe status.
- **Dynamic verdict**: Auto-generated comparison of ML-DSA-65 vs RSA-PSS sign/verify speed and signature size tradeoff.
- **Sign (ms) / Verify (ms)** columns are also visible in the Recent Transactions table.
- Data is fetched from `GET /api/v1/analytics/signature-health` and refreshes every 10 seconds.

### 2.5 Load Generator (Admin only)
The **Load Generator** card on the Admin Dashboard generates synthetic multi-pair traffic:
- On start, it fetches all registered account pairs from `/api/directory/users`.
- It cycles through real account pairs — no fake IDs are sent to the backend.
- Requires at least 2 registered users with accounts.

### 2.6 Session Management
- Navigate to the **Sessions** tab in the React SPA.
- All active login sessions (device, IP, last used) are listed.
- Individual sessions can be revoked, immediately invalidating that device's refresh token.

---

## 3. Demonstrating the "Harvest Now, Decrypt Later" Event Simulation

This isolated interactive module exposes the urgent requirement for ML-KEM mappings utilizing true, per-user live contexts.

1. Navigate to the **HNDL Attack Simulation** tab in the React SPA.
2. Use the interactive components to initialize the execution against genuine user transaction artifacts — these are real ciphertexts from live transactions, not synthetic parameters.
3. Observe the structured sequences:
   - **Phase 1**: Classical interception. Network footprints record accurate ciphertext captures from RSA-encrypted transactions.
   - **Phase 2**: Chronological delay modeling Y2Q (Year-to-Quantum) dependencies — the attacker waits.
   - **Phase 3**: Integration with **Qiskit** processes. Targets the captured RSA ciphertext, resolving underlying algebraic factors. The ML-KEM-encrypted payload remains computationally secure and cannot be broken.

---

## 4. Direct Execution of Developer Tooling

Beyond the UI, the system is backed by developer scripts for direct performance profiling and administration.

> All scripts must be run from inside the **`backend/`** directory with your virtual environment active.

### 4.1 Benchmark CLI
Execute isolated end-to-end timing benchmarks across all cryptographic pipelines:
```bash
python scripts/benchmark_cli.py
```
This runs thousands of rapid ML-KEM and RSA key generation and encapsulation cycles, printing timing statistics without requiring the Flask server to be running.

### 4.2 User Creation Utility
Manually create a user account from the command line (bypassing the web registration form):
```bash
python scripts/create_user.py <username> <password> [admin|viewer]
```

### 4.3 TLS Certificate Generation (Development)
Generate self-signed TLS certificates for local HTTPS testing:
```bash
python scripts/generate_certs.py
```
The generated `cert.pem` and `key.pem` files should be placed in the `infra/certs/` directory. `run_server.py` picks them up automatically.

### 4.4 Running the Test Suite
Execute the full pytest test suite from the `backend/` directory. Test logs are automatically written to `../logs/pytest.log`:
```bash
pytest
```
