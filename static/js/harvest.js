document.addEventListener('DOMContentLoaded', () => {
    const btnHarvest = document.getElementById('btn-harvest');
    const btnGoLeap = document.getElementById('btn-go-leap');
    const btnDecrypt = document.getElementById('btn-decrypt');
    
    const harvestResult = document.getElementById('harvest-result');
    const harvestJson = document.getElementById('harvest-json');
    const decryptResult = document.getElementById('decrypt-result');
    const decryptLog = document.getElementById('decrypt-log');
    
    const leapOverlay = document.getElementById('leap-overlay');
    const leapYearText = document.getElementById('leap-year-text');
    const leapYearStatic = document.getElementById('leap-year-static');
    const leapStatusText = document.getElementById('leap-status-text');
    const timelineProgress = document.getElementById('timeline-progress');
    const node1 = document.getElementById('node-1');
    const node2 = document.getElementById('node-2');
    const node3 = document.getElementById('node-3');

    let interceptedData = null;

    // --- Phase 1: Harvest ---
    btnHarvest.addEventListener('click', async () => {
        const pin = document.getElementById('secret-pin').value;
        btnHarvest.disabled = true;
        btnHarvest.textContent = 'Intercepting...';

        try {
            const response = await fetch('/api/harvest/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pin: parseInt(pin) })
            });
            
            interceptedData = await response.json();
            
            harvestJson.textContent = JSON.stringify({
                public_key: interceptedData.public_key,
                ciphertext: interceptedData.ciphertext
            }, null, 2);
            
            harvestResult.classList.remove('hidden');
            btnHarvest.textContent = 'Harvested & Intercepted';
            
            // Update Timeline
            timelineProgress.style.width = '25%';
            node1.classList.add('completed');
            
            // Allow next stage
            setTimeout(() => {
                document.getElementById('section-2').scrollIntoView({ behavior: 'smooth' });
            }, 800);
        } catch (error) {
            console.error('Harvest failed:', error);
            alert('Simulation failed to connect to server.');
            btnHarvest.disabled = false;
            btnHarvest.textContent = 'Encrypt & Harvest';
        }
    });

    // --- Phase 2: Quantum Leap ---
    btnGoLeap.addEventListener('click', () => {
        leapOverlay.style.display = 'flex';
        let year = 2026;
        const targetYear = 2035;
        
        const interval = setInterval(() => {
            year++;
            leapYearText.textContent = year;
            
            if (year === 2029) leapStatusText.textContent = "Error-corrected qubits achieved...";
            if (year === 2032) leapStatusText.textContent = "Large-scale quantum hardware production...";
            if (year === 2035) leapStatusText.textContent = "Quantum Supremacy fully realized.";

            if (year >= targetYear) {
                clearInterval(interval);
                setTimeout(() => {
                    leapOverlay.style.display = 'none';
                    leapYearStatic.textContent = "Current Year: 2035";
                    leapYearStatic.style.color = "var(--accent-purple)";
                    completePhase2();
                }, 800);
            }
        }, 150);
    });

    function completePhase2() {
        node2.classList.add('completed');
        node2.classList.add('active');
        timelineProgress.style.width = '75%';
        btnDecrypt.disabled = false;
        
        setTimeout(() => {
            document.getElementById('section-3').scrollIntoView({ behavior: 'smooth' });
        }, 300);
    }

    // --- Phase 3: Decrypt ---
    btnDecrypt.addEventListener('click', async () => {
        btnDecrypt.disabled = true;
        btnDecrypt.textContent = 'Running Shor\'s Algorithm...';
        decryptResult.classList.remove('hidden');
        decryptLog.innerHTML = ""; // Clear log

        const logs = [
            "[*] Factoring N=" + interceptedData.public_key.N + " using Shor's method...",
            "[*] Building quantum circuit with 8 qubits...",
            "[*] Applying Superposition (H) to counting register...",
            "[*] Implementing Modular Exponentiation (7^x mod 15)...",
            "[*] Applying Inverse Quantum Fourier Transform (QFT†)...",
            "[*] Measuring collapsing statevectors...",
            "[*] Done. Post-processing measurement results classically..."
        ];

        let i = 0;
        const logInterval = setInterval(() => {
            if (i < logs.length) {
                decryptLog.innerHTML += logs[i] + "<br>";
                decryptLog.scrollTop = decryptLog.scrollHeight;
                i++;
            } else {
                clearInterval(logInterval);
                executeActualDecryption();
            }
        }, 300);
    });

    async function executeActualDecryption() {
        try {
            const response = await fetch('/api/harvest/decrypt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    N: interceptedData.public_key.N,
                    e: interceptedData.public_key.e,
                    ciphertext: interceptedData.ciphertext
                })
            });
            
            const result = await response.json();
            
            decryptLog.innerHTML += `<span style="color: var(--accent-blue)">[+] Measurement successful: ${result.measurement}</span><br>`;
            decryptLog.innerHTML += `<span style="color: var(--accent-blue)">[+] Derived period r = ${result.period}</span><br>`;
            
            document.getElementById('res-factors').textContent = `${result.factors[0]} & ${result.factors[1]}`;
            document.getElementById('res-pin').textContent = result.decrypted_pin;
            
            node3.classList.add('completed');
            node3.classList.add('active');
            timelineProgress.style.width = '100%';
            btnDecrypt.textContent = 'Attack Successful';
        } catch (error) {
            console.error('Decryption failed:', error);
            alert('Quantum simulation failed.');
            btnDecrypt.disabled = false;
            btnDecrypt.textContent = 'Execute Shor\'s Algorithm';
        }
    }
});
