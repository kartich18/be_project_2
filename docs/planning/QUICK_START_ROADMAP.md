# Implementation Roadmap: Quick Start Guide

## 🎯 Top 5 Metrics (Selected for Maximum Impact)

### 1. **Latency Percentiles (p50, p95, p99)** ⭐⭐⭐⭐⭐
**Why**: Reveals hidden performance degradation that averages mask
- Average can be 85ms while 1% of users experience 500ms
- **Business Impact**: SLA compliance, customer experience
- **Effort**: Medium (requires aggregation logic)
- **Visibility**: High (clearly shows performance trends)

### 2. **Post-Quantum Migration Status** ⭐⭐⭐⭐⭐
**Why**: Quantifies your quantum-safe readiness—differentiates your project
- Track RSA→ML-KEM adoption with daily growth rate
- Predict when you'll hit 80% ML-KEM
- **Business Impact**: Regulatory compliance, security posture
- **Effort**: Low (simple counting + math)
- **Visibility**: High (single percentage metric + trajectory)

### 3. **Key Rotation Health Index** ⭐⭐⭐⭐
**Why**: Demonstrates cryptographic hygiene for compliance audits
- Shows which keys are overdue, pending, or healthy
- Compliance score (98.8%) is audit-friendly metric
- **Business Impact**: PCI-DSS, SOC 2 compliance
- **Effort**: Medium (requires key metadata tracking)
- **Visibility**: Medium (single score + warning count)

### 4. **Algorithm Performance Ratio** ⭐⭐⭐⭐
**Why**: Cost-benefit analysis of hybrid encryption approach
- Shows ML-KEM is 15% faster but has 3x larger keys
- Justifies infrastructure investment
- **Business Impact**: Resource planning, migration business case
- **Effort**: Low (aggregation of existing metrics)
- **Visibility**: High (side-by-side comparison)

### 5. **Encryption Failure Rate + Anomaly Detection** ⭐⭐⭐⭐⭐
**Why**: Real-time security incident visibility
- Detect spikes, unusual patterns, failures
- Actionable alerts for on-call engineers
- **Business Impact**: Security incident prevention
- **Effort**: Medium (aggregation + spike detection logic)
- **Visibility**: High (critical alerts + trend)

---

## 📋 Phase 1: Backend API Implementation (Week 1)

### Day 1-2: Database & Schema

**Task 1.1: Extend Transactions Table**
```sql
-- Add columns to existing transactions table
ALTER TABLE transactions ADD COLUMN latency_bucket VARCHAR(50);
ALTER TABLE transactions ADD COLUMN failure_reason VARCHAR(255);

-- Example values:
-- latency_bucket: '<50ms', '50-100ms', '100-200ms', '200-500ms', '>500ms'
-- failure_reason: NULL for success, 'validation_failed', 'key_not_found', etc.
```
- **Time**: 30 minutes
- **Skills**: SQL
- **Checklist**:
  - [ ] Columns added
  - [ ] Indexes added on latency_bucket, failure_reason
  - [ ] Backward compatible (existing data has NULL values)

**Task 1.2: Create Key Metadata Table**
```sql
CREATE TABLE key_metadata (
  key_id VARCHAR(36) PRIMARY KEY,
  algorithm VARCHAR(20),  -- 'RSA-2048', 'ML-KEM'
  created_at TIMESTAMP,
  last_used_at TIMESTAMP,
  rotation_due_at TIMESTAMP,
  status VARCHAR(20),  -- 'active', 'pending_rotation', 'rotated', 'revoked'
  key_version INT
);

CREATE INDEX idx_key_algorithm_status ON key_metadata(algorithm, status);
CREATE INDEX idx_rotation_due_at ON key_metadata(rotation_due_at);
```
- **Time**: 30 minutes
- **Skills**: SQL database design
- **Checklist**:
  - [ ] Table created
  - [ ] Indexes created
  - [ ] Sample data inserted (for testing)

