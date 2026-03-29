/**
 * dashboard.js
 * Handles data fetching, transaction submission, and Chart.js rendering for the PQC Dashboard.
 */

// Globals
let latencyChart, perfChart, sizeChart, migrationTrendChart, percentileTrendChart;
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
    fetchAdvancedAnalytics(getSelectedWindow());

    // Start regular polling
    setInterval(fetchMetrics, 2000);
    setInterval(() => fetchAdvancedAnalytics(getSelectedWindow()), 5000);
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

    // 4. Migration Trend Chart
    const migrationCanvas = document.getElementById('migrationTrendChart');
    if (migrationCanvas) {
        const ctxMigration = migrationCanvas.getContext('2d');
        migrationTrendChart = new Chart(ctxMigration, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'RSA-2048 %',
                        data: [],
                        borderColor: rsaColorBorder,
                        backgroundColor: 'rgba(47, 129, 247, 0.15)',
                        tension: 0.3,
                        borderWidth: 2,
                        pointRadius: 2
                    },
                    {
                        label: 'ML-KEM-768 %',
                        data: [],
                        borderColor: pqcColorBorder,
                        backgroundColor: 'rgba(163, 113, 247, 0.15)',
                        tension: 0.3,
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
                        max: 100,
                        title: { display: true, text: 'Adoption %' },
                        grid: { color: 'rgba(48, 54, 61, 0.5)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // 5. Latency Percentiles Trend Chart
    const percentileCanvas = document.getElementById('percentileTrendChart');
    if (percentileCanvas) {
        const ctxPercentile = percentileCanvas.getContext('2d');
        percentileTrendChart = new Chart(ctxPercentile, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'p50',
                        data: [],
                        borderColor: 'rgba(63, 185, 80, 1)',
                        backgroundColor: 'rgba(63, 185, 80, 0.2)',
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 1.5
                    },
                    {
                        label: 'p95',
                        data: [],
                        borderColor: pqcColorBorder,
                        backgroundColor: pqcColor,
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 1.5
                    },
                    {
                        label: 'p99',
                        data: [],
                        borderColor: 'rgba(248, 81, 73, 1)',
                        backgroundColor: 'rgba(248, 81, 73, 0.2)',
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 1.5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'Latency (ms)' },
                        grid: { color: 'rgba(48, 54, 61, 0.5)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }
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
            document.getElementById('val-lat-classical').textContent = (metrics.classical.avg_total_ms || 0).toFixed(2) + ' ms';
            document.getElementById('val-lat-pqc').textContent = (metrics.pqc.avg_total_ms || 0).toFixed(2) + ' ms';

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
        const [percentilesRes, migrationRes, rotationRes, comparisonRes, healthRes, anomalyRes] = await Promise.all([
            fetch(`/api/v1/analytics/latency-percentiles?time_window=${encodeURIComponent(timeWindow)}`),
            fetch(`/api/v1/analytics/migration-status?time_window=${encodeURIComponent(timeWindow)}`),
            fetch('/api/v1/keys/rotation-health'),
            fetch(`/api/v1/analytics/algorithm-comparison?time_window=${encodeURIComponent(timeWindow)}`),
            fetch(`/api/v1/analytics/security-health?time_window=${encodeURIComponent(timeWindow)}`),
            fetch('/api/v1/analytics/anomalies')
        ]);

        const [percentiles, migration, rotation, comparison, health, anomalies] = await Promise.all([
            percentilesRes.ok ? percentilesRes.json() : null,
            migrationRes.ok ? migrationRes.json() : null,
            rotationRes.ok ? rotationRes.json() : null,
            comparisonRes.ok ? comparisonRes.json() : null,
            healthRes.ok ? healthRes.json() : null,
            anomalyRes.ok ? anomalyRes.json() : null
        ]);

        if (percentiles) {
            const p95 = percentiles.p95_ms || 0;
            const p50 = percentiles.p50_ms || 0;
            const p99 = percentiles.p99_ms || 0;
            setText('kpi-p95', `${p95.toFixed(2)} ms`);
            setText('kpi-percentiles-sub', `p50: ${p50.toFixed(2)} ms | p99: ${p99.toFixed(2)} ms`);

            if (percentileTrendChart) {
                const ts = new Date().toLocaleTimeString();
                percentileTrendChart.data.labels.push(ts);
                percentileTrendChart.data.datasets[0].data.push(p50);
                percentileTrendChart.data.datasets[1].data.push(p95);
                percentileTrendChart.data.datasets[2].data.push(p99);

                while (percentileTrendChart.data.labels.length > MAX_DATA_POINTS) {
                    percentileTrendChart.data.labels.shift();
                    percentileTrendChart.data.datasets.forEach(ds => ds.data.shift());
                }
                percentileTrendChart.update('none');
            }
        }

        if (migration) {
            setText('kpi-migration', `${(migration.mlkem_percentage || 0).toFixed(1)}%`);
            const growth = migration.mlkem_daily_growth || '+0.00%';
            const status = migration.status || 'unknown';
            setText('kpi-migration-sub', `Target ${migration.migration_target || 80}% • ${status}`);
            setText('kpi-migration-meta', `Daily growth ${growth}`);

            if (migrationTrendChart && Array.isArray(migration.trend)) {
                migrationTrendChart.data.labels = migration.trend.map(t => t.date?.slice(5) || '');
                migrationTrendChart.data.datasets[0].data = migration.trend.map(t => t.rsa_percentage || 0);
                migrationTrendChart.data.datasets[1].data = migration.trend.map(t => t.mlkem_percentage || 0);
                migrationTrendChart.update('none');
            }
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
                box.innerHTML = `
                    <div>Latency: ${comparison.comparison?.latency_verdict || 'N/A'}</div>
                    <div>Throughput: ${comparison.comparison?.throughput_verdict || 'N/A'}</div>
                    <div>Key size delta: ${(comparison.comparison?.size_delta_pct ?? 0).toFixed(1)}%</div>
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
