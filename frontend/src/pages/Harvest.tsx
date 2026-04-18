import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import api from '../api/client';

// ── Types ─────────────────────────────────────────────────────────────────────
interface HarvestResult {
  ciphertext_hex?: string;
  n: number;
  e: number;
  encrypted_message: number;
  algorithm?: string;
  real_kem_ciphertext?: string | null;
  real_aes_ciphertext?: string | null;
}
interface DecryptResult {
  factors: [number, number];
  private_key_d: number;
  decrypted_message: number;
  log: string[];
  qiskit_used: boolean;
}

type Phase = 1 | 2 | 3;

export default function Harvest() {
  const [phase, setPhase]                 = useState<Phase>(1);
  const [pin, setPin]                     = useState(2);
  const [harvestData, setHarvestData]     = useState<HarvestResult | null>(null);
  const [decryptData, setDecryptData]     = useState<DecryptResult | null>(null);
  const [loading, setLoading]             = useState(false);
  const [leapYear, setLeapYear]           = useState(2026);
  const [showLeapOverlay, setShowLeapOverlay] = useState(false);
  const [leapStatusText, setLeapStatusText]   = useState('Quantum technology in development...');
  const leapInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  // Progress %
  const progressPct = phase === 1 ? 0 : phase === 2 ? 50 : 100;

  async function doHarvest() {
    setLoading(true);
    try {
      const res = await api.post('/harvest/encrypt', { message: pin });
      setHarvestData(res.data);
      setPhase(2);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function doLeap() {
    setShowLeapOverlay(true);
    setLeapYear(2026);
    setLeapStatusText('Quantum technology in development...');
    let year = 2026;
    const messages = [
      'Quantum technology in development...',
      'First quantum advantage demonstrated...',
      'Breaking 512-bit RSA in labs...',
      'Cryptographically relevant quantum computers...',
      'Y2Q: RSA vulnerable to Shor\'s Algorithm!',
    ];
    leapInterval.current = setInterval(() => {
      year += 2;
      setLeapYear(year);
      const idx = Math.min(Math.floor((year - 2026) / 2), messages.length - 1);
      setLeapStatusText(messages[idx]);
      if (year >= 2036) {
        if (leapInterval.current) clearInterval(leapInterval.current);
        setTimeout(() => {
          setShowLeapOverlay(false);
          setPhase(3);
        }, 1200);
      }
    }, 600);
  }

  async function doDecrypt() {
    if (!harvestData) return;
    setLoading(true);
    try {
      const res = await api.post('/harvest/decrypt', {
        n: harvestData.n,
        e: harvestData.e,
        ciphertext: harvestData.encrypted_message,
      });
      setDecryptData(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {/* Header */}
      <header className="glass-header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon" />
            <h1>Quantum-Safe Bank</h1>
          </div>
          <div className="status-badge">
            <span className="pulse" /> Simulation Mode
          </div>
        </div>
      </header>

      <div className="app-container">
        <Link to="/" className="nav-back">← Back to Dashboard</Link>

        {/* ── Timeline ── */}
        <div className="timeline-wrapper">
          <div className="timeline-container">
            <div className="timeline-line" />
            <div className="timeline-progress" style={{ width: `${progressPct}%` }} />
            {[1,2,3].map((n) => (
              <div
                key={n}
                className={`timeline-node ${phase === n ? 'active' : phase > n ? 'completed' : ''}`}
              >
                {n}
                <div className="timeline-label">
                  {n === 1 ? 'Harvest' : n === 2 ? 'The Leap' : 'Decrypt'}
                </div>
              </div>
            ))}
          </div>
        </div>

        <main className="simulation-container">
          {/* Summary */}
          <section className="card glass-card">
            <h1 style={{ fontSize:'1.5rem', marginBottom:8 }}>Harvest Now, Decrypt Later</h1>
            <p style={{ color:'var(--text-secondary)' }}>
              Demonstration of the end-to-end threat model: from today's data interception to future decryption.
            </p>
          </section>

          {/* Phase 1: Harvest */}
          <section className="phase-section" id="section-1">
            <div className="card glass-card">
              <h2>Phase 1: Harvest Now (Classical Interception)</h2>
              <p>Enter a secret PIN to encrypt using classical RSA-15. This data is harvested by an adversary today.</p>
              <div style={{ maxWidth:400, marginTop:20 }}>
                <div className="input-group">
                  <label>Secret PIN (Message)</label>
                  <input type="number" value={pin} min={1} max={14}
                    onChange={e => setPin(parseInt(e.target.value))} />
                </div>
                <button id="btn-harvest" className="btn primary-btn" onClick={doHarvest} disabled={loading}>
                  {loading && phase === 1 ? <span className="spinner" /> : 'Encrypt & Harvest'}
                </button>
              </div>

              {harvestData && (
                <div className="code-view">
                  <h4>Stolen Data (stolen_database.json)</h4>
                  <pre className="json-payload">{JSON.stringify({
                    classical_rsa: { n: harvestData.n, e: harvestData.e, ciphertext: harvestData.encrypted_message },
                    ml_kem: harvestData.real_kem_ciphertext ? { kem_ciphertext: harvestData.real_kem_ciphertext, aes_ciphertext: harvestData.real_aes_ciphertext } : "No per-user ML-KEM ciphertext found"
                  }, null, 2)}</pre>
                  <p style={{ fontSize:'0.78rem', color:'var(--text-secondary)', marginTop:10 }}>
                    Attacker successfully intercepted the payload. Encryption prevents classical access for now.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* Phase 2: Quantum Leap */}
          <section className="phase-section leap-section-v" id="section-2">
            <h2>Phase 2: The Quantum Leap</h2>
            <p>Simulating the passage of time as quantum computing capabilities mature.</p>
            <div className="leap-placeholder">Current Year: {leapYear}</div>
            <button
              id="btn-go-leap"
              className="btn secondary-btn"
              style={{ maxWidth:300, margin:'0 auto' }}
              onClick={doLeap}
              disabled={phase < 2 || loading}
            >
              Simulate 10 Year Leap →
            </button>
          </section>

          {/* Phase 3: Decrypt */}
          <section className="phase-section" id="section-3">
            <div className="card glass-card">
              <h2>Phase 3: Decrypt Later (Quantum Attack)</h2>
              <p>Year 2036. Utilizing Shor's Algorithm on simulated quantum hardware to factor the intercepted modulus.</p>
              <div style={{ maxWidth:400, marginTop:20 }}>
                <button
                  id="btn-decrypt"
                  className="btn primary-btn"
                  onClick={doDecrypt}
                  disabled={phase < 3 || !harvestData || loading}
                >
                  {loading && phase === 3 ? <span className="spinner" /> : "Execute Shor's Algorithm"}
                </button>
              </div>

              {decryptData && (
                <div className="code-view">
                  <h4>Quantum Simulation Results</h4>
                  <div className="data-stream">
                    {decryptData.log.map((line, i) => <div key={i}>{line}</div>)}
                  </div>

                  <div style={{ marginTop:20, display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
                    <div className="summary-card">
                      <h3>Factors Found</h3>
                      <div className="metric-value">{decryptData.factors[0]} &amp; {decryptData.factors[1]}</div>
                    </div>
                    <div className="summary-card highlight">
                      <h3>Decrypted PIN</h3>
                      <div className="metric-value">{decryptData.decrypted_message}</div>
                    </div>
                  </div>

                  <div style={{ marginTop:18, padding:14, background:'rgba(248,81,73,0.1)',
                    border:'1px solid rgba(248,81,73,0.3)', borderRadius:8 }}>
                    <p style={{ color:'#f85149', fontSize:'0.88rem', fontWeight:600 }}>
                      [!] SECURITY BREACH: Classical RSA data has been compromised.
                    </p>
                  </div>
                  {harvestData.real_kem_ciphertext && (
                    <div style={{ marginTop:12, padding:14, background:'rgba(45,212,191,0.1)',
                      border:'1px solid rgba(45,212,191,0.3)', borderRadius:8 }}>
                      <p style={{ color:'var(--accent-green)', fontSize:'0.88rem', fontWeight:600 }}>
                        [✓] ML-KEM DATA SECURE: Quantum attack failed to decapsulate the ML-KEM-768 ciphertext. AES-GCM payload remains encrypted.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        </main>
      </div>

      {/* Quantum Leap Overlay */}
      {showLeapOverlay && (
        <div className="quantum-leap-overlay">
          <div className="leap-year">{leapYear}</div>
          <p style={{ color:'var(--text-secondary)', letterSpacing:2 }}>TIME ELAPSING...</p>
          <div style={{ marginTop:40, fontSize:'1.1rem', color:'var(--accent-blue)' }}>
            {leapStatusText}
          </div>
        </div>
      )}
    </>
  );
}