**Task 1.3: Create Daily Snapshots & Audit Tables**
```sql
CREATE TABLE daily_migration_snapshot (
  snapshot_date DATE PRIMARY KEY,
  rsa_count INT,
  mlkem_count INT,
  hybrid_count INT,
  total_count INT,
  created_at TIMESTAMP
);

CREATE TABLE key_rotation_audit (
  rotation_id VARCHAR(36) PRIMARY KEY,
  old_key_id VARCHAR(36),
  new_key_id VARCHAR(36),
  rotated_at TIMESTAMP,
  rotation_reason VARCHAR(50),  -- 'manual', 'auto', 'overdue'
  created_at TIMESTAMP
);

CREATE TABLE security_events (
  event_id VARCHAR(36) PRIMARY KEY,
  timestamp TIMESTAMP,
  event_type VARCHAR(50),  -- 'decryption_failure', 'validation_error'
  algorithm VARCHAR(20),
  sender VARCHAR(50),
  receiver VARCHAR(50),
  error_message VARCHAR(500),
  INDEX idx_timestamp (timestamp),
  INDEX idx_algorithm_timestamp (algorithm, timestamp)
);
```
- **Time**: 45 minutes
- **Skills**: SQL
- **Checklist**:
  - [ ] All tables created
  - [ ] Indexes created
  - [ ] Retention policy documented (how long to keep old data)

---

### Day 2-3: API Endpoints (Backend Code)

**Task 1.4: Implement `/api/v1/analytics/latency-percentiles` Endpoint**
```javascript
// Pseudocode
GET /api/v1/analytics/latency-percentiles?algorithm=RSA-2048&time_window=24h

// 1. Query transactions
const transactions = db.query(`
  SELECT total_ms FROM transactions 
  WHERE algorithm = ? AND timestamp > NOW() - INTERVAL ? 
  ORDER BY total_ms ASC
`);

// 2. Calculate percentiles
const latencies = transactions.map(t => t.total_ms).sort((a,b) => a-b);
const p50 = latencies[Math.floor(latencies.length * 0.50)];
const p95 = latencies[Math.floor(latencies.length * 0.95)];
const p99 = latencies[Math.floor(latencies.length * 0.99)];

// 3. Calculate trend
const previousData = db.query(`
  SELECT AVG(total_ms) as avg FROM transactions 
  WHERE algorithm = ? AND timestamp > NOW() - INTERVAL ? - INTERVAL ?
    AND timestamp < NOW() - INTERVAL ?
`);

// 4. Return JSON
return { p50_ms, p95_ms, p99_ms, trend_p95, samples: latencies.length };
```
- **Time**: 1.5 hours
- **Skills**: Backend API development, SQL optimization
- **Checklist**:
  - [ ] Endpoint code written
  - [ ] Unit tests pass (mock data)
  - [ ] Query performance tested (< 500ms for 1M transactions)
  - [ ] Edge cases handled (empty dataset, null values)

**Task 1.5: Implement `/api/v1/analytics/migration-status` Endpoint**
```javascript
// Pseudocode
GET /api/v1/analytics/migration-status?time_window=24h

// 1. Count transactions by algorithm
const rsaCount = db.query(`SELECT COUNT(*) FROM transactions WHERE method = 'RSA-2048' AND timestamp > ?`);
const mlkemCount = db.query(`SELECT COUNT(*) FROM transactions WHERE method = 'ML-KEM' AND timestamp > ?`);
const totalCount = rsaCount + mlkemCount;

// 2. Calculate percentages
const rsaPct = (rsaCount / totalCount) * 100;
const mlkemPct = (mlkemCount / totalCount) * 100;

// 3. Calculate daily growth
const yesterdayMlkem = db.query(`SELECT COUNT(*) FROM transactions WHERE method = 'ML-KEM' AND timestamp > ? AND timestamp < ?`);
const dailyGrowth = ((mlkemCount - yesterdayMlkem) / yesterdayMlkem) * 100;

// 4. Predict days to 80% target
const daysToTarget = (100 - mlkemPct) / (dailyGrowth / 24);
const status = dailyGrowth >= 2 ? 'on_track' : 'at_risk';

return {
  rsa_percentage: rsaPct.toFixed(1),
  mlkem_percentage: mlkemPct.toFixed(1),
  mlkem_daily_growth: dailyGrowth.toFixed(1),
  days_to_target: Math.ceil(daysToTarget),
  status
};
```
- **Time**: 1 hour
- **Skills**: Backend API development
- **Checklist**:
  - [ ] Endpoint code written
  - [ ] Unit tests pass
  - [ ] Handles edge case: growth = 0% (no division by zero)
  - [ ] Response validated with sample data

