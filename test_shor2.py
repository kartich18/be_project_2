print("1. Importing...")
from qiskit_algorithms import Shor
from qiskit_aer.primitives import Sampler
print("2. Instantiating...")
shor = Shor(Sampler())
print("3. Running factor(15)...")
try:
    res = shor.factor(15)
    print("4. Done:", res.factors)
except Exception as e:
    print("Error:", e)
