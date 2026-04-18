# Banking API Security Dashboard Enhancement
## Detailed Implementation Plan & Task List

---

## EXECUTIVE SUMMARY

**Goal**: Enhance your encryption monitoring dashboard with 5 high-impact metrics that improve project visibility and security posture.

**Selected Top 5 Metrics** (rationale included):
1. **Latency Percentiles (p50, p95, p99)** — Reveals hidden performance degradation and SLA risks
2. **Post-Quantum Migration Status** — Quantifies ML-KEM adoption; demonstrates quantum-safe readiness
3. **Key Rotation Health Index** — Ensures cryptographic hygiene; critical for compliance
4. **Algorithm Performance Ratio** — Shows cost-benefit of hybrid encryption approach
5. **Encryption Failure Rate + Anomaly Detection** — Real-time security incident visibility

**Why these 5?**
- **Business Value**: Track quantum-safe migration progress (ML-KEM vs RSA adoption %)
- **Security**: Detect anomalies and failed operations before they become breaches
- **Performance**: Identify latency degradation at scale (p95/p99 matter more than averages)
- **Compliance**: Demonstrate key rotation discipline for audits
- **Competitive Advantage**: Few banking dashboards show post-quantum metrics — this differentiates you

---

## PHASE 1: API ENHANCEMENT

### 1.1 Latency Percentile Calculation

**Current State**: You capture single `Total (ms)` values per transaction

**Task 1.1.1: Add Latency Bucketing in Encryption Endpoint**
- **File**: Your encryption API handler
- **Changes**:
  ```
  BEFORE: return { total_ms: 181.7333 }
  AFTER: return { 
    total_ms: 181.7333,
    latency_bucket: "100-200ms"  // For real-time UI grouping
  }
  ```
- **Implementation**:
  - Define latency buckets: `<50ms, 50-100ms, 100-200ms, 200-500ms, >500ms`
  - During encryption, measure end-to-end time
  - Assign bucket at response time
  - Store bucket in transaction log alongside total_ms

**Task 1.1.2: Add Percentile Aggregation Endpoint**
- **New Endpoint**: `GET /api/v1/analytics/latency-percentiles`
- **Query Params**: `?algorithm=RSA-2048&time_window=1h|24h|7d`
- **Logic**:
  - Query last N transactions for algorithm + time window
  - Sort total_ms values
  - Calculate: p50 = median, p95 = 95th percentile, p99 = 99th percentile
  - Return with sample count and trend (e.g., "p95 up 12% vs yesterday")
- **Response Schema**:
  ```json
  {
    "algorithm": "RSA-2048",
    "time_window": "24h",
    "samples": 1247,
    "p50_ms": 85.42,
    "p95_ms": 156.89,
    "p99_ms": 203.45,
    "trend_p95": "+12%",
    "timestamp": "2026-03-28T12:48:41Z"
  }
  ```
- **Code Pattern**:
  ```
  1. Query transactions WHERE algorithm = ? AND timestamp > (now - time_window)
  2. Extract total_ms into array, sort ascending
  3. p50 = array[length * 0.5], p95 = array[length * 0.95], p99 = array[length * 0.99]
  4. Compare p95 from previous period, calculate % change
  5. Return JSON
  ```

**Task 1.1.3: Add p50/p95/p99 to Dashboard Data Stream**
- Modify transaction response to include percentile snapshot
- Cache percentiles (refresh every 5 minutes to avoid constant recalculation)
- Add percentile history table (last 7 days) for trend visualization

---

### 1.2 Post-Quantum Migration Status

**Current State**: You track RSA-2048 and ML-KEM separately but don't measure adoption rate

**Task 1.2.1: Add Migration Tracking Endpoint**
- **New Endpoint**: `GET /api/v1/analytics/migration-status`
- **Query Params**: `?time_window=24h|7d|30d`
- **Logic**:
  - Count total transactions
  - Count RSA-2048 transactions
  - Count ML-KEM transactions
  - Calculate percentages
  - Calculate daily growth rate of ML-KEM adoption
- **Response Schema**:
  ```json
  {
    "time_window": "30d",
    "total_transactions": 45230,
    "rsa_count": 31450,
    "mlkem_count": 13780,
    "hybrid_count": 0,
    "rsa_percentage": 69.5,
    "mlkem_percentage": 30.5,
    "hybrid_percentage": 0,
    "mlkem_daily_growth": "2.3%",
    "migration_target": 80,
    "days_to_target": 45,
    "status": "on_track",
    "timestamp": "2026-03-28T12:48:41Z"
  }
  ```
- **Code Pattern**:
  ```
  1. Query COUNT(*) WHERE timestamp > (now - time_window) → total_tx
  2. Query COUNT(*) WHERE method = 'RSA-2048' AND timestamp > (now - time_window) → rsa_tx
  3. Query COUNT(*) WHERE method = 'ML-KEM' AND timestamp > (now - time_window) → mlkem_tx
  4. rsa_pct = (rsa_tx / total_tx) * 100, mlkem_pct = (mlkem_tx / total_tx) * 100
  5. Query yesterday's mlkem_count, calculate (mlkem_tx - yesterday) / yesterday * 100 → growth
  6. If growth > 0: days_to_target = (100 - mlkem_pct) / growth_per_day
  7. Set status = "on_track" if growth >= 2%, "at_risk" if < 2%
  ```