**Task 1.6: Implement `/api/v1/keys/rotation-health` Endpoint**
```javascript
// Pseudocode
GET /api/v1/keys/rotation-health

// 1. Query all keys
const keys = db.query(`
  SELECT key_id, algorithm, created_at, rotation_due_at, status 
  FROM key_metadata WHERE status IN ('active', 'pending_rotation')
`);

// 2. Calculate health metrics per key
let overdue = 0, pending = 0;
let totalAgeDays = 0;
keys.forEach(key => {
  const ageDays = (Date.now() - key.created_at) / (1000*60*60*24);
  totalAgeDays += ageDays;
  if (Date.now() > key.rotation_due_at) overdue++;
  else if ((key.rotation_due_at - Date.now()) < 7*24*60*60*1000) pending++;
});

// 3. Calculate compliance score
let score = 100;
score -= (overdue / keys.length) * 30;
score -= (pending / keys.length) * 10;
score -= Math.max(0, (totalAgeDays/keys.length - 60)/60) * 20;

return {
  compliance_score: score.toFixed(1),
  keys_overdue: overdue,
  keys_pending: pending,
  health_status: score >= 95 ? 'excellent' : score >= 85 ? 'good' : 'fair'
};
```
- **Time**: 1.5 hours
- **Skills**: Backend API, business logic
- **Checklist**:
  - [ ] Endpoint code written
  - [ ] Score calculation logic correct
  - [ ] Unit tests with various scenarios
  - [ ] Response structure matches dashboard expectations

**Task 1.7: Implement `/api/v1/analytics/algorithm-comparison` Endpoint**
```javascript
// Pseudocode
GET /api/v1/analytics/algorithm-comparison?metric=latency&time_window=24h

// 1. Query stats for RSA
const rsaStats = db.query(`
  SELECT 
    COUNT(*) as samples,
    AVG(total_ms) as avg_latency,
    MAX(total_ms) as max_latency,
    AVG(key_size_b) as avg_key_size,
    AVG(cipher_size_b) as avg_cipher_size
  FROM transactions WHERE method = 'RSA-2048' AND timestamp > ?
`);

// 2. Query stats for ML-KEM (same metrics)
const mlkemStats = db.query(`
  SELECT COUNT(*), AVG(total_ms), MAX(total_ms), AVG(key_size_b), AVG(cipher_size_b)
  FROM transactions WHERE method = 'ML-KEM' AND timestamp > ?
`);

// 3. Calculate deltas
const latencyDelta = ((mlkemStats.avg - rsaStats.avg) / rsaStats.avg) * 100;
const sizeDelta = ((mlkemStats.key_size - rsaStats.key_size) / rsaStats.key_size) * 100;
const verdict = latencyDelta < 0 ? 'ML-KEM faster' : 'RSA faster';

return {
  rsa_2048: rsaStats,
  ml_kem: mlkemStats,
  comparison: { latency_delta_pct: latencyDelta, size_delta_pct: sizeDelta, verdict }
};
```
- **Time**: 1 hour
- **Skills**: Backend API, analytics
- **Checklist**:
  - [ ] Endpoint code written
  - [ ] Delta calculations correct
  - [ ] Handles small sample sizes gracefully
  - [ ] Test with real data

