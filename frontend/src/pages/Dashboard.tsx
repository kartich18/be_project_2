import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import AdminAnalytics from './AdminAnalytics';
import ClientTransactions from './ClientTransactions';

export default function Dashboard() {
  const navigate = useNavigate();
  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  })();

  const [activeTab, setActiveTab] = useState<'analytics' | 'transactions'>(user.role === 'admin' ? 'analytics' : 'transactions');

  function logout() {
    // End session by discarding tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    navigate('/login', { replace: true });
  }

  return (
    <>
      <header className="glass-header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon" />
            <h1>Quantum-Safe Bank</h1>
          </div>

          <div style={{display:'flex', gap:10}}>
            {user.role === 'admin' && (
              <>
                <button onClick={() => setActiveTab('analytics')} className="btn" style={{ background: activeTab === 'analytics' ? 'rgba(255,255,255,0.1)' : 'transparent', border:'none', color:'#fff', padding:'8px 16px', borderRadius:6, cursor:'pointer' }}>Server Analytics</button>
                <button onClick={() => setActiveTab('transactions')} className="btn" style={{ background: activeTab === 'transactions' ? 'rgba(255,255,255,0.1)' : 'transparent', border:'none', color:'#fff', padding:'8px 16px', borderRadius:6, cursor:'pointer' }}>Node Transfers</button>
              </>
            )}
            {user.role === 'viewer' && (
              <span className="badge" style={{background:'rgba(52, 211, 153, 0.1)', color:'var(--accent-green)', padding:'5px 12px', borderRadius:20, fontWeight:'bold', display:'flex', alignItems:'center'}}>
                Client Mode
              </span>
            )}
          </div>

          <nav style={{ display:'flex', alignItems:'center', gap:12 }}>
            <Link to="/harvest" style={{ color:'var(--accent-purple)', textDecoration:'none', border:'1px solid var(--accent-purple)', padding:'5px 12px', borderRadius:6 }}>Attack Simulator →</Link>
            <span style={{ fontSize:'0.8rem', color:'var(--text-muted)' }}>👤 {user.username} ({user.role})</span>
            <button onClick={logout} style={{ background:'rgba(248,113,113,0.12)', border:'1px solid rgba(248,113,113,0.3)', color:'#f87171', padding:'5px 12px', borderRadius:6, cursor:'pointer' }}>Logout</button>
          </nav>
        </div>
      </header>
      
      <div className="app-container">
        {activeTab === 'analytics' ? <AdminAnalytics /> : <ClientTransactions />}
      </div>
    </>
  );
}
