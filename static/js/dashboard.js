/**
 * dashboard.js
 * Handles data fetching, transaction submission, and Chart.js rendering for the PQC Dashboard.
 * Supports RSA-2048, ML-KEM-512, ML-KEM-768, and ML-KEM-1024.
 */

// Globals
let latencyChart, perfChart, sizeChart;
let lastChartUpdate = Date.now();
const MAX_DATA_POINTS = 30;

// Chart Common Config
Chart.defaults.color = '#8b949e';
Chart.defaults.font.family = "'Inter', sans-serif";

// Algorithm color palette
const rsaColor = 'rgba(47, 129, 247, 0.8)';
const rsaColorBorder = 'rgba(47, 129, 247, 1)';
const pqc512Color = 'rgba(45, 212, 191, 0.8)';
const pqc512ColorBorder = 'rgba(45, 212, 191, 1)';
const pqc768Color = 'rgba(163, 113, 247, 0.8)';
const pqc768ColorBorder = 'rgba(163, 113, 247, 1)';
const pqc1024Color = 'rgba(245, 158, 11, 0.8)';
const pqc1024ColorBorder = 'rgba(245, 158, 11, 1)';

// Method badge CSS class mapping
function methodBadgeClass(method) {
    switch (method) {
        case 'RSA-2048': return 'method-rsa';
        case 'ML-KEM-512': return 'method-pqc-512';
        case 'ML-KEM-768': return 'method-pqc-768';
        case 'ML-KEM-1024': return 'method-pqc-1024';
        default: return 'method-pqc';
    }
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setupEventListeners();
    
    // Initial fetch
    fetchMetrics();
    fetchAdvancedAnalytics(getSelectedWindow());

    // Start regular polling
    setInterval(fetchMetrics, 2000);
    setInterval(() => fetchAdvancedAnalytics(getSelectedWindow()), 5000);
});

// Setup Initial Chart.js Instances
function initCharts() {
    // 1. Latency Line Chart (Real-time) — 4 datasets
    const ctxLat = document.getElementById('latencyChart').getContext('2d');
    latencyChart = new Chart(ctxLat, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'RSA-2048',
                    data: [],
                    borderColor: rsaColorBorder,
                    backgroundColor: rsaColor,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'ML-KEM-512',
                    data: [],
                    borderColor: pqc512ColorBorder,
                    backgroundColor: pqc512Color,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'ML-KEM-768',
                    data: [],
                    borderColor: pqc768ColorBorder,
                    backgroundColor: pqc768Color,
                    tension: 0.4,
                    borderWidth: 2,
                    pointRadius: 2
                },
                {
                    label: 'ML-KEM-1024',
                    data: [],
                    borderColor: pqc1024ColorBorder,
                    backgroundColor: pqc1024Color,
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
                    ticks: { display: false }
                }
            },
            plugins: {
                legend: { position: 'top' }
            }
        }
    });

    // 2. Performance Comparison Bar Chart — 4 datasets
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
                    label: 'ML-KEM-512',
                    data: [0, 0, 0],
                    backgroundColor: pqc512Color
                },
                {
                    label: 'ML-KEM-768',
                    data: [0, 0, 0],
                    backgroundColor: pqc768Color
                },
                {
                    label: 'ML-KEM-1024',
                    data: [0, 0, 0],
                    backgroundColor: pqc1024Color
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

    // 3. Key Sizes Bar Chart — 4 datasets
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
                    label: 'ML-KEM-512',
                    data: [0, 0],
                    backgroundColor: pqc512Color
                },
                {
                    label: 'ML-KEM-768',
                    data: [0, 0],
                    backgroundColor: pqc768Color
                },
                {
                    label: 'ML-KEM-1024',
                    data: [0, 0],
                    backgroundColor: pqc1024Color
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
                    if (!data.error) updateChartsWithNewTx(data);
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

    const analyticsWindow = document.getElementById('analytics-window');
    if (analyticsWindow) {
        analyticsWindow.addEventListener('change', () => {
            fetchAdvancedAnalytics(getSelectedWindow());
        });
    }
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
    if (!txData.classical) return;
    
    const now = new Date().toLocaleTimeString();
    
    // Add latency points — RSA is always present
    latencyChart.data.labels.push(now);
    latencyChart.data.datasets[0].data.push(txData.classical.total_time_ms);
    latencyChart.data.datasets[1].data.push(txData.pqc_512 ? txData.pqc_512.total_time_ms : null);
    latencyChart.data.datasets[2].data.push(txData.pqc_768 ? txData.pqc_768.total_time_ms : null);
    latencyChart.data.datasets[3].data.push(txData.pqc_1024 ? txData.pqc_1024.total_time_ms : null);
    
    // Maintain max limit
    if (latencyChart.data.labels.length > MAX_DATA_POINTS) {
        latencyChart.data.labels.shift();
        latencyChart.data.datasets.forEach(ds => ds.data.shift());
    }
    
    latencyChart.update();
    
    // Update UI cards immediately
    document.getElementById('val-lat-classical').textContent = txData.classical.total_time_ms.toFixed(2) + ' ms';
    if (txData.pqc_512) {
        document.getElementById('val-lat-pqc-512').textContent = txData.pqc_512.total_time_ms.toFixed(2) + ' ms';
    }
    if (txData.pqc_768) {
        document.getElementById('val-lat-pqc-768').textContent = txData.pqc_768.total_time_ms.toFixed(2) + ' ms';
    }
    if (txData.pqc_1024) {
        document.getElementById('val-lat-pqc-1024').textContent = txData.pqc_1024.total_time_ms.toFixed(2) + ' ms';
    }
    
    addTransactionToList(txData);
}