**Task 1.8: Implement `/api/v1/analytics/security-health` Endpoint**
```javascript
// Pseudocode
GET /api/v1/analytics/security-health?time_window=24h&algorithm=RSA-2048

// 1. Count transaction outcomes
const total = db.query(`SELECT COUNT(*) FROM transactions WHERE timestamp > ?`);
const successful = db.query(`SELECT COUNT(*) FROM transactions WHERE status = 'success' AND timestamp > ?`);
const failed = db.query(`SELECT COUNT(*) FROM security_events WHERE event_type = 'decryption_failure' AND timestamp > ?`);
const rejected = db.query(`SELECT COUNT(*) FROM security_events WHERE event_type = 'policy_rejected' AND timestamp > ?`);

// 2. Calculate rates
const failureRate = (failed / total) * 100;
const rejectionRate = (rejected / total) * 100;

// 3. Check against thresholds & set status
let status = 'healthy';
let alerts = [];
if (failureRate > 5) { status = 'critical'; alerts.push('High failure rate'); }
else if (failureRate > 1) { status = 'warning'; alerts.push('Elevated failure rate'); }

return { total, successful, failed, rejected, failure_rate_pct: failureRate, status, alerts };
```
- **Time**: 1 hour
- **Skills**: Backend API
- **Checklist**:
  - [ ] Endpoint code written
  - [ ] Status thresholds configured
  - [ ] Test with edge cases (0% failure, 100% failure)

**Task 1.9: Implement `/api/v1/analytics/anomalies` Endpoint**
- Detects: Latency spikes, failure rate spikes, algorithm shifts, key usage anomalies
- Logic: Compare current metrics vs baseline, flag if > threshold
- **Time**: 2 hours
- **Skills**: Backend API, time-series analysis, alerting logic
- **Checklist**:
  - [ ] Endpoint code written
  - [ ] 5 anomaly types detected
  - [ ] Severity scoring implemented
  - [ ] Tests verify detection thresholds

---

### Day 3: Testing & Optimization

**Task 1.10: Write Comprehensive Tests**
- Unit tests for each endpoint (mock DB, test data)
- Integration tests (real DB with test data)
- Performance tests (1M transaction queries < 500ms)
- Edge cases (empty datasets, null values, future dates)
- **Time**: 2 hours
- **Checklist**:
  - [ ] All endpoints tested
  - [ ] Test coverage > 80%
  - [ ] Query performance acceptable
  - [ ] Error messages user-friendly

**Task 1.11: Deploy to Staging**
- Push code to staging environment
- Run full test suite
- Load test with production-like data volume
- Monitor for errors, timeouts
- **Time**: 1 hour
- **Checklist**:
  - [ ] Code deployed
  - [ ] All tests passing
  - [ ] No database errors
  - [ ] Ready for frontend integration

---

## 📋 Phase 2: Frontend Implementation (Week 2)

### Day 1-2: Layout & Components

**Task 2.1: Create Dashboard HTML Structure**
```html
<div class="dashboard">
  <!-- Header -->
  <header class="dashboard-header">
    <h1>Banking API Security Dashboard</h1>
    <div class="time-window-selector">
      <select id="timeWindow">
        <option value="1h">Last 1h</option>
        <option value="24h" selected>Last 24h</option>
        <option value="7d">Last 7 days</option>
        <option value="30d">Last 30 days</option>
      </select>
    </div>
  </header>
  
  <!-- KPI Cards Row -->
  <div class="kpi-cards">
    <div class="kpi-card" id="migrationCard">
      <div class="kpi-label">Migration Progress</div>
      <div class="kpi-value">--</div>
      <div class="kpi-subtext">--</div>
      <div class="kpi-progress-bar"><div class="progress-fill"></div></div>
      <div class="kpi-meta">--</div>
    </div>
    <!-- 3 more cards... -->
  </div>
  
  <!-- Charts Row -->
  <div class="charts-row">
    <div class="chart-container">
      <canvas id="migrationChart"></canvas>
    </div>
    <div class="chart-container">
      <canvas id="latencyChart"></canvas>
    </div>
  </div>
  
  <!-- Comparison & Alerts -->
  <div class="comparison-alerts">
    <div class="algorithm-comparison" id="algorithmComparison">
      <!-- Content filled by JS -->
    </div>
    <div class="anomaly-panel" id="anomalyPanel">
      <!-- Alerts rendered here -->
    </div>
  </div>
  
  <!-- Transaction Table -->
  <div class="transaction-table" id="transactionTable">
    <!-- Table rendered here -->
  </div>
</div>
```
- **Time**: 1.5 hours
- **Skills**: HTML structure, semantic markup
- **Checklist**:
  - [ ] All sections present
  - [ ] IDs match JS selectors
  - [ ] Accessibility attributes added (aria-label, etc.)
  - [ ] Valid HTML5

