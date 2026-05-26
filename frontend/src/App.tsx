import { useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import ReviewTable from './pages/ReviewTable';
import Upload from './pages/Upload';
import api from './api/client';

function Login({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async () => {
    try {
      const res = await api.post('/auth/token/', { username, password });
      localStorage.setItem('token', res.data.token);
      onLogin();
    } catch {
      setError('Invalid credentials');
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#f9fafb' }}>
      <div style={{ padding: '2rem', background: 'white', borderRadius: 12, border: '1px solid #e5e7eb', width: 360 }}>
        <h2 style={{ marginTop: 0 }}>Breathe ESG</h2>
        <p style={{ color: '#6b7280', fontSize: 14 }}>Sign in to your account</p>
        <input value={username} onChange={e => setUsername(e.target.value)}
          placeholder="Username" style={inputStyle} />
        <input value={password} onChange={e => setPassword(e.target.value)}
          type="password" placeholder="Password" style={inputStyle}
          onKeyDown={e => e.key === 'Enter' && handleLogin()} />
        {error && <p style={{ color: '#ef4444', fontSize: 13 }}>{error}</p>}
        <button onClick={handleLogin} style={btnStyle}>Sign in</button>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 12px', border: '1px solid #e5e7eb',
  borderRadius: 6, fontSize: 14, marginBottom: 12, boxSizing: 'border-box',
};
const btnStyle: React.CSSProperties = {
  width: '100%', padding: '10px', background: '#1e293b', color: 'white',
  border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14,
};

function Nav({ onLogout }: { onLogout: () => void }) {
  return (
    <nav style={{ padding: '1rem 2rem', borderBottom: '1px solid #e5e7eb', display: 'flex', gap: '1.5rem', alignItems: 'center', background: 'white' }}>
      <strong style={{ marginRight: '1rem', color: '#1e293b' }}>🌱 Breathe ESG</strong>
      <Link to="/" style={linkStyle}>Dashboard</Link>
      <Link to="/review" style={linkStyle}>Review Queue</Link>
      <Link to="/upload" style={linkStyle}>Upload Data</Link>
      <button onClick={onLogout} style={{ marginLeft: 'auto', padding: '6px 14px', background: '#f1f5f9', border: '1px solid #e5e7eb', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
        Sign out
      </button>
    </nav>
  );
}

const linkStyle: React.CSSProperties = { color: '#374151', textDecoration: 'none', fontSize: 14 };

export default function App() {
  const [loggedIn, setLoggedIn] = useState(!!localStorage.getItem('token'));

  const handleLogout = () => {
    localStorage.removeItem('token');
    setLoggedIn(false);
  };

  if (!loggedIn) return <Login onLogin={() => setLoggedIn(true)} />;

  return (
    <BrowserRouter>
      <div style={{ fontFamily: 'system-ui, sans-serif', background: '#f9fafb', minHeight: '100vh' }}>
        <Nav onLogout={handleLogout} />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/review" element={<ReviewTable />} />
          <Route path="/upload" element={<Upload />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}