// Fetch Aggregated Metrics
async function fetchMetrics() {
    console.debug('Fetching latest aggregated metrics...');
    try {
        const res = await fetch('/api/metrics?last=50');
        if (!res.ok) return;
        
        const metrics = await res.json();
        
        // Update summary cards
        if (metrics.classical) {
            document.getElementById('val-lat-classical').textContent = (metrics.classical.avg_total_ms || 0).toFixed(2) + ' ms';
        }
        if (metrics.pqc_512) {
            document.getElementById('val-lat-pqc-512').textContent = (metrics.pqc_512.avg_total_ms || 0).toFixed(2) + ' ms';
        }
        if (metrics.pqc_768) {
            document.getElementById('val-lat-pqc-768').textContent = (metrics.pqc_768.avg_total_ms || 0).toFixed(2) + ' ms';
        }
        if (metrics.pqc_1024) {
            document.getElementById('val-lat-pqc-1024').textContent = (metrics.pqc_1024.avg_total_ms || 0).toFixed(2) + ' ms';
        }

        // Update Performance Bar Chart (averages)
        if (metrics.classical) {
            perfChart.data.datasets[0].data = [
                metrics.classical.avg_key_gen_ms || 0,
                metrics.classical.avg_encrypt_ms || 0,
                metrics.classical.avg_decrypt_ms || 0
            ];
        }
        if (metrics.pqc_512) {
            perfChart.data.datasets[1].data = [
                metrics.pqc_512.avg_key_gen_ms || 0,
                metrics.pqc_512.avg_encrypt_ms || 0,
                metrics.pqc_512.avg_decrypt_ms || 0
            ];
        }
        if (metrics.pqc_768) {
            perfChart.data.datasets[2].data = [
                metrics.pqc_768.avg_key_gen_ms || 0,
                metrics.pqc_768.avg_encrypt_ms || 0,
                metrics.pqc_768.avg_decrypt_ms || 0
            ];
        }
        if (metrics.pqc_1024) {
            perfChart.data.datasets[3].data = [
                metrics.pqc_1024.avg_key_gen_ms || 0,
                metrics.pqc_1024.avg_encrypt_ms || 0,
                metrics.pqc_1024.avg_decrypt_ms || 0
            ];
        }
        perfChart.update('none');
        
        // Update Key Sizes
        if (metrics.classical) {
            sizeChart.data.datasets[0].data = [
                metrics.classical.avg_key_size_bytes || 294,
                metrics.classical.avg_ciphertext_size_bytes || 256
            ];
        }
        if (metrics.pqc_512) {
            sizeChart.data.datasets[1].data = [
                metrics.pqc_512.avg_key_size_bytes || 800,
                metrics.pqc_512.avg_ciphertext_size_bytes || 768
            ];
        }
        if (metrics.pqc_768) {
            sizeChart.data.datasets[2].data = [
                metrics.pqc_768.avg_key_size_bytes || 1184,
                metrics.pqc_768.avg_ciphertext_size_bytes || 1088
            ];
        }
        if (metrics.pqc_1024) {
            sizeChart.data.datasets[3].data = [
                metrics.pqc_1024.avg_key_size_bytes || 1568,
                metrics.pqc_1024.avg_ciphertext_size_bytes || 1568
            ];
        }
        sizeChart.update('none');

        // ── Crypto Breakdown panels ──
        updateBreakdownPanels(metrics);

        fetchAdvancedAnalytics(getSelectedWindow());
        
    } catch (error) {
        console.error("Failed to fetch metrics", error);
    }
}