**Task 1.2.2: Add Daily Migration Snapshots**
- Every day at midnight, store a snapshot:
  - `(date, rsa_count, mlkem_count, total_count, rsa_pct, mlkem_pct)`
- Use for 30-day trend chart (shows migration curve)
- Enables prediction: "At current pace, 80% ML-KEM by Apr 15"

**Task 1.2.3: Add Hybrid Encryption Support**
- If your system supports RSA+ML-KEM together (dual encryption):
  - Add `hybrid_count` field
  - Update percentages to account for all three
  - This future-proofs your API

---

### 1.3 Key Rotation Health Index

**Current State**: You track key sizes but not rotation frequency or age

**Task 1.3.1: Add Key Metadata Tracking**
- **New Endpoint**: `GET /api/v1/keys/rotation-health`
- **Per-Key Tracking** (store in key management table):
  - `key_id`: unique identifier
  - `algorithm`: RSA-2048 or ML-KEM
  - `created_at`: timestamp
  - `last_used_at`: timestamp (update on every encryption)
  - `rotation_due_at`: created_at + 90 days (configurable policy)
  - `status`: active | pending_rotation | rotated | revoked
- **Logic**:
  - Days since creation: `now - created_at`
  - Days until rotation: `rotation_due_at - now` (can be negative if overdue)
  - Is overdue? `now > rotation_due_at`
  - Last used: `now - last_used_at`
- **Response Schema**:
  ```json
  {
    "total_keys": 247,
    "keys_active": 236,
    "keys_pending_rotation": 8,
    "keys_overdue_rotation": 3,
    "avg_age_days": 45,
    "avg_days_until_rotation": 45,
    "overdue_percentage": 1.2,
    "compliance_score": 98.8,
    "health_status": "excellent",
    "next_rotation_date": "2026-04-15",
    "keys_by_algorithm": {
      "RSA-2048": { "active": 120, "pending": 5, "overdue": 2 },
      "ML-KEM": { "active": 116, "pending": 3, "overdue": 1 }
    },
    "timestamp": "2026-03-28T12:48:41Z"
  }
  ```
- **Compliance Score Calculation**:
  ```
  score = 100
  score -= (overdue_count / total_keys) * 30  // Severe penalty for overdue
  score -= (pending_count / total_keys) * 10  // Minor penalty for pending
  score -= MAX(0, (avg_age - 60) / 60) * 20   // Penalty if avg age > 60 days
  Health: score ≥ 95 = excellent, ≥ 85 = good, ≥ 70 = fair, < 70 = critical
  ```

**Task 1.3.2: Add Key Rotation Audit Trail**
- Log every key rotation event:
  - `rotation_id, old_key_id, new_key_id, rotated_at, reason` (manual/auto/overdue)
  - Use for compliance reports (SOC 2, PCI-DSS)
  - Enable "Key Rotation History" dashboard section

**Task 1.3.3: Add Key Age Distribution Endpoint**
- **Endpoint**: `GET /api/v1/keys/age-distribution`
- Returns histogram of key ages:
  ```json
  {
    "0-30_days": 45,
    "30-60_days": 89,
    "60-90_days": 92,
    "90-120_days": 15,
    "120+_days": 6,
    "median_age_days": 52
  }
  ```
- Visualize as bar chart to spot aging key clusters

---

### 1.4 Algorithm Performance Ratio

**Current State**: You show individual timings for RSA-2048 and ML-KEM but no comparison

**Task 1.4.1: Add Comparative Performance Endpoint**
- **New Endpoint**: `GET /api/v1/analytics/algorithm-comparison`
- **Query Params**: `?metric=latency|throughput|key_size&time_window=24h`
- **Logic**:
  - Query transactions for RSA-2048 and ML-KEM separately
  - Calculate aggregate stats for each:
    - Average latency, p99 latency, min, max
    - Throughput (tx/second)
    - Size ratios
  - Calculate ratios and performance delta
- **Response Schema**:
  ```json
  {
    "time_window": "24h",
    "comparison_date": "2026-03-28",
    "rsa_2048": {
      "samples": 892,
      "avg_latency_ms": 92.3,
      "p99_latency_ms": 185.5,
      "key_size_b": 294,
      "cipher_size_b": 256,
      "throughput_tx_per_sec": 45.2
    },
    "ml_kem": {
      "samples": 355,
      "avg_latency_ms": 78.5,
      "p99_latency_ms": 142.3,
      "key_size_b": 1184,
      "cipher_size_b": 1088,
      "throughput_tx_per_sec": 52.1
    },
    "comparison": {
      "latency_delta_pct": -14.9,
      "latency_verdict": "ML-KEM is 14.9% faster",
      "p99_delta_pct": -23.4,
      "size_delta_pct": 302.7,
      "throughput_delta_pct": 15.3,
      "throughput_verdict": "ML-KEM handles 15.3% more tx/sec",
      "recommendation": "ML-KEM superior in speed and throughput; accept 3x key size for quantum safety"
    }
  }
  ```
