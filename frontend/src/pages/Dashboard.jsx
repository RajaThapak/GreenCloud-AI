// src/pages/Dashboard.jsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  DollarSign, Leaf, CheckCircle, Zap,
  Download, ChevronRight, ArrowUpRight, ArrowDownRight, TrendingUp
} from 'lucide-react';
import { api } from '../api';
import './Dashboard.css';

/* ─── Status helpers ─────────────────────────────────────── */
const STATUS_MAP = {
  running:   { dot: 'running',  label: 'Running',             badge: 'badge-green' },
  awaiting:  { dot: 'awaiting', label: 'Awaiting',            badge: 'badge-amber' },
  completed: { dot: 'done',     label: 'Completed',           badge: 'badge-blue' },
  recovered: { dot: 'error',    label: 'Recovered',           badge: 'badge-amber' },
};

/* ─── Carbon bar color ─── */
function carbonColor(pct) {
  if (pct <= 20) return '#54C96A';
  if (pct <= 50) return '#36B779';
  if (pct <= 70) return '#E6921A';
  return '#D9897D';
}

/* ─── Custom Chart Tooltip ─── */
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#1a1a1a',
      border: 'none',
      borderRadius: 10,
      padding: '8px 13px',
      boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
    }}>
      <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', marginBottom: 5 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ fontSize: 12.5, fontWeight: 600, color: p.color }}>
          {p.name}: <span style={{ fontFamily: 'JetBrains Mono' }}>${p.value.toLocaleString()}</span>
        </p>
      ))}
    </div>
  );
}

/* ─── Stat Card ─── */
function StatCard({ icon: Icon, label, value, change, changeLabel, direction = 'up' }) {
  return (
    <div className="stat-card fade-in">
      <div className="stat-card-top">
        <span className="stat-label">{label}</span>
        <div className="stat-icon">
          <Icon size={15} strokeWidth={1.8} />
        </div>
      </div>
      <p className="stat-value">{value}</p>
      {change && (
        <span className={`stat-change ${direction}`}>
          {direction === 'up'
            ? <ArrowUpRight size={11} />
            : <ArrowDownRight size={11} />}
          {change} {changeLabel}
        </span>
      )}
    </div>
  );
}

