"""
Transaction service — business logic for processing transactions.

Orchestrates cryptographic operations (both classical and PQC),
stores results in the database, and returns comparison data.
"""

import json

from app import db
from app.crypto import classical
from app.crypto import pqc as pqc_mod
from app.models.transaction import Transaction
from app.utils.logger import logger


class TransactionService:
    """Encapsulates all transaction-processing logic."""

    # ------------------------------------------------------------------
    # Core: process a transaction through both crypto pipelines
    # ------------------------------------------------------------------

    @staticmethod
    def process_transaction(data: dict, session=None) -> dict:
        """
        Accept a transaction payload, encrypt with **both** classical and PQC
        methods, persist the results, and return a comparison dict.

        Args:
            data: dict with keys ``amount``, ``sender``, ``receiver``,
                  and optionally ``currency`` (default ``"INR"``).
            session: Optional SQLAlchemy session. Falls back to
                     ``db.session`` when ``None``.

        Returns:
            dict with ``classical``, ``pqc`` (or ``pqc_error``), and the
            serialised transaction payload that was encrypted.
        """
        if session is None:
            session = db.session

        amount = data.get("amount", 0)
        sender = data.get("sender", "")
        receiver = data.get("receiver", "")
        currency = data.get("currency", "INR")

        logger.debug("Processing transaction for %s -> %s (amount: %s %s)", sender, receiver, amount, currency)

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
            status="success" if classical_result["verified"] else "failed",
        )
        session.add(classical_tx)

        # --- PQC (ML-KEM-768) --------------------------------------------
        pqc_entry = None
        pqc_error = None

        if pqc_mod.PQC_AVAILABLE:
            try:
                pqc_result = pqc_mod.encrypt_transaction(payload)
                pqc_entry = Transaction(
                    amount=amount,
                    sender=sender,
                    receiver=receiver,
                    currency=currency,
                    crypto_method=pqc_result["method"],
                    key_gen_time_ms=pqc_result["key_gen_ms"],
                    encrypt_time_ms=pqc_result["encrypt_ms"],
                    decrypt_time_ms=pqc_result["decrypt_ms"],
                    total_time_ms=pqc_result["total_ms"],
                    key_size_bytes=pqc_result["public_key_bytes"],
                    ciphertext_size_bytes=pqc_result["ciphertext_bytes"],
                    status=(
                        "success" if pqc_result["verified"] else "failed"
                    ),
                )
                session.add(pqc_entry)
            except Exception as exc:  # noqa: BLE001
                pqc_error = str(exc)
                logger.warning("PQC encrypt_transaction failed: %s", exc)
        else:
            pqc_error = "liboqs not installed — PQC processing skipped"

        session.commit()

        # --- Build response -----------------------------------------------
        response: dict = {
            "classical": classical_tx.to_dict(),
        }

        if pqc_entry is not None:
            response["pqc"] = pqc_entry.to_dict()
        else:
            response["pqc_error"] = pqc_error

        logger.info(
            "Transaction processed — classical id=%s, pqc id=%s",
            classical_tx.id,
            pqc_entry.id if pqc_entry else "N/A",
        )

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
            method:  Filter by crypto method (``"RSA-2048"`` or
                     ``"ML-KEM-768"``).  ``None`` returns both.
            limit:   Max number of recent transactions to aggregate.

        Returns:
            dict with ``classical`` and/or ``pqc`` sub-dicts containing
            ``count``, ``avg_key_gen_ms``, ``avg_encrypt_ms``,
            ``avg_decrypt_ms``, ``avg_total_ms``, and
            ``avg_ciphertext_size_bytes``.
        """
        if session is None:
            session = db.session

        logger.debug("Aggregating metrics for method=%s, limit=%s", method, limit)

        result: dict = {}

        methods = (
            [method] if method else ["RSA-2048", "ML-KEM-768"]
        )

        for m in methods:
            rows = (
                session.query(Transaction)
                .filter(Transaction.crypto_method == m)
                .order_by(Transaction.timestamp.desc())
                .limit(limit)
                .all()
            )

            if not rows:
                label = "classical" if m == "RSA-2048" else "pqc"
                result[label] = {
                    "count": 0,
                    "avg_key_gen_ms": 0,
                    "avg_encrypt_ms": 0,
                    "avg_decrypt_ms": 0,
                    "avg_total_ms": 0,
                    "avg_ciphertext_size_bytes": 0,
                }
                continue

            count = len(rows)
            label = "classical" if m == "RSA-2048" else "pqc"
            result[label] = {
                "count": count,
                "avg_key_gen_ms": round(
                    sum(r.key_gen_time_ms for r in rows) / count, 4
                ),
                "avg_encrypt_ms": round(
                    sum(r.encrypt_time_ms for r in rows) / count, 4
                ),
                "avg_decrypt_ms": round(
                    sum(r.decrypt_time_ms for r in rows) / count, 4
                ),
                "avg_total_ms": round(
                    sum(r.total_time_ms for r in rows) / count, 4
                ),
                "avg_ciphertext_size_bytes": round(
                    sum(r.ciphertext_size_bytes for r in rows) / count, 2
                ),
            }

        return result
