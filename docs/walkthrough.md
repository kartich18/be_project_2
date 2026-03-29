---

# Phase 4 — REST API Routes Walkthrough

## What Was Built

### [run.py](file:///Users/kartik/be_project/run.py)
Flask application factory:
- [create_app()](file:///Users/kartik/be_project/run.py#11-35) → initializes Flask, SQLAlchemy, CORS, and registers blueprints.

### [transaction.py](file:///Users/kartik/be_project/app/routes/transaction.py)
POST endpoint:
- [POST /api/transaction](file:///Users/kartik/be_project/app/routes/transaction.py#11-30) → accepts `{amount, sender, receiver}` and processes both crypto methods via `TransactionService`.

### [metrics.py](file:///Users/kartik/be_project/app/routes/metrics.py)
GET endpoint:
- [GET /api/metrics](file:///Users/kartik/be_project/app/routes/metrics.py#11-25) → returns aggregated benchmark data using DB stats.

---

# Phase 5 — Dashboard Frontend Walkthrough

## What Was Built

### [index.html](file:///Users/kartik/be_project/static/index.html)
Responsive dashboard:
- **Comparison Charts**: Side-by-side bar charts (RSA vs ML-KEM) for keygen, encrypt, and decrypt.
- **Metric Cards**: Real-time summary of average latencies and throughput.
- **Transaction Form**: Submit a live transaction and watch metrics update.

### [dashboard.js](file:///Users/kartik/be_project/static/js/dashboard.js)
Frontend logic:
- Chart.js integration for real-time visualization.
- Load generator script for stress testing.

---

# Phase 6 — Harvest Now, Decrypt Later Simulation Walkthrough

## What Was Built

### [harvest_service.py](file:///Users/kartik/be_project/app/services/harvest_service.py)
Threat simulation core:
- [run_harvest()](file:///Users/kartik/be_project/app/services/harvest_service.py#37-53) → Phase 1: encrypts a secret with classical RSA-15.
- [run_decryption()](file:///Users/kartik/be_project/app/services/harvest_service.py#56-113) → Phase 3: executes **Shor's Algorithm** (via Qiskit) to find factors and recover the secret.

### [harvest.html](file:///Users/kartik/be_project/static/harvest.html)
Simulation UI:
- **Interactive Timeline**: Visualizing the threat lifecycle (Harvest → The Leap → Decrypt).
- **Quantum Execution Log**: Real-time display of the quantum circuit measurement and Shor's algorithm steps.

---

# Test Results Summary

```bash
pytest tests/ -v
```

| Suite | Tests | Result |
|-------|-------|--------|
| [test_classical.py](file:///Users/kartik/be_project/tests/test_classical.py) | 13 | ✅ Pass |
| [test_pqc.py](file:///Users/kartik/be_project/tests/test_pqc.py) | 12 | ✅ Pass (liboqs active) |
| [test_routes.py](file:///Users/kartik/be_project/tests/test_routes.py) | 15 | ✅ Pass |
| [test_service.py](file:///Users/kartik/be_project/tests/test_service.py) | 15 | ✅ Pass |
| [test_integration.py](file:///Users/kartik/be_project/tests/test_integration.py) | 8 | ✅ Pass |

> [!TIP]
> Use the **Benchmarking CLI** (`python benchmark_cli.py`) for statistically significant performance reports in JSON and CSV formats.
