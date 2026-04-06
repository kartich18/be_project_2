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

### 1.3 Launching the Application
Execute the primary development driver:
```bash
python run.py
```
*The command line log will indicate the HTTP server is bound exclusively over TLS (`https://`)*.

---

## 2. Navigating The Front-End Architecture

### 2.1 The Dashboard Portal
1. Open your browser to **`https://localhost:5000`**.  
   *(If prompted by browser SSL security configurations indicating self-signed risk, bypass utilizing **Advanced -> Proceed**)*.
2. The initial view defaults to an identity assertion requirement via `login.html`.
3. If no user profiles exist within the default SQL structure, you can bypass front-end forms orchestrating user seed pipelines:
   ```bash
   python scripts/create_user.py
   ```
   *(This binds a baseline administrator within the SQL structure for JWT provisioning).*
4. Once authenticated, the browser maps internal JWT definitions caching local sessions while unlocking the expansive visualization overview matrix (`index.html`).

### 2.2 Live Transaction Tracking
1. Notice the dashboard UI contains forms to initiate 'New Transactions'.
2. Provide dummy values: Recipient ID (`User-7A`), Sender context (`Wallet_88`), and any integer Amount. Submit the details.
3. Once engaged, the system automatically runs the dual-pipeline computation executing classical algorithms (RSA-2048) alongside the PQC (ML-KEM-768) process. 
4. Validated via **Server-Sent Events**, visually inspect performance line charts mapping new timing footprints asynchronously updating directly onto the graph matrix dynamically without requiring hard page refreshes.

---

## 3. Distributed Peer Architecture (P2P) Workflow

The primary enhancement scales operations onto interlinked nodes ensuring consensus capability. Here’s how to trigger multi-instance demonstrations:

1. Copy the codebase externally or run an identical process modifying the primary port map ensuring identical `.env` configurations dictating the same `PEER_HMAC_SECRET`.
2. Assuming **Node 1** operates on `https://192.168.1.10:5000` and **Node 2** runs on `https://192.168.1.50:5000`.
3. Launch your authenticated dashboard pointing at Node 1. Within the navigation context look for **Peers**.
4. Register the secondary operating address (`https://192.168.1.50:5000`). Node 1 dynamically attempts a zero-trust HMAC handshake tracking Node 2 successfully.
5. Create a transaction using Node 1's UI. Notice Node 1's logs broadcasting events automatically while Node 2 synchronizes the output natively reflecting identical transaction logs.

---

## 4. Demonstrating the "Harvest Now, Decrypt Later" Event Simulation

This isolated interactive module exists to explain the urgent requirement for ML-KEM mapping.

1. Via the Dashboard navigation, click on the **HNDL Attack Simulation** tab (or direct routing `https://localhost:5000/static/harvest.html`).
2. Utilize the interactive components initializing the execution. 
3. Observe the structured sequences:
   - **Phase 1**: Classical interception. Network footprints record ciphertext captures.
   - **Phase 2**: Chronological delay modeling Y2Q dependencies.
   - **Phase 3**: Systemic integration with **Qiskit** processes targeting captured properties resolving underlying algebraic factors representing quantum factorizations executing natively on your CPU returning fully exposed original values in the UI context. 

---

## 5. Direct Execution of Developer Tooling

Beyond user-interfaces, the system is backed by raw performance profiling tests. Executing these directly aids during backend debugging.

1. Ensure Python's virtual environment is activated correctly. 
2. Execute the stand-alone statistical analytics CLI pipeline isolating Post-Quantum logic from standard Flask context integrations.
   ```bash
   python scripts/benchmark_cli.py
   ```
3. Notice the iteration loops processing thousands of rapid ML-KEM Key Generation, Assurances, and Extractions isolating minimum dependencies, reporting precise distribution timings mapped to CLI out and persistent dataset properties.
