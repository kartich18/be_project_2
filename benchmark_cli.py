#!/usr/bin/env python3
"""
Standalone benchmark CLI — run cryptographic comparisons and export reports.

Usage:
    python benchmark_cli.py                         # 100 iterations, output to docs/
    python benchmark_cli.py --iterations 500        # custom count
    python benchmark_cli.py --output results/       # custom output directory
    python benchmark_cli.py --format json           # json only (json/csv/both)
"""

import argparse
import csv
import json
import os
import sys

# Ensure the project root is on sys.path so `app` is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.crypto.benchmark import run_comparison  # noqa: E402


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------

def _write_json(data: dict, filepath: str) -> None:
    """Write benchmark results as pretty-printed JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ JSON report saved → {filepath}")


def _write_csv(data: dict, filepath: str) -> None:
    """Write benchmark results as a CSV table."""
    operations = ["key_gen", "encrypt", "decrypt", "total"]
    stats = ["avg", "min", "max", "median", "stdev"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        header = ["Operation"]
        for method_label in ["RSA-2048", "ML-KEM-768"]:
            for stat in stats:
                header.append(f"{method_label} {stat} (ms)")
        writer.writerow(header)

        classical = data.get("classical", {})
        pqc = data.get("pqc", {})
        pqc_has_error = "error" in pqc

        for op in operations:
            row = [op]
            # Classical stats
            cl_op = classical.get(op, {})
            for stat in stats:
                row.append(cl_op.get(stat, "N/A"))
            # PQC stats
            if pqc_has_error:
                row.extend(["N/A"] * len(stats))
            else:
                pqc_op = pqc.get(op, {})
                for stat in stats:
                    row.append(pqc_op.get(stat, "N/A"))
            writer.writerow(row)

        # Extra PQC-specific operations
        if not pqc_has_error:
            for op in ["encapsulate", "decapsulate"]:
                if op in pqc:
                    row = [op]
                    row.extend(["—"] * len(stats))  # no classical equivalent
                    pqc_op = pqc[op]
                    for stat in stats:
                        row.append(pqc_op.get(stat, "N/A"))
                    writer.writerow(row)

        # Key sizes row
        writer.writerow([])
        writer.writerow(["Key Sizes (bytes)", "RSA-2048", "ML-KEM-768"])
        cl_sizes = data.get("key_sizes", {}).get("classical", {})
        pqc_sizes = data.get("key_sizes", {}).get("pqc", {})
        for key in ["public_key_bytes", "ciphertext_bytes"]:
            writer.writerow([
                key.replace("_", " ").title(),
                cl_sizes.get(key, "N/A"),
                pqc_sizes.get(key, "N/A"),
            ])

    print(f"  ✓ CSV report saved  → {filepath}")


# ---------------------------------------------------------------------------
# Terminal table
# ---------------------------------------------------------------------------

def _print_table(data: dict) -> None:
    """Print a formatted comparison table to the terminal."""
    iterations = data.get("iterations", "?")
    classical = data.get("classical", {})
    pqc = data.get("pqc", {})
    pqc_has_error = "error" in pqc

    print()
    print("=" * 72)
    print(f"  Quantum-Safe Benchmark Results — {iterations} iterations")
    print("=" * 72)

    # Timing table
    operations = ["key_gen", "encrypt", "decrypt", "total"]
    col_w = 14

    header = f"{'Operation':<16} {'RSA-2048 avg':>{col_w}} {'ML-KEM-768 avg':>{col_w}} {'Speedup':>{col_w}}"
    print()
    print(header)
    print("-" * len(header))

    for op in operations:
        cl_avg = classical.get(op, {}).get("avg", 0)
        if pqc_has_error:
            pqc_avg_str = "N/A"
            speedup_str = "—"
        else:
            pqc_avg = pqc.get(op, {}).get("avg", 0)
            pqc_avg_str = f"{pqc_avg:.4f} ms"
            if pqc_avg > 0:
                speedup = cl_avg / pqc_avg
                speedup_str = f"{speedup:.1f}x"
            else:
                speedup_str = "—"

        print(f"{op:<16} {cl_avg:>{col_w}.4f} ms {pqc_avg_str:>{col_w}} {speedup_str:>{col_w}}")

    # Extra PQC ops
    if not pqc_has_error:
        for op in ["encapsulate", "decapsulate"]:
            if op in pqc:
                pqc_avg = pqc[op].get("avg", 0)
                print(f"{op:<16} {'—':>{col_w}} {pqc_avg:>{col_w}.4f} ms {'':>{col_w}}")

    # Key sizes
    print()
    print("Key Sizes (bytes):")
    cl_sizes = data.get("key_sizes", {}).get("classical", {})
    pqc_sizes = data.get("key_sizes", {}).get("pqc", {})
    for label, key in [("Public key", "public_key_bytes"), ("Ciphertext", "ciphertext_bytes")]:
        cl_val = cl_sizes.get(key, "N/A")
        pqc_val = pqc_sizes.get(key, "N/A") if not pqc_has_error else "N/A"
        print(f"  {label:<16} RSA: {cl_val:>6}   ML-KEM: {pqc_val}")

    if pqc_has_error:
        print()
        print(f"  ⚠  PQC unavailable: {pqc['error']}")

    print()
    print("=" * 72)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run cryptographic benchmark: RSA-2048 vs ML-KEM-768",
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int, default=100,
        help="Number of benchmark iterations (default: 100)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str, default="docs",
        help="Output directory for reports (default: docs/)",
    )
    parser.add_argument(
        "--format", "-f",
        type=str, choices=["json", "csv", "both"], default="both",
        help="Output format (default: both)",
    )

    args = parser.parse_args()

    if args.iterations <= 0:
        print("Error: iterations must be a positive integer.")
        sys.exit(1)

    print(f"Running benchmark with {args.iterations} iterations...")
    print()

    # Run the comparison
    results = run_comparison(args.iterations)

    # Display terminal table
    _print_table(results)

    # Save reports
    os.makedirs(args.output, exist_ok=True)

    if args.format in ("json", "both"):
        json_path = os.path.join(args.output, "benchmark_results.json")
        _write_json(results, json_path)

    if args.format in ("csv", "both"):
        csv_path = os.path.join(args.output, "benchmark_results.csv")
        _write_csv(results, csv_path)

    print()
    print("Done.")


if __name__ == "__main__":
    main()