- **Code Pattern**:
  ```
  1. Query RSA transactions: COUNT, AVG(latency), MAX(latency) for p99 calculation
  2. Query ML-KEM transactions: same metrics
  3. Calculate latency_delta = ((ml_kem_avg - rsa_avg) / rsa_avg) * 100
  4. Calculate throughput = sample_count / time_window_seconds
  5. Compare and generate verdict string
  ```

**Task 1.4.2: Add Historical Ratio Tracking**
- Daily snapshot: store comparison metrics
- Enable 30-day trend chart
- Answer: "Is ML-KEM getting faster relative to RSA over time?"

**Task 1.4.3: Add Cost-Benefit Analysis Endpoint**
- Factor in infrastructure cost:
  ```json
  {
    "rsa_2048": {
      "latency_cost": "2.3ms per tx",
      "bandwidth_cost": "256 bytes per cipher",
      "monthly_bandwidth_mb": 234,
      "estimated_cost": "$12/month"
    },
    "ml_kem": {
      "latency_cost": "1.9ms per tx",
      "bandwidth_cost": "1088 bytes per cipher",
      "monthly_bandwidth_mb": 987,
      "estimated_cost": "$28/month"
    },
    "trade_off": "Pay $16/month extra for quantum safety and 15% faster processing"
  }
  ```

---

### 1.5 Encryption Failure Rate + Anomaly Detection

**Current State**: You track success/failure implicitly via response codes, but no aggregation

**Task 1.5.1: Add Failure Rate Tracking Endpoint**
- **New Endpoint**: `GET /api/v1/analytics/security-health`
- **Query Params**: `?time_window=1h|24h&algorithm=RSA-2048|ML-KEM`
- **Logic**:
  - Count total encryption attempts
  - Count failed attempts (e.g., decryption validation failed, key not found, crypto exception)
  - Count rejected attempts (policy violation, rate limit, unauthorized)
  - Calculate failure rate, rejection rate, alert if threshold exceeded
- **Response Schema**:
  ```json
  {
    "time_window": "24h",
    "algorithm": "RSA-2048",
    "total_attempts": 892,
    "successful": 887,
    "failed_crypto": 3,
    "failed_validation": 2,
    "rejected_policy": 0,
    "failure_rate_pct": 0.56,
    "rejection_rate_pct": 0.0,
    "status": "healthy",
    "alerts": [],
    "timestamp": "2026-03-28T12:48:41Z"
  }
  ```
- **Alert Thresholds**:
  - Failure rate > 1% → warning
  - Failure rate > 5% → critical
  - Spike detection: failure_rate_now > 2x failure_rate_1h_ago → alert

**Task 1.5.2: Add Anomaly Detection Engine**
- **Endpoint**: `GET /api/v1/analytics/anomalies`
- **Detects**:
  1. **Latency Spike**: If p95 latency increases by >30% in last 1h vs baseline
  2. **Failure Rate Spike**: If failure rate increases by >2x in last 1h
  3. **Algorithm Shift**: Unusual change in RSA/ML-KEM ratio (e.g., all traffic suddenly RSA)
  4. **Key Usage Anomaly**: A single key used 100x more than normal
  5. **Geographic Anomaly**: Requests from unexpected locations/IPs
- **Response Schema**:
  ```json
  {
    "detected_anomalies": [
      {
        "type": "latency_spike",
        "severity": "warning",
        "metric": "p95_latency_ms",
        "baseline": 156,
        "current": 235,
        "delta_pct": 50.6,
        "detected_at": "2026-03-28T12:45:00Z",
        "duration_minutes": 3,
        "recommendation": "Check if new key rotation was triggered"
      },
      {
        "type": "failure_rate_spike",
        "severity": "critical",
        "metric": "failure_rate_pct",
        "baseline": 0.3,
        "current": 2.1,
        "delta_pct": 600,
        "detected_at": "2026-03-28T12:43:00Z",
        "affected_algorithm": "ML-KEM",
        "recommendation": "Investigate decryption failures; check key management service"
      }
    ],
    "health_status": "attention_required"
  }
  ```
- **Code Pattern**:
  ```
  1. Calculate 1h baseline: avg latency, failure rate, key usage patterns
  2. Calculate current (last 5 min): same metrics
  3. Compare: if current > baseline * 1.3 → spike detected
  4. Store anomaly event with timestamp and context
  5. Return top anomalies sorted by severity + recency
  ```

**Task 1.5.3: Add Security Event Log**
- Log every failure/rejection with context:
  ```json
  {
    "event_id": "evt_2026032812484125",
    "timestamp": "2026-03-28T12:48:41Z",
    "event_type": "decryption_failure",
    "algorithm": "ML-KEM",
    "reason": "validation_failed",
    "sender": "ACCT-1001",
    "receiver": "ACCT-9002",
    "latency_ms": 45.3,
    "error_message": "AEAD authentication tag verification failed"
  }
  ```
- Searchable by sender, receiver, algorithm, error type
- Exportable for incident response

**Task 1.5.4: Add Anomaly Severity Scoring**
- Each anomaly gets severity: info | warning | critical
- **Calculation**:
  ```
  severity = info
  if delta_pct > 50% → severity = warning
  if delta_pct > 100% or (type = failure_rate AND delta_pct > 200%) → severity = critical
  if sustained for > 5 min → escalate one level
  ```

---

## PHASE 2: FRONTEND/HTML ENHANCEMENT

