/**
 * dashboard.js
 * Handles data fetching, transaction submission, and Chart.js rendering for the PQC Dashboard.
 */

// Globals
let latencyChart, perfChart, sizeChart;
let lastChartUpdate = Date.now();
const MAX_DATA_POINTS = 30;

// Chart Common Config
Chart.defaults.color = '#8b949e';
Chart.defaults.font.family = "'Inter', sans-serif";

const rsaColor = 'rgba(47, 129, 247, 0.8)';
const rsaColorBorder = 'rgba(47, 129, 247, 1)';
const pqcColor = 'rgba(163, 113, 247, 0.8)';
const pqcColorBorder = 'rgba(163, 113, 247, 1)';

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupEventListeners();
    
    // Initial fetch
    fetchMetrics();
    // Start regular polling
    setInterval(fetchMetrics, 2000);
});

// Setup Initial Chart.js Instances
function initCharts() {
    // 1. Latency Line Chart (Real-time)
    const ctxLat = document.getElementById('latencyChart').getContext('2d');
    latencyChart = new Chart(ctxLat, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Classical (RSA-2048)',
                    data: [],
                    borderColor: rsaColorBorder,
                    backgroundColor: rsaColor,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'PQC (ML-KEM-768)',
                    data: [],
                    borderColor: pqcColorBorder,
                    backgroundColor: pqcColor,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Total Latency (ms)' },
                    grid: { color: 'rgba(48, 54, 61, 0.5)' }
                },
                x: {
                    grid: { display: false },
                    ticks: { display: false } // Hide time labels for cleaner look
                }
            },
            plugins: {
                legend: { position: 'top' }
            }
        }
    });

    // 2. Performance Comparison Bar Chart
    const ctxPerf = document.getElementById('perfChart').getContext('2d');
    perfChart = new Chart(ctxPerf, {
        type: 'bar',
        data: {
            labels: ['Key Generation', 'Encryption', 'Decryption'],
            datasets: [
                {
                    label: 'RSA-2048',
                    data: [0, 0, 0],
                    backgroundColor: rsaColor
                },
                {
                    label: 'ML-KEM-768',
                    data: [0, 0, 0],
                    backgroundColor: pqcColor
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Time (ms)' },
                    grid: { color: 'rgba(48, 54, 61, 0.5)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    // 3. Key Sizes Bar Chart
    const ctxSize = document.getElementById('sizeChart').getContext('2d');
    sizeChart = new Chart(ctxSize, {
        type: 'bar',
        data: {
            labels: ['Public Key', 'Ciphertext'],
            datasets: [
                {
                    label: 'RSA-2048',
                    data: [0, 0],
                    backgroundColor: rsaColor
                },
                {
                    label: 'ML-KEM-768',
                    data: [0, 0],
                    backgroundColor: pqcColor
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    type: 'logarithmic',
                    title: { display: true, text: 'Size (Bytes) - Log Scale' },
                    grid: { color: 'rgba(48, 54, 61, 0.5)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

// Event Listeners for Forms and Buttons
function setupEventListeners() {
    const txForm = document.getElementById('tx-form');
    txForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const sender = document.getElementById('sender').value;
        const receiver = document.getElementById('receiver').value;
        const amount = parseFloat(document.getElementById('amount').value);
        
        console.log(`Submitting transaction: Sender=${sender}, Receiver=${receiver}, Amount=${amount}`);
        
        const statusEl = document.getElementById('tx-status');
        setStatus(statusEl, 'Processing...', 'neutral');
        
        try {
            const res = await fetch('/api/transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sender, receiver, amount })
            });
            
            const data = await res.json();
            if (res.ok) {
                const txId = data.classical ? String(data.classical.id) : "Unknown";
                setStatus(statusEl, `Success! Tx-ID: ${txId}`, 'success');
                // Trigger immediate update
                fetchMetrics(); 
                updateChartsWithNewTx(data);
            } else {
                setStatus(statusEl, `Error: ${data.error}`, 'error');
            }
        } catch (error) {
            setStatus(statusEl, 'Network error occurred.', 'error');
        }
    });

    const loadBtn = document.getElementById('btn-load-test');
    let loadTestRunning = false;
    let loadInterval;

    loadBtn.addEventListener('click', () => {
        console.log('Load test button clicked (status: ' + (loadTestRunning ? 'running' : 'stopped') + ')');
        const statusEl = document.getElementById('load-status');
        
        if (!loadTestRunning) {
            loadTestRunning = true;
            loadBtn.textContent = 'Stop Demo Load';
            loadBtn.classList.remove('secondary-btn');
            loadBtn.classList.add('primary-btn');
            setStatus(statusEl, 'Generating synthetic traffic...', 'success');
            
            // Fire 2 transactions every second
            loadInterval = setInterval(() => {
                const amount = (Math.random() * 1000).toFixed(2);
                fetch('/api/transaction', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        sender: `DEMO-${Math.floor(Math.random()*1000)}`, 
                        receiver: `DEMO-${Math.floor(Math.random()*1000)}`, 
                        amount: parseFloat(amount) 
                    })
                }).then(res => res.json()).then(data => {
                    if(!res.error) updateChartsWithNewTx(data);
                }).catch(e => console.error(e));
            }, 500);
            
        } else {
            loadTestRunning = false;
            loadBtn.textContent = 'Start Demo Load';
            clearInterval(loadInterval);
            loadBtn.classList.remove('primary-btn');
            loadBtn.classList.add('secondary-btn');
            setStatus(statusEl, 'Load generation stopped.', 'neutral');
            setTimeout(() => { statusEl.classList.add('hidden'); }, 3000);
        }
    });
}

function setStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.classList.remove('hidden');
    
    if (type !== 'neutral') {
        setTimeout(() => {
            element.classList.add('hidden');
        }, 5000);
    }
}

// Directly inject new transaction into charts before metrics polling catches up
function updateChartsWithNewTx(txData) {
    if (!txData.classical || !txData.pqc) return;
    
    const now = new Date().toLocaleTimeString();
    
    // Add latency points
    latencyChart.data.labels.push(now);
    latencyChart.data.datasets[0].data.push(txData.classical.total_time_ms);
    latencyChart.data.datasets[1].data.push(txData.pqc.total_time_ms);
    
    // Maintain max limit
    if (latencyChart.data.labels.length > MAX_DATA_POINTS) {
        latencyChart.data.labels.shift();
        latencyChart.data.datasets[0].data.shift();
        latencyChart.data.datasets[1].data.shift();
    }
    
    latencyChart.update();
    
    // Also update UI cards immediately to feel responsive
    document.getElementById('val-lat-classical').textContent = txData.classical.total_time_ms.toFixed(2) + ' ms';
    document.getElementById('val-lat-pqc').textContent = txData.pqc.total_time_ms.toFixed(2) + ' ms';
    
    addTransactionToList(txData);
}

// Fetch Aggregated Metrics
async function fetchMetrics() {
    console.debug('Fetching latest aggregated metrics...');
    try {
        // According to routes/metrics.py, limit isn't strictly necessary but helpful
        const res = await fetch('/api/metrics?last=50');
        if (!res.ok) return;
        
        const metrics = await res.json();
        
        // Update Performance Bar Chart (averages)
        if (metrics.classical && metrics.pqc) {
            perfChart.data.datasets[0].data = [
                metrics.classical.avg_key_gen_ms || 0,
                metrics.classical.avg_encrypt_ms || 0,
                metrics.classical.avg_decrypt_ms || 0
            ];
            
            perfChart.data.datasets[1].data = [
                metrics.pqc.avg_key_gen_ms || 0,
                metrics.pqc.avg_encrypt_ms || 0,
                metrics.pqc.avg_decrypt_ms || 0
            ];
            perfChart.update('none'); // Update without full animation
            
            // Update Key Sizes
            sizeChart.data.datasets[0].data = [
                metrics.classical.avg_key_size_bytes || 294, // fallback standard sizes if db empty
                metrics.classical.avg_ciphertext_size_bytes || 256
            ];
            
            sizeChart.data.datasets[1].data = [
                metrics.pqc.avg_key_size_bytes || 1184,
                metrics.pqc.avg_ciphertext_size_bytes || 1088
            ];
            sizeChart.update('none');
        }
        
    } catch (error) {
        console.error("Failed to fetch metrics", error);
    }
}

// Add transaction to the history list display
function addTransactionToList(txData) {
    const tbody = document.getElementById('tx-list');
    if (!tbody) return;
    
    const { classical, pqc } = txData;
    
    // Format functions
    const formatTime = (ms) => `<span class="time-val">${ms.toFixed(4)}</span>`;
    const formatTimeShort = (d) => new Date(d).toLocaleTimeString();

    // Create Classical Row
    const trClass = document.createElement('tr');
    trClass.innerHTML = `
        <td>#${classical.id}</td>
        <td>${formatTimeShort(classical.timestamp)}</td>
        <td>${classical.sender} &rarr; ${classical.receiver}</td>
        <td style="color: var(--accent-green)">$${classical.amount.toFixed(2)}</td>
        <td><span class="method-badge method-rsa">${classical.crypto_method}</span></td>
        <td>${formatTime(classical.key_gen_time_ms)}</td>
        <td>${formatTime(classical.encrypt_time_ms)}</td>
        <td>${formatTime(classical.decrypt_time_ms)}</td>
        <td><strong>${formatTime(classical.total_time_ms)}</strong></td>
        <td>${classical.key_size_bytes}</td>
        <td>${classical.ciphertext_size_bytes}</td>
    `;
    
    // Create PQC Row
    const trPQC = document.createElement('tr');
    trPQC.innerHTML = `
        <td>#${pqc.id}</td>
        <td>${formatTimeShort(pqc.timestamp)}</td>
        <td>${pqc.sender} &rarr; ${pqc.receiver}</td>
        <td style="color: var(--accent-green)">$${pqc.amount.toFixed(2)}</td>
        <td><span class="method-badge method-pqc">${pqc.crypto_method}</span></td>
        <td>${formatTime(pqc.key_gen_time_ms)}</td>
        <td>${formatTime(pqc.encrypt_time_ms)}</td>
        <td>${formatTime(pqc.decrypt_time_ms)}</td>
        <td><strong>${formatTime(pqc.total_time_ms)}</strong></td>
        <td>${pqc.key_size_bytes}</td>
        <td>${pqc.ciphertext_size_bytes}</td>
    `;
    
    // Add spacer line to separate transactions clearly
    trPQC.style.borderBottom = '2px solid rgba(48, 54, 61, 0.8)';
    
    tbody.insertBefore(trPQC, tbody.firstChild);
    tbody.insertBefore(trClass, tbody.firstChild);
    
    // Limit to 40 rows (20 transactions) in memory
    while (tbody.children.length > 40) {
        tbody.removeChild(tbody.lastChild);
    }
}
