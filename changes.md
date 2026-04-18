
---

## Architecture decisions

**Server role** — the server is the single trusted authority. It holds all keys, runs all crypto, validates every transaction, and maintains the master ledger. Clients are thin — they authenticate, submit intents, and display their own slice of data.

**Crypto flow per transaction** — every transaction goes through both pipelines in parallel, just like the current system, but now server-side only:
1. Client 1 submits a plain transaction intent (recipient, amount) over a JWT-authenticated HTTPS request
2. Server signs the transaction with both RSA-PSS and ML-DSA (or HMAC as a stand-in for signing)
3. Server encrypts the payload with both RSA-OAEP and ML-KEM-768, records both ciphertexts, timings, and sizes
4. Server writes to master ledger, then pushes the event to Client 2 via SSE

---

## What changes vs the current codebase

| Area | Current (P2P) | New (Client-Server) |
|---|---|---|
| `peer.py` route | Node-to-node HMAC relay | **Replaced** by `clients.py` — list available clients |
| `peer_service.py` | Broadcast to known peers | **Replaced** by `notification_service.py` — SSE push to target client |
| `PeerService` model | Peer registry | **Replaced** by `Client` model (registered users with ports) |
| Dashboard | Global analytics | **Split** — server sees all, each client sees only their own |
| `run.py` | Single server | **Three launchers** — `run_server.py`, `run_client.py --port 5001 --id C1` |
| Crypto | Already server-side | No change — stays in `app/crypto/` |

---

## New directory additions

```
├── client_app/               ← New: per-client Flask app
│   ├── routes/
│   │   ├── auth.py           ← Login, JWT storage
│   │   ├── transaction.py    ← Submit tx, view own tx list
│   │   └── stream.py         ← SSE listener from server
│   ├── services/
│   │   └── sync_service.py   ← Receives server push → writes local SQLite
│   ├── templates/
│   │   ├── login.html
│   │   └── dashboard.html    ← Own tx + own analytics only
│   └── instance/             ← Per-client local SQLite
├── run_server.py             ← Boots the central server
└── run_client.py             ← Boots a client (--port, --client-id args)
```

---

## Transaction flow (step by step)

```
Client 1 UI  →  POST /transaction {to: C2, amount: 500}  →  Server
Server       →  Validate JWT, resolve Client 2's address
Server       →  Run dual crypto: RSA-OAEP + ML-KEM-768 (encrypt), RSA-PSS + ML-DSA (sign)
Server       →  Write to master ledger (all analytics recorded)
Server       →  SSE event stream  →  Client 2's sync_service
Client 2     →  sync_service writes to local SQLite
Client 2 UI  →  SSE listener updates dashboard live (no page refresh)
```

---

## Suggested next steps

1. **Scaffold `client_app/`** — copy the minimal Flask structure from `app/`, strip to only client-relevant routes
2. **Replace `peer_service.py`** with `notification_service.py` that maintains an SSE stream per connected client
3. **Add `Client` model** to server DB — stores `client_id`, `port`, JWT identity
4. **Split dashboard templates** — server's `index.html` stays global, client's `dashboard.html` filters by `client_id`
5. **Update `run.py`** into two separate launchers