/* ─── Main Component ─── */
export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    api.dashboard().then(setData).catch((requestError) => setError(requestError.message));
  }, []);
  if (error) return <main className="dashboard"><div className="empty-state">{error}</div></main>;
  if (!data) return <main className="dashboard"><div className="empty-state">Loading dashboard…</div></main>;
  const costSaved = data.cost_saved;
  const costSavedPct = data.cost_saved_pct;
  const carbonAvoided = data.carbon_avoided_kg;
  const carbonAvoidedPct = data.carbon_avoided_pct;
  const deadlineCompliance = data.deadlines_met_pct ?? 0;
  const complianceOf = `${data.deadlines_met} of ${data.deadlines_total} jobs`;
  const activeWorkloads = data.active_workloads;
  const awaitingApproval = data.awaiting_approval;
  const costOverTime = data.months.map((row) => ({ month: row.label, onDemand: row.on_demand, withGC: row.actual }));
  const recentWorkloads = data.recent.map((row) => ({
    ...row, estCost: row.est_cost || 0, actCost: row.actual_cost,
  }));
  const maxCarbon = Math.max(...data.carbon_now.map((row) => row.g_per_kwh), 1);
  const carbonIntensity = data.carbon_now.map((row) => ({
    region: row.region, value: row.g_per_kwh, pct: Math.round(row.g_per_kwh / maxCarbon * 100),
  }));

  return (
    <main className="dashboard" id="dashboard-page">

      {/* ═══ 2-Column Layout ═══ */}
      <div className="dash-layout">

        {/* ──── Main column ──── */}
        <div className="dash-main">

          {/* Stat cards */}
          <div className="stats-grid">
            <StatCard
              icon={DollarSign}
              label="Cost saved this month"
              value={`$${costSaved.toLocaleString()}`}
              change={`${costSavedPct}%`}
              changeLabel="vs on-demand"
              direction="up"
            />
            <StatCard
              icon={Leaf}
              label="Carbon avoided"
              value={`${carbonAvoided} kg`}
              change={`${carbonAvoidedPct}%`}
              changeLabel="vs run-now"
              direction="up"
            />
            <StatCard
              icon={CheckCircle}
              label="Deadline compliance"
              value={`${deadlineCompliance}%`}
              change={complianceOf}
              changeLabel=""
              direction="up"
            />
            <StatCard
              icon={Zap}
              label="Active workloads"
              value={activeWorkloads}
              change={`${awaitingApproval} awaiting`}
              changeLabel="approval"
              direction="neutral"
            />
          </div>

          {/* Cost over time chart */}
          <div className="chart-card fade-in">
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <p className="chart-card-title">Cost over time</p>
                <p className="chart-card-sub">On-demand vs GreenCloud scheduling</p>
              </div>
              <button className="filter-pill">
                Last 6 months <ChevronRight size={12} />
              </button>
            </div>
            <div className="chart-legend">
              <span className="legend-item">
                <span className="legend-dot" style={{ background: '#E0E0E0' }} />
                On-demand
              </span>
              <span className="legend-item">
                <span className="legend-dot" style={{ background: '#54C96A' }} />
                With GreenCloud
              </span>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={costOverTime} barCategoryGap="30%" barGap={3}>
                <XAxis
                  dataKey="month"
                  tick={{ fill: '#A5A5A5', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis hide />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(0,0,0,0.03)' }} />
                <Bar dataKey="onDemand" name="On-demand" fill="#E0E0E0" radius={[5, 5, 0, 0]} />
                <Bar dataKey="withGC"   name="GreenCloud" fill="#54C96A" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Recent workloads table */}
          <div>
            <div className="section-header">
              <span className="section-title">Recent workloads</span>
              <button className="export-btn" aria-label="Export CSV">
                <Download size={12} />
                Export CSV
              </button>
            </div>
            <div className="table-card fade-in">
              <table className="workload-table" role="table" aria-label="Recent workloads">
                <thead>
                  <tr>
                    <th>Workload</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th>Region</th>
                    <th>Est / Actual</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {recentWorkloads.map(wl => {
                    const s = STATUS_MAP[wl.status.toLowerCase().replaceAll(' ', '_')] || STATUS_MAP.running;
                    return (
                      <tr key={wl.id}>
                        <td><span className="wl-name">{wl.name}</span></td>
                        <td>
                          <span className="badge" style={{
                            background: wl.mode === 'Cost'    ? '#EBF4FD' :
                                        wl.mode === 'Carbon'  ? '#E8F6EF' :
                                        '#F3F0FA',
                            color: wl.mode === 'Cost'    ? '#2c5f8a' :
                                   wl.mode === 'Carbon'  ? '#1a7a4a' :
                                   '#5a3d8a',
                          }}>
                            {wl.mode}
                          </span>
                        </td>
                        <td>
                          <div className="status-cell">
                            <span className={`status-dot ${s.dot}`} />
                            <span style={{ fontSize: 12.5 }}>{s.label}</span>
                          </div>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'JetBrains Mono' }}>
                          {wl.region}
                        </td>
                        <td className="cost-cell">
                          ${(wl.estCost || 0).toFixed(2)} / {wl.actCost != null ? `$${wl.actCost.toFixed(2)}` : '—'}
                        </td>
                        <td>
                          <button
                            className="icon-btn"
                            style={{ width: 28, height: 28 }}
                            aria-label={`View ${wl.name}`}
                            onClick={() => navigate('/workloads')}
                          >
                            <ChevronRight size={13} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ──── Aside column ──── */}
        <div className="dash-aside">

          {/* Carbon intensity card */}
          <div className="chart-card fade-in">
            <p className="chart-card-title">Carbon intensity</p>
            <p className="chart-card-sub" style={{ marginBottom: 16 }}>Live gCO₂/kWh by region</p>
            <div className="carbon-list">
              {carbonIntensity.map(({ region, value, pct }) => (
                <div key={region} className="carbon-row">
                  <span className="carbon-region">{region}</span>
                  <div className="carbon-bar-track">
                    <div
                      className="carbon-bar-fill"
                      style={{ width: `${pct}%`, background: carbonColor(pct) }}
                    />
                  </div>
                  <span className="carbon-value" style={{ color: carbonColor(pct) }}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
            <p className="carbon-footer">Lower = greener. Live sample data.</p>
          </div>

          {/* Quick stats aside */}
          <div className="chart-card fade-in">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <p className="chart-card-title" style={{ marginBottom: 0 }}>Workload modes</p>
              <TrendingUp size={14} color="var(--text-muted)" />
            </div>
            <p style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
              Mode breakdown is not exposed by the current dashboard API.
            </p>
          </div>

        </div>
      </div>
    </main>
  );
}
