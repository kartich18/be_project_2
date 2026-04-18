# Quantum-Safe Banking System: Working & Functional Guide

This document functions as a comprehensive usage guide showing exactly how to launch, operate, and review the live functionality of the implemented PQC capabilities. This allows any engineer to independently run the project with zero external instructions.

## 1. System Set up & Boot Sequence

### 1.1 Prerequisites Requirements
- Ensure **Python 3.11** or greater is available. 
- Ensure standard C compilation tools are available, which are utilized under the hood by the bundled `liboqs` Post-Quantum libraries.

### 1.2 Initializing The Environment
1. Clone the project and navigate to the repository's root execution context.
2. Initialize and activate the isolated virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Pull required packages strictly outlined in the configuration manifest:
   ```bash
   pip install -r requirements.txt
   ```
4. Create an ad-hoc TLS certificate needed for secure localhost execution:
   ```bash
   python scripts/generate_certs.py
   ```
   *This evaluates local IP tables, binds certificates directly avoiding mixed-content block errors dynamically mapping `cert.pem` and `key.pem`.*
5. Ensure your `.env` contains the keys for the client-server architecture:
   ```
   CLIENT_REGISTRATION_SECRET=super-secret-registration-key
   SERVER_URL=https://127.0.0.1:5000
   ```

### 1.3 Launching the Application
The architecture is split into a central server and multiple connecting clients. 

Execute the **primary central server**:
```bash
python run_server.py --port 5000
```
*The command line log will indicate the HTTP server is bound exclusively over TLS (`https://`)*.

Execute **connected clients** on separate terminals. Provide a unique port and generic ID for demonstration:
```bash
python run_client.py --port 5001 --client-id C1
python run_client.py --port 5002 --client-id C2
```

---

## 2. Navigating The Front-End Architecture

### 2.1 The Server Dashboard (Global Analytics)
1. Open your browser to **`https://localhost:5000`**.  
   *(If prompted by browser SSL security configurations indicating self-signed risk, bypass utilizing **Advanced -> Proceed**)*.
2. The initial view defaults to an identity assertion requirement via `login.html`.
3. If no user profiles exist within the default SQL structure, you can bypass front-end forms orchestrating user seed pipelines:
   ```bash
   python scripts/create_user.py
   ```
   *(This binds a baseline administrator within the SQL structure for JWT provisioning).*
4. Once authenticated, the browser maps internal JWT definitions caching local sessions while unlocking the expansive visualization overview matrix (`index.html`).
5. The dashboard presents **Connected Clients** logging live registrations alongside all systemic cryptographic telemetry.

### 2.2 The Client Dashboards (User-Level View) 
1. Open your browser to the designated client address: **`https://localhost:5001`** (for C1).
2. The UI limits information rendering only individual transaction data synchronized entirely via background SSE processing.

### 2.3 Live Transaction Tracking
1. Open the UI for an authenticated client (e.g. C1 at `https://localhost:5001`).
2. Notice the dashboard UI contains forms to initiate 'New Transactions'.
3. Submit a transaction targeted closely to another registered client (Recipient: `C2`, Amount: 500). 
4. The client will securely ferry the intent context directly towards the centralized Master validation system.
5. The Master API executes dual-pipeline cryptographic handling executing classical algorithms (RSA-2048) alongside the PQC (ML-KEM-768) process, immediately committing to the central Ledger metrics.
6. Validated via **Server-Sent Events (SSE)**, the server natively updates its own UI, then isolates routing directly pushing SSE elements back down towards C2 (`sync_service`).
7. Watch C2's interface reflect the fully complete transaction record silently onto the feed with no active polling or manual refresh required.

---

## 3. Demonstrating the "Harvest Now, Decrypt Later" Event Simulation

This isolated interactive module exists to explain the urgent requirement for ML-KEM mapping.

1. Via the Central Server's Dashboard navigation, click on the **HNDL Attack Simulation** tab (or direct routing `https://localhost:5000/static/harvest.html`).
2. Utilize the interactive components initializing the execution. 
3. Observe the structured sequences:
   - **Phase 1**: Classical interception. Network footprints record ciphertext captures.
   - **Phase 2**: Chronological delay modeling Y2Q dependencies.
   - **Phase 3**: Systemic integration with **Qiskit** processes targeting captured properties resolving underlying algebraic factors representing quantum factorizations executing natively on your CPU returning fully exposed original values in the UI context. 

---

## 4. Direct Execution of Developer Tooling

Beyond user-interfaces, the system is backed by raw performance profiling tests. Executing these directly aids during backend debugging.

1. Ensure Python's virtual environment is activated correctly. 
2. Execute the stand-alone statistical analytics CLI pipeline isolating Post-Quantum logic from standard Flask context integrations.
   ```bash
   python scripts/benchmark_cli.py
   ```
3. Notice the iteration loops processing thousands of rapid ML-KEM Key Generation, Assurances, and Extractions isolating minimum dependencies, reporting precise distribution timings mapped to CLI out and persistent dataset properties.
