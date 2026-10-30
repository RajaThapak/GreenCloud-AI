// src/App.jsx
import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar        from './components/Sidebar';
import Navbar         from './components/Navbar';
import Dashboard      from './pages/Dashboard';
import Workloads      from './pages/Workloads';
import SubmitWorkload from './pages/SubmitWorkload';
import Reports        from './pages/Reports';
import Settings       from './pages/Settings';
import Profile        from './pages/Profile';
import Auth           from './pages/Auth';
import { api, clearSession, getStoredUser, getToken } from './api';
import './App.css';

export default function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [user, setUser] = useState(getStoredUser);

  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener('greencloud:unauthorized', onUnauthorized);
    if (getToken() && !user) api.me().then(setUser).catch(() => clearSession());
    return () => window.removeEventListener('greencloud:unauthorized', onUnauthorized);
  }, [user]);

  const protectedLayout = (
    <ProtectedLayout user={user} onLogout={() => { clearSession(); setUser(null); }}>
      <div className="app-shell" data-sidebar-collapsed={collapsed}>
        <Sidebar collapsed={collapsed} onCollapse={setCollapsed} user={user} onLogout={() => { clearSession(); setUser(null); }} />
        <div className="app-content" id="main-content">
          <Navbar user={user} />
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/workloads" element={<Workloads />} />
            <Route path="/submit" element={<SubmitWorkload />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/profile" element={<Profile user={user} />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </div>
      </div>
    </ProtectedLayout>
  );

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <Auth mode="login" onAuthenticated={setUser} />} />
        <Route path="/signup" element={user ? <Navigate to="/dashboard" replace /> : <Auth mode="signup" onAuthenticated={setUser} />} />
        <Route path="/" element={<Navigate to={user ? '/dashboard' : '/login'} replace />} />
        <Route path="*" element={protectedLayout} />
      </Routes>
    </BrowserRouter>
  );
}

function ProtectedLayout({ user, children }) {
  return user ? children : <Navigate to="/login" replace />;
}
