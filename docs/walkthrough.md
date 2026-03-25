# Phase 2 — Cryptographic Core Walkthrough

## What Was Built

### [classical.py](file:///Users/kartik/be_project/app/crypto/classical.py)
RSA-2048 module with 6 public functions:
- [generate_keypair()](file:///Users/kartik/be_project/app/crypto/classical.py#23-67) → keygen with DER-encoded size metrics
- [encrypt()](file:///Users/kartik/be_project/app/crypto/classical.py#73-103) / [decrypt()](file:///Users/kartik/be_project/app/crypto/classical.py#105-134) → RSA-OAEP (SHA-256 + MGF1)
- [sign()](file:///Users/kartik/be_project/app/crypto/classical.py#140-169) / [verify()](file:///Users/kartik/be_project/app/crypto/classical.py#171-206) → RSA-PSS (SHA-256, max salt)
- [encrypt_transaction()](file:///Users/kartik/be_project/app/crypto/classical.py#212-258) → end-to-end helper returning uniform timing dict

### [pqc.py](file:///Users/kartik/be_project/app/crypto/pqc.py)
ML-KEM-768 + AES-256-GCM hybrid module:
- [generate_keypair()](file:///Users/kartik/be_project/app/crypto/pqc.py#71-99) / [encapsulate()](file:///Users/kartik/be_project/app/crypto/pqc.py#102-130) / [decapsulate()](file:///Users/kartik/be_project/app/crypto/pqc.py#132-156) → KEM operations via liboqs
- [aes_gcm_encrypt()](file:///Users/kartik/be_project/app/crypto/pqc.py#162-195) / [aes_gcm_decrypt()](file:///Users/kartik/be_project/app/crypto/pqc.py#197-224) → AES-256-GCM with HKDF-SHA256 key derivation
- [encrypt_transaction()](file:///Users/kartik/be_project/app/crypto/pqc.py#230-295) → full KEM + symmetric encrypt/decrypt cycle
- **Graceful fallback**: catches `ImportError`, `OSError`, and `SystemExit` from liboqs; sets `PQC_AVAILABLE = False`

### [benchmark.py](file:///Users/kartik/be_project/app/crypto/benchmark.py)
N-iteration benchmark engine:
- [run_classical_benchmark(n)](file:///Users/kartik/be_project/app/crypto/benchmark.py#40-90) / [run_pqc_benchmark(n)](file:///Users/kartik/be_project/app/crypto/benchmark.py#96-153) → per-operation stats (min/max/avg/median/stdev)
- [run_comparison(n)](file:///Users/kartik/be_project/app/crypto/benchmark.py#159-193) → unified side-by-side comparison dict

---

# Phase 3 — Data Layer Walkthrough

## What Was Built

### [transaction.py](file:///Users/kartik/be_project/app/models/transaction.py)
SQLAlchemy `Transaction` model with 14 columns:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | Integer PK | Auto-increment |
| `timestamp` | DateTime | Server default UTC |
| `amount`, `sender`, `receiver`, `currency` | Float/String | Business fields |
| `crypto_method` | String | `"RSA-2048"` or `"ML-KEM-768"` |
| `key_gen_time_ms`, `encrypt_time_ms`, `decrypt_time_ms`, `total_time_ms` | Float | Timing metrics |
| `key_size_bytes`, `ciphertext_size_bytes` | Integer | Size metrics |
| `status` | String | `"success"` / `"failed"` |

Includes [to_dict()](file:///Users/kartik/be_project/app/models/transaction.py#55-73) for JSON serialisation.

### [transaction_service.py](file:///Users/kartik/be_project/app/services/transaction_service.py)
`TransactionService` with two methods:
- [process_transaction()](file:///Users/kartik/be_project/app/services/transaction_service.py#27-109) — runs **both** classical and PQC crypto, stores rows, returns comparison dict. PQC degrades gracefully when liboqs absent.
- [get_metrics()](file:///Users/kartik/be_project/app/services/transaction_service.py#115-170) — aggregates recent transactions with optional method filter and limit.

## Test Results

```
43 passed, 15 skipped in 10.80s
```

| Suite | Tests | Result |
|-------|-------|--------|
| [test_classical.py](file:///Users/kartik/be_project/tests/test_classical.py) | 13 | ✅ All passed |
| [test_pqc.py](file:///Users/kartik/be_project/tests/test_pqc.py) | 12 | ⏭️ All skipped (liboqs not installed) |
| [test_benchmark.py](file:///Users/kartik/be_project/tests/test_benchmark.py) | 10 | ✅ 9 passed, 1 skipped |
| [test_models.py](file:///Users/kartik/be_project/tests/test_models.py) | 8 | ✅ All passed |
| [test_service.py](file:///Users/kartik/be_project/tests/test_service.py) | 15 | ✅ 13 passed, 2 skipped (PQC) |

> [!NOTE]
> PQC tests will automatically activate once you build and install the liboqs C library.

## Compatibility Notes
- **Python 3.9**: `Union` used instead of `X | Y` syntax
- **liboqs crash**: `SystemExit(1)` caught to prevent test-runner abort
- **In-memory SQLite**: all tests use `TestingConfig` (`:memory:` DB) — no file artifacts
