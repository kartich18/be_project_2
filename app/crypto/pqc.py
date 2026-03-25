"""
Post-quantum cryptography module — ML-KEM-768.

Implements key encapsulation/decapsulation using liboqs (FIPS 203),
with AES-256-GCM symmetric encryption for the actual payload.
All operations return timing data for benchmarking.
"""
