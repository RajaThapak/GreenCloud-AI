// src/pages/SubmitWorkload.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, ChevronLeft, Check } from 'lucide-react';
import { REGIONS, INSTANCE_TYPES, GPU_OPTIONS, recommendedPlan } from '../data/fakeData';
import ReviewPlan from './ReviewPlan';
import './SubmitWorkload.css';

const STEPS = ['Submit workload', 'Review plan', 'Monitor'];

const OPT_MODES = [
  { id: 'cost',    title: 'Cost priority',   desc: 'Cheapest plan that meets the deadline' },
  { id: 'balanced',title: 'Balanced',        desc: 'Weighs cost and carbon equally' },
  { id: 'carbon',  title: 'Carbon priority', desc: 'Lowest emissions that meets the deadline' },
];

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

  const handleGenerate = (e) => {
    e.preventDefault();
    setStep(1);
  };

  if (step === 1) {
    return (
      <div className="submit-page">
        <Stepper current={1} />
        <ReviewPlan plan={recommendedPlan} onBack={() => setStep(0)} />
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

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={() => navigate('/')}>
            Cancel
          </button>
          <button type="submit" id="generate-plan-btn" className="btn btn-primary">
            Generate plan
            <ChevronRight size={15} strokeWidth={2.5} />
          </button>
        </div>
      </form>
    </main>
  );
}
