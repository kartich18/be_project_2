"""
Tests for the benchmark comparison module.
"""

import pytest
from app.crypto import benchmark
from app.crypto import pqc as pqc_mod


SMALL_ITERATIONS = 3  # Keep tests fast


class TestComputeStats:
    """Test the internal statistics helper."""

    def test_basic_stats(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        stats = benchmark._compute_stats(values)
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["avg"] == 3.0
        assert stats["median"] == 3.0
        assert stats["stdev"] > 0

    def test_empty_list(self):
        stats = benchmark._compute_stats([])
        assert stats["min"] == 0
        assert stats["avg"] == 0

    def test_single_value(self):
        stats = benchmark._compute_stats([42.0])
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["stdev"] == 0


class TestClassicalBenchmark:
    """Test RSA-2048 benchmark."""

    def test_runs_and_returns_structure(self):
        result = benchmark.run_classical_benchmark(SMALL_ITERATIONS)
        assert result["method"] == "RSA-2048"
        assert result["iterations"] == SMALL_ITERATIONS

        # Check stats keys exist for each operation
        for op in ["key_gen", "encrypt", "decrypt", "sign", "verify", "total"]:
            assert op in result, f"Missing operation: {op}"
            for stat in ["min", "max", "avg", "median"]:
                assert stat in result[op], f"Missing stat {stat} in {op}"

    def test_key_sizes_present(self):
        result = benchmark.run_classical_benchmark(SMALL_ITERATIONS)
        assert "key_sizes" in result
        assert "public_key_bytes" in result["key_sizes"]


class TestPQCBenchmark:
    """Test ML-KEM-768 benchmark (skipped if liboqs unavailable)."""

    @pytest.mark.skipif(
        not pqc_mod.PQC_AVAILABLE,
        reason="liboqs not installed",
    )
    def test_runs_and_returns_structure(self):
        result = benchmark.run_pqc_benchmark(SMALL_ITERATIONS)
        assert result["method"] == "ML-KEM-768"
        assert result["iterations"] == SMALL_ITERATIONS

        for op in ["key_gen", "encapsulate", "encrypt", "decapsulate", "decrypt", "total"]:
            assert op in result

    @pytest.mark.skipif(
        pqc_mod.PQC_AVAILABLE,
        reason="liboqs IS installed — this test is for the missing case",
    )
    def test_raises_when_unavailable(self):
        with pytest.raises(RuntimeError):
            benchmark.run_pqc_benchmark(1)


class TestComparison:
    """Test the unified comparison function."""

    def test_comparison_always_has_classical(self):
        result = benchmark.run_comparison(SMALL_ITERATIONS)
        assert "classical" in result
        assert result["classical"]["method"] == "RSA-2048"
        assert "pqc_768" in result

    def test_comparison_iterations(self):
        result = benchmark.run_comparison(SMALL_ITERATIONS)
        assert result["iterations"] == SMALL_ITERATIONS

    def test_key_sizes_section(self):
        result = benchmark.run_comparison(SMALL_ITERATIONS)
        assert "key_sizes" in result
        assert "classical" in result["key_sizes"]