**Task 2.2: Create CSS Styling**
```css
/* Dashboard Grid Layout */
.dashboard {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 24px;
}

/* KPI Cards */
.kpi-cards {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.kpi-card {
  background: var(--color-background-secondary);
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--border-radius-lg);
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.kpi-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}

.kpi-value {
  font-size: 32px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.kpi-progress-bar {
  width: 100%;
  height: 8px;
  background: var(--color-border-tertiary);
  border-radius: var(--border-radius-md);
  overflow: hidden;
  margin: 12px 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #534AB7, #0F6E56);
  animation: fillProgress 0.5s ease-out;
}

@keyframes fillProgress {
  from { width: 0; }
  to { width: var(--fill-width); }
}

/* Charts */
.charts-row {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-container {
  background: var(--color-background-primary);
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--border-radius-lg);
  padding: 20px;
  position: relative;
  height: 300px;
}

/* Alerts */
.anomaly-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.alert-item {
  padding: 12px 16px;
  border-left: 4px solid;
  border-radius: var(--border-radius-md);
}

.alert-item.critical {
  border-left-color: var(--color-critical);
  background: rgba(255, 0, 0, 0.05);
}

.alert-item.warning {
  border-left-color: var(--color-warning);
  background: rgba(255, 165, 0, 0.05);
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
  
  .kpi-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .charts-row {
    grid-template-columns: 1fr;
  }
}
```
- **Time**: 2 hours
- **Skills**: CSS, responsive design
- **Checklist**:
  - [ ] All layouts render correctly
  - [ ] Colors use CSS variables
  - [ ] Responsive breakpoints work
  - [ ] Dark mode support added
  - [ ] Smooth animations implemented

**Task 2.3: Create JavaScript Data Binding**
```javascript
// Initialize dashboard
async function initDashboard() {
  // Load KPI data every 30s
  setInterval(async () => {
    const migration = await fetch('/api/v1/analytics/migration-status?time_window=24h')
      .then(r => r.json());
    updateMigrationCard(migration);
    
    const health = await fetch('/api/v1/keys/rotation-health')
      .then(r => r.json());
    updateHealthCard(health);
    
    const security = await fetch('/api/v1/analytics/security-health?time_window=24h')
      .then(r => r.json());
    updateSecurityCard(security);
    
    const latency = await fetch('/api/v1/analytics/latency-percentiles?time_window=24h')
      .then(r => r.json());
    updateLatencyCard(latency);
  }, 30000);
  
  // Load charts every 5 min
  setInterval(loadCharts, 300000);
  
  // Load anomalies every 2 min
  setInterval(loadAnomalies, 120000);
  
  // Trigger first load
  loadCharts();
  loadAnomalies();
}

function updateMigrationCard(data) {
  document.getElementById('migrationValue').textContent = data.mlkem_percentage + '%';
  document.getElementById('migrationMeta').textContent = `+${data.mlkem_daily_growth}% daily • ${data.days_to_target} days to 80%`;
  
  const fillWidth = (data.mlkem_percentage / 80) * 100;
  document.querySelector('#migrationCard .progress-fill')
    .style.setProperty('--fill-width', fillWidth + '%');
}

// Similar functions for other cards...

initDashboard();
```
- **Time**: 2 hours
- **Skills**: JavaScript, async/await, DOM manipulation
- **Checklist**:
  - [ ] Data fetching works
  - [ ] DOM updates work
  - [ ] Intervals set correctly
  - [ ] Error handling added
  - [ ] Loading states shown

---

### Day 3-4: Charts & Interactivity

