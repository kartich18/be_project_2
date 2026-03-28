liboqs-python faulthandler is disabled

======================================================================
  STEP 2: CLASSICAL ATTACK — SHOR'S ALGORITHM
======================================================================

  Factoring small composites to demonstrate RSA vulnerability...

  N=  15  →  factors=(3, 5)  time=0.000113s  attempts=1
  N=  21  →  factors=(7, 3)  time=0.000011s  attempts=1
  N=  35  →  factors=(7, 5)  time=0.000010s  attempts=1

======================================================================
  STEP 3: SCALING EXPERIMENT — SHOR ON MULTIPLE VALUES
======================================================================


------------------------------------------------------------
  SHOR'S ALGORITHM — SCALING EXPERIMENT
------------------------------------------------------------
       N             Factors  Attempts    Time (s)    Status
------------------------------------------------------------
      15               3 × 5         1    0.000006   ✓ BROKE
      21               3 × 7         1    0.000003   ✓ BROKE
      35               7 × 5         2    0.000007   ✓ BROKE
      51              3 × 17         1    0.000005   ✓ BROKE
      77              11 × 7         2    0.000009   ✓ BROKE
      91              7 × 13         1    0.000006   ✓ BROKE
     119              7 × 17         1    0.000007   ✓ BROKE
     143             11 × 13         2    0.000016   ✓ BROKE
     221             13 × 17         1    0.000032   ✓ BROKE
     323             19 × 17         1    0.000016   ✓ BROKE
     437             19 × 23         1    0.000035   ✓ BROKE
     667             23 × 29         1    0.000027   ✓ BROKE
     899             31 × 29         1    0.000026   ✓ BROKE
    1147             37 × 31         2    0.000016   ✓ BROKE
    2047             23 × 89         1    0.000007   ✓ BROKE
------------------------------------------------------------
  Success rate: 15/15
------------------------------------------------------------


======================================================================
  STEP 4: PQC IMPLEMENTATION — KYBER / ML-KEM BENCHMARK
======================================================================


-------------------------------------------------------------------------------------------------
  PQC KEM BENCHMARK (averages, ms)
-------------------------------------------------------------------------------------------------
Algorithm            KeyGen     Encaps     Decaps      Total      PK      SK      CT    SS  Match
-------------------------------------------------------------------------------------------------
ML-KEM-512           0.4849     0.0417     0.0269     0.5535     800    1632     768    32      ✓
ML-KEM-768           0.0333     0.0330     0.0326     0.0989    1184    2400    1088    32      ✓
ML-KEM-1024          0.0403     0.0464     0.0388     0.1255    1568    3168    1568    32      ✓
Kyber512             0.1267     0.0275     0.0324     0.1866     800    1632     768    32      ✓
Kyber768             0.0353     0.0346     0.0264     0.0963    1184    2400    1088    32      ✓
Kyber1024            0.0357     0.0341     0.0291     0.0989    1568    3168    1568    32      ✓
-------------------------------------------------------------------------------------------------


======================================================================
  STEP 5: BRUTE-FORCE ATTACK SIMULATION ON PQC
======================================================================


  Target algorithm  : ML-KEM-768
  Shared-secret len : 32 bytes (256 bits)
  Keyspace size     : 2^256  (1.16e+77)
  Max attempts      : 1,000,000
  Starting brute-force attack...

    attempt    200,000  |  elapsed    0.237s  |  rate 844,708 guesses/s
    attempt    400,000  |  elapsed    0.404s  |  rate 990,078 guesses/s
    attempt    600,000  |  elapsed    0.514s  |  rate 1,166,520 guesses/s
    attempt    800,000  |  elapsed    0.617s  |  rate 1,297,624 guesses/s
    attempt  1,000,000  |  elapsed    0.735s  |  rate 1,359,767 guesses/s

  [✓] Attack FAILED after 1,000,000 attempts (0.7355s)
      Probability of success was 1000000/1.16e+77
      ≈ 8.64e-72  (effectively zero)

------------------------------------------------------------
  PQC BRUTE-FORCE ATTACK REPORT
