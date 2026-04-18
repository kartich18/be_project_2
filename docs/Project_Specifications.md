# Quantum-Safe Banking Transaction System: Project Specifications

## 1. Executive Summary
The **Quantum-Safe Banking Transaction System** is a state-of-the-art Proof-of-Concept (PoC) designed to evaluate and demonstrate the transition of financial transaction systems from classical cryptographic standards to Post-Quantum Cryptography (PQC). The core objective is to protect financial architectures against the imminent threat of quantum computing and "Harvest Now, Decrypt Later" (HNDL) attacks by implementing next-generation, quantum-resistant algorithms side-by-side with classical counterparts. The project specifically integrates ML-KEM (Kyber) within a centralized client-server architecture.

## 2. Complete Project Specifications

### 2.1 Cryptographic Standards
- **Classical Suite (Baseline)**:
  - **Asymmetric**: RSA-2048 (OAEP padding for encryption, PSS for signing).
  - **Symmetric**: AES-256-GCM (used for bulk payload encryption).
  - **Hash Function**: SHA-256.
- **Post-Quantum Suite**:
  - **Key Encapsulation Mechanism (KEM)**: ML-KEM-768 standard (aligned with NIST FIPS 203 draft).
  - **Implementation**: Utilizes the `liboqs` C-library bound via `liboqs-python` for native CPU-based post-quantum math structures.
- **Quantum Simulation Framework**:
  - Utilizes **Qiskit** (IBM Quantum SDK) for classical, circuit-based simulations of Shor's algorithm (using simplified moduli like N=15) to statistically demonstrate the mathematical failure of RSA to quantum observation.

### 2.2 Telemetry & Benchmarking
- **Latency comparison**: Tracks sub-millisecond variations during dynamic execution for key generation, encapsulation, and decapsulation stages.
- **Scalability**: Seamless transaction execution over SQLite with optimized transactional reads powering high-frequency analytical dashboards.

## 3. Implemented Features

### 3.1 Dual-Path Transaction Engine
- Executes each banking transaction concurrently across parallel algorithmic pipelines: Classical (RSA) and Post-Quantum (ML-KEM).
- Extracts and visualizes exact payload size expansions, allowing systemic engineering decisions regarding transmission overhead.

### 3.2 Client-Server Architecture & Real-Time Synchronization
- Centralized model with a trusted server authority holding all keys, running all crypto, validating transactions, and maintaining the master ledger.
- Thin client nodes authenticate, submit transaction intents, and receive updates via Server-Sent Events (SSE) from a central `NotificationService`.
- Immediate transaction reflection on localized client-side SQL structures synchronized dynamically via a `SyncService`.

### 3.3 Access Control & Authorization Boundaries
- JWT (JSON Web Tokens) backed sessions providing role-based interactions over dynamic dashboards.
- Client nodes register automatically with the central server upon startup using a pre-shared `CLIENT_REGISTRATION_SECRET` stored in the master configuration.
- Strict data siloing ensures clients only have visibility over their respective transactions while the server aggregates global network analytics.

### 3.4 Operational Interactive Dashboard Layer 
- Sophisticated "Glassmorphism" UI highlighting aesthetic, real-time KPI overviews natively coupled to the API via Server-Sent Events (SSE). No manual polling is utilized.
- Renders advanced security insights visually: Latency Percentiles (p50, p95, p99), ML-KEM Migration Status thresholds, algorithmic ratio costs, and Anomaly Detections.
- Segregated perspectives: Central server views global system telemetry, while connected clients display localized user-specific transaction histories.

### 3.5 "Harvest Now, Decrypt Later" (HNDL) Sandbox
- Live simulation illustrating a phased Threat Actor approach targeting legacy banking traffic.
- Phase 1: Cryptographic metadata is harvested in transit. Phase 2: Simulates timeline stagnation until Y2Q (Year-to-Quantum). Phase 3: Evaluates Shor’s algorithm logic across Qiskit quantum registers directly extracting encoded banking payloads.

## 4. Architecture

