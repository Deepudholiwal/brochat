import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../utils/api';
import { LogIn } from 'lucide-react';

export default function Login({ adminMode = false }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.login({ email, password });
      localStorage.setItem('brochat_token', data.access_token);
      navigate(adminMode ? '/admin' : '/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card glass-panel">
        <div className="auth-header">
          <h2>{adminMode ? 'BroChat Admin' : 'BroChat'}</h2>
          <p>{adminMode ? 'Administrator sign in' : 'Welcome back'}</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary auth-submit">
            {loading ? 'Signing in...' : 'Sign In'} <LogIn size={18} />
          </button>
        </form>
        <div className="auth-footer">
          {adminMode
            ? <p><Link to="/login">User sign in</Link></p>
            : <p>Don't have an account? <Link to="/signup">Sign up</Link></p>}
        </div>
      </div>
    </div>
  );
}
