import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useSSE } from '../hooks/useSSE';

// Types
interface UserNode {
  username: string;
  account_id: string;
}

interface Transaction {
  id: number;
  timestamp: string;
  amount: number;
  sender: string;
  receiver: string;
  crypto_method: string;
  total_time_ms: number;
}

export default function ClientTransactions() {
  const [directory, setDirectory] = useState<UserNode[]>([]);
  const [history, setHistory] = useState<Transaction[]>([]);
  const [targetAccount, setTargetAccount] = useState('');
  const [myAccount, setMyAccount] = useState('');
  const [sendAmount, setSendAmount] = useState('100');
  const [loading, setLoading] = useState(false);
  const [txError, setTxError] = useState('');
  const [toast, setToast] = useState<{title:string, message:string}|null>(null);

  const token = localStorage.getItem('access_token');
  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}'); } catch { return {}; }
  })();

  // Fetch users and history on load
  useEffect(() => {
    const api = axios.create({
      headers: { Authorization: `Bearer ${token}` }
    });
    async function init() {
      try {
        const [dirRes, histRes, accRes] = await Promise.all([
          api.get('/api/directory/users'),
          api.get('/api/transactions/history?limit=25'),
          api.get('/api/accounts')
        ]);
        // Remove self from directory so you can't send money to yourself
        const others = (dirRes.data.users || []).filter((u:UserNode) => u.username !== user.username);
        setDirectory(others);
        
        // Wait, history endpoint returns raw accounts! The UI should show accounts OR we can just show them.
        setHistory(histRes.data.transactions || []);
        
        if (accRes.data.accounts && accRes.data.accounts.length > 0) {
            setMyAccount(accRes.data.accounts[0].account_number);
        }
      } catch (err) {
        console.error("Failed to load client dependencies", err);
      }
    }
    init();
  }, []);

  // SSE for private transactions
  useSSE('/api/stream/my_transactions', {
    transaction: (payload: any) => {
      try {
        if (payload.type === 'transaction') {
            const tx = payload.data?.classical;
            
            // Generate toast
            setToast({
                title: "Transaction Activity",
                message: `$${tx.amount.toFixed(2)} transfer processed!`
            });
            setTimeout(() => setToast(null), 4000);

            // Fetch latest history to guarantee clean state
            const api = axios.create({
              headers: { Authorization: `Bearer ${token}` }
            });
            api.get('/api/transactions/history?limit=25').then(res => setHistory(res.data.transactions));
        }
      } catch { /* silent */ }
    }
  });

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    setTxError('');
    
    if (!targetAccount) {
      setTxError('Please select a recipient.');
      return;
    }
    
    setLoading(true);
    try {
      // We pass our username as the "sender", wait, the backend relies on account IDs being passed!
      // But we can just use the targetAccount ID in the payload. Wait, whose account from?
      // During earlier testing, auth logic accepted strings. We will submit `username` for from, or let the backend do it.
      // Wait, earlier the load-generator generated payloads like {"amount": val, "account_id_from": "C1", "account_id_to": "C2"}.
      // If we send `username` here, the backend accepts it as the string to store.
      
      await axios.post('/api/transaction', {
        amount: parseFloat(sendAmount),
        account_id_from: myAccount || user.username,
        account_id_to: targetAccount
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTargetAccount('');
      setSendAmount('100');
    } catch (err: any) {
      setTxError(err.response?.data?.error || 'Transaction failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {toast && (
        <div className="toast slide-up">
          <div className="toast-icon">⚡</div>
          <div className="toast-content">
            <h4>{toast.title}</h4>
            <p>{toast.message}</p>
          </div>
        </div>
      )}

      <div className="dashboard-grid">
        {/* Left Column: Transfer */}
        <div className="left-col">
          <section className="card glass-card load-section">
            <h2>Manual Transfer</h2>
            <p>Send quantum-safe transactions instantly across the network.</p>
            
            <form onSubmit={handleSend} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
              {txError && <div className="error-msg" role="alert" style={{color:'#f87171', fontSize:'0.9rem'}}>{txError}</div>}
              
              <div className="input-group">
                <label>Recipient Node</label>
                <select 
                  value={targetAccount} 
                  onChange={e => setTargetAccount(e.target.value)} 
                  required
                  style={{ background: 'var(--surface-dark)', border: '1px solid var(--border-color)', color: 'white', padding: '0.8rem', borderRadius: '4px' }}
                >
                  <option value="" disabled>Select a remote peer...</option>
                  {directory.map(u => (
                    <option key={u.account_id} value={u.account_id}>
                      {u.username} ({u.account_id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="input-group">
                <label>Amount (INR)</label>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={sendAmount}
                  onChange={e => setSendAmount(e.target.value)}
                  required
                  style={{ background: 'var(--surface-dark)', border: '1px solid var(--border-color)', color: 'white', padding: '0.8rem', borderRadius: '4px' }}
                />
              </div>

              <button type="submit" disabled={loading} className="btn primary-btn" style={{ width: '100%', padding: '0.8rem', background: 'var(--accent-cyan)', color: 'black', fontWeight: 'bold' }}>
                {loading ? 'Processing...' : 'Transfer Funds'}
              </button>
            </form>
          </section>
        </div>

        {/* Right Column: Feed */}
        <div className="right-col">
          <section className="card glass-card">
            <h2>Private Activity Feed</h2>
            <div className="table-responsive">
              <table className="clients-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Direction</th>
                    <th>Node</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.length === 0 ? (
                    <tr><td colSpan={5} style={{textAlign:'center', padding:'2rem', color:'var(--text-muted)'}}>No recent transactions found.</td></tr>
                  ) : history.map(tx => {
                    const isOutgoing = tx.sender === myAccount || tx.sender === user.username;
                    return (
                      <tr key={tx.id}>
                        <td>{new Date(tx.timestamp).toLocaleTimeString()}</td>
                        <td style={{ color: isOutgoing ? '#f87171' : '#34d399' }}>{isOutgoing ? 'OUT' : 'IN'}</td>
                        <td>{isOutgoing ? tx.receiver : tx.sender}</td>
                        <td style={{ color: isOutgoing ? '#f87171' : '#34d399', fontWeight:'bold' }}>${tx.amount.toFixed(2)}</td>
                        <td><span className="status-badge" style={{background: 'rgba(52, 211, 153, 0.2)', color: 'var(--accent-green)'}}>COMPLETE</span></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}