### 4.1 Distributed Topology
1. **Frontend Layer (Web Session)** 
   - Receives persistent telemetry via HTTP streams (SSE).
   - Secures persistent context integrity via JWT caching protocols.
2. **Flask REST API interface (Control Plane)** 
   - Decoupled server logic processing transaction intents from authenticated thin clients.
3. **Core Services Layer (Server)** 
   - **TransactionService**: Formats structured data, routes cryptographic execution.
   - **AnalyticsService**: Processes latencies, computes rolling SLA compliance percentiles, and exposes security metric heuristics.
   - **HarvestService**: Converts logical mathematical endpoints into executable IBM Qiskit Quantum instructions.
   - **NotificationService / EventBus**: Maintains real-time SSE push streams dedicated per-client and updates the server dashboard internally.
4. **Client Services Layer**
   - **SyncService**: Analyzes inbound SSE server-pushed models and reliably records entries into localized storage.
5. **Data Persistence**
   - Implemented natively over **SQLite**, interfaced smoothly via **SQLAlchemy ORM**.
   - **Server Base**: Master ledger definitions for Transactions, Clients registry, Key Metric Snapshots, and Audit logs.
   - **Client Base**: Local transaction replica maintaining lightweight, fast reads without historical cryptographic metric bloat.

## 5. Codebase Structure

The ecosystem relies on an extensively modular directory design matching Python microservice architectures:

```text
├── app/                  # Main Server Application logic hub
│   ├── crypto/           # Abstractions for Cryptographic functions
│   │   ├── classical.py  # Standard RSA-2048 / AES handling
│   │   ├── pqc.py        # liboqs wrapped ML-KEM methods
│   │   └── benchmark.py  # Execution timing logic
│   ├── models/           # SQLAlchemy Data Definition Structures
│   │   ├── user.py, client.py, transaction.py, anomaly.py, key_metadata.py
│   ├── routes/           # REST Handlers
│   │   ├── analytics.py  # Dashboard KPI streams
│   │   ├── auth.py       # User Identity validations
│   │   ├── clients.py    # Client registry REST API endpoints
│   │   ├── stream.py     # Global & per-client SSE mappings
│   │   └── transaction.py# Transaction generation & validation endpoints
│   ├── services/         # Decoupled Engine Rules
│   │   ├── analytics_service.py
│   │   ├── event_bus.py  # In-memory publish-subscribe broker
│   │   ├── harvest_service.py
│   │   └── notification_service.py # Routing logic for downstream client notifications    
│   ├── templates/        # HTML Templates for UI Rendering (Server)
│   │   ├── harvest.html  # Qiskit visualizer UI
│   │   ├── index.html    # Master authenticated dashboard
│   │   └── login.html    # Registration portal
│   └── utils/            # Decorators & Loggers
├── client_app/           # Thin-Client Node Application logic
│   ├── models/           # Specialized light replica schemas
│   │   └── local_transaction.py
│   ├── routes/           # App mappings & Proxy handlers
│   │   ├── auth.py, stream.py, transaction.py
│   ├── services/
│   │   └── sync_service.py # Database handler for SSE ingestions
│   └── templates/        # Node-specific UI
│       ├── dashboard.html
│       └── login.html 
├── docs/                 # Project documentation and specifications
│   └── planning/         # Pre-flight architectures and implementations
├── experiments/          # Sandbox area for Shor's alg. prototypes
├── instance/             # Isolated local database storage
├── liboqs/               # Git-submodule for Post Quantum Safe bindings
├── output/               # Generated reports and theoretical exploits
├── scripts/              # Development scripts, DB population
│   ├── benchmark_cli.py  # Standalone testing of algorithmic execution
│   ├── create_user.py    # Database initializations
│   ├── generate_certs.py # Dev-environment PKI generator
│   └── quantum_attack_demo.py  
├── static/               # Client-Side Render Assets
│   ├── css/style.css
│   └── js/dashboard.js   # Front-end analytical bridging
├── run_server.py         # Standalone central server launch process 
├── run_client.py         # Dedicated client process handling launch configs
├── config.py             # Systemic environment settings
├── .env                  # Configuration overlays
└── requirements.txt      # Dependency manifest
```