**Task 2.4: Create Chart.js Visualizations**
```javascript
// Migration Trend Chart
function createMigrationChart(data) {
  const ctx = document.getElementById('migrationChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.dates,  // Last 30 days
      datasets: [
        {
          label: 'RSA-2048',
          data: data.rsa_trend,
          borderColor: '#993C1D',
          backgroundColor: 'rgba(153, 60, 29, 0.1)',
          tension: 0.4,
          fill: false
        },
        {
          label: 'ML-KEM',
          data: data.mlkem_trend,
          borderColor: '#0F6E56',
          backgroundColor: 'rgba(15, 110, 86, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        annotation: {
          annotations: {
            target: {
              type: 'line',
              yMin: 80,
              yMax: 80,
              borderColor: '#A32D2D',
              borderWidth: 2,
              borderDash: [5, 5],
              label: { content: ['Target: 80%'] }
            }
          }
        }
      },
      scales: {
        y: { min: 0, max: 100 }
      }
    }
  });
}

// Latency Percentiles Chart
function createLatencyChart(data) {
  // Similar structure with p50, p95, p99 as separate datasets
  // Include SLA threshold line
  // Use dashed lines for p95, dotted for p99
}

initDashboard();
```
- **Time**: 2 hours
- **Skills**: Chart.js, data visualization
- **Checklist**:
  - [ ] Both charts render correctly
  - [ ] Legends work
  - [ ] Tooltips show on hover
  - [ ] Responsive sizing
  - [ ] Data updates without flicker

**Task 2.5: Add Interactivity & Drill-Down**
```javascript
// Click KPI card to drill down
document.getElementById('migrationCard').addEventListener('click', () => {
  showModal('Migration Trend', createMigrationDetailChart());
});

// Time window selector
document.getElementById('timeWindow').addEventListener('change', (e) => {
  const window = e.target.value;
  localStorage.setItem('dashboardTimeWindow', window);
  // Reload all data with new time window
  location.search = `?window=${window}`;
});

// Alert dismissal
document.querySelectorAll('.alert-dismiss').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.target.closest('.alert-item').remove();
    showToast('Alert dismissed');
  });
});
```
- **Time**: 1.5 hours
- **Skills**: JavaScript event handling
- **Checklist**:
  - [ ] Card click handlers work
  - [ ] Time window selector updates data
  - [ ] Alert dismiss buttons work
  - [ ] Modal opens/closes
  - [ ] URL params preserved

---

### Day 5: Testing & Optimization

**Task 2.6: Frontend Testing**
- Responsive design testing (mobile 375px, tablet 768px, desktop 1920px)
- Cross-browser testing (Chrome, Firefox, Safari, Edge)
- Performance testing (Lighthouse, WebPageTest)
- Data accuracy testing (verify API values match display)
- **Time**: 2 hours
- **Checklist**:
  - [ ] Responsive at 375px, 768px, 1920px
  - [ ] No console errors
  - [ ] Lighthouse score > 80
  - [ ] Data values correct
  - [ ] Interactions smooth

**Task 2.7: Performance Optimization**
- Minify CSS/JS
- Lazy-load table data
- Cache API responses (client-side)
- Reduce animation frame rate if needed
- **Time**: 1 hour
- **Checklist**:
  - [ ] Page load < 3s
  - [ ] Time to interactive < 5s
  - [ ] Smooth scrolling 60fps
  - [ ] No jank on updates

---

## 📋 Phase 3: Deployment & Monitoring (Week 3)

### Day 1-2: Production Deployment

**Task 3.1: Blue-Green Deployment**
1. Deploy new APIs to "green" environment
2. Run smoke tests against green
3. Switch load balancer to green
4. Monitor for errors
5. Keep blue as rollback
- **Time**: 2 hours
- **Checklist**:
  - [ ] New APIs deployed
  - [ ] Smoke tests pass
  - [ ] Load balancer switched
  - [ ] Monitoring active
  - [ ] Rollback tested

**Task 3.2: Update Frontend**
1. Deploy new HTML/CSS/JS to CDN
2. Clear browser caches
3. Test on production URLs
4. Verify data is live
- **Time**: 1 hour
- **Checklist**:
  - [ ] Frontend deployed
  - [ ] Cache cleared
  - [ ] Live data flowing
  - [ ] No API errors

---

### Day 3-5: Documentation & Training

**Task 3.3: Create API Documentation**
- Document each endpoint (purpose, params, response, examples)
- Include error codes and handling
- Add rate limits and quotas
- **Time**: 2 hours

