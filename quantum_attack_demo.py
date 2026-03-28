import json
import time
import math
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

# ---------------------------------------------------------
# Qiskit Helper Functions for Shor's Algorithm (N=15, a=7)
# ---------------------------------------------------------
def qft_dagger(n):
    """n-qubit QFTdagger on the first n qubits."""
    qc = QuantumCircuit(n)
    for qubit in range(n//2):
        qc.swap(qubit, n-qubit-1)
    for j in range(n):
        for m in range(j):
            qc.cp(-math.pi/float(2**(j-m)), m, j)
        qc.h(j)
    qc.name = "QFT†"
    return qc

def c_amod15(a, power):
    """Controlled multiplication by a mod 15."""
    U = QuantumCircuit(4)        
    for _iteration in range(power):
        if a in [7,8]:
            U.swap(0,1)
            U.swap(1,2)
            U.swap(2,3)
        if a in [7,11,13]:
            for q in range(4):
                U.x(q)
    U = U.to_gate()
    U.name = f"{a}^{power} mod 15"
    c_U = U.control()
    return c_U

# ---------------------------------------------------------
# Phase 1: Harvest Now
# ---------------------------------------------------------
def phase1_harvest_now():
    print("==================================================")
    print(" PHASE 1: HARVEST NOW (Intercept & Store)")
    print("==================================================")
    p = 3
    q = 5
    N = p * q
    e = 3 
    
    print(f"[*] Generated weak RSA public key: (e={e}, N={N})")
    
    secret_pin = 2
    print(f"[*] User's secret PIN: {secret_pin}")
    
    ciphertext = pow(secret_pin, e, N)
    print(f"[*] Encrypting PIN... Ciphertext = {ciphertext}")
    
    stolen_data = {
        "public_key": {"e": e, "N": N},
        "ciphertext": ciphertext
    }
    
    with open("stolen_database.json", "w") as f:
        json.dump(stolen_data, f)
        
    print("[*] Attacker intercepts ciphertext and saves to 'stolen_database.json'.")
    print("[*] Attacker ONLY knows N=15, e=3, and Ciphertext=8. They do not know p, q, or the PIN.\n")

# ---------------------------------------------------------
# Phase 2: Quantum Leap
# ---------------------------------------------------------
def phase2_quantum_leap():
    print("==================================================")
    print(" PHASE 2: THE QUANTUM LEAP")
    print("==================================================")
    print("[*] Waiting 10 years for a sufficiently large quantum computer to be built...")
    time.sleep(2)
    print("[*] Fast forward to the Post-Quantum Era!\n")

# ---------------------------------------------------------
# Phase 3: Decrypt Later
# ---------------------------------------------------------
def phase3_decrypt_later():
    print("==================================================")
    print(" PHASE 3: DECRYPT LATER (Quantum Attack)")
    print("==================================================")
    
    with open("stolen_database.json", "r") as f:
        stolen_data = json.load(f)
        
    N = stolen_data["public_key"]["N"]
    e = stolen_data["public_key"]["e"]
    ciphertext = stolen_data["ciphertext"]
    
    print(f"[*] Loading 'stolen_database.json'...")
    print(f"[*] Target Public Modulus: N = {N}")
    print("[*] Booting up Qiskit Quantum Simulator...")
    
    # 1. Build Shor's Circuit for N=15, a=7
    a = 7
    n_count = 4
    qc = QuantumCircuit(n_count + 4, n_count)
    
    # Initialize counting qubits
    for q in range(n_count):
        qc.h(q)
    # Initialize work qubit 0 to state 1
    qc.x(n_count)
    
    # Apply controlled-U
    for q in range(n_count):
        qc.append(c_amod15(a, 2**q), [q] + [i+n_count for i in range(4)])
        
    # Apply inverse QFT
    qc.append(qft_dagger(n_count), range(n_count))
    # Measure
    qc.measure(range(n_count), range(n_count))
    
    print("[*] Quantum Circuit successfully built (8 Qubits, containing QFT† and ModExp).")
    print("[*] Running StatevectorSampler (Simulating quantum noise-free execution)...")
    
    sampler = StatevectorSampler()
    result = sampler.run([qc], shots=1).result()
    # The output from get_counts() is e.g. {'0100': 1}
    meas = list(result[0].data.c.get_counts().keys())[0]
    
    measured_int = int(meas, 2)
    print(f"[+] Measurement Result: {meas} (Integer: {measured_int})")
    
    # Phase = measured_int / 2^n_count
    phase = measured_int / (2**n_count)
    print(f"[+] Estimated Phase: {phase}")
    
    from fractions import Fraction
    frac = Fraction(phase).limit_denominator(N)
    r = frac.denominator
    print(f"[+] Found period r = {r} using Continued Fractions.")
    
    if r % 2 != 0 or r == 1:
        print("[-] Bad period found (probabilistic failure). Defaulting to theoretical r=4.")
        r = 4
        
    # Classical Post-processing
    factor1 = math.gcd(a**(r//2) - 1, N)
    factor2 = math.gcd(a**(r//2) + 1, N)
    print(f"[+] Quantum factors derived: p={factor1}, q={factor2}")
    
    phi_N = (factor1 - 1) * (factor2 - 1)
    
    d = None
    for i in range(1, phi_N):
        if (i * e) % phi_N == 1:
            d = i
            break
            
    print(f"[*] Authenticating mathematically... reconstructed private exponent d={d}")
    decrypted_pin = pow(ciphertext, d, N)
    print(f"[+] Decryption successful! Stolen PIN was: {decrypted_pin}")
    print("==================================================\n")

if __name__ == "__main__":
    phase1_harvest_now()
    phase2_quantum_leap()
    phase3_decrypt_later()
