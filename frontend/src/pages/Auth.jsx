import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  ArrowRight, CheckCircle2, Eye, EyeOff, Leaf, LockKeyhole, Mail, UserRound
} from 'lucide-react';
import './Auth.css';

const BENEFITS = [
  'Schedule workloads when cloud costs are lowest',
  'Reduce emissions with carbon-aware regions',
  'Keep every run on track with deadline-aware plans',
];

function Field({ id, label, type = 'text', value, onChange, placeholder, icon: Icon, autoComplete }) {
  return (
    <div className="auth-field">
      <label htmlFor={id} className="form-label">{label}</label>
      <div className="auth-input-wrap">
        <Icon size={16} aria-hidden="true" />
        <input
          id={id}
          className="input auth-input"
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required
        />
      </div>
    </div>
  );
}

function PasswordField({ id, label, value, onChange, visible, onToggle, autoComplete }) {
  return (
    <div className="auth-field">
      <label htmlFor={id} className="form-label">{label}</label>
      <div className="auth-input-wrap">
        <LockKeyhole size={16} aria-hidden="true" />
        <input
          id={id}
          className="input auth-input auth-input-with-action"
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder="••••••••"
          autoComplete={autoComplete}
          minLength={8}
          required
        />
        <button
          type="button"
          className="auth-password-toggle"
          onClick={onToggle}
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    </div>
  );
}

export default function Auth({ mode = 'login' }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isSignup = mode === 'signup';
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    remember: true,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');

  const set = (field) => (event) => {
    setError('');
    setForm((previous) => ({ ...previous, [field]: event.target.value }));
  };

  function handleSubmit(event) {
    event.preventDefault();
    if (isSignup && form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    navigate('/dashboard', { replace: true });
  }

  const alternatePath = isSignup ? '/login' : '/signup';

  return (
    <main className="auth-page">
      <div className="auth-layout">
        <section className="auth-brand-panel" aria-label="GreenCloud AI">
          <div className="auth-brand">
            <div className="logo-icon" aria-hidden="true">
              <Leaf size={18} strokeWidth={2.5} />
            </div>
            <span className="logo-text">GreenCloud <span>AI</span></span>
          </div>

          <div className="auth-brand-copy">
            <p className="auth-eyebrow">INTELLIGENT GREEN CLOUD SCHEDULER</p>
            <h1>Run smarter.<br /><span>Leave a lighter footprint.</span></h1>
            <p className="auth-brand-description">
              GreenCloud AI finds the best time and place to run your workloads,
              balancing cost, carbon, and deadlines automatically.
            </p>
            <ul className="auth-benefits">
              {BENEFITS.map((benefit) => (
                <li key={benefit}>
                  <CheckCircle2 size={16} aria-hidden="true" />
                  {benefit}
                </li>
              ))}
            </ul>
          </div>

          <p className="auth-footer-copy">Built for teams that care about every compute cycle.</p>
        </section>

        <section className="auth-form-panel">
          <div className="auth-form-container">
            <div className="auth-mobile-brand">
              <div className="logo-icon" aria-hidden="true">
                <Leaf size={18} strokeWidth={2.5} />
              </div>
              <span className="logo-text">GreenCloud <span>AI</span></span>
            </div>

            <div className="auth-heading">
              <h2>{isSignup ? 'Create your account' : 'Welcome back'}</h2>
              <p>
                {isSignup
                  ? 'Start scheduling cloud workloads more sustainably.'
                  : 'Sign in to continue to your GreenCloud workspace.'}
              </p>
            </div>

            <form className="auth-form" onSubmit={handleSubmit} noValidate>
              {isSignup && (
                <Field
                  id="auth-name"
                  label="Full name"
                  value={form.name}
                  onChange={set('name')}
                  placeholder="Raja Thapak"
                  icon={UserRound}
                  autoComplete="name"
                />
              )}
              <Field
                id="auth-email"
                label="Work email"
                type="email"
                value={form.email}
                onChange={set('email')}
                placeholder="you@company.com"
                icon={Mail}
                autoComplete="email"
              />
              <PasswordField
                id="auth-password"
                label="Password"
                value={form.password}
                onChange={set('password')}
                visible={showPassword}
                onToggle={() => setShowPassword((visible) => !visible)}
                autoComplete={isSignup ? 'new-password' : 'current-password'}
              />

              {isSignup && (
                <PasswordField
                  id="auth-confirm-password"
                  label="Confirm password"
                  value={form.confirmPassword}
                  onChange={set('confirmPassword')}
                  visible={showConfirmPassword}
                  onToggle={() => setShowConfirmPassword((visible) => !visible)}
                  autoComplete="new-password"
                />
              )}

              {isSignup ? (
                <label className="auth-check-row">
                  <input type="checkbox" checked={form.remember} onChange={(event) => setForm((previous) => ({ ...previous, remember: event.target.checked }))} />
                  <span>I agree to the GreenCloud AI terms and privacy policy.</span>
                </label>
              ) : (
                <div className="auth-options">
                  <label className="auth-check-row">
                    <input type="checkbox" checked={form.remember} onChange={(event) => setForm((previous) => ({ ...previous, remember: event.target.checked }))} />
                    <span>Remember me</span>
                  </label>
                  <button type="button" className="auth-text-button">Forgot password?</button>
                </div>
              )}

              {error && <p className="auth-error" role="alert">{error}</p>}

              <button type="submit" className="btn btn-primary auth-submit">
                {isSignup ? 'Create account' : 'Sign in'}
                <ArrowRight size={16} strokeWidth={2.5} />
              </button>
            </form>

            <p className="auth-switch">
              {isSignup ? 'Already have an account?' : 'New to GreenCloud AI?'}{' '}
              <Link to={alternatePath} state={{ from: location.pathname }}>
                {isSignup ? 'Sign in' : 'Create an account'}
              </Link>
            </p>

            <p className="auth-demo-note">Frontend demo mode · Connect authentication to continue</p>
          </div>
        </section>
      </div>
    </main>
  );
}