function getSelectedWindow() {
    const picker = document.getElementById('analytics-window');
    return picker ? picker.value : '24h';
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

async function fetchAdvancedAnalytics(timeWindow) {
    try {
        const [migrationRes, rotationRes, comparisonRes, healthRes, anomalyRes] = await Promise.all([
            fetch(`/api/v1/analytics/migration-status?time_window=${encodeURIComponent(timeWindow)}`),
            fetch('/api/v1/keys/rotation-health'),
            fetch(`/api/v1/analytics/algorithm-comparison?time_window=${encodeURIComponent(timeWindow)}`),
            fetch(`/api/v1/analytics/security-health?time_window=${encodeURIComponent(timeWindow)}`),
            fetch('/api/v1/analytics/anomalies')
        ]);

        const [migration, rotation, comparison, health, anomalies] = await Promise.all([
            migrationRes.ok ? migrationRes.json() : null,
            rotationRes.ok ? rotationRes.json() : null,
            comparisonRes.ok ? comparisonRes.json() : null,
            healthRes.ok ? healthRes.json() : null,
            anomalyRes.ok ? anomalyRes.json() : null
        ]);

        if (migration) {
            setText('kpi-migration', `${(migration.mlkem_percentage || 0).toFixed(1)}%`);
            const status = migration.status || 'unknown';
            setText('kpi-migration-sub', `Target ${migration.migration_target || 80}% • ${status}`);
        }

        if (rotation) {
            setText('kpi-rotation', `${(rotation.compliance_score || 0).toFixed(1)}`);
            setText('kpi-rotation-sub', `${rotation.health_status || 'unknown'} • Overdue ${rotation.keys_overdue_rotation || 0}`);
        }

        if (comparison) {
            const latencyDelta = comparison.comparison?.latency_delta_pct || 0;
            setText('kpi-algo-ratio', `${latencyDelta.toFixed(1)}%`);
            setText('kpi-algo-ratio-sub', comparison.comparison?.latency_verdict || 'No comparison available');

            const box = document.getElementById('algo-comparison-content');
            if (box) {
                // Build per-variant latency summary
                const rsa = comparison.rsa_2048 || {};
                const m512 = comparison.ml_kem_512 || {};
                const m768 = comparison.ml_kem || {};
                const m1024 = comparison.ml_kem_1024 || {};

                box.innerHTML = `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px;">
                        <div><strong style="color: ${rsaColorBorder};">RSA-2048</strong>: ${(rsa.avg_latency_ms || 0).toFixed(3)} ms avg</div>
                        <div><strong style="color: ${pqc512ColorBorder};">ML-KEM-512</strong>: ${(m512.avg_latency_ms || 0).toFixed(3)} ms avg</div>
                        <div><strong style="color: ${pqc768ColorBorder};">ML-KEM-768</strong>: ${(m768.avg_latency_ms || 0).toFixed(3)} ms avg</div>
                        <div><strong style="color: ${pqc1024ColorBorder};">ML-KEM-1024</strong>: ${(m1024.avg_latency_ms || 0).toFixed(3)} ms avg</div>
                    </div>
                    <div>Verdict: ${comparison.comparison?.latency_verdict || 'N/A'}</div>
                    <div>Throughput: ${comparison.comparison?.throughput_verdict || 'N/A'}</div>
                    <div>Key size delta (768 vs RSA): ${(comparison.comparison?.size_delta_pct ?? 0).toFixed(1)}%</div>
                    <div style="margin-top: 8px; color: var(--text-primary);">${comparison.comparison?.recommendation || ''}</div>
                `;
            }
        }

        if (health) {
            setText('kpi-failure', `${(health.failure_rate_pct || 0).toFixed(2)}%`);
            setText('kpi-failure-sub', `Status: ${health.status || 'unknown'}`);
        }

        if (anomalies) {
            const listEl = document.getElementById('anomaly-list');
            if (listEl) {
                listEl.innerHTML = '';
                const rows = anomalies.detected_anomalies || [];

                if (rows.length === 0) {
                    const li = document.createElement('li');
                    li.textContent = 'No anomalies detected.';
                    listEl.appendChild(li);
                } else {
                    rows.forEach(item => {
                        const li = document.createElement('li');
                        li.className = `anomaly-${item.severity || 'info'}`;
                        const metric = item.metric ? `${item.metric}: ` : '';
                        li.textContent = `[${(item.severity || 'info').toUpperCase()}] ${metric}${(item.delta_pct || 0).toFixed(1)}%`;
                        listEl.appendChild(li);
                    });
                }
            }
        }
    } catch (error) {
        console.error('Failed to fetch advanced analytics', error);
    }
}

// ── Crypto Breakdown: update all three panels from metrics ────────────
function updateBreakdownPanels(metrics) {
    const pqcMap = {
        '512':  metrics.pqc_512,
        '768':  metrics.pqc_768,
        '1024': metrics.pqc_1024,
    };

    // 1. Encap + Decap table
    for (const [key, m] of Object.entries(pqcMap)) {
        const row = document.getElementById(`bd-${key}`);
        if (!row || !m) continue;
        const cells = row.querySelectorAll('td');
        const encap = m.avg_encapsulate_ms != null ? m.avg_encapsulate_ms.toFixed(4) : '--';
        const decap = m.avg_decapsulate_ms != null ? m.avg_decapsulate_ms.toFixed(4) : '--';
        const kemTotal = (m.avg_encapsulate_ms != null && m.avg_decapsulate_ms != null)
            ? (m.avg_encapsulate_ms + m.avg_decapsulate_ms).toFixed(4)
            : '--';
        if (cells[1]) cells[1].textContent = encap;
        if (cells[2]) cells[2].textContent = decap;
        if (cells[3]) cells[3].textContent = kemTotal;
    }

    // 2. Payload Overhead Ratio bars
    const allRatios = {
        rsa:  metrics.classical?.payload_overhead_ratio || 0,
        512:  metrics.pqc_512?.payload_overhead_ratio  || 0,
        768:  metrics.pqc_768?.payload_overhead_ratio  || 0,
        1024: metrics.pqc_1024?.payload_overhead_ratio || 0,
    };
    const maxRatio = Math.max(...Object.values(allRatios), 1);
    for (const [key, val] of Object.entries(allRatios)) {
        const fill = document.getElementById(`ratio-fill-${key}`);
        const label = document.getElementById(`ratio-val-${key}`);
        if (fill) fill.style.width = `${(val / maxRatio * 100).toFixed(1)}%`;
        if (label) label.textContent = `${val.toFixed(1)}×`;
    }

    // 3. Key Material Footprint bars
    const allFootprints = {
        rsa:  metrics.classical?.key_material_footprint_bytes || 0,
        512:  metrics.pqc_512?.key_material_footprint_bytes  || 0,
        768:  metrics.pqc_768?.key_material_footprint_bytes  || 0,
        1024: metrics.pqc_1024?.key_material_footprint_bytes || 0,
    };
    const maxFp = Math.max(...Object.values(allFootprints), 1);
    for (const [key, val] of Object.entries(allFootprints)) {
        const fill = document.getElementById(`fp-fill-${key}`);
        const label = document.getElementById(`fp-val-${key}`);
        if (fill) fill.style.width = `${(val / maxFp * 100).toFixed(1)}%`;
        if (label) label.textContent = val >= 1000 ? `${(val / 1024).toFixed(2)} KB` : `${Math.round(val)} B`;
    }
}

// Add transaction to the history list display
function addTransactionToList(txData) {
    const tbody = document.getElementById('tx-list');
    if (!tbody) return;

    const { classical, pqc_512, pqc_768, pqc_1024 } = txData;
    if (!classical) return;

    const formatTime = (ms) => ms != null ? `<span class="time-val">${ms.toFixed(4)}</span>` : `<span class="time-val" style="color:var(--text-secondary)">—</span>`;
    const formatTimeShort = (d) => new Date(d).toLocaleTimeString();

    function buildRow(tx) {
        const tr = document.createElement('tr');
        const keyMaterial = tx.secret_key_bytes
            ? tx.key_size_bytes + tx.secret_key_bytes
            : tx.key_size_bytes;
        tr.innerHTML = `
            <td>#${tx.id}</td>
            <td>${formatTimeShort(tx.timestamp)}</td>
            <td>${tx.sender} &rarr; ${tx.receiver}</td>
            <td style="color: var(--accent-green)">$${tx.amount.toFixed(2)}</td>
            <td><span class="method-badge ${methodBadgeClass(tx.crypto_method)}">${tx.crypto_method}</span></td>
            <td>${formatTime(tx.key_gen_time_ms)}</td>
            <td>${formatTime(tx.encapsulate_time_ms)}</td>
            <td>${formatTime(tx.encrypt_time_ms)}</td>
            <td>${formatTime(tx.decapsulate_time_ms)}</td>
            <td>${formatTime(tx.decrypt_time_ms)}</td>
            <td><strong>${formatTime(tx.total_time_ms)}</strong></td>
            <td>${keyMaterial}</td>
            <td>${tx.ciphertext_size_bytes}</td>
        `;
        return tr;
    }

    const rows = [];
    rows.push(buildRow(classical));
    if (pqc_512) rows.push(buildRow(pqc_512));
    if (pqc_768) rows.push(buildRow(pqc_768));
    if (pqc_1024) {
        const lastRow = buildRow(pqc_1024);
        lastRow.style.borderBottom = '2px solid rgba(48, 54, 61, 0.8)';
        rows.push(lastRow);
    }

    for (let i = rows.length - 1; i >= 0; i--) {
        tbody.insertBefore(rows[i], tbody.firstChild);
    }

    while (tbody.children.length > 80) {
        tbody.removeChild(tbody.lastChild);
    }
}