------------------------------------------------------------
  algorithm               : ML-KEM-768
  shared_secret_bytes     : 32
  keyspace_bits           : 256
  max_attempts            : 1,000,000
  attempts_made           : 1,000,000
  success                 : 0
  time_s                  : 0.735502
  guesses_per_second      : 1,359,614.700000
  probability             : 8.64e-72
------------------------------------------------------------


======================================================================
  STEP 6: RESULT COMPARISON — RSA vs PQC
======================================================================


========================================================================
                   RSA  vs  PQC  —  SECURITY COMPARISON
========================================================================

  CLASSICAL SYSTEM: RSA (integer factoring)
------------------------------------------------------------------------
    Attack method      : Shor's Algorithm (simulated)
    Numbers tested     : 15
    Numbers broken     : 15
    Success rate       : 100.0%
    Avg attack time    : 0.000015 s
    Verdict            : VULNERABLE — factorable in polynomial time on a quantum computer        

  POST-QUANTUM SYSTEM: ML-KEM-768 (lattice-based KEM)
------------------------------------------------------------------------
    Attack method      : Brute-force random guessing
    Attempts           : 1,000,000
    Success            : False
    Attack time        : 0.735502 s
    Guesses/sec        : 1,359,615
    Keyspace           : 2^256 bits
    P(success)         : 8.64e-72
    KEM keygen         : 0.0333 ms
    KEM encaps         : 0.0330 ms
    KEM decaps         : 0.0326 ms
    Verdict            : SECURE — no known quantum algorithm breaks lattice-based crypto

========================================================================


======================================================================
  STEP 7: GENERATING CHARTS
======================================================================

  ✓ Saved: /home/kshitij_dhake/pqc-project/app/quantum_simulation/output/chart_attack_time.png
  ✓ Saved: /home/kshitij_dhake/pqc-project/app/quantum_simulation/output/chart_success_failure.png
  ✓ Saved: /home/kshitij_dhake/pqc-project/app/quantum_simulation/output/chart_kem_performance.png
  ✓ Saved: /home/kshitij_dhake/pqc-project/app/quantum_simulation/output/chart_shor_scaling.png  

======================================================================
  STEP 8: SAVING REPORTS
======================================================================

  Report saved → /home/kshitij_dhake/pqc-project/app/quantum_simulation/output/simulation_report.json

======================================================================
  STEP 10: FINAL INTERPRETATION & CONCLUSION
======================================================================


╔══════════════════════════════════════════════════════════════════════════╗
║                         FINAL CONCLUSION                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  WHY RSA FAILS UNDER QUANTUM ATTACK                                   ║
║  ──────────────────────────────────                                    ║
║  • RSA's security relies on the hardness of integer factoring.         ║
║  • Shor's Algorithm solves factoring in O(n³) on a quantum computer,   ║
║    rendering RSA key sizes (2048, 4096 bit) trivially breakable.       ║
║  • Our simulation showed that even with a classical emulation of       ║
║    Shor's quantum subroutine, small RSA-like moduli were factored      ║
║    instantly — confirming the theoretical vulnerability.               ║
║                                                                        ║
║  WHY PQC (KYBER / ML-KEM) REMAINS SECURE                              ║
║  ────────────────────────────────────────                              ║
║  • ML-KEM-768 is based on the Module Learning With Errors (MLWE)       ║
║    problem — a lattice problem with no known efficient quantum         ║
║    algorithm.                                                          ║
║  • Grover's Algorithm (best quantum attack on symmetric-like keys)     ║
║    only provides a quadratic speedup → 2^256 → 2^128 operations,      ║
║    still far beyond feasibility.                                       ║
║  • Our brute-force simulation (1 million attempts) had a probability   ║
║    of success ≈ 0.0, confirming practical resistance.                  ║
║  • NIST standardised ML-KEM as FIPS 203 in 2024, validating it for    ║
║    banking, government, and critical infrastructure use.               ║
║                                                                        ║
║  BOTTOM LINE FOR BANKING APIs:                                         ║
║    Migrate from RSA/ECDSA → ML-KEM-768 / ML-DSA-65 before large-      ║
║    scale quantum computers arrive (estimated 2030–2035).               ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝


======================================================================
  SIMULATION COMPLETE  —  Total time: 1.63s
  Output directory: /home/kshitij_dhake/pqc-project/app/quantum_simulation/output
======================================================================