### 2.1 Dashboard Layout Architecture

**Current Design**: Table-based row view (good for raw data, limited insight)

**Proposed Design**: Multi-panel dashboard (real-time + historical + diagnostic)

**Structure**:
```
┌─────────────────────────────────────────────────────────────┐
│  HEADER: Dashboard Title + Time Window Selector             │
├─────────────────────────────────────────────────────────────┤
│  ROW 1: KPI CARDS (4 metric cards)                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│  │ Migration %  │ │ Key Health   │ │ Failure Rate │ │ Avg      │
│  │ 30.5% → 80% │ │ 98.8% score  │ │ 0.56% ⚠️    │ │ Latency  │
│  │ On Track     │ │ 3 Overdue    │ │ 3 Failures   │ │ p95:157ms│
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────┘
├─────────────────────────────────────────────────────────────┤
│  ROW 2: CHARTS (2 columns)                                  │
│  ┌──────────────────────────┐ ┌──────────────────────────┐  │
│  │ Migration Trend          │ │ Latency Percentiles      │  │
│  │ (Line chart: 30d)        │ │ (Time series: p50/p95/p99)  │
│  │ 📈 RSA 69% → ML-KEM 31%  │ │ 📊 Shows SLA risk       │  │
│  └──────────────────────────┘ └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ROW 3: ALGORITHM COMPARISON + ANOMALIES                    │
│  ┌──────────────────────────┐ ┌──────────────────────────┐  │
│  │ RSA-2048 vs ML-KEM       │ │ Security Alerts          │  │
│  │ (Side-by-side metrics)   │ │ ⚠️  Latency up 50%       │  │
│  │ Latency: ML-KEM 15% ✓    │ │ 🚨 Failure rate spike    │  │
│  │ Throughput: ML-KEM 15% ✓ │ │ 📌 6 New anomalies       │  │
│  │ Size: RSA wins 3x ✓      │ │ Clear / Dismiss          │  │
│  └──────────────────────────┘ └──────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ROW 4: DETAILED TRANSACTION TABLE (collapsible)            │
│  Sender | Receiver | Amount | Algorithm | Latency | Status  │
│  ...existing table with new columns...                      │
├─────────────────────────────────────────────────────────────┤
│  FOOTER: Last Updated + Export + Settings                   │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 Task Breakdown: Dashboard Components

**Task 2.2.1: Create KPI Card Component**
- **Location**: In your HTML `<head>` or separate CSS file
- **Component** (reusable for all 4 cards):
  ```html
  <div class="kpi-card">
    <div class="kpi-label">Migration Progress</div>
    <div class="kpi-value">30.5%</div>
    <div class="kpi-goal">Target: 80%</div>
    <div class="kpi-progress-bar">
      <div class="progress-fill" style="width: 38%"></div>
    </div>
    <div class="kpi-meta">On Track • +2.3% daily</div>
  </div>
  ```
- **Styling**:
  - Background: soft accent color (e.g., #E6F1FB for blue theme)
  - Border: subtle 0.5px border
  - Typography: large bold number, smaller labels
  - Progress bar: animated fill over time
  - Meta text: secondary color, 12px
- **Interactivity**:
  - Hover: slight shadow lift + pointer
  - Click: navigate to detailed view for that metric

**Task 2.2.2: Create Migration Trend Chart**
- **Chart Type**: Line chart (Chart.js or D3)
- **Data**:
  - X-axis: Last 30 days (daily snapshots)
  - Y-axis: Percentage (0-100%)
  - Two lines: RSA-2048 (red/coral ramp) and ML-KEM (green/teal ramp)
  - Area fill under ML-KEM to emphasize growth
- **Interactivity**:
  - Hover: show exact date + values + daily growth rate
  - Tooltip: "ML-KEM up 2.3% vs yesterday"
  - X-axis labels: every 5 days (avoid clutter)
- **Annotations**:
  - Horizontal dotted line at 80% (migration target)
  - Label: "Your 80% goal"
  - Projection line: "Reaching goal by Apr 15" (if trending)

**Task 2.2.3: Create Latency Percentiles Chart**
- **Chart Type**: Time-series line chart
- **Data**:
  - X-axis: Last 24 hours (hourly buckets)
  - Y-axis: Latency in ms (0-300ms)
  - Three lines: p50 (solid), p95 (dashed), p99 (dotted)
  - Different colors per algorithm (RSA vs ML-KEM toggle)
- **Interactivity**:
  - Hover point: show all three percentiles at that hour
  - Shaded region between p95 and p99 to show tail latency "risk zone"
  - Click legend to toggle p50/p95/p99 visibility
  - Time window picker: 1h | 24h | 7d
- **SLA Indicator**:
  - Add horizontal red line: "SLA threshold = 200ms"
  - Highlight hours where p99 > threshold in light red
  - Count: "2 hours breached SLA"

**Task 2.2.4: Create Algorithm Comparison Card**
- **Layout**: Two side-by-side boxes (RSA vs ML-KEM)
- **Content** (per algorithm):
  ```
  RSA-2048                    ML-KEM
  ─────────                   ──────
  Latency: 92.3ms             Latency: 78.5ms ← 14.9% faster ✓
  p99:      185.5ms           p99:      142.3ms ← 23.4% faster ✓
  Key Size: 294B              Key Size: 1184B ← 4x larger ⚠️
  Throughput: 45.2 tx/s       Throughput: 52.1 tx/s ← 15% faster ✓
  Sample Size: 892 tx         Sample Size: 355 tx
  
  🎯 Recommendation: ML-KEM is faster and safer; accept larger keys
  ```
- **Styling**:
  - Two columns with border divider
  - Checkmarks (✓) for ML-KEM wins (green)
  - Warning (⚠️) for tradeoffs (amber)
  - Recommendation box at bottom (highlight)
- **Interactivity**:
  - Click any metric to drill into historical trend
  - "Why is ML-KEM larger?" tooltip
  - "Cost breakdown" link → modal with bandwidth/infra cost comparison

**Task 2.2.5: Create Security Alerts Panel**
- **Layout**: Vertical list of alerts (newest first)
- **Alert Item**:
  ```
  [🚨 CRITICAL] Failure Rate Spike
  Detected 3 min ago in ML-KEM
  Baseline 0.3% → Current 2.1% (600% increase)
  Affected: 18 failed decryptions
  → Investigate key rotation / Check KMS service
  [Dismiss] [View Details] [Export Log]
  ```
- **Alert Levels**:
  - 🔵 INFO (blue): Routine observations
  - 🟡 WARNING (amber): Degradation > 30%
  - 🚨 CRITICAL (red): Degradation > 100% or failures > 5%
- **Auto-dismiss**: Alerts auto-collapse after 10 min if not actioned
- **Sticky**: Critical alerts stay pinned until dismissed manually
- **Interactivity**:
  - Click to expand full context + raw event logs
  - "View Details" opens modal with security event log for that anomaly
  - "Acknowledge" marks alert as reviewed (useful for shift handoff)
  - "Export" → CSV of events

**Task 2.2.6: Enhance Transaction Table**
- **Add Columns**:
  1. `Latency Bucket` — visual indicator (green/amber/red based on p95 baseline)
  2. `Deviation from Baseline` — % change in latency for that tx
  3. `Key Age (days)` — days since key created
  4. `Status` — ✓ Success | ⚠️ Warning | ✗ Failed
- **Row Styling**:
  - Failed rows: light red background
  - Outlier latency (>p99): light yellow background
  - Normal: default
- **Sorting**: By any column (especially useful: Algorithm, Status, Latency)
- **Filtering**:
  - Algorithm: RSA-2048 | ML-KEM
  - Status: Success | Failed
  - Date range picker: Quick links (last 1h | 24h | 7d)
  - Search: Sender/Receiver ACCT ID
- **Collapsible Rows**:
  - Click row to expand → Show raw event log, full error message, related anomalies
  - Show which anomaly this transaction triggered (if any)

---

### 2.3 Layout & Styling Guide

**Task 2.3.1: Create CSS Layout Foundation**
- **Grid System** (use CSS Grid):
  ```css
  .dashboard {
    display: grid;
    grid-template-columns: 1fr 1fr;  /* 2-column layout */
    gap: 16px;
    padding: 24px;
  }
  
  .kpi-cards {
    grid-column: 1 / -1;  /* Full width */
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
  
  .charts-row {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  
  .comparison-anomalies {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }
  
  .transaction-table {
    grid-column: 1 / -1;
  }
  ```
- **Responsive** (tablet/mobile):
  - At <768px: switch to 1-column layout
  - KPI cards stack to 2 columns
  - Charts stack vertically
  - Table becomes horizontally scrollable card view

**Task 2.3.2: Create Color Palette + Theme Variables**
- **CSS Variables** (define in `:root`):
  ```css
  :root {
    /* Primary colors */
    --color-rsa: #993C1D;      /* Coral for RSA */
    --color-mlkem: #0F6E56;    /* Teal for ML-KEM */
    --color-hybrid: #534AB7;   /* Purple for hybrid */
    
    /* Semantic colors */
    --color-success: #0F6E56;
    --color-warning: #BA7517;
    --color-critical: #A32D2D;
    --color-info: #185FA5;
    
    /* Backgrounds */
    --bg-primary: #FFFFFF;
    --bg-secondary: #F1EFE8;
    --bg-tertiary: #E6F1FB;
    
    /* Text */
    --text-primary: #2C2C2A;
    --text-secondary: #5F5E5A;
    --text-tertiary: #888780;
    
    /* Borders */
    --border-light: rgba(127, 119, 221, 0.15);
    --border-medium: rgba(127, 119, 221, 0.3);
    --border-strong: rgba(127, 119, 221, 0.4);
  }
  ```
- **Dark Mode**: Create corresponding `@media (prefers-color-scheme: dark)` variant

**Task 2.3.3: Create Reusable Components (CSS Classes)**
- **Card**: `.card` — white bg, subtle border, rounded corners, shadow on hover
- **KPI Card**: `.kpi-card` — light bg, large number, progress bar
- **Alert**: `.alert.info|warning|critical` — colored left border, icon, dismissable
- **Badge**: `.badge.success|warning|critical` — small colored pill
- **Progress Bar**: `.progress-bar` — animated fill, smooth transition
- **Button**: `.btn.primary|secondary|danger` — existing or new styles
- **Metric Row**: `.metric-row` — label + value on left + sparkline on right

**Task 2.3.4: Create Typography Hierarchy**
- **H1** (28px, bold): Dashboard title
- **H2** (20px, bold): Section headers (Migration, Latency, Comparison)
- **H3** (16px, bold): Card titles
- **Body** (14px, regular): Content text
- **Small** (12px, regular): Metadata, labels
- **Mono** (12px, regular): Code values (error messages, event IDs)

---

### 2.4 Interactivity & Data Binding

**Task 2.4.1: Set Up Real-Time Data Updates**
- **Polling Strategy**:
  - KPI Cards + Anomalies: refresh every 30 sec (critical data)
  - Charts: refresh every 5 min (computation-heavy)
  - Transaction table: lazy-load on demand
- **Code Pattern**:
  ```javascript
  setInterval(() => {
    fetch('/api/v1/analytics/migration-status?time_window=24h')
      .then(r => r.json())
      .then(data => updateKPICard('migration', data))
  }, 30000);
  ```

**Task 2.4.2: Create Data Display Functions**
- **`updateKPICard(metric, data)`**:
  - Update .kpi-value with data.percentage
  - Update progress bar width
  - Update trend arrow + color (green if positive growth, red if not)
  - Animate bar fill over 500ms
- **`updateChart(chartId, data)`**:
  - Re-render Chart.js instance with new data
  - Preserve zoom/pan state if user was interacting
- **`displayAlerts(anomalies)`**:
  - Clear existing alerts
  - Render each anomaly as alert card
  - Sort by severity + timestamp
  - Add dismiss buttons with event listeners

**Task 2.4.3: Create Drill-Down Navigation**
- **KPI Card Clicks**: 
  - Migration % → Open modal with 30-day trend + projected completion date
  - Key Health → Show key age distribution bar chart + overdue list
  - Failure Rate → Show failure event log + top error types
  - Latency p95 → Show hourly latency percentiles + SLA breaches
- **Chart Clicks**:
  - Click data point → Show transaction details for that hour/day
  - Right-click to export data as CSV
- **Alert Clicks**:
  - Expand to show full security event log
  - Link to related transactions in table

**Task 2.4.4: Create Time Window Selector**
- **Dropdown**: Last 1h | 24h | 7d | 30d | Custom Range
- **Behavior**:
  - Updates all charts + KPI cards simultaneously
  - URL param: `?window=24h` for bookmarking
  - Persists in localStorage for next visit
  - Validates range: don't allow future dates

**Task 2.4.5: Create Export / Download Features**
- **Export Formats**:
  - CSV: Full transaction table with all new columns
  - JSON: Raw API responses (for integration with BI tools)
  - PDF: Dashboard snapshot + summary metrics
- **Scope Options**:
  - Full data vs selected date range
  - Filtered vs unfiltered (if filters are applied)
- **Automation**:
  - Email scheduled reports (daily/weekly) to compliance team

---

### 2.5 Visual Enhancements for Differentiation

**Task 2.5.1: Add Status Indicators**
- **Health Badge** (top-right of dashboard):
  ```
  Overall Status: ✓ HEALTHY
  (All systems normal, last anomaly 2h ago)
  ```
  - Green if no critical alerts
  - Amber if warnings exist
  - Red if critical alerts
  - Click to view all anomalies
- **Update Indicator**:
  ```
  Last updated: 23 seconds ago
  Next update: 7 seconds
  [Manual Refresh]
  ```

**Task 2.5.2: Create Animated Transitions**
- KPI cards: slide-in on page load
- Charts: fade-in then draw (no instant jump)
- Alerts: slide-in from top with color flash
- Table rows: highlight briefly when data updates
- Progress bars: animated fill (smooth over 1s)

**Task 2.5.3: Add Micro-Interactions**
- **Hover States**:
  - Cards: subtle shadow + slight scale up (1.02x)
  - Buttons: color shift on hover
  - Table rows: highlight on hover
  - Chart data points: tooltip + tooltip label
- **Loading States**:
  - Skeleton loaders while data fetches
  - Pulse animation on skeleton
  - "Loading..." text for longer operations
- **Success Feedback**:
  - Toast notification when alert dismissed
  - "✓ Data exported" confirmation

**Task 2.5.4: Add Smart Number Formatting**
- Percentages: `30.5%` (1 decimal)
- Latency: `92.3ms` (1 decimal) or `0.5ms` (2 decimals if sub-second)
- Throughput: `45.2 tx/s` (1 decimal)
- Large numbers: `1.2M` for millions, `1.2K` for thousands
- Percentile deltas: `+15.3%` (show sign)
- Dates: relative (`2 hours ago`) + absolute (`Mar 28, 12:48 PM`)

---

## PHASE 3: INTEGRATION & DEPLOYMENT

### 3.1 API Integration Checklist

**Task 3.1.1: Update Backend Routes**
```
✓ POST /api/v1/encrypt         → Add latency_bucket to response
✓ POST /api/v1/decrypt         → Add status + failure details
✓ GET  /api/v1/analytics/latency-percentiles    [NEW]
✓ GET  /api/v1/analytics/migration-status       [NEW]
✓ GET  /api/v1/keys/rotation-health             [NEW]
✓ GET  /api/v1/analytics/algorithm-comparison   [NEW]
✓ GET  /api/v1/analytics/security-health        [NEW]
✓ GET  /api/v1/analytics/anomalies              [NEW]
```

**Task 3.1.2: Add Database Migrations**
```
✓ Add columns to transactions table:
  - latency_bucket
  - failure_reason
  
✓ Create new tables:
  - key_metadata (key_id, algorithm, created_at, last_used_at, rotation_due_at, status)
  - key_rotation_audit (rotation_id, old_key_id, new_key_id, rotated_at, reason)
  - daily_migration_snapshot (date, rsa_count, mlkem_count, total_count)
  - security_events (event_id, timestamp, type, algorithm, details)
  - anomalies (anomaly_id, detected_at, type, severity, metric, baseline, current)
  
✓ Add indexes on:
  - transactions(timestamp, algorithm)
  - security_events(timestamp, type)
  - anomalies(detected_at, severity)
```

**Task 3.1.3: Test API Responses**
```
✓ Unit test each new endpoint with mock data
✓ Integration test: call APIs, verify data freshness
✓ Load test: ensure percentile calculations complete < 500ms
✓ Edge cases: empty datasets, null values, future dates
```

---

### 3.2 Frontend Integration Checklist

**Task 3.2.1: Update HTML Structure**
```html
✓ Replace old table-only layout with multi-panel grid
✓ Add semantic HTML elements: <main>, <section>, <article>
✓ Create reusable component templates (using <template> tag or JS)
✓ Add accessibility attributes: aria-label, role, tabindex
```

**Task 3.2.2: Link Data to UI**
```
✓ Fetch KPI data → Bind to card elements
✓ Fetch chart data → Render Chart.js instances
✓ Fetch alerts → Render alert list with click handlers
✓ Fetch transaction table → Render rows with new columns
✓ Handle loading states (skeleton screens)
✓ Handle error states (API down, no data)
```

**Task 3.2.3: Test Dashboard**
```
✓ Responsive design: test on mobile/tablet/desktop
✓ Data updates: refresh data every 30s, verify UI updates
✓ Interactions: click cards, filters, time window changes
✓ Charts: hover tooltips, legend toggle, zoom
✓ Performance: lighthouse score > 80, load time < 3s
```

---

### 3.3 Documentation & Training

**Task 3.3.1: Create API Documentation**
- For each new endpoint:
  - Description of purpose
  - Request/response schema (JSON examples)
  - Query parameters + defaults
  - Error codes + messages
  - Rate limits
  - Example curl commands

**Task 3.3.2: Create Dashboard User Guide**
- Screenshots of each section
- How to interpret KPI cards
- How to read charts + spot anomalies
- How to use filters + time window selector
- How to export data
- Troubleshooting: "Why is migration % changing?"

**Task 3.3.3: Create Operations Runbook**
- Alert response playbooks:
  - "Failure rate spike detected" → checklist of investigation steps
  - "Latency spike detected" → check key rotation, KMS load
  - "Key overdue rotation" → manual rotation steps
- Escalation paths
- Contact info for on-call engineer

---

## PHASE 4: ROLLOUT STRATEGY

### Timeline

**Week 1: Backend API**
- Days 1-2: Implement API endpoints + database schema
- Days 3-4: Write unit tests + integration tests
- Days 5: Deploy to staging, full test pass

**Week 2: Frontend**
- Days 1-2: Build component structure + CSS
- Days 3-4: Integrate APIs, implement data binding
- Days 5: Testing + performance optimization

**Week 3: Deployment**
- Days 1-2: Production deployment (blue/green or canary)
- Days 3: Monitoring + incident response
- Days 4-5: Documentation + training

---

## SUCCESS METRICS

**After Implementation, Measure**:
1. **Dashboard Adoption**: % of users viewing new metrics weekly
2. **Alert Actionability**: % of anomalies that lead to root-cause fix
3. **Migration Clarity**: Team confidence in ML-KEM adoption timeline (survey)
4. **Key Rotation Compliance**: Percentage of keys rotated on-time (target: >98%)
5. **Performance Visibility**: Reduction in surprise outages (baseline vs. post-deployment)

---

## APPENDIX: Sample Code Templates

### A1. Latency Percentile Calculation (Python/Node.js pseudocode)

```javascript
async function calculateLatencyPercentiles(algorithm, timeWindowMs) {
  const now = Date.now();
  const startTime = now - timeWindowMs;
  
  // Query all transactions for this algorithm in time window
  const transactions = await db.query(`
    SELECT total_ms FROM transactions 
    WHERE algorithm = ? AND timestamp > ? 
    ORDER BY total_ms ASC
  `, [algorithm, startTime]);
  
  const latencies = transactions.map(t => t.total_ms);
  
  // Sort already done by ORDER BY, but ensure it
  latencies.sort((a, b) => a - b);
  
  // Calculate percentiles
  const p50 = percentile(latencies, 0.50);
  const p95 = percentile(latencies, 0.95);
  const p99 = percentile(latencies, 0.99);
  
  // Calculate trend
  const yesterday = await db.query(`
    SELECT AVG(total_ms) as avg_latency FROM transactions 
    WHERE algorithm = ? AND timestamp > ? AND timestamp < ?
  `, [algorithm, startTime - 86400000, startTime - 86400000 + timeWindowMs]);
  
  const trend = ((p95 - yesterday.avg_latency) / yesterday.avg_latency * 100).toFixed(1);
  
  return {
    algorithm,
    time_window: timeWindowMs / 1000 / 60 + 'm',
    samples: latencies.length,
    p50_ms: p50.toFixed(2),
    p95_ms: p95.toFixed(2),
    p99_ms: p99.toFixed(2),
    trend_p95: trend + '%',
    timestamp: new Date().toISOString()
  };
}

function percentile(arr, p) {
  const index = Math.ceil(arr.length * p) - 1;
  return arr[Math.max(0, index)];
}
```

### A2. Migration Status Calculation

```javascript
async function getMigrationStatus(timeWindowMs) {
  const now = Date.now();
  const startTime = now - timeWindowMs;
  
  const [rsaCount, mlkemCount, totalCount, yesterdayMlkem] = await Promise.all([
    db.query(`SELECT COUNT(*) as count FROM transactions WHERE method = 'RSA-2048' AND timestamp > ?`, [startTime]),
    db.query(`SELECT COUNT(*) as count FROM transactions WHERE method = 'ML-KEM' AND timestamp > ?`, [startTime]),
    db.query(`SELECT COUNT(*) as count FROM transactions WHERE timestamp > ?`, [startTime]),
    db.query(`SELECT COUNT(*) as count FROM transactions WHERE method = 'ML-KEM' AND timestamp > ? AND timestamp < ?`, 
             [startTime - 86400000, startTime - 86400000 + timeWindowMs])
  ]);
  
  const rsaPct = (rsaCount[0].count / totalCount[0].count) * 100;
  const mlkemPct = (mlkemCount[0].count / totalCount[0].count) * 100;
  const dailyGrowth = ((mlkemCount[0].count - yesterdayMlkem[0].count) / yesterdayMlkem[0].count * 100);
  
  const daysToTarget = (100 - mlkemPct) / (dailyGrowth / 24); // Assuming linear growth
  const status = dailyGrowth >= 2 ? 'on_track' : 'at_risk';
  
  return {
    total_transactions: totalCount[0].count,
    rsa_count: rsaCount[0].count,
    mlkem_count: mlkemCount[0].count,
    rsa_percentage: rsaPct.toFixed(1),
    mlkem_percentage: mlkemPct.toFixed(1),
    mlkem_daily_growth: dailyGrowth.toFixed(1) + '%',
    migration_target: 80,
    days_to_target: Math.ceil(daysToTarget),
    status: status,
    timestamp: new Date().toISOString()
  };
}
```

### A3. Key Rotation Health Calculation

```javascript
async function getKeyRotationHealth() {
  const keys = await db.query(`
    SELECT key_id, algorithm, created_at, last_used_at, 
           DATE_ADD(created_at, INTERVAL 90 DAY) as rotation_due_at, status 
    FROM key_metadata 
    WHERE status IN ('active', 'pending_rotation')
  `);
  
  const now = Date.now();
  let overduCount = 0, pendingCount = 0, activeCount = 0;
  let totalAgeDays = 0;
  
  keys.forEach(key => {
    const ageMs = now - new Date(key.created_at).getTime();
    const ageDays = ageMs / (1000 * 60 * 60 * 24);
    totalAgeDays += ageDays;
    
    const daysUntilRotation = (new Date(key.rotation_due_at).getTime() - now) / (1000 * 60 * 60 * 24);
    
    if (key.status === 'active') {
      activeCount++;
      if (daysUntilRotation < 0) overduCount++;
      else if (daysUntilRotation < 7) pendingCount++; // Mark as pending if < 7 days
    }
  });
  
  const avgAgeDays = totalAgeDays / keys.length;
  let complianceScore = 100;
  complianceScore -= (overduCount / keys.length) * 30;
  complianceScore -= (pendingCount / keys.length) * 10;
  complianceScore -= Math.max(0, (avgAgeDays - 60) / 60) * 20;
  
  const healthStatus = complianceScore >= 95 ? 'excellent' : 
                       complianceScore >= 85 ? 'good' :
                       complianceScore >= 70 ? 'fair' : 'critical';
  
  return {
    total_keys: keys.length,
    keys_active: activeCount,
    keys_pending_rotation: pendingCount,
    keys_overdue_rotation: overduCount,
    avg_age_days: avgAgeDays.toFixed(1),
    compliance_score: complianceScore.toFixed(1),
    health_status: healthStatus,
    timestamp: new Date().toISOString()
  };
}
```

---

## FINAL CHECKLIST

Before marking complete:

- [ ] All 5 metrics' backend APIs are implemented + tested
- [ ] Database schema updated with new tables + columns
- [ ] KPI cards render correctly with live data
- [ ] Charts display with proper legends + tooltips
- [ ] Alert system detects anomalies in real-time
- [ ] Transaction table has new columns + filtering
- [ ] Responsive design works on mobile/tablet/desktop
- [ ] All interactions (click, hover, time window) tested
- [ ] Performance: dashboard loads in < 3s
- [ ] Documentation complete + team trained
- [ ] Monitoring alerts set up for critical metrics
- [ ] Rollback plan documented in case of issues

