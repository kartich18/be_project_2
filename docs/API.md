# API Documentation

Quantum-Safe Banking Transaction PoC — REST API Reference.

**Base URL**: `http://localhost:5000`

---

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/transaction` | POST | Process a transaction through both crypto methods |
| `/api/metrics` | GET | Aggregated performance metrics |
| `/api/benchmark` | GET | On-demand benchmark comparison |
| `/` | GET | Dashboard frontend |

---

## POST /api/transaction

Process a banking transaction through both classical (RSA-2048) and post-quantum (ML-KEM-768) cryptographic pipelines.

### Request

```http
POST /api/transaction
Content-Type: application/json
```

```json
{
  "amount": 1500.00,
  "sender": "Alice",
  "receiver": "Bob"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `amount` | float | ✅ | Transaction amount (must be positive) |
| `sender` | string | ✅ | Sender name (non-empty, max 128 chars) |
| `receiver` | string | ✅ | Receiver name (non-empty, must differ from sender) |
| `currency` | string | ❌ | Currency code (default: `"INR"`) |

### Response — 201 Created

```json
{
  "classical": {
    "id": 1,
    "timestamp": "2026-03-25T07:15:00.000Z",
    "amount": 1500.0,
    "sender": "Alice",
    "receiver": "Bob",
    "currency": "INR",
    "crypto_method": "RSA-2048",
    "key_gen_time_ms": 45.2,
    "encrypt_time_ms": 1.8,
    "decrypt_time_ms": 3.1,
    "total_time_ms": 50.1,
    "key_size_bytes": 294,
    "ciphertext_size_bytes": 256,
    "status": "success"
  },
  "pqc": {
    "id": 2,
    "crypto_method": "ML-KEM-768",
    "key_gen_time_ms": 0.8,
    "encrypt_time_ms": 0.3,
    "decrypt_time_ms": 0.2,
    "total_time_ms": 1.3,
    "key_size_bytes": 1184,
    "ciphertext_size_bytes": 1116,
    "status": "success"
  }
}
```

> **Note**: When `liboqs` is not installed, `"pqc"` is replaced by `"pqc_error"` with a descriptive message. The classical result is always present.

### Error Responses

| Status | Condition | Example |
|--------|-----------|---------|
| 400 | Missing required field | `{"error": "Missing required field: 'amount'"}` |
| 400 | Invalid amount | `{"error": "Amount must be a positive number"}` |
| 400 | Same sender/receiver | `{"error": "Sender and receiver must be different"}` |
| 500 | Internal error | `{"error": "Internal server error"}` |

---

## GET /api/metrics

Return aggregated performance metrics from recent transactions stored in the database.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `method` | string | *(both)* | Filter by crypto method: `RSA-2048` or `ML-KEM-768` |
| `last` | int | 100 | Max number of recent transactions to aggregate (1–10000) |

### Response — 200 OK

```json
{
  "classical": {
    "count": 25,
    "avg_key_gen_ms": 42.3,
    "avg_encrypt_ms": 1.5,
    "avg_decrypt_ms": 2.8,
    "avg_total_ms": 46.6,
    "avg_ciphertext_size_bytes": 256.0
  },
  "pqc": {
    "count": 25,
    "avg_key_gen_ms": 0.7,
    "avg_encrypt_ms": 0.25,
    "avg_decrypt_ms": 0.18,
    "avg_total_ms": 1.13,
    "avg_ciphertext_size_bytes": 1116.0
  }
}
```

### Filtered Example

```http
GET /api/metrics?method=RSA-2048&last=10
```

Returns only the `"classical"` section, aggregated over the last 10 RSA-2048 transactions.

---

## GET /api/benchmark

Run an on-demand benchmark comparing classical vs PQC cryptographic operations.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `iterations` | int | 100 | Number of benchmark iterations (capped at 10000) |

### Response — 200 OK

```json
{
  "iterations": 50,
  "classical": {
    "method": "RSA-2048",
    "iterations": 50,
    "key_gen": { "min": 38.1, "max": 62.4, "avg": 44.2, "median": 43.8, "stdev": 4.1 },
    "encrypt": { "min": 0.8, "max": 2.1, "avg": 1.4, "median": 1.3, "stdev": 0.3 },
    "decrypt": { "min": 2.0, "max": 4.5, "avg": 2.9, "median": 2.8, "stdev": 0.5 },
    "sign":    { "min": 1.5, "max": 3.8, "avg": 2.2, "median": 2.1, "stdev": 0.4 },
    "verify":  { "min": 0.04, "max": 0.12, "avg": 0.06, "median": 0.05, "stdev": 0.01 },
    "total":   { "min": 41.0, "max": 68.0, "avg": 48.5, "median": 47.9, "stdev": 4.8 },
    "key_sizes": {
      "public_key_bytes": 294,
      "private_key_bytes": 1218,
      "ciphertext_bytes": 256
    }
  },
  "pqc": {
    "method": "ML-KEM-768",
    "iterations": 50,
    "key_gen":      { "min": 0.3, "max": 1.2, "avg": 0.6, "median": 0.5, "stdev": 0.2 },
    "encapsulate":  { "min": 0.1, "max": 0.5, "avg": 0.2, "median": 0.2, "stdev": 0.05 },
    "encrypt":      { "min": 0.01, "max": 0.05, "avg": 0.02, "median": 0.02, "stdev": 0.01 },
    "decapsulate":  { "min": 0.08, "max": 0.3, "avg": 0.12, "median": 0.1, "stdev": 0.04 },
    "decrypt":      { "min": 0.01, "max": 0.04, "avg": 0.02, "median": 0.02, "stdev": 0.01 },
    "total":        { "min": 0.5, "max": 2.0, "avg": 0.96, "median": 0.84, "stdev": 0.3 },
    "key_sizes": {
      "public_key_bytes": 1184,
      "secret_key_bytes": 2400,
      "ciphertext_bytes": 1088
    }
  },
  "key_sizes": {
    "classical": { "public_key_bytes": 294, "private_key_bytes": 1218, "ciphertext_bytes": 256 },
    "pqc": { "public_key_bytes": 1184, "secret_key_bytes": 2400, "ciphertext_bytes": 1088 }
  }
}
```

### Error Responses

| Status | Condition | Example |
|--------|-----------|---------|
| 400 | Invalid iterations | `{"error": "iterations must be a positive integer"}` |
| 500 | Internal error | `{"error": "Internal server error"}` |

---

## Common Error Format

All error responses follow this structure:

```json
{
  "error": "Human-readable error message"
}
```
