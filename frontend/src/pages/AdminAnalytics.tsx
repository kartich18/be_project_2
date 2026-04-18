import { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Chart,
  LineElement, BarElement, PointElement, CategoryScale, LinearScale,
  LogarithmicScale, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import api from '../api/client';
import { useSSE } from '../hooks/useSSE';

Chart.register(LineElement, BarElement, PointElement, CategoryScale, LinearScale,
  LogarithmicScale, Tooltip, Legend, Filler);
Chart.defaults.color = '#8b949e';
Chart.defaults.font.family = "'Inter', sans-serif";

// ── Types ────────────────────────────────────────────────────────────────────
interface TxRecord {
  id: number; timestamp: string; amount: number; sender: string;
  receiver: string; crypto_method: string; key_gen_time_ms: number;
  encapsulate_time_ms: number | null; encrypt_time_ms: number;
  decapsulate_time_ms: number | null; decrypt_time_ms: number;
  total_time_ms: number; key_size_bytes: number; secret_key_bytes: number | null;
  ciphertext_size_bytes: number; status: string;
}
interface TxBundle { classical: TxRecord; pqc_512?: TxRecord; pqc_768?: TxRecord; pqc_1024?: TxRecord; }
interface MetricsGroup {
  avg_total_ms: number; avg_key_gen_ms: number; avg_encrypt_ms: number;
  avg_decrypt_ms: number; avg_key_size_bytes: number; avg_ciphertext_size_bytes: number;
  avg_encapsulate_ms?: number; avg_decapsulate_ms?: number;
  payload_overhead_ratio?: number; key_material_footprint_bytes?: number;
}
interface Metrics { classical?: MetricsGroup; pqc_512?: MetricsGroup; pqc_768?: MetricsGroup; pqc_1024?: MetricsGroup; }
interface ClientInfo { client_id: string; port: number; status: string; last_seen: string | null; }

// ── Palette ──────────────────────────────────────────────────────────────────
const C = {
  rsa:    { fill: 'rgba(47,129,247,0.8)',   line: 'rgba(47,129,247,1)'   },
  pqc512: { fill: 'rgba(45,212,191,0.8)',   line: 'rgba(45,212,191,1)'   },
  pqc768: { fill: 'rgba(163,113,247,0.8)',  line: 'rgba(163,113,247,1)'  },
  pqc1024:{ fill: 'rgba(245,158,11,0.8)',   line: 'rgba(245,158,11,1)'   },
};

function methodBadgeClass(m: string) {
  if (m === 'RSA-2048')   return 'method-rsa';
  if (m === 'ML-KEM-512') return 'method-pqc-512';
  if (m === 'ML-KEM-768') return 'method-pqc-768';
  if (m === 'ML-KEM-1024') return 'method-pqc-1024';
  return 'method-pqc-768';
}

function fmt(ms: number | null | undefined) {
  return ms != null ? ms.toFixed(4) : '—';
}

const MAX_LATENCY_PTS = 30;

// ── Toast ─────────────────────────────────────────────────────────────────────
function Toast({ tx }: { tx: TxRecord }) {
  return (
    <div className="toast">
      🖥 <strong>Transaction processed</strong><br />
      {tx.sender} → {tx.receiver}: ${tx.amount.toFixed(2)}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function AdminAnalytics() {
  const navigate = useNavigate();
  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  })();

  // Guard
  useEffect(() => {
    if (!localStorage.getItem('access_token')) navigate('/login', { replace: true });
  }, [navigate]);

  // State
  const [sseStatus, setSseStatus]       = useState<'connecting' | 'live' | 'reconnecting'>('connecting');
  const [txList, setTxList]             = useState<TxRecord[]>([]);
  const [toast, setToast]               = useState<TxRecord | null>(null);
  const [loadRunning, setLoadRunning]   = useState(false);
  const [loadMsg, setLoadMsg]           = useState('');
  const [analyticsWindow, setAnalyticsWindow] = useState('24h');
  const [clients, setClients]           = useState<ClientInfo[]>([]);

  // KPIs
  const [latency, setLatency]   = useState({ rsa:'-- ms', pqc512:'-- ms', pqc768:'-- ms', pqc1024:'-- ms' });
  const [kpiMig, setKpiMig]     = useState({ val: '--%', sub: 'Target 80%' });
  const [kpiRot, setKpiRot]     = useState({ val: '--', sub: 'Compliance score --' });
  const [kpiAlgo, setKpiAlgo]   = useState({ val: '--', sub: 'Comparing RSA vs ML-KEM' });
  const [kpiFail, setKpiFail]   = useState({ val: '--%', sub: 'Status: --' });
  const [algoContent, setAlgoContent] = useState('No data yet.');
  const [anomalies, setAnomalies]     = useState<{ severity: string; metric?: string; delta_pct?: number }[]>([]);
  const [breakdown, setBreakdown]     = useState<{ encap512: string; decap512: string; encap768: string; decap768: string; encap1024: string; decap1024: string }>({ encap512:'--',decap512:'--',encap768:'--',decap768:'--',encap1024:'--',decap1024:'--' });
  const [ratios, setRatios]     = useState({ rsa:0, r512:0, r768:0, r1024:0,  max:1 });
  const [footprints, setFp]     = useState({ rsa:0, f512:0, f768:0, f1024:0,  max:1 });

  // Chart data refs (mutable, no re-render on chart update)
  const latLabels  = useRef<string[]>([]);
  const latRsa     = useRef<(number|null)[]>([]);
  const lat512     = useRef<(number|null)[]>([]);
  const lat768     = useRef<(number|null)[]>([]);
  const lat1024    = useRef<(number|null)[]>([]);
  const latChartRef  = useRef<Chart<'line'> | null>(null);

  const [perfData, setPerfData] = useState({
    labels: ['Key Generation', 'Encryption', 'Decryption'],
    datasets: [
      { label:'RSA-2048',    data:[0,0,0], backgroundColor: C.rsa.fill },
      { label:'ML-KEM-512',  data:[0,0,0], backgroundColor: C.pqc512.fill },
      { label:'ML-KEM-768',  data:[0,0,0], backgroundColor: C.pqc768.fill },
      { label:'ML-KEM-1024', data:[0,0,0], backgroundColor: C.pqc1024.fill },
    ],
  });
  const [sizeData, setSizeData] = useState({
    labels: ['Public Key', 'Ciphertext'],
    datasets: [
      { label:'RSA-2048',    data:[0,0], backgroundColor: C.rsa.fill },
      { label:'ML-KEM-512',  data:[0,0], backgroundColor: C.pqc512.fill },
      { label:'ML-KEM-768',  data:[0,0], backgroundColor: C.pqc768.fill },
      { label:'ML-KEM-1024', data:[0,0], backgroundColor: C.pqc1024.fill },
    ],
  });

  // ── Helpers ───────────────────────────────────────────────────────────────
  const pushToChart = useCallback((bundle: TxBundle) => {
    const now = new Date().toLocaleTimeString();
    latLabels.current.push(now);
    latRsa.current.push(bundle.classical.total_time_ms);
    lat512.current.push(bundle.pqc_512?.total_time_ms ?? null);
    lat768.current.push(bundle.pqc_768?.total_time_ms ?? null);
    lat1024.current.push(bundle.pqc_1024?.total_time_ms ?? null);

    if (latLabels.current.length > MAX_LATENCY_PTS) {
      latLabels.current.shift();
      latRsa.current.shift(); lat512.current.shift();
      lat768.current.shift(); lat1024.current.shift();
    }
    latChartRef.current?.update('none');

    setLatency({
      rsa:    bundle.classical.total_time_ms.toFixed(2) + ' ms',
      pqc512: bundle.pqc_512  ? bundle.pqc_512.total_time_ms.toFixed(2)  + ' ms' : '-- ms',
      pqc768: bundle.pqc_768  ? bundle.pqc_768.total_time_ms.toFixed(2)  + ' ms' : '-- ms',
      pqc1024:bundle.pqc_1024 ? bundle.pqc_1024.total_time_ms.toFixed(2) + ' ms' : '-- ms',
    });

    const rows: TxRecord[] = [bundle.classical];
    if (bundle.pqc_512)  rows.push(bundle.pqc_512);
    if (bundle.pqc_768)  rows.push(bundle.pqc_768);
    if (bundle.pqc_1024) rows.push(bundle.pqc_1024);
    setTxList(prev => [...rows, ...prev].slice(0, 80));
  }, []);

  // ── SSE ───────────────────────────────────────────────────────────────────
  useSSE('/api/stream/transactions', {
    status: (raw) => {
      const d = raw as { type?: string };
      if (d.type === 'connected') setSseStatus('live');
    },
    transaction: (raw) => {
      const event = raw as { data?: TxBundle };
      if (event.data) {
        pushToChart(event.data);
        setToast(event.data.classical);
        setTimeout(() => setToast(null), 4000);
      }
    },
  });

  // ── Data fetching ─────────────────────────────────────────────────────────
  const fetchMetrics = useCallback(async () => {
    try {
      const res = await api.get<Metrics>('/metrics?last=50');
      const m = res.data;
      if (!m) return;

      setLatency({
        rsa:    ((m.classical?.avg_total_ms) ?? 0).toFixed(2) + ' ms',
        pqc512: ((m.pqc_512?.avg_total_ms)   ?? 0).toFixed(2) + ' ms',
        pqc768: ((m.pqc_768?.avg_total_ms)   ?? 0).toFixed(2) + ' ms',
        pqc1024:((m.pqc_1024?.avg_total_ms)  ?? 0).toFixed(2) + ' ms',
      });

      // Perf chart
      setPerfData(prev => ({
        ...prev,
        datasets: [
          { ...prev.datasets[0], data: [m.classical?.avg_key_gen_ms??0, m.classical?.avg_encrypt_ms??0, m.classical?.avg_decrypt_ms??0] },
          { ...prev.datasets[1], data: [m.pqc_512?.avg_key_gen_ms??0,   m.pqc_512?.avg_encrypt_ms??0,   m.pqc_512?.avg_decrypt_ms??0]   },
          { ...prev.datasets[2], data: [m.pqc_768?.avg_key_gen_ms??0,   m.pqc_768?.avg_encrypt_ms??0,   m.pqc_768?.avg_decrypt_ms??0]   },
          { ...prev.datasets[3], data: [m.pqc_1024?.avg_key_gen_ms??0,  m.pqc_1024?.avg_encrypt_ms??0,  m.pqc_1024?.avg_decrypt_ms??0]  },
        ],
      }));

      // Size chart
      setSizeData(prev => ({
        ...prev,
        datasets: [
          { ...prev.datasets[0], data: [m.classical?.avg_key_size_bytes??294,  m.classical?.avg_ciphertext_size_bytes??256]  },
          { ...prev.datasets[1], data: [m.pqc_512?.avg_key_size_bytes??800,    m.pqc_512?.avg_ciphertext_size_bytes??768]    },
          { ...prev.datasets[2], data: [m.pqc_768?.avg_key_size_bytes??1184,   m.pqc_768?.avg_ciphertext_size_bytes??1088]   },
          { ...prev.datasets[3], data: [m.pqc_1024?.avg_key_size_bytes??1568,  m.pqc_1024?.avg_ciphertext_size_bytes??1568]  },
        ],
      }));

      // Breakdown
      setBreakdown({
        encap512:  fmt(m.pqc_512?.avg_encapsulate_ms),
        decap512:  fmt(m.pqc_512?.avg_decapsulate_ms),
        encap768:  fmt(m.pqc_768?.avg_encapsulate_ms),
        decap768:  fmt(m.pqc_768?.avg_decapsulate_ms),
        encap1024: fmt(m.pqc_1024?.avg_encapsulate_ms),
        decap1024: fmt(m.pqc_1024?.avg_decapsulate_ms),
      });

      // Ratio bars
      const rv = { rsa: m.classical?.payload_overhead_ratio??0, r512:m.pqc_512?.payload_overhead_ratio??0, r768:m.pqc_768?.payload_overhead_ratio??0, r1024:m.pqc_1024?.payload_overhead_ratio??0, max:1 };
      rv.max = Math.max(rv.rsa, rv.r512, rv.r768, rv.r1024, 1);
      setRatios(rv);

      // Footprint bars
      const fv = { rsa:m.classical?.key_material_footprint_bytes??0, f512:m.pqc_512?.key_material_footprint_bytes??0, f768:m.pqc_768?.key_material_footprint_bytes??0, f1024:m.pqc_1024?.key_material_footprint_bytes??0, max:1 };
      fv.max = Math.max(fv.rsa, fv.f512, fv.f768, fv.f1024, 1);
      setFp(fv);

    } catch { /* silent */ }
  }, []);

  const fetchAdvanced = useCallback(async (w: string) => {
    try {
      const [migRes, rotRes, cmpRes, hlthRes, anomRes] = await Promise.all([
        api.get(`/v1/analytics/migration-status?time_window=${w}`),
        api.get('/v1/keys/rotation-health'),
        api.get(`/v1/analytics/algorithm-comparison?time_window=${w}`),
        api.get(`/v1/analytics/security-health?time_window=${w}`),
        api.get('/v1/analytics/anomalies'),
      ]);

      const mig  = migRes.data;
      const rot  = rotRes.data;
      const cmp  = cmpRes.data;
      const hlth = hlthRes.data;
      const anom = anomRes.data;

      if (mig) setKpiMig({ val:`${(mig.mlkem_percentage??0).toFixed(1)}%`, sub:`Target ${mig.migration_target??80}% • ${mig.status??'unknown'}` });
      if (rot) setKpiRot({ val:`${(rot.compliance_score??0).toFixed(1)}`, sub:`${rot.health_status??'unknown'} • Overdue ${rot.keys_overdue_rotation??0}` });
      if (cmp) {
        const delta = cmp.comparison?.latency_delta_pct??0;
        setKpiAlgo({ val:`${delta.toFixed(1)}%`, sub: cmp.comparison?.latency_verdict??'N/A' });
        const r=cmp.rsa_2048??{}; const m5=cmp.ml_kem_512??{}; const m7=cmp.ml_kem??{}; const m10=cmp.ml_kem_1024??{};
        setAlgoContent(
          `RSA-2048: ${(r.avg_latency_ms??0).toFixed(3)} ms | ML-KEM-512: ${(m5.avg_latency_ms??0).toFixed(3)} ms | ML-KEM-768: ${(m7.avg_latency_ms??0).toFixed(3)} ms | ML-KEM-1024: ${(m10.avg_latency_ms??0).toFixed(3)} ms\n` +
          `Verdict: ${cmp.comparison?.latency_verdict??'N/A'} | Throughput: ${cmp.comparison?.throughput_verdict??'N/A'}\n` +
          `Key size delta (768 vs RSA): ${(cmp.comparison?.size_delta_pct??0).toFixed(1)}%\n${cmp.comparison?.recommendation??''}`
        );
      }
      if (hlth) setKpiFail({ val:`${(hlth.failure_rate_pct??0).toFixed(2)}%`, sub:`Status: ${hlth.status??'unknown'}` });
      if (anom) setAnomalies(anom.detected_anomalies??[]);
    } catch { /* silent */ }
  }, []);

  const fetchClients = useCallback(async () => {
    try {
      const res = await api.get('/clients');
      setClients(res.data.clients ?? []);
    } catch { /* silent */ }
  }, []);

  const fetchTxHistory = useCallback(async () => {
    try {
      // Fetch more rows so we can reconstruct ~30 bundles (120 / 4)
      const res = await api.get<{transactions: TxRecord[]}>('/transactions/history?limit=120');
      if (res.data.transactions) {
        const rows = res.data.transactions;
        setTxList(rows.slice(0, 80));

        // Group rows to rebuild Latency graph across tabs
        latLabels.current = [];
        latRsa.current = [];
        lat512.current = [];
        lat768.current = [];
        lat1024.current = [];

        const sorted = [...rows].reverse();
        const groups: Record<string, TxBundle> = {};

        for (const tx of sorted) {
            // Group by approximate timestamp (per second) and origin to rebuild bundles
            const timeKey = Math.floor(new Date(tx.timestamp).getTime() / 1000);
            const key = `${timeKey}_${tx.sender}_${tx.receiver}`;
            if (!groups[key]) groups[key] = { classical: tx };
            
            if (tx.crypto_method === 'RSA-2048') groups[key].classical = tx;
            if (tx.crypto_method === 'ML-KEM-512') groups[key].pqc_512 = tx;
            if (tx.crypto_method === 'ML-KEM-768') groups[key].pqc_768 = tx;
            if (tx.crypto_method === 'ML-KEM-1024') groups[key].pqc_1024 = tx;
        }

        Object.values(groups).forEach(b => {
            const timeStr = new Date(b.classical.timestamp).toLocaleTimeString();
            latLabels.current.push(timeStr);
            latRsa.current.push(b.classical.total_time_ms);
            lat512.current.push(b.pqc_512?.total_time_ms ?? null);
            lat768.current.push(b.pqc_768?.total_time_ms ?? null);
            lat1024.current.push(b.pqc_1024?.total_time_ms ?? null);
        });

        if (latLabels.current.length > MAX_LATENCY_PTS) {
            const offset = latLabels.current.length - MAX_LATENCY_PTS;
            latLabels.current = latLabels.current.slice(offset);
            latRsa.current = latRsa.current.slice(offset);
            lat512.current = lat512.current.slice(offset);
            lat768.current = lat768.current.slice(offset);
            lat1024.current = lat1024.current.slice(offset);
        }

        latChartRef.current?.update('none');
      }
    } catch { /* silent */ }
  }, []);

  // ── Effects ───────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchMetrics();
    fetchAdvanced(analyticsWindow);
    fetchClients();
    fetchTxHistory();
    const t1 = setInterval(fetchMetrics, 5000);
    const t2 = setInterval(() => fetchAdvanced(analyticsWindow), 10000);
    const t3 = setInterval(fetchClients, 10000);
    return () => { clearInterval(t1); clearInterval(t2); clearInterval(t3); };
  }, [fetchMetrics, fetchAdvanced, fetchClients, fetchTxHistory, analyticsWindow]);

  // ── Load generator ────────────────────────────────────────────────────────
  const loadInterval = useRef<ReturnType<typeof setInterval> | null>(null);
  function toggleLoad() {
    if (!loadRunning) {
      setLoadRunning(true);
      setLoadMsg('Generating synthetic traffic...');
      loadInterval.current = setInterval(async () => {
        try {
          const res = await api.post('/transaction', {
            account_id_from: `DEMO-${Math.floor(Math.random() * 1000)}`,
            account_id_to:   `DEMO-${Math.floor(Math.random() * 1000)}`,
            amount:          parseFloat((Math.random() * 1000).toFixed(2)),
          });
          pushToChart(res.data);
        } catch { /* silent */ }
      }, 500);
    } else {
      setLoadRunning(false);
      setLoadMsg('Load generation stopped.');
      if (loadInterval.current) clearInterval(loadInterval.current);
    }
  }

  // ── Logout ────────────────────────────────────────────────────────────────
  async function logout() {
    try { await api.post('/auth/logout'); } catch { /* */ }
    localStorage.clear();
    navigate('/login', { replace: true });
  }

  // ── Latency chart data (built from refs) ──────────────────────────────────
  const latChartData = {
    labels: latLabels.current,
    datasets: [
      { label:'RSA-2048',    data: latRsa.current,  borderColor: C.rsa.line,    backgroundColor: C.rsa.fill,    tension:0.4, borderWidth:2, pointRadius:2 },
      { label:'ML-KEM-512',  data: lat512.current,  borderColor: C.pqc512.line, backgroundColor: C.pqc512.fill, tension:0.4, borderWidth:2, pointRadius:2 },
      { label:'ML-KEM-768',  data: lat768.current,  borderColor: C.pqc768.line, backgroundColor: C.pqc768.fill, tension:0.4, borderWidth:2, pointRadius:2 },
      { label:'ML-KEM-1024', data: lat1024.current, borderColor: C.pqc1024.line,backgroundColor: C.pqc1024.fill,tension:0.4, borderWidth:2, pointRadius:2 },
    ],
  };

  // ── Bar fill helper ───────────────────────────────────────────────────────
  function fpLabel(v: number) { return v >= 1000 ? `${(v/1024).toFixed(2)} KB` : `${Math.round(v)} B`; }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <>
      {/* Header */}
      

      <>
        {/* ── Main Grid ── */}
        <main className="dashboard-grid">
          {/* Left Column */}
          <div className="left-col">
            {/* Load Generator */}
            <section className="card glass-card load-section">
              <h2>Load Generator</h2>
              <p>Simulate high-volume network traffic to visualize performance under load.</p>
              <button
                id="btn-load-test"
                className={`btn ${loadRunning ? 'primary-btn' : 'secondary-btn'}`}
                onClick={toggleLoad}
              >
                {loadRunning ? 'Stop Demo Load' : 'Start Demo Load'}
              </button>
              {loadMsg && (
                <div className={`status-message ${loadRunning ? 'success' : ''}`}
                  style={{ color: loadRunning ? undefined : 'var(--text-secondary)' }}>
                  {loadMsg}
                </div>
              )}
            </section>

            {/* Connected Clients */}
            <section className="card glass-card" style={{ padding:20 }}>
              <h2 style={{ marginBottom:12 }}>🖥️ Connected Clients</h2>
              <div style={{ display:'flex', flexDirection:'column', gap:0 }}>
                {clients.length === 0
                  ? <p style={{ color:'var(--text-muted)', fontSize:'0.82rem' }}>No clients connected.</p>
                  : clients.map(c => {
                    const online = c.status === 'online';
                    return (
                      <div key={c.client_id} className="client-row">
                        <span className="client-dot"
                          style={{ background: online ? 'var(--accent-green)' : '#f87171',
                            boxShadow: online ? '0 0 6px var(--accent-green)' : undefined }} />
                        <span className="client-name">{c.client_id}</span>
                        <span className="client-port">:{c.port}</span>
                        <span className={online ? 'client-status-online' : 'client-status-offline'}>
                          {online ? 'online' : 'offline'}
                        </span>
                      </div>
                    );
                  })
                }
              </div>
            </section>

            {/* Metric Summary Cards */}
            <section className="summary-cards">
              <div className="summary-card"><h3>Avg Latency (Classical)</h3><div className="metric-value" id="val-lat-classical">{latency.rsa}</div><div className="metric-sub">RSA-2048</div></div>
              <div className="summary-card highlight-512"><h3>Avg Latency (PQC-512)</h3><div className="metric-value" id="val-lat-pqc-512">{latency.pqc512}</div><div className="metric-sub">ML-KEM-512</div></div>
              <div className="summary-card highlight"><h3>Avg Latency (PQC-768)</h3><div className="metric-value" id="val-lat-pqc-768">{latency.pqc768}</div><div className="metric-sub">ML-KEM-768</div></div>
              <div className="summary-card highlight-1024"><h3>Avg Latency (PQC-1024)</h3><div className="metric-value" id="val-lat-pqc-1024">{latency.pqc1024}</div><div className="metric-sub">ML-KEM-1024</div></div>
            </section>
          </div>

          {/* Right Column */}
          <div className="right-col">
            <section className="card glass-card chart-container">
              <h2>Latency Over Time</h2>
              <div className="chart-wrapper">
                <Line
                  ref={latChartRef as React.RefObject<Chart<'line'>>}
                  data={latChartData}
                  options={{ responsive:true, maintainAspectRatio:false,
                    scales: { y:{ beginAtZero:true, title:{display:true,text:'Total Latency (ms)'}, grid:{color:'rgba(48,54,61,0.5)'} }, x:{ grid:{display:false}, ticks:{display:false} } },
                    plugins: { legend:{position:'top'} },
                    animation: false,
                  }}
                />
              </div>
            </section>

            <section className="card glass-card chart-container">
              <h2>Performance Comparison</h2>
              <div className="chart-wrapper">
                <Bar data={perfData} options={{ responsive:true, maintainAspectRatio:false,
                  scales: { y:{beginAtZero:true,title:{display:true,text:'Time (ms)'},grid:{color:'rgba(48,54,61,0.5)'}}, x:{grid:{display:false}} } }} />
              </div>
            </section>

            <section className="card glass-card chart-container">
              <h2>Key Size Comparison (Bytes)</h2>
              <div className="chart-wrapper">
                <Bar data={sizeData} options={{ responsive:true, maintainAspectRatio:false,
                  scales: { y:{type:'logarithmic',title:{display:true,text:'Size (Bytes) - Log Scale'},grid:{color:'rgba(48,54,61,0.5)'}}, x:{grid:{display:false}} } }} />
              </div>
            </section>
          </div>
        </main>

        {/* ── Advanced Analytics ── */}
        <section className="card glass-card advanced-section">
          <h2>Advanced Security &amp; Migration Analytics</h2>
          <div className="advanced-kpi-grid">
            <div className="kpi-card-adv"><h3>Post-Quantum Migration</h3><div className="kpi-main" id="kpi-migration">{kpiMig.val}</div><p id="kpi-migration-sub">{kpiMig.sub}</p></div>
            <div className="kpi-card-adv"><h3>Key Rotation Health</h3><div className="kpi-main" id="kpi-rotation">{kpiRot.val}</div><p id="kpi-rotation-sub">{kpiRot.sub}</p></div>
            <div className="kpi-card-adv"><h3>Algorithm Ratio</h3><div className="kpi-main" id="kpi-algo-ratio">{kpiAlgo.val}</div><p id="kpi-algo-ratio-sub">{kpiAlgo.sub}</p></div>
            <div className="kpi-card-adv"><h3>Failure Rate</h3><div className="kpi-main" id="kpi-failure">{kpiFail.val}</div><p id="kpi-failure-sub">{kpiFail.sub}</p></div>
          </div>

          <div className="advanced-bottom-grid">
            <div className="algo-comparison-panel">
              <h3>Algorithm Performance Comparison</h3>
              <pre className="analytics-content" style={{ whiteSpace:'pre-wrap', fontFamily:'inherit' }}>{algoContent}</pre>
            </div>
            <div className="anomaly-panel">
              <h3>Security Anomalies</h3>
              <ul className="anomaly-list">
                {anomalies.length === 0
                  ? <li>No anomalies detected.</li>
                  : anomalies.map((a, i) => (
                    <li key={i} className={`anomaly-${a.severity ?? 'info'}`}>
                      [{(a.severity ?? 'info').toUpperCase()}] {a.metric ? `${a.metric}: ` : ''}{(a.delta_pct ?? 0).toFixed(1)}%
                    </li>
                  ))
                }
              </ul>
            </div>
          </div>

          {/* Crypto Breakdown */}
          <div className="crypto-breakdown-grid">
            {/* Encap/Decap table */}
            <div className="breakdown-panel">
              <h3>Encap + Decap Time <span className="tag-pqc">PQC Only</span></h3>
              <table className="breakdown-table">
                <thead><tr><th>Algorithm</th><th>Encap (ms)</th><th>Decap (ms)</th><th>KEM Total</th></tr></thead>
                <tbody>
                  <tr><td><span className="method-badge method-pqc-512">ML-KEM-512</span></td><td>{breakdown.encap512}</td><td>{breakdown.decap512}</td><td>{breakdown.encap512 !== '--' && breakdown.decap512 !== '--' ? (parseFloat(breakdown.encap512)+parseFloat(breakdown.decap512)).toFixed(4) : '--'}</td></tr>
                  <tr><td><span className="method-badge method-pqc-768">ML-KEM-768</span></td><td>{breakdown.encap768}</td><td>{breakdown.decap768}</td><td>{breakdown.encap768 !== '--' && breakdown.decap768 !== '--' ? (parseFloat(breakdown.encap768)+parseFloat(breakdown.decap768)).toFixed(4) : '--'}</td></tr>
                  <tr><td><span className="method-badge method-pqc-1024">ML-KEM-1024</span></td><td>{breakdown.encap1024}</td><td>{breakdown.decap1024}</td><td>{breakdown.encap1024 !== '--' && breakdown.decap1024 !== '--' ? (parseFloat(breakdown.encap1024)+parseFloat(breakdown.decap1024)).toFixed(4) : '--'}</td></tr>
                </tbody>
              </table>
            </div>

            {/* Payload Overhead Ratio */}
            <div className="breakdown-panel">
              <h3>Payload Overhead Ratio</h3>
              <p className="breakdown-hint">KEM ciphertext bytes ÷ 28 B AES-GCM base overhead</p>
              {[['rsa','RSA-2048','method-rsa',ratios.rsa],['r512','ML-KEM-512','method-pqc-512',ratios.r512],['r768','ML-KEM-768','method-pqc-768',ratios.r768],['r1024','ML-KEM-1024','method-pqc-1024',ratios.r1024]].map(([k,label,cls,val]) => (
                <div key={k as string} className="ratio-row">
                  <span className={`ratio-label method-badge ${cls}`}>{label}</span>
                  <div className="ratio-track"><div className={`ratio-fill ${k === 'rsa' ? 'rsa-fill' : k === 'r512' ? 'pqc512-fill' : k === 'r768' ? 'pqc768-fill' : 'pqc1024-fill'}`} style={{ width:`${((val as number)/ratios.max*100).toFixed(1)}%` }} /></div>
                  <span className="ratio-val">{(val as number).toFixed(1)}×</span>
                </div>
              ))}
            </div>

            {/* Key Material Footprint */}
            <div className="breakdown-panel">
              <h3>Key Material Footprint</h3>
              <p className="breakdown-hint">Public key + Secret key (bytes total)</p>
              {[['rsa','RSA-2048','method-rsa',footprints.rsa],['f512','ML-KEM-512','method-pqc-512',footprints.f512],['f768','ML-KEM-768','method-pqc-768',footprints.f768],['f1024','ML-KEM-1024','method-pqc-1024',footprints.f1024]].map(([k,label,cls,val]) => (
                <div key={k as string} className="footprint-row">
                  <span className={`fp-label method-badge ${cls}`}>{label}</span>
                  <div className="fp-track"><div className={`fp-fill ${k === 'rsa' ? 'rsa-fill' : k === 'f512' ? 'pqc512-fill' : k === 'f768' ? 'pqc768-fill' : 'pqc1024-fill'}`} style={{ width:`${((val as number)/footprints.max*100).toFixed(1)}%` }} /></div>
                  <span className="fp-val">{fpLabel(val as number)}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Recent Transactions ── */}
        <section className="card glass-card history-section-wide">
          <h2>Recent Transactions</h2>
          <div className="table-responsive">
            <table className="tx-table" id="tx-table">
              <thead>
                <tr>
                  <th>Tx ID</th><th>Time</th><th>Sender → Receiver</th>
                  <th>Amount</th><th>Method</th>
                  <th>Key Gen (ms)</th><th>Encap (ms)</th><th>Encrypt (ms)</th>
                  <th>Decap (ms)</th><th>Decrypt (ms)</th><th>Total (ms)</th>
                  <th>Key Material (B)</th><th>Cipher Size (B)</th>
                </tr>
              </thead>
              <tbody id="tx-list">
                {txList.map((tx, i) => {
                  const km = tx.secret_key_bytes ? tx.key_size_bytes + tx.secret_key_bytes : tx.key_size_bytes;
                  return (
                    <tr key={`${tx.id}-${i}`}
                      style={{ borderBottom: tx.crypto_method === 'ML-KEM-1024' ? '2px solid rgba(48,54,61,0.8)' : undefined }}>
                      <td>#{tx.id}</td>
                      <td>{new Date(tx.timestamp).toLocaleTimeString()}</td>
                      <td>{tx.sender} → {tx.receiver}</td>
                      <td style={{ color:'var(--accent-green)' }}>${tx.amount.toFixed(2)}</td>
                      <td><span className={`method-badge ${methodBadgeClass(tx.crypto_method)}`}>{tx.crypto_method}</span></td>
                      <td>{tx.key_gen_time_ms.toFixed(4)}</td>
                      <td>{tx.encapsulate_time_ms != null ? tx.encapsulate_time_ms.toFixed(4) : '—'}</td>
                      <td>{tx.encrypt_time_ms.toFixed(4)}</td>
                      <td>{tx.decapsulate_time_ms != null ? tx.decapsulate_time_ms.toFixed(4) : '—'}</td>
                      <td>{tx.decrypt_time_ms.toFixed(4)}</td>
                      <td><strong>{tx.total_time_ms.toFixed(4)}</strong></td>
                      <td>{km}</td>
                      <td>{tx.ciphertext_size_bytes}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </>

      {/* Toast */}
      {toast && <Toast tx={toast} />}
    </>
  );
}
