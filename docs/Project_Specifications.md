# Quantum-Safe Banking Transaction System: Project Specifications

## 1. Executive Summary
The **Quantum-Safe Banking Transaction System** is a state-of-the-art Proof-of-Concept (PoC) designed to evaluate and demonstrate the transition of financial transaction systems from classical cryptographic standards to Post-Quantum Cryptography (PQC). The core objective is to protect financial architectures against the imminent threat of quantum computing and "Harvest Now, Decrypt Later" (HNDL) attacks by implementing next-generation, quantum-resistant algorithms side-by-side with classical counterparts. The project specifically integrates ML-KEM (Kyber) within an emulated multi-node network.

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

### 3.2 Peer-to-Peer (P2P) Distributed Synchronization
- Decentralized multi-node architecture communicating via HMAC-SHA256 authenticated REST protocol.
- Independent, scalable nodes dynamically track the distributed registry of network neighbors mapping state synchronization immediately as transactions finalize.

### 3.3 Access Control & Authorization Boundaries
- JWT (JSON Web Tokens) backed sessions providing role-based interactions over dynamic dashboards.
- Zero-trust network interfaces using a customized `@require_hmac_signature` middleware validator ensure cross-node P2P requests cannot be replayed or arbitrarily minted.

### 3.4 Operational Interactive Dashboard Layer 
- Sophisticated "Glassmorphism" UI highlighting aesthetic, real-time KPI overviews natively coupled to the API via Server-Sent Events (SSE). No manual polling is utilized.
- Renders advanced security insights visually: Latency Percentiles (p50, p95, p99), ML-KEM Migration Status thresholds, algorithmic ratio costs, and Anomaly Detections derived from key integration failures.

### 3.5 "Harvest Now, Decrypt Later" (HNDL) Sandbox
- Live simulation illustrating a phased Threat Actor approach targeting legacy banking traffic.
- Phase 1: Cryptographic metadata is harvested in transit. Phase 2: Simulates timeline stagnation until Y2Q (Year-to-Quantum). Phase 3: Evaluates Shor’s algorithm logic across Qiskit quantum registers directly extracting encoded banking payloads.

## 4. Architecture

### 4.1 Distributed Topology
1. **Frontend Layer (Web Session)** 
   - Receives persistent telemetry via HTTP streams.
   - Secures persistent context integrity via JWT caching protocols.
2. **Flask REST API interface (Control Plane)** 
   - Decoupled logic processing transactions from authenticated frontends while reacting to P2P triggers verified via HMAC. 
3. **Core Services Layer** 
   - **TransactionService**: Formats structured data, routes cryptographic execution.
   - **AnalyticsService**: Processes latencies, computes rolling SLA compliance percentiles, and exposes security metric heuristics.
   - **HarvestService**: Converts logical mathematical endpoints into executable IBM Qiskit Quantum instructions.
   - **PeerService / EventBus**: Tracks node statuses and multiplexes real-time transactions internally (via threading) and externally (over HTTP).
4. **Data Persistence**
   - Implemented natively over **SQLite**, interfaced smoothly via **SQLAlchemy ORM** containing rigid definitions for Transactions, Users, Peer Connectivity, Key Metric Snapshots, and Audit logs.

## 5. Codebase Structure

The ecosystem relies on an extensively modular directory design matching Python microservice architectures:

```text
├── app/                  # Main Application logic hub
│   ├── crypto/           # Abstractions for Cryptographic functions
│   │   ├── classical.py  # Standard RSA-2048 / AES handling
│   │   ├── pqc.py        # liboqs wrapped ML-KEM methods
│   │   └── benchmark.py  # Execution timing logic
│   ├── models/           # SQLAlchemy Data Definition Structures
│   │   ├── user.py, peer.py, transaction.py, anomaly.py, key_metadata.py
│   ├── routes/           # REST Handlers
│   │   ├── analytics.py  # Dashboard KPI streams
│   │   ├── auth.py       # User Identity validations
│   │   ├── peer.py       # Node to node endpoints
│   │   ├── stream.py     # SSE integration mappings
│   │   └── transaction.py# Transaction generation endpoints
│   ├── services/         # Decoupled Engine Rules
│   │   ├── analytics_service.py
│   │   ├── event_bus.py  # In-memory publish-subscribe broker
│   │   ├── harvest_service.py
│   │   └── peer_service.py    
│   ├── templates/        # HTML Templates for UI Rendering
│   │   ├── harvest.html  # Qiskit visualizer UI
│   │   ├── index.html    # Main authenticated dashboard
│   │   └── login.html    # Registration portal
│   └── utils/            # Decorators (HMAC verification) & Loggers
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
├── run.py                # TLS Execution server wrapping Waitress/Flask
├── config.py             # Systemic environment settings
├── .env                  # Configuration overlays
└── requirements.txt      # Dependency manifest
```
