// src/pages/Reports.jsx
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts';
import { useEffect, useState } from 'react';
import { TrendingDown, Leaf, Award } from 'lucide-react';
import { api } from '../api';
import './Reports.css';

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'rgba(255,255,255,0.97)',
      border: '1px solid rgba(0,0,0,0.10)',
      borderRadius: 10,
      padding: '10px 14px',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 4px 16px rgba(0,0,0,0.10)',
    }}>
      <p style={{ fontSize: 11, color: '#4a5568', marginBottom: 6 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ fontSize: 12, fontWeight: 600, color: p.color, marginBottom: 2 }}>
          {p.name}: <span style={{ fontFamily: 'monospace' }}>{p.value}</span>
        </p>
      ))}
    </div>
  );
}

const COLORS = ['#00a651', '#1565c0', '#e65100', '#6a1b9a', '#0097a7'];

export default function Reports() {
  const [report, setReport] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    Promise.all([api.reports(6), api.dashboard()])
      .then(([reportData, dashboardData]) => { setReport(reportData); setDashboard(dashboardData); })
      .catch((requestError) => setError(requestError.message));
  }, []);
  if (error) return <main className="reports-page"><div className="empty-state">{error}</div></main>;
  if (!report || !dashboard) return <main className="reports-page"><div className="empty-state">Loading reports…</div></main>;
  const totalSaved = report.saved;
  const avgSavePct = report.saved_pct ?? 0;
  const costOverTime = report.rows.map((row) => ({
    month: row.label, onDemand: row.on_demand, withGC: row.actual,
  }));
  const carbonTrend = [{
    time: 'Current',
    ...Object.fromEntries(dashboard.carbon_now.map((row) => [row.region, row.g_per_kwh])),
  }];
  const spotPriceHistory = [];

  return (
    <main className="reports-page" id="reports-page">
      <h1 className="page-title">Reports & Analytics</h1>

      {/* Summary row */}
      <div className="report-summary-grid">
        <div className="report-summary-card glass fade-in">
          <div style={{ display:'flex', gap:12, alignItems:'center' }}>
            <div className="report-icon" style={{ background: 'rgba(0,230,118,0.15)' }}>
              <TrendingDown size={18} color="var(--green)" />
            </div>
            <div>
              <p style={{ fontSize:11, color:'var(--text-muted)', textTransform:'uppercase', letterSpacing:'0.07em', fontWeight:600 }}>
                6-month savings
              </p>
              <p style={{ fontSize:26, fontWeight:800, letterSpacing:'-0.02em' }}>
                ${totalSaved.toLocaleString()}
              </p>
              <p style={{ fontSize:12, color:'var(--green)', marginTop:2 }}>~{avgSavePct}% avg vs on-demand</p>
            </div>
          </div>
        </div>

        <div className="report-summary-card glass fade-in">
          <div style={{ display:'flex', gap:12, alignItems:'center' }}>
            <div className="report-icon" style={{ background: 'rgba(0,188,212,0.15)' }}>
              <Leaf size={18} color="var(--teal)" />
            </div>
            <div>
              <p style={{ fontSize:11, color:'var(--text-muted)', textTransform:'uppercase', letterSpacing:'0.07em', fontWeight:600 }}>
                Carbon avoided (6 mo)
              </p>
              <p style={{ fontSize:26, fontWeight:800, letterSpacing:'-0.02em' }}>{dashboard.carbon_avoided_kg} kg</p>
              <p style={{ fontSize:12, color:'var(--teal)', marginTop:2 }}>CO₂ equivalent</p>
            </div>
          </div>
        </div>

        <div className="report-summary-card glass fade-in">
          <div style={{ display:'flex', gap:12, alignItems:'center' }}>
            <div className="report-icon" style={{ background: 'rgba(255,171,64,0.15)' }}>
              <Award size={18} color="var(--amber)" />
            </div>
            <div>
              <p style={{ fontSize:11, color:'var(--text-muted)', textTransform:'uppercase', letterSpacing:'0.07em', fontWeight:600 }}>
                Jobs scheduled optimally
              </p>
              <p style={{ fontSize:26, fontWeight:800, letterSpacing:'-0.02em' }}>{dashboard.deadlines_met}</p>
              <p style={{ fontSize:12, color:'var(--amber)', marginTop:2 }}>{dashboard.deadlines_met_pct ?? 0}% deadline compliance</p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="reports-charts-grid">
        {/* Cost area chart */}
        <div className="chart-card glass fade-in">
          <h2 className="chart-title">Cost savings over time</h2>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={costOverTime}>
              <defs>
                <linearGradient id="gcGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#448aff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#448aff" stopOpacity={0.02} />
                </linearGradient>
                <linearGradient id="odGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#4a5568" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#4a5568" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="month" tick={{ fill:'#8b98a9', fontSize:12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#8b98a9', fontSize:11 }} axisLine={false} tickLine={false}
                     tickFormatter={v => `$${v}`} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="onDemand" name="On-demand" stroke="#4a5568"
                    strokeWidth={2} fill="url(#odGrad)" />
              <Area type="monotone" dataKey="withGC" name="With GreenCloud" stroke="#448aff"
                    strokeWidth={2} fill="url(#gcGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Carbon trend */}
        <div className="chart-card glass fade-in">
          <h2 className="chart-title">Carbon intensity trend (gCO₂/kWh)</h2>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={carbonTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fill:'#8b98a9', fontSize:12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#8b98a9', fontSize:11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} />
              {dashboard.carbon_now.slice(0, 3).map((row, i) => (
                <Line key={row.region} type="monotone" dataKey={row.region} stroke={COLORS[i]} strokeWidth={2} dot />
              ))}
            </LineChart>
          </ResponsiveContainer>
          <div style={{ display:'flex', gap:16, flexWrap:'wrap', marginTop:12 }}>
            {[['eu-north-1','#00e676'],['ca-central-1','#00bcd4'],['eu-west-1','#ffab40']].map(([r,c]) => (
              <span key={r} style={{ fontSize:11, color:'var(--text-secondary)', display:'flex', alignItems:'center', gap:5 }}>
                <span style={{ width:16, height:2, borderRadius:1, background:c, display:'inline-block' }}/>
                {r}
              </span>
            ))}
          </div>
        </div>

        {/* Spot price history */}
        <div className="chart-card glass fade-in">
          <h2 className="chart-title">Spot price history — g5.xlarge ($/hr)</h2>
          <div className="empty-state" style={{ minHeight: 240 }}>Spot price history is not exposed by the current backend API.</div>
          {spotPriceHistory.length > 0 && <ResponsiveContainer width="100%" height={240}>
            <LineChart data={spotPriceHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fill:'#8b98a9', fontSize:12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#8b98a9', fontSize:11 }} axisLine={false} tickLine={false}
                     tickFormatter={v => `$${v}`} />
              <Tooltip content={<ChartTooltip />} />
              {['eu-north-1','us-east-1','ca-central-1'].map((k, i) => (
                <Line key={k} type="monotone" dataKey={k} stroke={COLORS[i]}
                      strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>}
          <div style={{ display:'flex', gap:16, flexWrap:'wrap', marginTop:12 }}>
            {['eu-north-1','us-east-1','ca-central-1'].map((r, i) => (
              <span key={r} style={{ fontSize:11, color:'var(--text-secondary)', display:'flex', alignItems:'center', gap:5 }}>
                <span style={{ width:16, height:2, borderRadius:1, background:COLORS[i], display:'inline-block' }}/>
                {r}
              </span>
            ))}
          </div>
        </div>

        {/* Mode breakdown */}
        <div className="chart-card glass fade-in mode-breakdown">
          <h2 className="chart-title">Optimization mode usage</h2>
          <div className="mode-bars">
            {[
              { label:'Cost priority',   pct:52, color:'var(--blue)',   count:75 },
              { label:'Balanced',        pct:31, color:'var(--purple)', count:45 },
              { label:'Carbon priority', pct:17, color:'var(--green)',  count:24 },
            ].map(({ label, pct, color, count }) => (
              <div key={label} className="mode-bar-row">
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
                  <span style={{ fontSize:13, fontWeight:500, color:'var(--text-secondary)' }}>{label}</span>
                  <span style={{ fontSize:12, fontWeight:700, fontFamily:'monospace', color }}>
                    {pct}% <span style={{ color:'var(--text-muted)', fontWeight:400 }}>({count} jobs)</span>
                  </span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width:`${pct}%`, background: color }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
