// src/pages/ReviewPlan.jsx
import { ArrowLeft, CheckCircle2, AlertTriangle } from 'lucide-react';
import './ReviewPlan.css';

export default function ReviewPlan({ plan, onBack, onApprove }) {
  const costSavePct = Math.round(
    ((plan.onDemandCost - plan.estCost) / plan.onDemandCost) * 100
  );
  const carbonSavePct = Math.round(
    ((plan.runNowCarbon - plan.estCarbon) / plan.runNowCarbon) * 100
  );

  return (
    <div className="review-card glass fade-in" id="review-plan-page">
      {/* Header */}
      <div className="review-header">
        <div>
          <p className="review-subtitle">Recommended plan · Cost mode</p>
          <h1 className="review-title" style={{ fontSize: 20 }}>
            Schedule Review
          </h1>
        </div>
        <div className="meets-deadline">
          Meets deadline with {plan.sparehours} h to spare
        </div>
      </div>

      {/* 4-col metrics */}
      <div className="plan-metrics">
        <div className="plan-metric">
          <p className="metric-label">Region</p>
          <p className="metric-value mono">{plan.region}</p>
        </div>
        <div className="plan-metric">
          <p className="metric-label">Instance</p>
          <p className="metric-value mono" style={{ fontSize: 14 }}>{plan.instance}</p>
        </div>
        <div className="plan-metric">
          <p className="metric-label">Start time</p>
          <p className="metric-value">{plan.startTime}</p>
        </div>
        <div className="plan-metric">
          <p className="metric-label">Interruption risk</p>
          <p className="metric-value" style={{ color: 'var(--green)' }}>{plan.interruptionRisk}</p>
        </div>
      </div>

      {/* Comparison cards */}
      <div className="comparison-row">
        <div className="cmp-card">
          <p className="cmp-label">Est. cost</p>
          <p className="cmp-main" style={{ color: 'var(--green)' }}>
            ${plan.estCost.toFixed(2)}
          </p>
          <p className="cmp-sub">vs ${plan.onDemandCost.toFixed(2)} on-demand now</p>
        </div>
        <div className="cmp-card">
          <p className="cmp-label">Est. carbon</p>
          <p className="cmp-main" style={{ color: 'var(--teal)' }}>
            {plan.estCarbon} kg
          </p>
          <p className="cmp-sub">vs {plan.runNowCarbon} kg run-now</p>
        </div>
        <div className="cmp-card">
          <p className="cmp-label">Finish by</p>
          <p className="cmp-main" style={{ fontSize: 22 }}>{plan.finishBy}</p>
          <p className="cmp-sub">deadline {plan.deadline}</p>
        </div>
      </div>

      {/* Savings badges */}
      <div style={{ display:'flex', gap:10, marginBottom: 20, flexWrap:'wrap' }}>
        <span className="badge badge-green">
          <CheckCircle2 size={11} />
          {costSavePct}% cost saving vs on-demand
        </span>
        <span className="badge badge-teal">
          <CheckCircle2 size={11} />
          {carbonSavePct}% carbon reduction vs run-now
        </span>
        <span className="badge badge-amber">
          <AlertTriangle size={11} />
          Low interruption risk
        </span>
      </div>

      {/* Why this plan */}
      <div className="why-section">
        <h3>Why this plan</h3>
        <ul className="why-list">
          {plan.reasons.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      </div>

      {/* Other options */}
      <div className="alt-section">
        <h3>Other options</h3>
        {plan.alternatives.map((alt, i) => (
          <div key={i} className="alt-row" role="button" tabIndex={0}>
            <span className="alt-label">{alt.label}</span>
            <span className="alt-cost">${alt.cost.toFixed(2)} · {alt.carbon} kg</span>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="review-actions">
        <button id="edit-workload-btn" className="btn btn-ghost" onClick={onBack}>
          <ArrowLeft size={15} />
          Edit workload
        </button>
        <button
          id="approve-schedule-btn"
          className="btn btn-primary"
          onClick={onApprove}
        >
          <CheckCircle2 size={15} />
          Approve and schedule
        </button>
      </div>
    </div>
  );
}
