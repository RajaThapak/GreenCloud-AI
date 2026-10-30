// src/pages/Workloads.jsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Plus, Zap } from 'lucide-react';
import { api } from '../api';
import './Workloads.css';

const STATUS_COLORS = {
  Running:   { dot: 'running',  text: 'Running',                  badge: 'badge-green' },
  'Awaiting approval': { dot: 'awaiting', text: 'Awaiting approval', badge: 'badge-amber' },
  Completed: { dot: 'done',     text: 'Completed',                 badge: 'badge-teal' },
  Recovered: { dot: 'error',    text: 'Recovered from interrupt',   badge: 'badge-amber' },
};

const MODE_COLORS = {
  Cost:    { bg: 'rgba(68,138,255,0.12)',   color: 'var(--blue)'   },
  Carbon:  { bg: 'rgba(0,230,118,0.12)',    color: 'var(--green)'  },
  Balanced:{ bg: 'rgba(206,147,216,0.12)',  color: 'var(--purple)' },
};

function progressPct(wl) {
  if (wl.status === 'Completed' || wl.status === 'Recovered') return 100;
  return 0;
}

export default function Workloads() {
  const navigate = useNavigate();
  const [search, setSearch]       = useState('');
  const [statusFilter, setStatus] = useState('all');
  const [modeFilter, setMode]     = useState('all');
  const [workloads, setWorkloads] = useState([]);
  const [error, setError] = useState('');
  useEffect(() => {
    api.workloads().then(setWorkloads).catch((requestError) => setError(requestError.message));
  }, []);

  const filtered = workloads.filter(wl => {
    const matchSearch = wl.name.toLowerCase().includes(search.toLowerCase()) ||
                        (wl.region || '').toLowerCase().includes(search.toLowerCase());
    const normalizedStatus = wl.status.toLowerCase();
    const matchStatus = statusFilter === 'all' ||
      (statusFilter === 'awaiting' && normalizedStatus === 'awaiting approval') ||
      normalizedStatus === statusFilter;
    const matchMode   = modeFilter   === 'all' || wl.mode   === modeFilter;
    return matchSearch && matchStatus && matchMode;
  });

  return (
    <main className="workloads-page" id="workloads-page">
      {error && <div className="auth-error" role="alert">{error}</div>}
      <div className="page-title-row">
        <h1 className="page-title">Workloads</h1>
        <button
          id="new-workload-page-btn"
          className="btn btn-primary"
          onClick={() => navigate('/submit')}
        >
          <Plus size={15} strokeWidth={2.5} />
          New workload
        </button>
      </div>

      {/* Filter bar */}
      <div className="filter-bar">
        <div className="search-input-wrap">
          <Search size={14} />
          <input
            id="workload-search"
            className="input"
            placeholder="Search workloads or regions…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            aria-label="Search workloads"
          />
        </div>

        <select
          id="status-filter"
          className="select filter-select"
          value={statusFilter}
          onChange={e => setStatus(e.target.value)}
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          <option value="running">Running</option>
          <option value="awaiting">Awaiting</option>
          <option value="completed">Completed</option>
          <option value="recovered">Recovered</option>
        </select>

        <select
          id="mode-filter"
          className="select filter-select"
          value={modeFilter}
          onChange={e => setMode(e.target.value)}
          aria-label="Filter by mode"
        >
          <option value="all">All modes</option>
          <option value="Cost">Cost</option>
          <option value="Balanced">Balanced</option>
          <option value="Carbon">Carbon</option>
        </select>
      </div>

      {/* Cards */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <Zap size={48} />
          <p style={{ fontSize: 16, fontWeight: 600 }}>No workloads found</p>
          <p style={{ fontSize: 13, marginTop: 6 }}>Try adjusting your filters</p>
        </div>
      ) : (
        <div className="wl-cards-grid">
          {filtered.map(wl => {
            const s    = STATUS_COLORS[wl.status] || STATUS_COLORS.Running;
            const mc   = MODE_COLORS[wl.mode] || {};
            const pct  = progressPct(wl);
            return (
              <article
                key={wl.id}
                className="wl-card glass fade-in"
                onClick={() => navigate(`/workloads/${wl.id}`)}
                role="button"
                aria-label={`View workload ${wl.name}`}
              >
                <div className="wl-card-top">
                  <div>
                    <p className="wl-card-name">{wl.name}</p>
                    <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3, fontFamily: 'monospace' }}>
                      {wl.region || '—'}
                    </p>
                  </div>
                  <div style={{ display:'flex', flexDirection:'column', alignItems:'flex-end', gap: 6 }}>
                    <span className={`badge ${s.badge}`}>
                      <span className={`status-dot ${s.dot}`} />
                      {s.text}
                    </span>
                    <span
                      className="badge"
                      style={{ background: mc.bg, color: mc.color }}
                    >{wl.mode}</span>
                  </div>
                </div>

                {/* Progress bar for running jobs */}
                {(wl.status === 'Running' || wl.status === 'Recovering') && (
                  <div>
                    <div style={{ display:'flex', justifyContent:'space-between', fontSize:11, color:'var(--text-muted)', marginBottom: 4 }}>
                      <span>Progress</span>
                      <span>{pct}%</span>
                    </div>
                    <div className="progress-track">
                      <div className="progress-fill" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )}

                {/* Metrics */}
                <div className="wl-card-metrics">
                  <div className="wl-metric">
                    <p className="wl-metric-label">Est. cost</p>
                    <p className="wl-metric-value text-green">${(wl.est_cost || 0).toFixed(2)}</p>
                  </div>
                  <div className="wl-metric">
                    <p className="wl-metric-label">Actual cost</p>
                    <p className="wl-metric-value">
                      {wl.actual_cost != null ? `$${wl.actual_cost.toFixed(2)}` : '—'}
                    </p>
                  </div>
                  <div className="wl-metric">
                    <p className="wl-metric-label">GPU</p>
                    <p className="wl-metric-value" style={{ fontSize: 12 }}>{wl.instance_type || '—'}</p>
                  </div>
                  <div className="wl-metric">
                    <p className="wl-metric-label">Duration</p>
                    <p className="wl-metric-value">{wl.deadline ? new Date(wl.deadline).toLocaleDateString() : '—'}</p>
                  </div>
                </div>

                <div className="wl-card-footer">
                  <span>Deadline: {new Date(wl.deadline).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' })}</span>
                  <span style={{ color: 'var(--green)', fontWeight: 600 }}>View →</span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </main>
  );
}
