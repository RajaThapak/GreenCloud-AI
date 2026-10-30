// src/pages/SubmitWorkload.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Check } from 'lucide-react';
import { REGIONS, GPU_OPTIONS } from '../data/fakeData';
import ReviewPlan from './ReviewPlan';
import './SubmitWorkload.css';

const STEPS = ['Submit workload', 'Review plan', 'Monitor'];

const OPT_MODES = [
  { id: 'cost',    title: 'Cost priority',   desc: 'Cheapest plan that meets the deadline' },
  { id: 'balanced',title: 'Balanced',        desc: 'Weighs cost and carbon equally' },
  { id: 'carbon',  title: 'Carbon priority', desc: 'Lowest emissions that meets the deadline' },
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function toReviewPlan(response) {
  const best = response.best;
  return {
    region: best.region,
    instance: `${best.instance} ${best.purchase}`,
    startTime: best.start,
    interruptionRisk: best.risk_label,
    estCost: best.cost,
    onDemandCost: response.on_demand_cost ?? best.cost,
    estCarbon: best.carbon_kg,
    runNowCarbon: response.run_now_carbon_kg ?? best.carbon_kg,
    finishBy: best.finish,
    deadline: response.inputs?.spec?.deadline ?? '',
    sparehours: response.inputs?.spec?.deadline
      ? Math.max(0, Math.round(
          (new Date(response.inputs.spec.deadline).getTime() - new Date(best.finish).getTime()) / 3600000
        ))
      : 0,
    reasons: response.reasons,
    alternatives: response.alternatives.map((alternative) => ({
      label: `${alternative.region} · ${alternative.start}`,
      cost: alternative.cost,
      carbon: alternative.carbon_kg,
    })),
  };
}

function Stepper({ current }) {
  return (
    <div className="stepper" role="list" aria-label="Progress steps">
      {STEPS.map((label, i) => (
        <div key={i} style={{ display:'flex', alignItems:'center', flex: i < STEPS.length - 1 ? 1 : 'initial' }}>
          <div
            className={`step-item ${i === current ? 'active' : i < current ? 'done' : ''}`}
            role="listitem"
            aria-current={i === current ? 'step' : undefined}
          >
            <div className="step-num">
              {i < current ? <Check size={12} strokeWidth={3} /> : i + 1}
            </div>
            <span className="step-label">{label}</span>
          </div>
          {i < STEPS.length - 1 && <div className="step-connector" aria-hidden="true" />}
        </div>
      ))}
    </div>
  );
}

export default function SubmitWorkload() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [selectedRegions, setSelectedRegions] = useState([...REGIONS]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState('');
  const [plan, setPlan] = useState(null);

  const [form, setForm] = useState({
    name: 'BERT fine-tune',
    image: 'ghcr.io/team/bert-train:1.4',
    vcpu: '8',
    memory: '32',
    gpu: '1x A10G',
    duration: '6',
    deadline: '2026-10-20T18:00',
    priority: 'Normal',
    optMode: 'cost',
  });

  const set = (field) => (e) =>
    setForm(prev => ({ ...prev, [field]: e.target.value }));

  const toggleRegion = (region) => (e) => {
    setSelectedRegions((previous) => (
      e.target.checked
        ? [...previous, region]
        : previous.filter((selected) => selected !== region)
    ));
    setError('');
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (selectedRegions.length === 0) {
      setError('Select at least one AWS region before generating a plan.');
      return;
    }

    setIsGenerating(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/workloads/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          image: form.image,
          vcpu: Number(form.vcpu),
          memory: Number(form.memory),
          gpu: form.gpu,
          duration: Number(form.duration),
          deadline: form.deadline,
          priority: form.priority,
          optMode: form.optMode,
          selected_regions: selectedRegions,
        }),
      });

      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = Array.isArray(body.detail)
          ? body.detail.map((item) => item.msg).join(' ')
          : body.detail;
        throw new Error(detail || 'Unable to generate a scheduling plan.');
      }

      setPlan(toReviewPlan(body));
      setStep(1);
    } catch (requestError) {
      setError(requestError.message || 'Unable to generate a scheduling plan.');
    } finally {
      setIsGenerating(false);
    }
  };

  if (step === 1) {
    return (
      <div className="submit-page">
        <Stepper current={1} />
        <ReviewPlan plan={plan} onBack={() => setStep(0)} />
      </div>
    );
  }

  if (step === 2) {
    navigate('/workloads');
    return null;
  }

  return (
    <main className="submit-page" id="submit-workload-page">
      <Stepper current={0} />

      <form className="form-card glass fade-in" onSubmit={handleGenerate} noValidate>
        <h1>Submit workload</h1>

        {/* Row 1 */}
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="wl-name" className="form-label">Workload name</label>
            <input id="wl-name" className="input" value={form.name} onChange={set('name')} required />
          </div>
          <div className="form-group">
            <label htmlFor="wl-image" className="form-label">Docker image</label>
            <input id="wl-image" className="input" value={form.image} onChange={set('image')} required />
          </div>
        </div>

        {/* Row 2 */}
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="wl-vcpu" className="form-label">vCPU</label>
            <input id="wl-vcpu" className="input" type="number" min="1" value={form.vcpu} onChange={set('vcpu')} />
          </div>
          <div className="form-group">
            <label htmlFor="wl-memory" className="form-label">Memory (GB)</label>
            <input id="wl-memory" className="input" type="number" min="1" value={form.memory} onChange={set('memory')} />
          </div>
          <div className="form-group">
            <label htmlFor="wl-gpu" className="form-label">GPU</label>
            <select id="wl-gpu" className="select" value={form.gpu} onChange={set('gpu')}>
              {GPU_OPTIONS.map(g => <option key={g}>{g}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="wl-duration" className="form-label">Duration (hours)</label>
            <input id="wl-duration" className="input" type="number" min="1" value={form.duration} onChange={set('duration')} />
          </div>
        </div>

        {/* Row 3 */}
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="wl-deadline" className="form-label">Hard deadline</label>
            <input
              id="wl-deadline" className="input" type="datetime-local"
              value={form.deadline} onChange={set('deadline')}
            />
          </div>
          <div className="form-group">
            <label htmlFor="wl-priority" className="form-label">Priority</label>
            <select id="wl-priority" className="select" value={form.priority} onChange={set('priority')}>
              {['Low', 'Normal', 'High', 'Critical'].map(p => <option key={p}>{p}</option>)}
            </select>
          </div>
        </div>

        {/* Optimization mode */}
        <div style={{ marginBottom: 8 }}>
          <label className="form-label">Optimization mode</label>
          <div className="opt-modes">
            {OPT_MODES.map(({ id, title, desc }) => (
              <div
                key={id}
                id={`opt-${id}`}
                className={`opt-card ${form.optMode === id ? 'selected' : ''}`}
                onClick={() => setForm(prev => ({ ...prev, optMode: id }))}
                role="radio"
                aria-checked={form.optMode === id}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setForm(prev => ({ ...prev, optMode: id }))}
              >
                <h3>{title}</h3>
                <p>{desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="region-selection">
          <div className="region-selection-header">
            <label className="form-label">AWS regions</label>
            <span className="region-selection-count">
              {selectedRegions.length} of {REGIONS.length} selected
            </span>
          </div>
          <p className="region-selection-help">
            Choose where GreenCloud AI may schedule this workload.
          </p>
          <div className="region-checkboxes">
            {REGIONS.map((region) => (
              <label key={region} className="region-checkbox">
                <input
                  type="checkbox"
                  checked={selectedRegions.includes(region)}
                  onChange={toggleRegion(region)}
                />
                <span>{region}</span>
              </label>
            ))}
          </div>
        </div>

        {error && <p className="submit-error" role="alert">{error}</p>}

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={() => navigate('/')}>
            Cancel
          </button>
          <button type="submit" id="generate-plan-btn" className="btn btn-primary" disabled={isGenerating}>
            {isGenerating ? 'Generating plan…' : 'Generate plan'}
            {!isGenerating && <ChevronRight size={15} strokeWidth={2.5} />}
          </button>
        </div>
      </form>
    </main>
  );
}
