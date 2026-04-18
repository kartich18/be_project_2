import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [accessCode, setAccessCode] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  // Redirect if already logged in
  if (localStorage.getItem('access_token')) {
    navigate('/', { replace: true });
    return null;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Please enter both username and password.');
      return;
    }
    if (isRegistering && !accessCode) {
      setError('An access code is required to register a new node.');
      return;
    }
    setLoading(true);
    try {
      if (isRegistering) {
        // Create the user first
        await axios.post('/api/auth/register', { username, password, access_code: accessCode });
      }

      // Login to get tokens
      const { data } = await axios.post('/api/auth/login', { username, password });
      localStorage.setItem('access_token',  data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('user',          JSON.stringify(data.user));
      navigate('/', { replace: true });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error
        ?? 'Network error — is the server reachable?';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-wrapper">
        {/* Brand */}
        <div className="brand">
          <div className="brand-icon">🏦</div>
          <h1>Quantum-Safe Bank</h1>
          <p>Post-Quantum Cryptography Node</p>
        </div>

        {/* Card */}
        <div className="login-card">
          <h2>{isRegistering ? 'Create an Account' : 'Welcome back'}</h2>
          <p className="subtitle">
            {isRegistering ? 'Register your node with a valid access code' : 'Sign in to access the banking dashboard'}
          </p>

          {error && <div className="error-msg" role="alert">{error}</div>}

          <form onSubmit={handleSubmit} noValidate>
            <div className="input-group">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                placeholder="Enter your username"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="input-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            {isRegistering && (
              <div className="input-group">
                <label htmlFor="accessCode">Access Code</label>
                <input
                  id="accessCode"
                  type="text"
                  placeholder="Enter administrator or viewer code"
                  value={accessCode}
                  onChange={e => setAccessCode(e.target.value)}
                  required={isRegistering}
                />
              </div>
            )}

            <button
              type="submit"
              className="login-btn"
              id="login-btn"
              disabled={loading}
            >
              {loading ? <span className="spinner" /> : (isRegistering ? 'Register & Sign In' : 'Sign In')}
            </button>
          </form>

          <div className="pqc-badge">
            🔒 ML-KEM-768 encrypted · JWT authenticated · TLS transport
          </div>
        </div>

        <p className="login-hint">
          {isRegistering ? (
            <>
              Already have an account?&nbsp;
              <a href="#" onClick={(e) => { e.preventDefault(); setIsRegistering(false); setError(''); }} style={{ color: 'var(--accent-cyan)', textDecoration: 'none' }}>
                Sign in here
              </a>
            </>
          ) : (
            <>
              No account yet?&nbsp;
              <a href="#" onClick={(e) => { e.preventDefault(); setIsRegistering(true); setError(''); }} style={{ color: 'var(--accent-cyan)', textDecoration: 'none' }}>
                Register your node
              </a>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
