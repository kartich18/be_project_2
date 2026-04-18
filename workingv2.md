# Walkthrough: P2P → Client-Server Redesign

## What Was Done

The system was redesigned from a peer-to-peer HMAC-broadcast model into a clean client-server architecture. The central server holds all keys, runs all crypto, and maintains the master ledger. Client nodes are thin Flask apps that authenticate via JWT, submit transaction intents, and see only their own data via SSE.

---

## Files Changed

### Server-side

| File | Change |
|---|---|
| `.env` | Replaced `PEER_HMAC_SECRET` with `CLIENT_REGISTRATION_SECRET` + `SERVER_URL` |
| `config.py` | Removed `PEER_HMAC_SECRET`/`PEER_REQUEST_TIMEOUT`; added `CLIENT_REGISTRATION_SECRET`, `SERVER_URL` |
| `app/models/client.py` | **[NEW]** `Client` model — replaces `Peer` (client_id, port, status, last_seen) |
| `app/models/__init__.py` | Imported `Client` alongside `Peer` (Peer kept for DB backward compat) |
| `app/services/notification_service.py` | **[NEW]** Routes SSE events per-client instead of broadcasting over HTTP |
| `app/routes/clients.py` | **[NEW]** REST API for client registry — replaces `peer.py` |
| `app/routes/stream.py` | Added `/api/stream/client/<client_id>` per-client SSE endpoint |
| `app/services/transaction_service.py` | Replaced `PeerService.broadcast_transaction()` with `NotificationService.push_to_client()` |
| `app/__init__.py` | Swapped `peer_bp` → `clients_bp`; updated `_PUBLIC_PREFIXES` |
| `templates/index.html` | Replaced Peer Network panel with Connected Clients panel |
| `static/js/dashboard.js` | Replaced `setupPeerPanel`/`fetchPeers`/`renderPeerList` with `fetchClients`/`renderClientList` |

### New: `client_app/`

| File | Purpose |
|---|---|
| `client_app/__init__.py` | Flask factory for thin client app |
| `client_app/client_state.py` | Module-level JWT + identity singleton |
| `client_app/routes/auth.py` | Login/logout proxy to central server |
| `client_app/routes/transaction.py` | Submit tx (sender = CLIENT_ID); view history |
| `client_app/routes/stream.py` | SSE relay from server's per-client endpoint to browser |
| `client_app/services/sync_service.py` | Writes received transactions to local SQLite |
| `client_app/models/local_transaction.py` | Lightweight tx model (no crypto timing columns) |
| `client_app/templates/login.html` | Login page — shows CLIENT_ID badge |
| `client_app/templates/dashboard.html` | Per-client dashboard — own txs, live SSE feed, send form |

### New Launchers

| File | Command |
|---|---|
| `run_server.py` | `python run_server.py [--port 5000]` |
| `run_client.py` | `python run_client.py --port 5001 --client-id C1` |

---

## Transaction Flow (New)

```
Client 1 browser  →  POST /transaction {receiver: "C2", amount: 500}
                  →  client_app/routes/transaction.py (adds sender=C1)
                  →  POST /api/transaction (JWT)  →  Central Server

Central Server:
  - Validates JWT
  - Runs dual crypto: RSA-OAEP + ML-KEM-768
  - Writes to master ledger (all analytics recorded)
  - EventBus.publish()  →  server dashboard live update
  - NotificationService.push_to_client("C2", event)  →  SSE queue for C2

Client 2 app:
  - /api/stream/client/C2 yields the event
  - client_app/routes/stream.py relays to C2 browser
  - SyncService.save_transaction()  →  C2's local SQLite
  - dashboard.html SSE listener updates the live feed (no page refresh)
```

---

## How to Run

```bash
# 1. Source env
source .env

# 2. Start server
python run_server.py --port 5000

# 3. In separate terminals, start clients
python run_client.py --port 5001 --client-id C1
python run_client.py --port 5002 --client-id C2
```

On client startup, `run_client.py` auto-registers with the server using `CLIENT_REGISTRATION_SECRET`.  
The server dashboard at `http://127.0.0.1:5000` shows all registered clients and global analytics.  
Each client dashboard at `http://127.0.0.1:5001` shows only that client's own transactions.

---

## Verification

### Smoke Test (run at completion)
```
✓ app
✓ app.models.client
✓ app.services.notification_service
✓ app.routes.clients
✓ app.routes.stream
✓ client_app.client_state
✓ client_app.models.local_transaction
✓ client_app.services.sync_service
✓ client_app.routes.auth
✓ client_app.routes.transaction
✓ client_app.routes.stream

OK: Server app created, clients table ready (0 rows)
OK: NotificationService push/receive: {'type': 'ping'}
Server-side smoke test PASSED.
```

### What Was NOT Changed
- `app/crypto/` — zero changes; all crypto stays server-side
- `run.py` — still works as-is (alias for `run_server.py`)
- All existing analytics, harvest simulator, and key-management endpoints
- JWT auth flow for users — unchanged
