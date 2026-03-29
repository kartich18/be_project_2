# Code Templates: Copy-Paste Ready Implementations

This document contains production-ready code snippets you can directly use in your project.

---

## 1. DATABASE SCHEMA (SQL)

### Add Columns to Existing transactions Table
```sql
ALTER TABLE transactions ADD COLUMN latency_bucket VARCHAR(50) DEFAULT NULL;
ALTER TABLE transactions ADD COLUMN failure_reason VARCHAR(255) DEFAULT NULL;
ALTER TABLE transactions ADD KEY idx_latency_bucket (latency_bucket);
ALTER TABLE transactions ADD KEY idx_failure_reason (failure_reason);
```

### Create key_metadata Table
```sql
CREATE TABLE IF NOT EXISTS key_metadata (
  key_id VARCHAR(36) PRIMARY KEY,
  algorithm VARCHAR(20) NOT NULL,  -- 'RSA-2048', 'ML-KEM'
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_used_at TIMESTAMP NULL,
  rotation_due_at TIMESTAMP NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active', 'pending_rotation', 'rotated', 'revoked'
  key_version INT DEFAULT 1,
  created_date DATE GENERATED ALWAYS AS (DATE(created_at)) STORED,
  INDEX idx_algorithm_status (algorithm, status),
  INDEX idx_rotation_due_at (rotation_due_at),
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Create daily_migration_snapshot Table
```sql
CREATE TABLE IF NOT EXISTS daily_migration_snapshot (
  snapshot_id INT AUTO_INCREMENT PRIMARY KEY,
  snapshot_date DATE NOT NULL UNIQUE,
  rsa_count INT DEFAULT 0,
  mlkem_count INT DEFAULT 0,
  hybrid_count INT DEFAULT 0,
  total_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_snapshot_date (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Create security_events Table
```sql
CREATE TABLE IF NOT EXISTS security_events (
  event_id VARCHAR(36) PRIMARY KEY,
  event_date DATE GENERATED ALWAYS AS (DATE(timestamp)) STORED,
  timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  event_type VARCHAR(50) NOT NULL,  -- 'decryption_failure', 'validation_error', 'policy_rejected'
  algorithm VARCHAR(20),
  sender VARCHAR(50),
  receiver VARCHAR(50),
  error_message VARCHAR(500),
  latency_ms DECIMAL(10, 2),
  INDEX idx_timestamp (timestamp),
  INDEX idx_event_date (event_date),
  INDEX idx_algorithm_timestamp (algorithm, timestamp),
  INDEX idx_event_type (event_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Create anomalies Table
```sql
CREATE TABLE IF NOT EXISTS anomalies (
  anomaly_id VARCHAR(36) PRIMARY KEY,
  detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  detected_date DATE GENERATED ALWAYS AS (DATE(detected_at)) STORED,
  anomaly_type VARCHAR(50) NOT NULL,  -- 'latency_spike', 'failure_rate_spike', 'algorithm_shift'
  severity VARCHAR(20) NOT NULL,  -- 'info', 'warning', 'critical'
  metric_name VARCHAR(100),
  baseline_value DECIMAL(15, 4),
  current_value DECIMAL(15, 4),
  delta_pct DECIMAL(10, 2),
  description TEXT,
  acknowledged BOOLEAN DEFAULT FALSE,
  resolved BOOLEAN DEFAULT FALSE,
  INDEX idx_detected_at (detected_at),
  INDEX idx_severity (severity),
  INDEX idx_resolved (resolved)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 2. BACKEND API ENDPOINTS (Node.js/Express)

### 2.1 Latency Percentiles Endpoint

```javascript
const express = require('express');
const router = express.Router();

// GET /api/v1/analytics/latency-percentiles
router.get('/latency-percentiles', async (req, res) => {
  try {
    const { algorithm, time_window = '24h' } = req.query;
    
    // Parse time window to milliseconds
    const timeWindowMs = parseTimeWindow(time_window);
    const cutoffTime = new Date(Date.now() - timeWindowMs);
    
    // Validate algorithm
    if (algorithm && !['RSA-2048', 'ML-KEM'].includes(algorithm)) {
      return res.status(400).json({ error: 'Invalid algorithm' });
    }
    
    // Query transactions
    const query = `
      SELECT total_ms FROM transactions 
      WHERE timestamp > ? 
      ${algorithm ? 'AND method = ?' : ''}
      ORDER BY total_ms ASC
    `;
    
    const params = [cutoffTime];
    if (algorithm) params.push(algorithm);
    
    const transactions = await db.query(query, params);
    
    if (transactions.length === 0) {
      return res.json({
        algorithm: algorithm || 'all',
        time_window,
        samples: 0,
        p50_ms: null,
        p95_ms: null,
        p99_ms: null,
        trend_p95: '0%',
        timestamp: new Date().toISOString()
      });
    }
    
    // Extract latency values
    const latencies = transactions.map(t => t.total_ms);
    
    // Calculate percentiles
    const p50 = percentile(latencies, 0.50);
    const p95 = percentile(latencies, 0.95);
    const p99 = percentile(latencies, 0.99);
    
    // Get previous period for trend
    const previousCutoff = new Date(cutoffTime.getTime() - timeWindowMs);
    const prevQuery = `
      SELECT AVG(total_ms) as avg_latency FROM transactions 
      WHERE timestamp > ? AND timestamp <= ?
      ${algorithm ? 'AND method = ?' : ''}
    `;
    const prevParams = [previousCutoff, cutoffTime];
    if (algorithm) prevParams.push(algorithm);
    
    const prevResult = await db.query(prevQuery, prevParams);
    const prevP95 = prevResult[0]?.avg_latency || p95;
    const trend = ((p95 - prevP95) / prevP95) * 100;
    
    res.json({
      algorithm: algorithm || 'all',
      time_window,
      samples: transactions.length,
      p50_ms: parseFloat(p50.toFixed(2)),
      p95_ms: parseFloat(p95.toFixed(2)),
      p99_ms: parseFloat(p99.toFixed(2)),
      trend_p95: (trend > 0 ? '+' : '') + trend.toFixed(1) + '%',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error calculating latency percentiles:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// Helper function: Calculate percentile
function percentile(arr, p) {
  if (arr.length === 0) return 0;
  const index = Math.ceil(arr.length * p) - 1;
  return arr[Math.max(0, Math.min(index, arr.length - 1))];
}

// Helper function: Parse time window string
function parseTimeWindow(window) {
  const matches = window.match(/(\d+)([hd])/);
  if (!matches) return 24 * 60 * 60 * 1000; // Default 24h
  
  const value = parseInt(matches[1]);
  const unit = matches[2];
  
  if (unit === 'h') return value * 60 * 60 * 1000;
  if (unit === 'd') return value * 24 * 60 * 60 * 1000;
  return 24 * 60 * 60 * 1000;
}

module.exports = router;
```

### 2.2 Migration Status Endpoint

```javascript
// GET /api/v1/analytics/migration-status
router.get('/migration-status', async (req, res) => {
  try {
    const { time_window = '24h' } = req.query;
    const timeWindowMs = parseTimeWindow(time_window);
    const cutoffTime = new Date(Date.now() - timeWindowMs);
    
    // Count transactions by algorithm
    const [rsaResult, mlkemResult, totalResult] = await Promise.all([
      db.query(
        'SELECT COUNT(*) as count FROM transactions WHERE method = ? AND timestamp > ?',
        ['RSA-2048', cutoffTime]
      ),
      db.query(
        'SELECT COUNT(*) as count FROM transactions WHERE method = ? AND timestamp > ?',
        ['ML-KEM', cutoffTime]
      ),
      db.query(
        'SELECT COUNT(*) as count FROM transactions WHERE timestamp > ?',
        [cutoffTime]
      )
    ]);
    
    const rsaCount = rsaResult[0]?.count || 0;
    const mlkemCount = mlkemResult[0]?.count || 0;
    const totalCount = totalResult[0]?.count || 1; // Avoid division by zero
    
    // Calculate percentages
    const rsaPct = (rsaCount / totalCount) * 100;
    const mlkemPct = (mlkemCount / totalCount) * 100;
    
    // Get yesterday's ML-KEM count for growth rate
    const yesterdayStart = new Date(cutoffTime.getTime() - timeWindowMs);
    const yesterdayEnd = cutoffTime;
    
    const yesterdayResult = await db.query(
      'SELECT COUNT(*) as count FROM transactions WHERE method = ? AND timestamp > ? AND timestamp < ?',
      ['ML-KEM', yesterdayStart, yesterdayEnd]
    );
    
    const yesterdayMlkem = yesterdayResult[0]?.count || mlkemCount;
    const dailyGrowth = yesterdayMlkem === 0 
      ? 0 
      : ((mlkemCount - yesterdayMlkem) / yesterdayMlkem) * 100;
    
    // Predict days to target (80%)
    const mlkemTarget = 80;
    const daysToTarget = dailyGrowth === 0 
      ? Infinity 
      : ((mlkemTarget - mlkemPct) / (dailyGrowth / 24));
    
    const status = dailyGrowth >= 2 ? 'on_track' : dailyGrowth > 0 ? 'slow' : 'at_risk';
    
    res.json({
      time_window,
      total_transactions: totalCount,
      rsa_count: rsaCount,
      mlkem_count: mlkemCount,
      hybrid_count: 0,
      rsa_percentage: parseFloat(rsaPct.toFixed(1)),
      mlkem_percentage: parseFloat(mlkemPct.toFixed(1)),
      hybrid_percentage: 0,
      mlkem_daily_growth: (dailyGrowth > 0 ? '+' : '') + dailyGrowth.toFixed(1) + '%',
      migration_target: 80,
      days_to_target: daysToTarget === Infinity ? null : Math.ceil(daysToTarget),
      status,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error calculating migration status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});
```

### 2.3 Key Rotation Health Endpoint

```javascript
// GET /api/v1/keys/rotation-health
router.get('/rotation-health', async (req, res) => {
  try {
    const keys = await db.query(`
      SELECT key_id, algorithm, created_at, 
             DATE_ADD(created_at, INTERVAL 90 DAY) as rotation_due_at, 
             status 
      FROM key_metadata 
      WHERE status IN ('active', 'pending_rotation')
    `);
    
    const now = new Date();
    let overdueCount = 0;
    let pendingCount = 0;
    let activeCount = 0;
    let totalAgeDays = 0;
    
    const algorithmStats = {
      'RSA-2048': { active: 0, pending: 0, overdue: 0 },
      'ML-KEM': { active: 0, pending: 0, overdue: 0 }
    };
    
    keys.forEach(key => {
      const ageMs = now - new Date(key.created_at).getTime();
      const ageDays = ageMs / (1000 * 60 * 60 * 24);
      totalAgeDays += ageDays;
      
      const rotationDueTime = new Date(key.rotation_due_at).getTime();
      const daysUntilRotation = (rotationDueTime - now.getTime()) / (1000 * 60 * 60 * 24);
      
      if (key.status === 'active') {
        activeCount++;
        algorithmStats[key.algorithm].active++;
        
        if (daysUntilRotation < 0) {
          overdueCount++;
          algorithmStats[key.algorithm].overdue++;
        } else if (daysUntilRotation < 7) {
          pendingCount++;
          algorithmStats[key.algorithm].pending++;
        }
      }
    });
    
    // Calculate compliance score
    let complianceScore = 100;
    const totalKeys = keys.length || 1;
    
    complianceScore -= (overdueCount / totalKeys) * 30;  // Severe penalty
    complianceScore -= (pendingCount / totalKeys) * 10;  // Minor penalty
    
    const avgAge = totalAgeDays / totalKeys;
    if (avgAge > 60) {
      complianceScore -= Math.min(20, ((avgAge - 60) / 60) * 20);
    }
    
    // Determine health status
    let healthStatus = 'excellent';
    if (complianceScore >= 95) healthStatus = 'excellent';
    else if (complianceScore >= 85) healthStatus = 'good';
    else if (complianceScore >= 70) healthStatus = 'fair';
    else healthStatus = 'critical';
    
    // Find next rotation date
    const nextRotationKey = keys.find(k => k.status === 'pending_rotation');
    const nextRotationDate = nextRotationKey 
      ? new Date(nextRotationKey.rotation_due_at).toISOString().split('T')[0]
      : null;
    
    res.json({
      total_keys: totalKeys,
      keys_active: activeCount,
      keys_pending_rotation: pendingCount,
      keys_overdue_rotation: overdueCount,
      avg_age_days: parseFloat(avgAge.toFixed(1)),
      avg_days_until_rotation: parseFloat(((avgAge) - 90).toFixed(1)),
      overdue_percentage: parseFloat(((overdueCount / totalKeys) * 100).toFixed(1)),
      compliance_score: parseFloat(complianceScore.toFixed(1)),
      health_status: healthStatus,
      next_rotation_date: nextRotationDate,
      keys_by_algorithm: algorithmStats,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error calculating key rotation health:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});
```

### 2.4 Algorithm Comparison Endpoint

```javascript
// GET /api/v1/analytics/algorithm-comparison
router.get('/algorithm-comparison', async (req, res) => {
  try {
    const { metric = 'latency', time_window = '24h' } = req.query;
    const timeWindowMs = parseTimeWindow(time_window);
    const cutoffTime = new Date(Date.now() - timeWindowMs);
    
    // Get stats for both algorithms
    const [rsaStats, mlkemStats] = await Promise.all([
      db.query(`
        SELECT 
          COUNT(*) as samples,
          AVG(total_ms) as avg_latency_ms,
          MAX(total_ms) as max_latency_ms,
          MIN(total_ms) as min_latency_ms,
          PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_ms) as p99_latency_ms,
          AVG(key_size_b) as avg_key_size_b,
          AVG(cipher_size_b) as avg_cipher_size_b
        FROM transactions 
        WHERE method = 'RSA-2048' AND timestamp > ?
      `, [cutoffTime]),
      db.query(`
        SELECT 
          COUNT(*) as samples,
          AVG(total_ms) as avg_latency_ms,
          MAX(total_ms) as max_latency_ms,
          MIN(total_ms) as min_latency_ms,
          PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_ms) as p99_latency_ms,
          AVG(key_size_b) as avg_key_size_b,
          AVG(cipher_size_b) as avg_cipher_size_b
        FROM transactions 
        WHERE method = 'ML-KEM' AND timestamp > ?
      `, [cutoffTime])
    ]);
    
    const rsa = rsaStats[0] || {};
    const mlkem = mlkemStats[0] || {};
    
    // Calculate deltas
    const latencyDelta = rsa.avg_latency_ms 
      ? ((mlkem.avg_latency_ms - rsa.avg_latency_ms) / rsa.avg_latency_ms) * 100 
      : 0;
    
    const p99Delta = rsa.p99_latency_ms
      ? ((mlkem.p99_latency_ms - rsa.p99_latency_ms) / rsa.p99_latency_ms) * 100
      : 0;
    
    const sizeDelta = rsa.avg_key_size_b
      ? ((mlkem.avg_key_size_b - rsa.avg_key_size_b) / rsa.avg_key_size_b) * 100
      : 0;
    
    const throughput_rsa = (rsa.samples || 0) / (timeWindowMs / 1000);
    const throughput_mlkem = (mlkem.samples || 0) / (timeWindowMs / 1000);
    const throughputDelta = throughput_rsa > 0
      ? ((throughput_mlkem - throughput_rsa) / throughput_rsa) * 100
      : 0;
    
    // Generate verdicts
    const latencyVerdict = latencyDelta < -5 
      ? `ML-KEM is ${Math.abs(latencyDelta).toFixed(1)}% faster`
      : latencyDelta > 5
      ? `RSA-2048 is ${latencyDelta.toFixed(1)}% faster`
      : 'Similar latency';
    
    const throughputVerdict = throughputDelta > 10
      ? `ML-KEM handles ${throughputDelta.toFixed(1)}% more tx/sec`
      : 'Similar throughput';
    
    const recommendation = `ML-KEM is quantum-safe and ${
      latencyDelta < 0 ? 'faster' : 'comparable'
    } in speed; accept ${sizeDelta.toFixed(0)}% larger keys for post-quantum security`;
    
    res.json({
      time_window,
      comparison_date: cutoffTime.toISOString().split('T')[0],
      rsa_2048: {
        samples: rsa.samples || 0,
        avg_latency_ms: parseFloat((rsa.avg_latency_ms || 0).toFixed(1)),
        p99_latency_ms: parseFloat((rsa.p99_latency_ms || 0).toFixed(1)),
        min_latency_ms: parseFloat((rsa.min_latency_ms || 0).toFixed(1)),
        max_latency_ms: parseFloat((rsa.max_latency_ms || 0).toFixed(1)),
        avg_key_size_b: rsa.avg_key_size_b || 0,
        avg_cipher_size_b: rsa.avg_cipher_size_b || 0,
        throughput_tx_per_sec: parseFloat(throughput_rsa.toFixed(2))
      },
      ml_kem: {
        samples: mlkem.samples || 0,
        avg_latency_ms: parseFloat((mlkem.avg_latency_ms || 0).toFixed(1)),
        p99_latency_ms: parseFloat((mlkem.p99_latency_ms || 0).toFixed(1)),
        min_latency_ms: parseFloat((mlkem.min_latency_ms || 0).toFixed(1)),
        max_latency_ms: parseFloat((mlkem.max_latency_ms || 0).toFixed(1)),
        avg_key_size_b: mlkem.avg_key_size_b || 0,
        avg_cipher_size_b: mlkem.avg_cipher_size_b || 0,
        throughput_tx_per_sec: parseFloat(throughput_mlkem.toFixed(2))
      },
      comparison: {
        latency_delta_pct: parseFloat(latencyDelta.toFixed(1)),
        p99_delta_pct: parseFloat(p99Delta.toFixed(1)),
        latency_verdict: latencyVerdict,
        size_delta_pct: parseFloat(sizeDelta.toFixed(1)),
        throughput_delta_pct: parseFloat(throughputDelta.toFixed(1)),
        throughput_verdict: throughputVerdict,
        recommendation
      }
    });
  } catch (error) {
    console.error('Error comparing algorithms:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});
```

### 2.5 Security Health & Anomalies Endpoint

```javascript
// GET /api/v1/analytics/security-health
router.get('/security-health', async (req, res) => {
  try {
    const { time_window = '24h', algorithm } = req.query;
    const timeWindowMs = parseTimeWindow(time_window);
    const cutoffTime = new Date(Date.now() - timeWindowMs);
    
    let query = 'SELECT COUNT(*) as count FROM transactions WHERE timestamp > ?';
    let params = [cutoffTime];
    
    if (algorithm) {
      query += ' AND method = ?';
      params.push(algorithm);
    }
    
    const totalResult = await db.query(query, params);
    const totalAttempts = totalResult[0]?.count || 0;
    
    // Count successful transactions
    query = 'SELECT COUNT(*) as count FROM transactions WHERE status = ? AND timestamp > ?';
    params = ['success', cutoffTime];
    if (algorithm) {
      query += ' AND method = ?';
      params.push(algorithm);
    }
    
    const successResult = await db.query(query, params);
    const successful = successResult[0]?.count || 0;
    
    // Count failures from security_events
    query = `SELECT 
      SUM(CASE WHEN event_type = 'decryption_failure' THEN 1 ELSE 0 END) as failed_crypto,
      SUM(CASE WHEN event_type = 'validation_failed' THEN 1 ELSE 0 END) as failed_validation,
      SUM(CASE WHEN event_type = 'policy_rejected' THEN 1 ELSE 0 END) as rejected_policy
      FROM security_events 
      WHERE timestamp > ?`;
    params = [cutoffTime];
    if (algorithm) {
      query += ' AND algorithm = ?';
      params.push(algorithm);
    }
    
    const eventResult = await db.query(query, params);
    const failedCrypto = eventResult[0]?.failed_crypto || 0;
    const failedValidation = eventResult[0]?.failed_validation || 0;
    const rejectedPolicy = eventResult[0]?.rejected_policy || 0;
    
    const failureRate = totalAttempts > 0 
      ? (((failedCrypto + failedValidation) / totalAttempts) * 100)
      : 0;
    
    const rejectionRate = totalAttempts > 0 
      ? ((rejectedPolicy / totalAttempts) * 100)
      : 0;
    
    // Determine status
    let status = 'healthy';
    let alerts = [];
    
    if (failureRate > 5) {
      status = 'critical';
      alerts.push('High failure rate detected');
    } else if (failureRate > 1) {
      status = 'warning';
      alerts.push('Elevated failure rate');
    }
    
    if (rejectionRate > 2) {
      alerts.push('Policy rejections elevated');
    }
    
    res.json({
      time_window,
      algorithm: algorithm || 'all',
      total_attempts: totalAttempts,
      successful,
      failed_crypto: failedCrypto,
      failed_validation: failedValidation,
      rejected_policy: rejectedPolicy,
      failure_rate_pct: parseFloat(failureRate.toFixed(2)),
      rejection_rate_pct: parseFloat(rejectionRate.toFixed(2)),
      status,
      alerts,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error calculating security health:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /api/v1/analytics/anomalies
router.get('/anomalies', async (req, res) => {
  try {
    const anomalies = await db.query(`
      SELECT 
        anomaly_id,
        anomaly_type,
        severity,
        metric_name,
        baseline_value,
        current_value,
        delta_pct,
        description,
        detected_at
      FROM anomalies 
      WHERE resolved = FALSE 
      ORDER BY detected_at DESC 
      LIMIT 10
    `);
    
    res.json({
      detected_anomalies: anomalies.map(a => ({
        type: a.anomaly_type,
        severity: a.severity,
        metric: a.metric_name,
        baseline: parseFloat(a.baseline_value),
        current: parseFloat(a.current_value),
        delta_pct: parseFloat(a.delta_pct),
        detected_at: a.detected_at.toISOString(),
        recommendation: a.description
      })),
      health_status: anomalies.some(a => a.severity === 'critical') 
        ? 'attention_required' 
        : 'normal'
    });
  } catch (error) {
    console.error('Error fetching anomalies:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});
```

---

## 3. FRONTEND CODE (JavaScript/HTML/CSS)

### 3.1 KPI Card Component (HTML + CSS)

```html
<style>
  .kpi-card {
    background: var(--color-background-secondary, #F1EFE8);
    border: 0.5px solid var(--color-border-tertiary, #B4B2A9);
    border-radius: 8px;
    padding: 16px;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .kpi-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }

  .kpi-card-label {
    font-size: 11px;
    color: var(--color-text-secondary, #5F5E5A);
    font-weight: 500;
    margin-bottom: 8px;
  }

  .kpi-card-value {
    font-size: 32px;
    font-weight: 500;
    color: var(--color-text-primary, #2C2C2A);
    margin-bottom: 4px;
  }

  .kpi-card-subtext {
    font-size: 11px;
    color: var(--color-text-secondary, #5F5E5A);
    margin-bottom: 12px;
  }

  .kpi-progress-bar {
    width: 100%;
    height: 8px;
    background: var(--color-border-tertiary, #B4B2A9);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 12px;
  }

  .kpi-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #534AB7, #0F6E56);
    transition: width 0.5s ease-out;
  }

  .kpi-card-meta {
    font-size: 10px;
    color: var(--color-text-tertiary, #888780);
  }
</style>

<div class="kpi-card" id="migrationCard">
  <div class="kpi-card-label">Migration Progress</div>
  <div class="kpi-card-value" id="migrationValue">--</div>
  <div class="kpi-card-subtext" id="migrationSubtext">Target: 80% ML-KEM</div>
  <div class="kpi-progress-bar">
    <div class="kpi-progress-fill" id="migrationProgressFill"></div>
  </div>
  <div class="kpi-card-meta" id="migrationMeta">Loading...</div>
</div>
```

### 3.2 Data Binding JavaScript

```javascript
// Configuration
const API_BASE = '/api/v1';
const REFRESH_INTERVALS = {
  kpi: 30000,      // 30 seconds
  charts: 300000,  // 5 minutes
  anomalies: 120000 // 2 minutes
};

// State
let timeWindow = localStorage.getItem('dashboardTimeWindow') || '24h';
let charts = {};

// Initialize dashboard
async function initDashboard() {
  console.log('Initializing dashboard...');
  
  // Set up time window selector
  const timeWindowSelect = document.getElementById('timeWindow');
  if (timeWindowSelect) {
    timeWindowSelect.value = timeWindow;
    timeWindowSelect.addEventListener('change', (e) => {
      timeWindow = e.target.value;
      localStorage.setItem('dashboardTimeWindow', timeWindow);
      loadAllData();
    });
  }
  
  // Initial load
  loadAllData();
  
  // Set up refresh intervals
  setInterval(() => loadKPIData(), REFRESH_INTERVALS.kpi);
  setInterval(() => loadCharts(), REFRESH_INTERVALS.charts);
  setInterval(() => loadAnomalies(), REFRESH_INTERVALS.anomalies);
}

// Load all data
async function loadAllData() {
  await Promise.all([
    loadKPIData(),
    loadCharts(),
    loadAnomalies()
  ]);
}

// Load KPI cards
async function loadKPIData() {
  try {
    // Load migration status
    const migration = await fetch(
      `${API_BASE}/analytics/migration-status?time_window=${timeWindow}`
    ).then(r => r.json());
    
    updateMigrationCard(migration);
    
    // Load key rotation health
    const health = await fetch(`${API_BASE}/keys/rotation-health`)
      .then(r => r.json());
    
    updateHealthCard(health);
    
    // Load security health
    const security = await fetch(
      `${API_BASE}/analytics/security-health?time_window=${timeWindow}`
    ).then(r => r.json());
    
    updateSecurityCard(security);
    
    // Load latency percentiles
    const latency = await fetch(
      `${API_BASE}/analytics/latency-percentiles?time_window=${timeWindow}`
    ).then(r => r.json());
    
    updateLatencyCard(latency);
    
  } catch (error) {
    console.error('Error loading KPI data:', error);
  }
}

// Update migration card
function updateMigrationCard(data) {
  const card = document.getElementById('migrationCard');
  if (!card) return;
  
  document.getElementById('migrationValue').textContent = 
    data.mlkem_percentage + '%';
  
  document.getElementById('migrationSubtext').textContent = 
    `Target: 80% ML-KEM`;
  
  const fillPercentage = Math.min(100, (data.mlkem_percentage / 80) * 100);
  document.getElementById('migrationProgressFill').style.width = fillPercentage + '%';
  
  const daysText = data.days_to_target === null 
    ? 'N/A' 
    : data.days_to_target + ' days';
  
  document.getElementById('migrationMeta').textContent = 
    `${data.status === 'on_track' ? '✓' : '⚠'} ${data.status} • ${data.mlkem_daily_growth} daily • ${daysText} to target`;
  
  // Color code based on status
  const color = data.status === 'on_track' ? '#0F6E56' : '#BA7517';
  card.style.borderColor = color;
}

// Update health card
function updateHealthCard(data) {
  const card = document.getElementById('healthCard');
  if (!card) return;
  
  document.getElementById('healthValue').textContent = 
    data.compliance_score + '%';
  
  const statusEmoji = data.health_status === 'excellent' ? '✓' : 
                      data.health_status === 'good' ? '✓' :
                      data.health_status === 'fair' ? '⚠' : '🚨';
  
  document.getElementById('healthMeta').textContent = 
    `${statusEmoji} ${data.health_status}${data.keys_overdue_rotation > 0 
      ? ' • ' + data.keys_overdue_rotation + ' overdue' 
      : ''}`;
}

// Update security card
function updateSecurityCard(data) {
  const card = document.getElementById('securityCard');
  if (!card) return;
  
  document.getElementById('securityValue').textContent = 
    data.failure_rate_pct.toFixed(2) + '%';
  
  const statusEmoji = data.status === 'healthy' ? '✓' :
                      data.status === 'warning' ? '⚠' : '🚨';
  
  document.getElementById('securityMeta').textContent = 
    `${statusEmoji} ${data.status} • ${data.failed_crypto} failures`;
  
  const color = data.status === 'healthy' ? '#0F6E56' :
                data.status === 'warning' ? '#BA7517' : '#A32D2D';
  card.style.borderColor = color;
}

// Update latency card
function updateLatencyCard(data) {
  const card = document.getElementById('latencyCard');
  if (!card) return;
  
  document.getElementById('latencyValue').textContent = 
    data.p95_ms + 'ms';
  
  document.getElementById('latencySubtext').textContent = 
    `p50: ${data.p50_ms}ms • p99: ${data.p99_ms}ms`;
  
  document.getElementById('latencyMeta').textContent = 
    `${data.trend_p95} trend • ${data.samples} samples`;
}

// Load charts
async function loadCharts() {
  try {
    // Fetch migration trend data
    const migrationData = await fetch(
      `${API_BASE}/analytics/migration-status?time_window=30d`
    ).then(r => r.json());
    
    // Fetch latency percentiles
    const latencyData = await fetch(
      `${API_BASE}/analytics/latency-percentiles?time_window=${timeWindow}`
    ).then(r => r.json());
    
    // Create or update charts
    // (Chart.js implementation shown below)
  } catch (error) {
    console.error('Error loading charts:', error);
  }
}

// Load anomalies
async function loadAnomalies() {
  try {
    const response = await fetch(`${API_BASE}/analytics/anomalies`)
      .then(r => r.json());
    
    displayAnomalies(response.detected_anomalies);
  } catch (error) {
    console.error('Error loading anomalies:', error);
  }
}

// Display anomalies
function displayAnomalies(anomalies) {
  const panel = document.getElementById('anomalyPanel');
  if (!panel) return;
  
  panel.innerHTML = '';
  
  if (anomalies.length === 0) {
    panel.innerHTML = '<div style="padding: 16px; color: var(--color-text-secondary);">No anomalies detected</div>';
    return;
  }
  
  anomalies.forEach(anomaly => {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert-item alert-${anomaly.severity}`;
    alertDiv.innerHTML = `
      <div class="alert-title">
        ${anomaly.severity === 'critical' ? '🚨' : '⚠️'} 
        ${anomaly.type.replace(/_/g, ' ').toUpperCase()}
      </div>
      <div class="alert-content">
        ${anomaly.metric}: ${anomaly.baseline.toFixed(1)} → ${anomaly.current.toFixed(1)} (${anomaly.delta_pct.toFixed(1)}%)
      </div>
      <div class="alert-meta">
        Detected: ${new Date(anomaly.detected_at).toLocaleTimeString()}
      </div>
      <button class="btn-dismiss" onclick="this.parentElement.remove()">Dismiss</button>
    `;
    panel.appendChild(alertDiv);
  });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initDashboard);
