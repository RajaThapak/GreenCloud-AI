// src/components/Sidebar.jsx
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Zap, BarChart3, Settings,
  Plus, Leaf, Bell,
  LogOut, HelpCircle
} from 'lucide-react';
import './Sidebar.css';

const NAV_ITEMS = [
  { to: '/',          label: 'Dashboard', icon: LayoutDashboard },
  { to: '/workloads', label: 'Workloads', icon: Zap },
  { to: '/reports',   label: 'Reports',   icon: BarChart3 },
  { to: '/settings',  label: 'Settings',  icon: Settings },
];

export default function Sidebar({ collapsed, onCollapse }) {
  const navigate = useNavigate();

  return (
    <aside
      className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''}`}
      aria-label="Main navigation"
    >
      {/* ─── Logo ─── */}
      <div className="sidebar-logo">
        <button
          className="sidebar-brand"
          onClick={() => onCollapse(v => !v)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <div className="logo-icon" aria-hidden="true">
            <Leaf size={18} strokeWidth={2.5} />
          </div>
          {!collapsed && (
            <span className="logo-text">
              GreenCloud <span>AI</span>
            </span>
          )}
        </button>
      </div>

      {/* ─── New Workload CTA ─── */}
      <div className="sidebar-cta">
        <button
          id="sidebar-new-workload-btn"
          className={`btn sidebar-cta-btn ${collapsed ? 'cta-icon-only' : ''}`}
          onClick={() => navigate('/submit')}
          aria-label="Create new workload"
          title="New workload"
        >
          <Plus size={16} strokeWidth={2.5} />
          {!collapsed && <span>New Workload</span>}
        </button>
      </div>

      {/* ─── Nav Links ─── */}
      <nav className="sidebar-nav" role="navigation">
        {!collapsed && (
          <p className="nav-group-label">Navigation</p>
        )}
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'sidebar-link--active' : ''}`
            }
            title={collapsed ? label : undefined}
            aria-label={label}
          >
            <span className="sidebar-link-icon">
              <Icon size={18} strokeWidth={2} />
            </span>
            {!collapsed && <span className="sidebar-link-label">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* ─── Spacer ─── */}
      <div className="sidebar-spacer" />

      {/* ─── Bottom section ─── */}
      <div className="sidebar-bottom">
        {/* Notification bell */}
        <button
          className="sidebar-link sidebar-link-btn"
          aria-label="Notifications"
          title="Notifications"
        >
          <span className="sidebar-link-icon" style={{ position: 'relative' }}>
            <Bell size={18} strokeWidth={2} />
            <span className="notif-dot" aria-hidden="true" />
          </span>
          {!collapsed && <span className="sidebar-link-label">Notifications</span>}
          {!collapsed && <span className="notif-pill">2</span>}
        </button>

        {/* Help */}
        <button
          className="sidebar-link sidebar-link-btn"
          aria-label="Help"
          title="Help"
        >
          <span className="sidebar-link-icon">
            <HelpCircle size={18} strokeWidth={2} />
          </span>
          {!collapsed && <span className="sidebar-link-label">Help & Support</span>}
        </button>

        {/* Divider */}
        <div className="sidebar-divider" />

        {/* User avatar */}
        <div className="sidebar-user" title="User profile">
          <div className="user-avatar">R</div>
          {!collapsed && (
            <div className="user-info">
              <p className="user-name">Raja Thapak</p>
              <p className="user-role">Administrator</p>
            </div>
          )}
          {!collapsed && (
            <button className="icon-btn logout-btn" aria-label="Sign out" title="Sign out">
              <LogOut size={14} />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
