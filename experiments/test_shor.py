from qiskit_algorithms import Shor
from qiskit.primitives import Sampler

def test():
    shor = Shor()
    # Actually Shor class doesn't take sampler in its __init__ sometimes, let's see its signature
    print("Running Shor factor(15)...")
    try:
        res = shor.factor(15)
        print(res.factors)
    except Exception as e:
        print(e)
test()