```

### 3.3 Chart.js Implementation

```javascript
let migrationChart = null;
let latencyChart = null;

function createMigrationChart() {
  const ctx = document.getElementById('migrationChart');
  if (!ctx) return;
  
  if (migrationChart) migrationChart.destroy();
  
  migrationChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: generateDateLabels(30), // Last 30 days
      datasets: [
        {
          label: 'RSA-2048',
          data: [/* API data */],
          borderColor: '#993C1D',
          backgroundColor: 'rgba(153, 60, 29, 0.05)',
          borderWidth: 2,
          tension: 0.4,
          fill: false,
          pointRadius: 3,
          pointBackgroundColor: '#993C1D'
        },
        {
          label: 'ML-KEM',
          data: [/* API data */],
          borderColor: '#0F6E56',
          backgroundColor: 'rgba(15, 110, 86, 0.1)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: '#0F6E56'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top'
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          ticks: { callback: value => value + '%' }
        }
      }
    }
  });
}

function createLatencyChart() {
  const ctx = document.getElementById('latencyChart');
  if (!ctx) return;
  
  if (latencyChart) latencyChart.destroy();
  
  latencyChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: generateHourLabels(24), // Last 24 hours
      datasets: [
        {
          label: 'p50',
          data: [/* API data */],
          borderColor: '#0F6E56',
          borderWidth: 2,
          tension: 0.4,
          pointRadius: 2
        },
        {
          label: 'p95',
          data: [/* API data */],
          borderColor: '#185FA5',
          borderWidth: 2,
          borderDash: [5, 5],
          tension: 0.4,
          pointRadius: 2
        },
        {
          label: 'p99',
          data: [/* API data */],
          borderColor: '#A32D2D',
          borderWidth: 2,
          borderDash: [10, 5],
          tension: 0.4,
          pointRadius: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true, position: 'top' }
      },
      scales: {
        y: {
          ticks: { callback: value => value + 'ms' }
        }
      }
    }
  });
}

