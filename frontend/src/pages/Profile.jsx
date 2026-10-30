import { useState } from 'react';
import { ArrowLeft, Camera, Check, KeyRound, Mail, Shield, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import './Profile.css';

export default function Profile() {
  const navigate = useNavigate();
  const [name, setName] = useState('Raja Thapak');
  const [email, setEmail] = useState('raja.thapak@example.com');
  const [saved, setSaved] = useState(false);

  function handleSave(event) {
    event.preventDefault();
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2500);
  }

  return (
    <main className="profile-page" id="profile-page">
      <div className="profile-header">
        <div>
          <button className="profile-back" type="button" onClick={() => navigate(-1)}>
            <ArrowLeft size={15} />
            Back
          </button>
          <p className="eyebrow">Account</p>
          <h1 className="page-title">Your profile</h1>
          <p className="profile-subtitle">Manage your GreenCloud AI account details.</p>
        </div>
      </div>

      <div className="profile-layout">
        <section className="profile-card profile-identity glass">
          <div className="profile-avatar-wrap">
            <div className="profile-avatar" aria-label="Profile avatar">R</div>
            <button className="profile-camera" type="button" aria-label="Change profile photo" title="Change profile photo">
              <Camera size={14} />
            </button>
          </div>
          <h2>{name}</h2>
          <p>{email}</p>
          <span className="profile-role">Administrator</span>
          <div className="profile-status">
            <span className="status-dot" />
            Active account
          </div>
        </section>

        <form className="profile-card profile-details glass" onSubmit={handleSave}>
          <div className="profile-section-heading">
            <div className="profile-section-icon"><UserRound size={16} /></div>
            <div>
              <h2>Personal information</h2>
              <p>Update the details associated with your account.</p>
            </div>
          </div>

          <div className="profile-form-grid">
            <div className="form-group">
              <label className="form-label" htmlFor="profile-name">Full name</label>
              <input id="profile-name" className="input" value={name} onChange={(event) => setName(event.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="profile-email">Email address</label>
              <div className="profile-input-icon">
                <Mail size={15} />
                <input id="profile-email" className="input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
              </div>
            </div>
          </div>

          <div className="profile-meta">
            <div><span>Role</span><strong>Administrator</strong></div>
            <div><span>Member since</span><strong>October 2026</strong></div>
          </div>

          <div className="profile-actions">
            {saved && <span className="profile-saved"><Check size={14} /> Changes saved</span>}
            <button className="btn btn-primary" type="submit">Save changes</button>
          </div>
        </form>

        <section className="profile-card profile-security glass">
          <div className="profile-section-heading">
            <div className="profile-section-icon"><Shield size={16} /></div>
            <div>
              <h2>Security</h2>
              <p>Keep your account protected.</p>
            </div>
          </div>
          <button className="profile-security-row" type="button">
            <span className="profile-security-leading"><KeyRound size={16} /><span><strong>Password</strong><small>Last changed recently</small></span></span>
            <span className="profile-link">Change</span>
          </button>
        </section>
      </div>
    </main>
  );
}
