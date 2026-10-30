// src/components/Navbar.jsx
import { useLocation, useNavigate } from 'react-router-dom';
import { Bell, MessageCircle } from 'lucide-react';
import './Navbar.css';

const PAGE_TITLES = {
  '/':          'Login',
  '/dashboard': 'Dashboard',
  '/workloads': 'Workloads',
  '/submit':    'Submit Workload',
  '/reports':   'Reports',
  '/settings':  'Settings',
};

export default function Navbar({ user }) {
  const location = useLocation();
  const navigate = useNavigate();
  const title = PAGE_TITLES[location.pathname] ?? 'Dashboard';

  return (
    <header className="navbar" role="banner">
      <div className="navbar-inner">
        {/* Left — Page title */}
        <h1 className="navbar-title">{title}</h1>

        {/* Right — Icon controls */}
        <div className="navbar-actions">
          <button className="nav-icon-btn" aria-label="Notifications" title="Notifications">
            <Bell size={17} strokeWidth={1.8} />
            <span className="nav-notif-dot" aria-hidden="true" />
          </button>

          <button className="nav-icon-btn" aria-label="Messages" title="Messages">
            <MessageCircle size={17} strokeWidth={1.8} />
          </button>

          <button
            className="nav-avatar"
            aria-label="Open user profile"
            title={user?.email || 'Profile'}
            onClick={() => navigate('/profile')}
          >
            R
          </button>
        </div>
      </div>
    </header>
  );
}