function generateDateLabels(days) {
  return Array.from({length: days}, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (days - i - 1));
    return (d.getMonth() + 1) + '/' + d.getDate();
  });
}

function generateHourLabels(hours) {
  return Array.from({length: hours}, (_, i) => {
    const d = new Date();
    d.setHours(d.getHours() - (hours - i - 1));
    return d.getHours() + ':00';
  });
}
```

---

## 4. UTILITY FUNCTIONS

### 4.1 Time Window Parser

```javascript
function parseTimeWindow(window) {
  if (!window) return 24 * 60 * 60 * 1000; // Default 24h
  
  const match = window.match(/(\d+)([hd])/);
  if (!match) return 24 * 60 * 60 * 1000;
  
  const value = parseInt(match[1]);
  const unit = match[2];
  
  if (unit === 'h') return value * 60 * 60 * 1000;
  if (unit === 'd') return value * 24 * 60 * 60 * 1000;
  
  return 24 * 60 * 60 * 1000;
}
```

### 4.2 Percentile Calculator

```javascript
function calculatePercentile(arr, percentile) {
  if (arr.length === 0) return 0;
  
  const sorted = [...arr].sort((a, b) => a - b);
  const index = Math.ceil(sorted.length * percentile) - 1;
  
  return sorted[Math.max(0, Math.min(index, sorted.length - 1))];
}
```

### 4.3 Spike Detection

```javascript
function detectSpike(current, baseline, threshold = 1.3) {
  if (baseline === 0) return false;
  return current > baseline * threshold;
}

function calculateDelta(current, baseline) {
  if (baseline === 0) return 0;
  return ((current - baseline) / baseline) * 100;
}
```

---

This file provides copy-paste ready code for all major components. Adjust database queries for your specific SQL dialect (PostgreSQL, MySQL, etc.).
