from __future__ import annotations
"""Analytics service for advanced security and migration dashboard metrics."""

from datetime import datetime, timedelta, timezone, date
import math

from app import db
from app.models.transaction import Transaction
from app.models.key_metadata import KeyMetadata
from app.models.daily_migration_snapshot import DailyMigrationSnapshot
from app.models.security_event import SecurityEvent
from app.models.anomaly import Anomaly
from app.utils.logger import logger


class AnalyticsService:
    """Service layer for analytics endpoints added in dashboard enhancement."""

    METHOD_RSA = "RSA-2048"
    METHOD_MLKEM_512 = "ML-KEM-512"
    METHOD_MLKEM = "ML-KEM-768"
    METHOD_MLKEM_1024 = "ML-KEM-1024"
    ALL_PQC_METHODS = [METHOD_MLKEM_512, METHOD_MLKEM, METHOD_MLKEM_1024]

    @staticmethod
    def parse_time_window(window: str | None) -> timedelta:
        """Parse strings like 1h, 24h, 7d, 30d into timedelta."""
        if not window:
            return timedelta(hours=24)

        try:
            value = int(window[:-1])
            unit = window[-1].lower()
        except (ValueError, IndexError):
            return timedelta(hours=24)

        if unit == "h":
            return timedelta(hours=value)
        if unit == "d":
            return timedelta(days=value)
        return timedelta(hours=24)

    @staticmethod
    def _normalize_algorithm(algorithm: str | None) -> str | None:
        if not algorithm:
            return None
        value = algorithm.strip().upper()
        if value in {"RSA", "RSA-2048"}:
            return AnalyticsService.METHOD_RSA
        if value in {"ML-KEM-512", "MLKEM-512", "MLKEM512"}:
            return AnalyticsService.METHOD_MLKEM_512
        if value in {"ML-KEM", "ML-KEM-768", "MLKEM", "KYBER", "MLKEM-768", "MLKEM768"}:
            return AnalyticsService.METHOD_MLKEM
        if value in {"ML-KEM-1024", "MLKEM-1024", "MLKEM1024"}:
            return AnalyticsService.METHOD_MLKEM_1024
        return algorithm

    @staticmethod
    def _percentile(sorted_values: list[float], p: float) -> float:
        if not sorted_values:
            return 0.0
        index = max(0, math.ceil(len(sorted_values) * p) - 1)
        index = min(index, len(sorted_values) - 1)
        return float(sorted_values[index])

    @staticmethod
    def _format_trend(current: float, previous: float) -> str:
        if previous <= 0:
            return "0.0%"
        delta = ((current - previous) / previous) * 100.0
        prefix = "+" if delta > 0 else ""
        return f"{prefix}{delta:.1f}%"

    @staticmethod
    def _window_bounds(time_window: str | None) -> tuple[datetime, datetime, datetime]:
        now = datetime.now(timezone.utc)
        delta = AnalyticsService.parse_time_window(time_window)
        start = now - delta
        prev_start = start - delta
        return now, start, prev_start

    @staticmethod
    def _latency_rows(algorithm: str | None, start: datetime, end: datetime) -> list[float]:
        query = db.session.query(Transaction.total_time_ms).filter(
            Transaction.timestamp >= start,
            Transaction.timestamp < end,
        )
        if algorithm:
            query = query.filter(Transaction.crypto_method == algorithm)

        values = [float(r[0]) for r in query.order_by(Transaction.total_time_ms.asc()).all() if r[0] is not None]
        return values

    @staticmethod
    def get_latency_percentiles(algorithm: str | None = None, time_window: str = "24h") -> dict:
        """Return p50/p95/p99 latency and trend for selected algorithm and window."""
        algorithm = AnalyticsService._normalize_algorithm(algorithm)
        now, start, prev_start = AnalyticsService._window_bounds(time_window)

        current_values = AnalyticsService._latency_rows(algorithm, start, now)
        prev_values = AnalyticsService._latency_rows(algorithm, prev_start, start)

        p50 = AnalyticsService._percentile(current_values, 0.50)
        p95 = AnalyticsService._percentile(current_values, 0.95)
        p99 = AnalyticsService._percentile(current_values, 0.99)
        prev_p95 = AnalyticsService._percentile(prev_values, 0.95)

        return {
            "algorithm": algorithm or "all",
            "time_window": time_window,
            "samples": len(current_values),
            "p50_ms": round(p50, 4) if current_values else None,
            "p95_ms": round(p95, 4) if current_values else None,
            "p99_ms": round(p99, 4) if current_values else None,
            "trend_p95": AnalyticsService._format_trend(p95, prev_p95),
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def _count_by_method(start: datetime, end: datetime) -> tuple[int, int, int]:
        """Return (total, rsa_count, combined_pqc_count) for migration tracking."""
        total = (
            db.session.query(Transaction)
            .filter(Transaction.timestamp >= start, Transaction.timestamp < end)
            .count()
        )
        rsa = (
            db.session.query(Transaction)
            .filter(
                Transaction.timestamp >= start,
                Transaction.timestamp < end,
                Transaction.crypto_method == AnalyticsService.METHOD_RSA,
            )
            .count()
        )
        # Combine all ML-KEM variants for migration percentage
        mlkem = (
            db.session.query(Transaction)
            .filter(
                Transaction.timestamp >= start,
                Transaction.timestamp < end,
                Transaction.crypto_method.in_(AnalyticsService.ALL_PQC_METHODS),
            )
            .count()
        )
        return total, rsa, mlkem

    @staticmethod
    def _upsert_daily_snapshot(target_date: date) -> None:
        day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        total, rsa, mlkem = AnalyticsService._count_by_method(day_start, day_end)

        row = (
            db.session.query(DailyMigrationSnapshot)
            .filter(DailyMigrationSnapshot.snapshot_date == target_date)
            .first()
        )
        if row is None:
            row = DailyMigrationSnapshot(snapshot_date=target_date)
            db.session.add(row)

        row.rsa_count = rsa
        row.mlkem_count = mlkem
        row.hybrid_count = 0
        row.total_count = total

    @staticmethod
    def get_migration_status(time_window: str = "24h") -> dict:
        """Return adoption percentages and days-to-target estimate for ML-KEM."""
        now, start, prev_start = AnalyticsService._window_bounds(time_window)
        delta = AnalyticsService.parse_time_window(time_window)
        days = max(delta.total_seconds() / 86400.0, 1.0)

        total, rsa, mlkem = AnalyticsService._count_by_method(start, now)
        prev_total, _, prev_mlkem = AnalyticsService._count_by_method(prev_start, start)

        total_safe = total if total > 0 else 1
        prev_total_safe = prev_total if prev_total > 0 else 1

        rsa_pct = (rsa / total_safe) * 100.0
        mlkem_pct = (mlkem / total_safe) * 100.0
        prev_mlkem_pct = (prev_mlkem / prev_total_safe) * 100.0

        growth_pct_points = (mlkem_pct - prev_mlkem_pct) / days
        target = 80.0
        if growth_pct_points > 0 and mlkem_pct < target:
            days_to_target = math.ceil((target - mlkem_pct) / growth_pct_points)
        else:
            days_to_target = None

        status = "on_track" if growth_pct_points >= 2 else "at_risk"
        if 0 < growth_pct_points < 2:
            status = "slow"
        if mlkem_pct >= target:
            status = "target_reached"

        # Maintain daily snapshot for trending
        AnalyticsService._upsert_daily_snapshot(now.date())
        db.session.commit()

        # Return latest 30 snapshots for charting
        snapshots = (
            db.session.query(DailyMigrationSnapshot)
            .order_by(DailyMigrationSnapshot.snapshot_date.desc())
            .limit(30)
            .all()
        )
        trend = [
            {
                "date": s.snapshot_date.isoformat(),
                "rsa_count": s.rsa_count,
                "mlkem_count": s.mlkem_count,
                "total_count": s.total_count,
                "rsa_percentage": round((s.rsa_count / (s.total_count or 1)) * 100, 2),
                "mlkem_percentage": round((s.mlkem_count / (s.total_count or 1)) * 100, 2),
            }
            for s in reversed(snapshots)
        ]

        return {
            "time_window": time_window,
            "total_transactions": total,
            "rsa_count": rsa,
            "mlkem_count": mlkem,
            "hybrid_count": 0,
            "rsa_percentage": round(rsa_pct, 2),
            "mlkem_percentage": round(mlkem_pct, 2),
            "hybrid_percentage": 0,
            "mlkem_daily_growth": f"{growth_pct_points:+.2f}%",
            "migration_target": int(target),
            "days_to_target": days_to_target,
            "status": status,
            "trend": trend,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def log_security_event(
        event_type: str,
        algorithm: str | None = None,
        sender: str | None = None,
        receiver: str | None = None,
        error_message: str | None = None,
        latency_ms: float | None = None,
        auto_commit: bool = True,
    ) -> None:
        """Persist a security event row (best effort)."""
        try:
            row = SecurityEvent(
                event_type=event_type,
                algorithm=AnalyticsService._normalize_algorithm(algorithm),
                sender=sender,
                receiver=receiver,
                error_message=error_message,
                latency_ms=latency_ms,
            )
            db.session.add(row)
            if auto_commit:
                db.session.commit()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            logger.warning("Failed to log security event: %s", exc)

    @staticmethod
    def get_rotation_health() -> dict:
        """Return key rotation health score and status breakdown."""
        now = datetime.now(timezone.utc)
        keys = (
            db.session.query(KeyMetadata)
            .filter(KeyMetadata.status.in_(["active", "pending_rotation"]))
            .all()
        )

        total = len(keys)
        if total == 0:
            return {
                "total_keys": 0,
                "keys_active": 0,
                "keys_pending_rotation": 0,
                "keys_overdue_rotation": 0,
                "avg_age_days": 0,
                "avg_days_until_rotation": 0,
                "overdue_percentage": 0,
                "compliance_score": 100,
                "health_status": "excellent",
                "next_rotation_date": None,
                "keys_by_algorithm": {
                    AnalyticsService.METHOD_RSA: {"active": 0, "pending": 0, "overdue": 0},
                    AnalyticsService.METHOD_MLKEM_512: {"active": 0, "pending": 0, "overdue": 0},
                    AnalyticsService.METHOD_MLKEM: {"active": 0, "pending": 0, "overdue": 0},
                    AnalyticsService.METHOD_MLKEM_1024: {"active": 0, "pending": 0, "overdue": 0},
                },
                "timestamp": now.isoformat(),
            }

        active_count = 0
        pending_count = 0
        overdue_count = 0
        age_days_total = 0.0
        days_until_total = 0.0
        next_rotation = None

        by_algo = {
            AnalyticsService.METHOD_RSA: {"active": 0, "pending": 0, "overdue": 0},
            AnalyticsService.METHOD_MLKEM_512: {"active": 0, "pending": 0, "overdue": 0},
            AnalyticsService.METHOD_MLKEM: {"active": 0, "pending": 0, "overdue": 0},
            AnalyticsService.METHOD_MLKEM_1024: {"active": 0, "pending": 0, "overdue": 0},
        }

        for key in keys:
            created = key.created_at or now
            # Ensure timezone-aware (SQLite stores naive datetimes)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            due = key.rotation_due_at or (created + timedelta(days=90))
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)

            age_days = (now - created).total_seconds() / 86400.0
            days_until = (due - now).total_seconds() / 86400.0
            age_days_total += age_days
            days_until_total += days_until

            algorithm = key.algorithm if key.algorithm in by_algo else AnalyticsService.METHOD_RSA
            by_algo.setdefault(algorithm, {"active": 0, "pending": 0, "overdue": 0})

            if due < now:
                overdue_count += 1
                by_algo[algorithm]["overdue"] += 1
            elif key.status == "pending_rotation" or days_until <= 7:
                pending_count += 1
                by_algo[algorithm]["pending"] += 1
            else:
                active_count += 1
                by_algo[algorithm]["active"] += 1

            if next_rotation is None or due < next_rotation:
                next_rotation = due

        score = 100.0
        score -= (overdue_count / total) * 30.0
        score -= (pending_count / total) * 10.0
        avg_age = age_days_total / total
        if avg_age > 60:
            score -= max(0.0, ((avg_age - 60.0) / 60.0) * 20.0)
        score = max(0.0, round(score, 1))

        if score >= 95:
            health_status = "excellent"
        elif score >= 85:
            health_status = "good"
        elif score >= 70:
            health_status = "fair"
        else:
            health_status = "critical"

        return {
            "total_keys": total,
            "keys_active": active_count,
            "keys_pending_rotation": pending_count,
            "keys_overdue_rotation": overdue_count,
            "avg_age_days": round(avg_age, 1),
            "avg_days_until_rotation": round(days_until_total / total, 1),
            "overdue_percentage": round((overdue_count / total) * 100.0, 2),
            "compliance_score": score,
            "health_status": health_status,
            "next_rotation_date": next_rotation.date().isoformat() if next_rotation else None,
            "keys_by_algorithm": by_algo,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def get_key_age_distribution() -> dict:
        """Return key-age histogram buckets for rotation diagnostics."""
        now = datetime.now(timezone.utc)
        keys = db.session.query(KeyMetadata).all()

        buckets = {
            "0-30_days": 0,
            "30-60_days": 0,
            "60-90_days": 0,
            "90-120_days": 0,
            "120+_days": 0,
        }

        if not keys:
            return {
                **buckets,
                "median_age_days": 0,
                "timestamp": now.isoformat(),
            }

        ages = []
        for key in keys:
            created = key.created_at or now
            age_days = max(0.0, (now - created).total_seconds() / 86400.0)
            ages.append(age_days)

            if age_days < 30:
                buckets["0-30_days"] += 1
            elif age_days < 60:
                buckets["30-60_days"] += 1
            elif age_days < 90:
                buckets["60-90_days"] += 1
            elif age_days < 120:
                buckets["90-120_days"] += 1
            else:
                buckets["120+_days"] += 1

        ages_sorted = sorted(ages)
        median_idx = len(ages_sorted) // 2
        if len(ages_sorted) % 2 == 0:
            median_age = (ages_sorted[median_idx - 1] + ages_sorted[median_idx]) / 2
        else:
            median_age = ages_sorted[median_idx]

        return {
            **buckets,
            "median_age_days": round(median_age, 2),
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def _algo_stats(method: str, start: datetime, end: datetime) -> dict:
        rows = (
            db.session.query(Transaction)
            .filter(
                Transaction.crypto_method == method,
                Transaction.timestamp >= start,
                Transaction.timestamp < end,
            )
            .all()
        )
        if not rows:
            return {
                "samples": 0,
                "avg_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "avg_key_size_b": 0.0,
                "avg_cipher_size_b": 0.0,
            }

        latencies = sorted([r.total_time_ms for r in rows])
        key_sizes = [r.key_size_bytes for r in rows]
        c_sizes = [r.ciphertext_size_bytes for r in rows]

        return {
            "samples": len(rows),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 4),
            "p99_latency_ms": round(AnalyticsService._percentile(latencies, 0.99), 4),
            "min_latency_ms": round(min(latencies), 4),
            "max_latency_ms": round(max(latencies), 4),
            "avg_key_size_b": round(sum(key_sizes) / len(key_sizes), 2),
            "avg_cipher_size_b": round(sum(c_sizes) / len(c_sizes), 2),
        }

    @staticmethod
    def get_algorithm_comparison(time_window: str = "24h") -> dict:
        """Return side-by-side algorithm comparison ratios and verdicts."""
        now, start, _ = AnalyticsService._window_bounds(time_window)
        delta_seconds = max(1.0, AnalyticsService.parse_time_window(time_window).total_seconds())

        rsa = AnalyticsService._algo_stats(AnalyticsService.METHOD_RSA, start, now)
        mlkem_512 = AnalyticsService._algo_stats(AnalyticsService.METHOD_MLKEM_512, start, now)
        mlkem_768 = AnalyticsService._algo_stats(AnalyticsService.METHOD_MLKEM, start, now)
        mlkem_1024 = AnalyticsService._algo_stats(AnalyticsService.METHOD_MLKEM_1024, start, now)

        # Use ML-KEM-768 as the primary comparison baseline against RSA
        rsa_avg = rsa["avg_latency_ms"]
        ml_avg = mlkem_768["avg_latency_ms"]
        latency_delta = ((ml_avg - rsa_avg) / rsa_avg * 100.0) if rsa_avg else 0.0

        rsa_p99 = rsa["p99_latency_ms"]
        ml_p99 = mlkem_768["p99_latency_ms"]
        p99_delta = ((ml_p99 - rsa_p99) / rsa_p99 * 100.0) if rsa_p99 else 0.0

        rsa_key = rsa["avg_key_size_b"]
        ml_key = mlkem_768["avg_key_size_b"]
        size_delta = ((ml_key - rsa_key) / rsa_key * 100.0) if rsa_key else 0.0

        throughput_rsa = rsa["samples"] / delta_seconds
        throughput_ml = mlkem_768["samples"] / delta_seconds
        throughput_delta = (
            ((throughput_ml - throughput_rsa) / throughput_rsa) * 100.0
            if throughput_rsa else 0.0
        )

        if latency_delta < -5:
            latency_verdict = f"ML-KEM-768 is {abs(latency_delta):.1f}% faster"
        elif latency_delta > 5:
            latency_verdict = f"RSA-2048 is {latency_delta:.1f}% faster"
        else:
            latency_verdict = "Similar latency"

        if throughput_delta > 10:
            throughput_verdict = f"ML-KEM handles {throughput_delta:.1f}% more tx/sec"
        elif throughput_delta < -10:
            throughput_verdict = f"RSA-2048 handles {abs(throughput_delta):.1f}% more tx/sec"
        else:
            throughput_verdict = "Similar throughput"

        recommendation = (
            "ML-KEM superior in speed and throughput; accept larger keys for quantum safety"
            if latency_delta <= 0 and throughput_delta >= 0
            else "Performance is mixed; prefer ML-KEM for quantum safety and monitor bandwidth impact"
        )

        rsa_out = dict(rsa)
        rsa_out["throughput_tx_per_sec"] = round(throughput_rsa, 4)
        ml768_out = dict(mlkem_768)
        ml768_out["throughput_tx_per_sec"] = round(throughput_ml, 4)
        ml512_out = dict(mlkem_512)
        ml512_out["throughput_tx_per_sec"] = round(mlkem_512["samples"] / delta_seconds, 4)
        ml1024_out = dict(mlkem_1024)
        ml1024_out["throughput_tx_per_sec"] = round(mlkem_1024["samples"] / delta_seconds, 4)

        return {
            "time_window": time_window,
            "comparison_date": now.date().isoformat(),
            "rsa_2048": rsa_out,
            "ml_kem_512": ml512_out,
            "ml_kem": ml768_out,
            "ml_kem_1024": ml1024_out,
            "comparison": {
                "latency_delta_pct": round(latency_delta, 2),
                "latency_verdict": latency_verdict,
                "p99_delta_pct": round(p99_delta, 2),
                "size_delta_pct": round(size_delta, 2),
                "throughput_delta_pct": round(throughput_delta, 2),
                "throughput_verdict": throughput_verdict,
                "recommendation": recommendation,
            },
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def get_security_health(time_window: str = "24h", algorithm: str | None = None) -> dict:
        """Return failure/rejection rates and status for selected window."""
        algorithm = AnalyticsService._normalize_algorithm(algorithm)
        now, start, _ = AnalyticsService._window_bounds(time_window)

        tx_query = db.session.query(Transaction).filter(
            Transaction.timestamp >= start,
            Transaction.timestamp < now,
        )
        if algorithm:
            tx_query = tx_query.filter(Transaction.crypto_method == algorithm)

        total_attempts = tx_query.count()
        successful = tx_query.filter(Transaction.status == "success").count()

        ev_query = db.session.query(SecurityEvent).filter(
            SecurityEvent.timestamp >= start,
            SecurityEvent.timestamp < now,
        )
        if algorithm:
            ev_query = ev_query.filter(SecurityEvent.algorithm == algorithm)

        failed_crypto = ev_query.filter(SecurityEvent.event_type.in_(["decryption_failure", "encryption_failure", "internal_error"])).count()
        failed_validation = ev_query.filter(SecurityEvent.event_type.in_(["validation_error", "validation_failed"])).count()
        rejected_policy = ev_query.filter(SecurityEvent.event_type == "policy_rejected").count()

        denom = total_attempts if total_attempts > 0 else 1
        failure_rate = ((failed_crypto + failed_validation) / denom) * 100.0
        rejection_rate = (rejected_policy / denom) * 100.0

        alerts = []
        status = "healthy"
        if failure_rate > 5:
            status = "critical"
            alerts.append("High failure rate detected")
        elif failure_rate > 1:
            status = "warning"
            alerts.append("Elevated failure rate")

        if rejection_rate > 2:
            alerts.append("Policy rejections elevated")

        return {
            "time_window": time_window,
            "algorithm": algorithm or "all",
            "total_attempts": total_attempts,
            "successful": successful,
            "failed_crypto": failed_crypto,
            "failed_validation": failed_validation,
            "rejected_policy": rejected_policy,
            "failure_rate_pct": round(failure_rate, 4),
            "rejection_rate_pct": round(rejection_rate, 4),
            "status": status,
            "alerts": alerts,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def _severity_from_delta(anomaly_type: str, delta_pct: float, duration_minutes: int = 0) -> str:
        severity = "info"
        if delta_pct > 50:
            severity = "warning"
        if delta_pct > 100 or (anomaly_type == "failure_rate_spike" and delta_pct > 200):
            severity = "critical"
        if duration_minutes > 5 and severity == "warning":
            severity = "critical"
        return severity

    @staticmethod
    def _store_anomaly(
        anomaly_type: str,
        metric_name: str,
        baseline: float,
        current: float,
        delta_pct: float,
        description: str,
        severity: str,
    ) -> None:
        # deduplicate near-term duplicates (same type unresolved within 15 min)
        since = datetime.now(timezone.utc) - timedelta(minutes=15)
        existing = (
            db.session.query(Anomaly)
            .filter(
                Anomaly.anomaly_type == anomaly_type,
                Anomaly.resolved.is_(False),
                Anomaly.detected_at >= since,
            )
            .first()
        )
        if existing:
            return

        row = Anomaly(
            anomaly_type=anomaly_type,
            severity=severity,
            metric_name=metric_name,
            baseline_value=baseline,
            current_value=current,
            delta_pct=delta_pct,
            description=description,
        )
        db.session.add(row)

    @staticmethod
    def get_anomalies() -> dict:
        """Detect and return unresolved anomalies with severity ordering."""
        now = datetime.now(timezone.utc)
        cur_start = now - timedelta(minutes=5)
        base_start = now - timedelta(minutes=60)
        base_end = cur_start

        detected = []

        # 1) Latency spike (p95)
        cur_vals = AnalyticsService._latency_rows(None, cur_start, now)
        base_vals = AnalyticsService._latency_rows(None, base_start, base_end)
        cur_p95 = AnalyticsService._percentile(cur_vals, 0.95)
        base_p95 = AnalyticsService._percentile(base_vals, 0.95)
        if base_p95 > 0 and cur_p95 > base_p95 * 1.3:
            delta = ((cur_p95 - base_p95) / base_p95) * 100.0
            sev = AnalyticsService._severity_from_delta("latency_spike", delta)
            desc = "Latency spike detected in p95 response time"
            AnalyticsService._store_anomaly(
                anomaly_type="latency_spike",
                metric_name="p95_latency_ms",
                baseline=base_p95,
                current=cur_p95,
                delta_pct=delta,
                description=desc,
                severity=sev,
            )
            detected.append({
                "type": "latency_spike",
                "severity": sev,
                "metric": "p95_latency_ms",
                "baseline": round(base_p95, 4),
                "current": round(cur_p95, 4),
                "delta_pct": round(delta, 2),
                "detected_at": now.isoformat(),
                "duration_minutes": 5,
                "recommendation": "Check infrastructure load and key-rotation events",
            })

        # 2) Failure rate spike
        cur_health = AnalyticsService.get_security_health("1h")
        # baseline prior hour approximation
        prev_now = cur_start
        prev_start = prev_now - timedelta(hours=1)

        prev_total = (
            db.session.query(Transaction)
            .filter(Transaction.timestamp >= prev_start, Transaction.timestamp < prev_now)
            .count()
        )
        prev_events = (
            db.session.query(SecurityEvent)
            .filter(SecurityEvent.timestamp >= prev_start, SecurityEvent.timestamp < prev_now)
            .count()
        )
        prev_failure_rate = ((prev_events / prev_total) * 100.0) if prev_total > 0 else 0.0
        cur_failure_rate = float(cur_health["failure_rate_pct"])

        if prev_failure_rate > 0 and cur_failure_rate > prev_failure_rate * 2:
            delta = ((cur_failure_rate - prev_failure_rate) / prev_failure_rate) * 100.0
            sev = AnalyticsService._severity_from_delta("failure_rate_spike", delta)
            desc = "Failure rate spike detected"
            AnalyticsService._store_anomaly(
                anomaly_type="failure_rate_spike",
                metric_name="failure_rate_pct",
                baseline=prev_failure_rate,
                current=cur_failure_rate,
                delta_pct=delta,
                description=desc,
                severity=sev,
            )
            detected.append({
                "type": "failure_rate_spike",
                "severity": sev,
                "metric": "failure_rate_pct",
                "baseline": round(prev_failure_rate, 4),
                "current": round(cur_failure_rate, 4),
                "delta_pct": round(delta, 2),
                "detected_at": now.isoformat(),
                "affected_algorithm": "all",
                "recommendation": "Investigate crypto failures and validation errors",
            })

        # 3) Algorithm shift
        current_total, _, current_ml = AnalyticsService._count_by_method(cur_start, now)
        base_total, _, base_ml = AnalyticsService._count_by_method(base_start, base_end)
        current_ml_pct = (current_ml / (current_total or 1)) * 100.0
        base_ml_pct = (base_ml / (base_total or 1)) * 100.0
        shift_delta = abs(current_ml_pct - base_ml_pct)
        if base_total > 0 and shift_delta > 40:
            sev = AnalyticsService._severity_from_delta("algorithm_shift", shift_delta)
            desc = "Unusual shift in RSA/ML-KEM traffic ratio"
            AnalyticsService._store_anomaly(
                anomaly_type="algorithm_shift",
                metric_name="mlkem_percentage",
                baseline=base_ml_pct,
                current=current_ml_pct,
                delta_pct=shift_delta,
                description=desc,
                severity=sev,
            )
            detected.append({
                "type": "algorithm_shift",
                "severity": sev,
                "metric": "mlkem_percentage",
                "baseline": round(base_ml_pct, 2),
                "current": round(current_ml_pct, 2),
                "delta_pct": round(shift_delta, 2),
                "detected_at": now.isoformat(),
                "recommendation": "Review routing policy and client algorithm negotiation",
            })

        db.session.commit()

        unresolved = (
            db.session.query(Anomaly)
            .filter(Anomaly.resolved.is_(False))
            .order_by(Anomaly.detected_at.desc())
            .limit(10)
            .all()
        )

        payload = []
        for a in unresolved:
            payload.append({
                "anomaly_id": a.anomaly_id,
                "type": a.anomaly_type,
                "severity": a.severity,
                "metric": a.metric_name,
                "baseline": a.baseline_value,
                "current": a.current_value,
                "delta_pct": a.delta_pct,
                "description": a.description,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
            })

        health_status = "healthy"
        if any(a["severity"] == "critical" for a in payload):
            health_status = "attention_required"
        elif any(a["severity"] == "warning" for a in payload):
            health_status = "watch"

        return {
            "detected_anomalies": payload,
            "newly_detected": detected,
            "health_status": health_status,
            "timestamp": now.isoformat(),
        }
