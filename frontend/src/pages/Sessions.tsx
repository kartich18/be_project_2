import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/client';

interface Session {
  id: number;
  user_id: number;
  device_id: string | null;
  user_agent: string | null;
  created_at: string;
  last_used_at: string;
  revoked: boolean;
}

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  })();

  const fetchSessions = async () => {
    try {
      setLoading(true);
      const res = await api.get('/auth/sessions');
      setSessions(res.data.sessions || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleRevoke = async (id: number) => {
    try {
      await api.delete(`/auth/sessions/${id}`);
      fetchSessions(); // refresh the list
    } catch (e) {
      console.error(e);
    }
  };

  async function logout() {
    try { await api.post('/auth/logout'); } catch { /* */ }
    localStorage.clear();
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
          <div className="status-badge">
            <span className="pulse" /> Session Management
          </div>

          <nav style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Link to="/" style={{ color: 'var(--text-secondary)', textDecoration: 'none', fontSize: '0.88rem', fontWeight: 600 }}>
              Dashboard
            </Link>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>👤 {user.username}</span>
            <button
              onClick={logout}
              style={{
                background: 'rgba(248,113,113,0.12)', border: '1px solid rgba(248,113,113,0.3)',
                color: '#f87171', padding: '5px 12px', borderRadius: 6, fontSize: '0.83rem',
                fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s'
              }}
            >
              Logout
            </button>
          </nav>
        </div>
      </header>

      <div className="app-container">
        <Link to="/" className="nav-back">← Back to Dashboard</Link>

        <section className="card glass-card history-section-wide">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2>Active Sessions</h2>
            <button className="btn secondary-btn" onClick={fetchSessions} disabled={loading} style={{ padding: '6px 12px', fontSize: '0.85rem' }}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          <div className="table-responsive">
            <table className="tx-table">
              <thead>
                <tr>
                  <th>Session ID</th>
                  <th>Device / User Agent</th>
                  <th>Created At</th>
                  <th>Last Used At</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sessions.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No sessions found.</td>
                  </tr>
                ) : (
                  sessions.map((s) => (
                    <tr key={s.id} style={{ opacity: s.revoked ? 0.6 : 1 }}>
                      <td>#{s.id}</td>
                      <td style={{ maxWidth: 300, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={s.user_agent || 'Unknown'}>
                        {s.user_agent || 'Unknown Device'}
                      </td>
                      <td>{new Date(s.created_at).toLocaleString()}</td>
                      <td>{new Date(s.last_used_at).toLocaleString()}</td>
                      <td>
                        {s.revoked ? (
                          <span style={{ color: '#f87171', fontWeight: 600 }}>Revoked</span>
                        ) : (
                          <span style={{ color: 'var(--accent-green)', fontWeight: 600 }}>Active</span>
                        )}
                      </td>
                      <td>
                        {!s.revoked && (
                          <button
                            className="btn primary-btn"
                            style={{ background: '#b91c1c', border: 'none', padding: '4px 8px', fontSize: '0.75rem' }}
                            onClick={() => handleRevoke(s.id)}
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}
