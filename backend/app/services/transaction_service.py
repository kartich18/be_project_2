"""
Transaction service — business logic for processing transactions.

Orchestrates cryptographic operations (both classical and PQC),
stores results in the database, and returns comparison data.
"""

import json
from datetime import datetime, timedelta, timezone

from app import db
from app.crypto import classical
from app.crypto import pqc as pqc_mod
from app.models.audit_log import AuditLog
from app.models.key_metadata import KeyMetadata
from app.models.transaction import Transaction, TransactionState
from app.services.analytics_service import AnalyticsService
from app.services.event_bus import EventBus
from app.utils.logger import logger


# Response keys for each PQC variant — maps algorithm name to response key
_PQC_RESPONSE_KEYS = {
    "ML-KEM-512": "pqc_512",
    "ML-KEM-768": "pqc_768",
    "ML-KEM-1024": "pqc_1024",
}


class TransactionService:
    """Encapsulates all transaction-processing logic."""

    @staticmethod
    def _latency_bucket(total_ms: float) -> str:
        """Map transaction latency to configured bucket labels."""
        if total_ms < 50:
            return "<50ms"
        if total_ms < 100:
            return "50-100ms"
        if total_ms < 200:
            return "100-200ms"
        if total_ms < 500:
            return "200-500ms"
        return ">500ms"

    @staticmethod
    def _record_key_metadata(session, algorithm: str, timestamp):
        """Create key metadata row for rotation-health analytics."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        key_row = KeyMetadata(
            algorithm=algorithm,
            created_at=timestamp,
            last_used_at=timestamp,
            rotation_due_at=timestamp + timedelta(days=90),
            status="active",
            key_version=1,
        )
        session.add(key_row)

    @staticmethod
    def _log_audit(session, transaction_id: int, event_type: str, status: str, details: dict = None):
        """Append an event to the audit_log table."""
        log = AuditLog(
            transaction_id=transaction_id,
            event_type=event_type,
            status=status,
        )
        if details:
            log.set_details(details)
        session.add(log)

    # ------------------------------------------------------------------
    # Core: process a transaction through both crypto pipelines
    # ------------------------------------------------------------------

    @staticmethod
    def process_transaction(data: dict, session=None, origin_ip: str = None) -> dict:
        """
        Accept a transaction payload, encrypt with **both** classical and PQC
        methods (all three ML-KEM security levels), persist the results,
        and return a comparison dict.

        Args:
            data:       dict with keys ``amount``, ``sender``, ``receiver``,
                        and optionally ``currency`` (default ``"INR"``).
            session:    Optional SQLAlchemy session. Falls back to
                        ``db.session`` when ``None``.
            origin_ip:  LAN IP of the machine that initiated this transaction.

        Returns:
            dict with ``classical``, ``pqc_512``, ``pqc_768``, ``pqc_1024``
            (or ``pqc_error`` if liboqs unavailable), and the serialised
            transaction payload that was encrypted.
        """
        if session is None:
            session = db.session

        amount   = float(data.get("amount", 0))
        sender   = data.get("account_id_from", "")
        receiver = data.get("account_id_to", "")
        currency = data.get("currency", "INR")

        logger.debug(
            "Processing transaction for %s -> %s (amount: %s %s, origin_ip: %s)",
            sender, receiver, amount, currency, origin_ip,
        )

        # --- Balance check & deduction (runs once per business transaction) --
        from app.models.account import Account
        sender_acct = session.query(Account).filter_by(account_number=sender).first()
        receiver_acct = session.query(Account).filter_by(account_number=receiver).first()

        if not sender_acct:
            raise ValueError(f"Sender account '{sender}' not found")
        if not receiver_acct:
            raise ValueError(f"Receiver account '{receiver}' not found")
        if sender_acct.balance < amount:
            raise ValueError(
                f"Insufficient funds: balance {sender_acct.balance:.2f}, required {amount:.2f}"
            )

        sender_acct.balance   -= amount
        receiver_acct.balance += amount
        logger.debug("Balance updated: %s → %.2f, %s → %.2f",
                     sender, sender_acct.balance, receiver, receiver_acct.balance)

        # Build the plaintext that the crypto layer will encrypt
        payload = json.dumps(data, sort_keys=True).encode("utf-8")

        # --- Classical (RSA-2048) -----------------------------------------
        classical_result = classical.encrypt_transaction(payload)
        classical_tx = Transaction(
            amount=amount,
            sender=sender,
            receiver=receiver,
            currency=currency,
            crypto_method=classical_result["method"],
            key_gen_time_ms=classical_result["key_gen_ms"],
            encrypt_time_ms=classical_result["encrypt_ms"],
            decrypt_time_ms=classical_result["decrypt_ms"],
            total_time_ms=classical_result["total_ms"],
            key_size_bytes=classical_result["public_key_bytes"],
            ciphertext_size_bytes=classical_result["ciphertext_bytes"],
            status=TransactionState.SETTLED.value if classical_result["verified"] else TransactionState.FAILED.value,
            latency_bucket=TransactionService._latency_bucket(classical_result["total_ms"]),
            failure_reason=None if classical_result["verified"] else "verification_failed",
            origin_ip=origin_ip,
            # RSA-PSS digital signature telemetry
            sign_time_ms=classical_result.get("sign_ms"),
            verify_time_ms=classical_result.get("verify_ms"),
            dsa_algorithm="RSA-PSS",
            dsa_public_key_bytes=classical_result.get("public_key_bytes"),  # same RSA key
            signature_size_bytes=256,  # RSA-2048 signature is always 256 B
        )
        session.add(classical_tx)
        TransactionService._record_key_metadata(
            session,
            classical_result["method"],
            classical_tx.timestamp,
        )
        session.flush() # Get classical_tx.id

        TransactionService._log_audit(session, classical_tx.id, TransactionState.INITIATED.value, "success")
        TransactionService._log_audit(session, classical_tx.id, TransactionState.VALIDATED.value, "success")
        TransactionService._log_audit(session, classical_tx.id, TransactionState.CRYPTO_PROCESSED.value, "success")
        TransactionService._log_audit(session, classical_tx.id, TransactionState.COMMITTED.value, "success")
        
        final_status = "success" if classical_result["verified"] else "failed"
        TransactionService._log_audit(session, classical_tx.id, TransactionState.SETTLED.value if classical_result["verified"] else TransactionState.FAILED.value, final_status)

        if not classical_result["verified"]:
            AnalyticsService.log_security_event(
                event_type="decryption_failure",
                algorithm=classical_result["method"],
                sender=sender,
                receiver=receiver,
                error_message="RSA verification failed",
                latency_ms=classical_result["total_ms"],
                auto_commit=False,
            )

        # --- PQC (ML-KEM-512 / 768 / 1024) --------------------------------
        pqc_entries = {}  # algo → Transaction
        pqc_error = None

        if pqc_mod.PQC_AVAILABLE:
            for algo in pqc_mod.KEM_ALGORITHMS:
                try:
                    pqc_result = pqc_mod.encrypt_transaction(payload, algorithm=algo)
                    actual_kem_ct = None
                    actual_aes_ct = None

                    if algo == "ML-KEM-768" and receiver:
                        from app.models.account import Account
                        from app.models.user_keys import UserKeys
                        rec_acct = session.query(Account).filter_by(id=receiver).first()
                        if rec_acct:
                            u_keys = session.query(UserKeys).filter_by(user_id=rec_acct.user_id).first()
                            if u_keys and u_keys.kem_public_key:
                                try:
                                    kem = pqc_mod._oqs.KeyEncapsulation("ML-KEM-768")
                                    kem_ct, shared_sec = kem.encap_secret(u_keys.kem_public_key)
                                    aes_dict = pqc_mod.aes_gcm_encrypt(shared_sec, payload)
                                    actual_kem_ct = kem_ct
                                    actual_aes_ct = aes_dict["encrypted_data"]
                                except Exception as e:
                                    logger.warning("Failed to generate actual ciphertext mapping: %s", e)

                    pqc_tx = Transaction(
                        amount=amount,
                        sender=sender,
                        receiver=receiver,
                        currency=currency,
                        crypto_method=pqc_result["method"],
                        key_gen_time_ms=pqc_result["key_gen_ms"],
                        encapsulate_time_ms=pqc_result["encapsulate_ms"],
                        encrypt_time_ms=pqc_result["encrypt_ms"],
                        decapsulate_time_ms=pqc_result["decapsulate_ms"],
                        decrypt_time_ms=pqc_result["decrypt_ms"],
                        total_time_ms=pqc_result["total_ms"],
                        key_size_bytes=pqc_result["public_key_bytes"],
                        secret_key_bytes=pqc_result["secret_key_bytes"],
                        ciphertext_size_bytes=pqc_result["ciphertext_bytes"],
                        kem_ciphertext=actual_kem_ct,
                        aes_ciphertext=actual_aes_ct,
                        status=TransactionState.SETTLED.value if pqc_result["verified"] else TransactionState.FAILED.value,
                        latency_bucket=TransactionService._latency_bucket(pqc_result["total_ms"]),
                        failure_reason=None if pqc_result["verified"] else "verification_failed",
                        origin_ip=origin_ip,
                        # ML-DSA digital signature telemetry (paired security level)
                        sign_time_ms=pqc_result.get("sign_ms"),
                        verify_time_ms=pqc_result.get("verify_ms"),
                        dsa_algorithm=pqc_result.get("dsa_algorithm"),
                        dsa_public_key_bytes=pqc_result.get("dsa_public_key_bytes"),
                        signature_size_bytes=pqc_result.get("signature_bytes"),
                    )
                    session.add(pqc_tx)
                    TransactionService._record_key_metadata(
                        session,
                        pqc_result["method"],
                        pqc_tx.timestamp,
                    )
                    session.flush()
                    
                    TransactionService._log_audit(session, pqc_tx.id, TransactionState.INITIATED.value, "success", {"algo": algo})
                    TransactionService._log_audit(session, pqc_tx.id, TransactionState.VALIDATED.value, "success", {"algo": algo})
                    TransactionService._log_audit(session, pqc_tx.id, TransactionState.CRYPTO_PROCESSED.value, "success", {"algo": algo})
                    TransactionService._log_audit(session, pqc_tx.id, TransactionState.COMMITTED.value, "success", {"algo": algo})
                    
                    final_pqc_status = "success" if pqc_result["verified"] else "failed"
                    TransactionService._log_audit(session, pqc_tx.id, TransactionState.SETTLED.value if pqc_result["verified"] else TransactionState.FAILED.value, final_pqc_status, {"algo": algo})

                    pqc_entries[algo] = pqc_tx

                    if not pqc_result["verified"]:
                        AnalyticsService.log_security_event(
                            event_type="decryption_failure",
                            algorithm=pqc_result["method"],
                            sender=sender,
                            receiver=receiver,
                            error_message=f"{algo} verification failed",
                            latency_ms=pqc_result["total_ms"],
                            auto_commit=False,
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("PQC encrypt_transaction (%s) failed: %s", algo, exc)
                    AnalyticsService.log_security_event(
                        event_type="encryption_failure",
                        algorithm=algo,
                        sender=sender,
                        receiver=receiver,
                        error_message=str(exc),
                        auto_commit=False,
                    )
        else:
            pqc_error = "liboqs not installed — PQC processing skipped"

        session.commit()

        # --- Build response -----------------------------------------------
        response: dict = {
            "classical": classical_tx.to_dict(),
        }

        if pqc_error:
            response["pqc_error"] = pqc_error
        else:
            for algo, resp_key in _PQC_RESPONSE_KEYS.items():
                if algo in pqc_entries:
                    response[resp_key] = pqc_entries[algo].to_dict()

        pqc_ids = [
            f"{algo}={pqc_entries[algo].id}" if algo in pqc_entries else f"{algo}=N/A"
            for algo in pqc_mod.KEM_ALGORITHMS
        ]
        logger.info(
            "Transaction processed — classical id=%s, %s",
            classical_tx.id,
            ", ".join(pqc_ids),
        )

        # --- Publish to SSE subscribers (server dashboard) ------------------
        EventBus.publish({
            "type":   "transaction",
            "source": "server",
            "data":   response,
        })

        # --- Push to target client via per-client SSE ----------------------
        receiver_client_id = data.get("account_id_to", "")
        if receiver_client_id:
            try:
                from app.services.notification_service import NotificationService
                NotificationService.push_to_client(
                    receiver_client_id,
                    {
                        "type":   "transaction",
                        "source": "server",
                        "data":   response,
                    },
                )
            except Exception as exc:
                logger.warning("SSE push to client %s failed: %s", receiver_client_id, exc)

        return response

    # ------------------------------------------------------------------
    # Metrics / aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def get_metrics(session=None, method: str = None, limit: int = 100) -> dict:
        """
        Return aggregated performance metrics from recent transactions.

        Args:
            session: Optional SQLAlchemy session. Falls back to
                     ``db.session`` when ``None``.
            method:  Filter by crypto method (``"RSA-2048"``,
                     ``"ML-KEM-512"``, ``"ML-KEM-768"``,
                     ``"ML-KEM-1024"``).  ``None`` returns all.
            limit:   Max number of recent transactions to aggregate.

        Returns:
            dict with ``classical`` and/or ``pqc_512``, ``pqc_768``,
            ``pqc_1024`` sub-dicts containing ``count``,
            ``avg_key_gen_ms``, ``avg_encrypt_ms``, ``avg_decrypt_ms``,
            ``avg_total_ms``, and ``avg_ciphertext_size_bytes``.
        """
        if session is None:
            session = db.session

        logger.debug("Aggregating metrics for method=%s, limit=%s", method, limit)

        result: dict = {}

        # Method label mapping
        _label_map = {
            "RSA-2048": "classical",
            "ML-KEM-512": "pqc_512",
            "ML-KEM-768": "pqc_768",
            "ML-KEM-1024": "pqc_1024",
        }

        methods = (
            [method] if method else list(_label_map.keys())
        )

        for m in methods:
            rows = (
                session.query(Transaction)
                .filter(Transaction.crypto_method == m)
                .order_by(Transaction.timestamp.desc())
                .limit(limit)
                .all()
            )

            label = _label_map.get(m, m)

            if not rows:
                result[label] = {
                    "count": 0,
                    "avg_key_gen_ms": 0,
                    "avg_encapsulate_ms": None,
                    "avg_encrypt_ms": 0,
                    "avg_decapsulate_ms": None,
                    "avg_decrypt_ms": 0,
                    "avg_total_ms": 0,
                    "avg_key_size_bytes": 0,
                    "avg_secret_key_bytes": 0,
                    "avg_ciphertext_size_bytes": 0,
                    "key_material_footprint_bytes": 0,
                    "payload_overhead_ratio": 0,
                }
                continue

            count = len(rows)
            pqc_rows = [r for r in rows if r.encapsulate_time_ms is not None]
            pqc_count = len(pqc_rows) or 1  # avoid ZeroDivisionError

            avg_pub_key = round(sum(r.key_size_bytes for r in rows) / count, 2)
            avg_secret_key = round(
                sum(r.secret_key_bytes for r in pqc_rows if r.secret_key_bytes) / pqc_count, 2
            ) if pqc_rows else 0
            avg_ct = round(sum(r.ciphertext_size_bytes for r in rows) / count, 2)

            result[label] = {
                "count": count,
                "avg_key_gen_ms": round(
                    sum(r.key_gen_time_ms for r in rows) / count, 4
                ),
                "avg_encapsulate_ms": round(
                    sum(r.encapsulate_time_ms for r in pqc_rows) / pqc_count, 4
                ) if pqc_rows else None,
                "avg_encrypt_ms": round(
                    sum(r.encrypt_time_ms for r in rows) / count, 4
                ),
                "avg_decapsulate_ms": round(
                    sum(r.decapsulate_time_ms for r in pqc_rows) / pqc_count, 4
                ) if pqc_rows else None,
                "avg_decrypt_ms": round(
                    sum(r.decrypt_time_ms for r in rows) / count, 4
                ),
                "avg_total_ms": round(
                    sum(r.total_time_ms for r in rows) / count, 4
                ),
                # Key sizes
                "avg_key_size_bytes": avg_pub_key,
                "avg_secret_key_bytes": avg_secret_key,
                "avg_ciphertext_size_bytes": avg_ct,
                # Derived: key material footprint (public + secret)
                "key_material_footprint_bytes": round(avg_pub_key + avg_secret_key, 2),
                # Derived: ratio of KEM ciphertext to AES-GCM output overhead (28 B fixed)
                "payload_overhead_ratio": round(avg_ct / 28.0, 2),
            }

        return result