**Task 3.4: Create Dashboard User Guide**
- Screenshots of each section
- How to interpret metrics
- How to respond to alerts
- Troubleshooting guide
- **Time**: 2 hours

**Task 3.5: Team Training**
- Demo dashboard to team
- Explain each metric
- Show alert response playbooks
- Hands-on practice
- **Time**: 2 hours

---

## 🎯 Success Criteria Checklist

### Backend (API)
- [ ] All 5 metric endpoints implemented
- [ ] Unit test coverage > 80%
- [ ] Query performance < 500ms
- [ ] Database schema migrated
- [ ] No data validation errors
- [ ] Error handling robust
- [ ] Rate limiting configured

### Frontend (UI)
- [ ] All KPI cards render with live data
- [ ] Both charts display correctly
- [ ] Anomaly alerts functional
- [ ] Time window selector works
- [ ] Responsive on mobile/tablet/desktop
- [ ] Lighthouse score > 80
- [ ] No console errors

### Deployment
- [ ] APIs deployed to production
- [ ] Frontend deployed to CDN
- [ ] Load testing passed
- [ ] Monitoring alerts configured
- [ ] Documentation complete
- [ ] Team trained
- [ ] Rollback plan documented

---

## 🚀 Quick Start (TL;DR)

### Priority Order (Implement in This Sequence)

**Week 1 - Backend (API)**
1. ✅ Create key_metadata table (30 min)
2. ✅ Add latency_bucket column (30 min)
3. ✅ Implement `/migration-status` endpoint (1h)
4. ✅ Implement `/latency-percentiles` endpoint (1.5h)
5. ✅ Implement `/rotation-health` endpoint (1.5h)
6. ✅ Implement `/algorithm-comparison` endpoint (1h)
7. ✅ Implement `/security-health` endpoint (1h)
8. ✅ Test all endpoints (2h)
9. ✅ Deploy to staging (1h)

**Week 2 - Frontend (UI)**
1. ✅ Build HTML structure (1.5h)
2. ✅ Create CSS styling (2h)
3. ✅ Link KPI card data (1.5h)
4. ✅ Create charts (2h)
5. ✅ Add interactivity (1.5h)
6. ✅ Test responsive design (2h)
7. ✅ Optimize performance (1h)

**Week 3 - Deployment**
1. ✅ Production deployment (2h)
2. ✅ Documentation (2h)
3. ✅ Team training (2h)

**Total Effort**: ~40 hours of development

---

## 💡 Pro Tips for Success

### Backend Tips
- **Use Indexed Queries**: Add indexes on timestamp + algorithm for fast filtering
- **Batch Calculations**: Run daily snapshots in off-peak hours
- **Cache Results**: Cache percentile results for 5 min to avoid recalc every request
- **Monitor Query Performance**: Use `EXPLAIN ANALYZE` to verify indexes work

### Frontend Tips
- **Use Skeleton Loaders**: Show shimmer placeholders while data loads
- **Debounce Inputs**: Debounce time-window selector (prevent rapid API calls)
- **Progressive Enhancement**: Show table first, charts later
- **Accessibility**: Add aria-labels, keyboard navigation, color-blind friendly colors

### Deployment Tips
- **Feature Flags**: Wrap new features in feature flag (can disable without redeployment)
- **Gradual Rollout**: Deploy to 10% users first, monitor errors
- **Monitoring**: Set alerts on API latency, error rate, anomaly count
- **Alerting**: Page on-call engineer if anomaly severity = critical

---

## 📞 Support & Questions

**If API response is slow**:
- Check database indexes
- Run `EXPLAIN ANALYZE` on slow queries
- Add caching layer
- Consider read replica for analytics queries

**If frontend shows stale data**:
- Check fetch intervals (should be 30s for KPI, 5min for charts)
- Clear browser cache
- Check API response times
- Verify time window selector is working

**If anomalies aren't detected**:
- Check spike detection thresholds
- Verify baseline calculation is correct
- Look at security_events table to see if failures are logged
- Check anomaly alerts table for debugging

