# Phasewise Implementation Plan: Quantum-Safe Banking P2P

## Overview
This updated plan incorporates the peer-to-peer (P2P) architecture, manual user registration, self-signed TLS for secure transport, and a two-layer security model (JWT for users, HMAC for nodes).

---

## Architecture Map

**Two-Layer Security Architecture:**
1. **User Auth (Browser)**: Users securely log into the UI with TLS + JWT.
2. **Node Auth (P2P)**: Any incoming P2P requests from other nodes are authenticated securely using an HMAC signature with a shared secret.

> [!NOTE]
> Since we are going P2P, when Machine A starts, it can register with Machine B (if Machine B's IP is provided), and once connected, they will securely share transactions.

---

## Phase 1: Foundation (TLS & Dependencies)

1. **Update Dependencies**
   - Add `flask-jwt-extended>=4.6.0`, `bcrypt>=4.1.2`, `pyOpenSSL>=23.2.0`, `requests>=2.31.0` to `requirements.txt`.
2. **TLS Configuration**
   - Provide a script `scripts/generate_certs.py` to generate ad-hoc self-signed TLS certificates (`cert.pem`, `key.pem`).
   - Modify `run.py` to use `ssl_context=('cert.pem', 'key.pem')` when running `app.run()`.
3. **Environment Updates**
   - Add `.env` keys for: `JWT_SECRET_KEY`, `PEER_HMAC_SECRET` (for node-to-node auth).

## Phase 2: User Authentication (JWT)

1. **User Model** (`app/models/user.py`)
   - `username`, `password_hash` (bcrypt). No default seeding.
2. **Auth Routes** (`app/routes/auth.py`)
   - `POST /api/auth/register` — Create initial user/subsequent users.
   - `POST /api/auth/login` — Return JWT.
3. **App Initialization** (`app/__init__.py`)
   - JWT integration, token verification middleware for all protected API routes (excluding auth).
4. **Login UI** (`static/login.html`)
   - Secure login form, store JWT in `localStorage`.
   - Setup `fetch` wrappers in `dashboard.js` to attach tokens. 

## Phase 3: Peer-to-Peer Discovery & Auth

1. **Peer Model** (`app/models/peer.py`)
   - `ip_address`, `port`, `last_seen`, `status`.
2. **HMAC Utility** (`app/utils/hmac_auth.py`)
   - `@require_hmac_signature` decorator for P2P routes.
   - `sign_p2p_request(payload)` for outbound requests.
3. **Peer Routes** (`app/routes/peer.py`)
   - `POST /api/peers/register` — A node calls this to register with a counterpart. Secured by HMAC.
   - `POST /api/peers/ping` — Heartbeat mechanism.
4. **Peer Manager Service** (`app/services/peer_service.py`)
   - Logic to handle discovering and syncing with peers.

## Phase 4: Decentralized Transactions & Real-Time Sync

1. **Transaction Syncing** 
   - Modify `app/services/transaction_service.py` to broadcast new transactions to all known active peers over HTTP.
   - Add an endpoint `POST /api/p2p/transaction` restricted by the HMAC decorator to receive transactions from peers.
2. **Real-Time Dashboard (SSE)**
   - Add `app/routes/stream.py` to push `text/event-stream`.
   - Update `dashboard.js` to use `EventSource` for real-time visualization of incoming and outoging transactions.

## Phase 5: UI/UX Finalization

1. **Dashboard Enhancements** (`static/index.html` & `static/js/dashboard.js`)
   - Display active peer connections.
   - Display a visual indicator of Local vs P2P Remote transactions.
   - Add manual peer registration form in the UI.

---

## Open Questions

> [!IMPORTANT]
> **Q1: Peer Discovery**
> For two nodes to find each other, one must initiate the connection. Would you like a small UI component in the dashboard where you can enter the remote node's IP address (e.g., `https://192.168.1.5:5000`) and click "Connect to Peer", which then establishes the secure bond?
