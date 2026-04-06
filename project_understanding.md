# Project Overview: Quantum-Safe Banking Transaction PoC

This project is a sophisticated Proof-of-Concept (PoC) designed to evaluate and demonstrate the transition from classical cryptography to Post-Quantum Cryptography (PQC) within a banking environment.

## 🚀 Core Functionality

- **Side-by-Side Comparison**: Every transaction is processed through two parallel cryptographic pipelines:
    - **Classical**: RSA-2048 (OAEP for encryption, PSS for signing).
    - **Post-Quantum**: ML-KEM-768 (FIPS 203) for key encapsulation, paired with AES-256-GCM for payload encryption.
- **Real-Time Analytics**: A comprehensive dashboard visualizes performance metrics (latency, key sizes, throughput) and security health.
- **Threat Simulation**: Demonstrates the "Harvest Now, Decrypt Later" (HNDL) attack vector, showing how data intercepted today can be decrypted tomorrow using quantum algorithms (Shor's algorithm).

---

## 🏗 System Architecture

### Backend (Python/Flask)
- **Routes**:
    - [transaction.py](file:///Users/kartik/be_project/app/routes/transaction.py): Main entry point for processing banking transactions.
    - [metrics.py](file:///Users/kartik/be_project/app/routes/metrics.py): Aggregated performance data.
    - [analytics.py](file:///Users/kartik/be_project/app/routes/analytics.py): Advanced KPIs like migration status and anomaly detection.
    - [harvest.py](file:///Users/kartik/be_project/app/routes/harvest.py): Orchestrates the 3-phase HNDL simulation.
- **Services**:
    - `TransactionService`: Manages the crypto logic and database operations.
    - `AnalyticsService`: A massive (~31KB) logic engine for complex metric calculations.
    - `HarvestService`: Uses **Qiskit** to simulate quantum factoring.
- **Database**: SQLite with SQLAlchemy ORM, tracking everything from transaction timings to key rotation audits.

### Frontend (Modern Web)
- **Dashboard**: [index.html](file:///Users/kartik/be_project/static/index.html) powered by [dashboard.js](file:///Users/kartik/be_project/static/js/dashboard.js) and **Chart.js**.
- **Attack UI**: [harvest.html](file:///Users/kartik/be_project/static/harvest.html) featuring an interactive timeline of the quantum threat lifecycle.

---

## 🔐 Advanced Security Metrics

The project includes several high-impact security metrics designed for industry-level reporting:
1. **PQC Migration Status**: Tracking the adoption rate of ML-KEM vs RSA.
2. **Key Rotation Health Index**: Monitoring the age and compliance of cryptographic keys.
3. **Latency Percentiles (p50/p95/p99)**: Identifying tail-end performance risks.
4. **Algorithm Performance Ratio**: Cost-benefit analysis of PQC overhead.
5. **Encryption Anomaly Detection**: Real-time identification of security events.

---

## 🛠 Tech Stack Highlights

- **Languages**: Python (Backend), Javascript (Frontend).
- **Crypto Libraries**: `cryptography`, `liboqs-python` (Open Quantum Safe wrapper), `qiskit` (IBM Quantum SDK).
- **Frameworks**: Flask, SQLAlchemy, Chart.js.
- **Reporting**: CLI-based benchmarking tool (`benchmark_cli.py`) for CSV/JSON exports.

---

## 📄 Key Documentation Directories
- [/docs](file:///Users/kartik/be_project/docs): Technical specs, walkthroughs, and benchmark reports.
- [/files](file:///Users/kartik/be_project/files): Implementation plans and templates for system enhancements.
