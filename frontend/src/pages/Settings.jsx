// src/pages/Settings.jsx
import { useState } from 'react';
import { Save, Key, Globe, Bell, Shield } from 'lucide-react';
import './Settings.css';

const REGIONS_LIST = [
  "us-east-1", "us-east-2", "eu-north-1",
  "eu-west-1", "ca-central-1", "ap-south-1",
];

function Toggle({ id, checked, onChange, label }) {
  return (
    <label htmlFor={id} className="toggle-wrap" aria-label={label}>
      <input id={id} type="checkbox" className="toggle-input" checked={checked} onChange={onChange} />
      <span className="toggle-track">
        <span className="toggle-thumb" />
      </span>
    </label>
  );
}

function SettingsSection({ icon: Icon, title, children }) {
  return (
    <section className="settings-section glass fade-in" aria-labelledby={`section-${title.replace(/\s+/g,'-').toLowerCase()}`}>
      <div className="settings-section-head">
        <div className="settings-icon">
          <Icon size={16} strokeWidth={2} />
        </div>
        <h2 id={`section-${title.replace(/\s+/g,'-').toLowerCase()}`} className="settings-section-title">
          {title}
        </h2>
      </div>
      <div className="settings-body">{children}</div>
    </section>
  );
}

export default function Settings() {
  const [awsKey, setAwsKey]       = useState('AKIA••••••••••••••••');
  const [awsSecret, setAwsSecret] = useState('••••••••••••••••••••••••••••••••');
  const [emToken, setEmToken]     = useState('em_live_••••••••••••••••');

  const [enabledRegions, setEnabledRegions] = useState(
    new Set(['eu-north-1', 'us-east-1', 'ca-central-1'])
  );
  const [defaultMode, setDefaultMode]       = useState('cost');
  const [notifyEmail, setNotifyEmail]       = useState(true);
  const [notifySlack, setNotifySlack]       = useState(false);
  const [slackWebhook, setSlackWebhook]     = useState('');
  const [maxRetries, setMaxRetries]         = useState('2');
  const [spotBuffer, setSpotBuffer]         = useState('1');

  function toggleRegion(r) {
    setEnabledRegions(prev => {
      const next = new Set(prev);
      next.has(r) ? next.delete(r) : next.add(r);
      return next;
    });
  }

  function handleSave(e) {
    e.preventDefault();
    // Would POST to /api/settings in real implementation
    alert('Settings saved (fake — no backend connected yet)');
  }

  return (
    <main className="settings-page" id="settings-page">
      <div className="settings-header">
        <h1 className="page-title">Settings</h1>
        <button id="save-settings-btn" className="btn btn-primary" onClick={handleSave}>
          <Save size={15} />
          Save changes
        </button>
      </div>

      <form onSubmit={handleSave} className="settings-grid" noValidate>

        {/* AWS Credentials */}
        <SettingsSection icon={Key} title="AWS Credentials">
          <div className="form-grid-2">
            <div className="form-group">
              <label htmlFor="aws-key" className="form-label">AWS Access Key ID</label>
              <input id="aws-key" className="input mono" value={awsKey}
                     onChange={e => setAwsKey(e.target.value)} autoComplete="off" />
            </div>
            <div className="form-group">
              <label htmlFor="aws-secret" className="form-label">AWS Secret Access Key</label>
              <input id="aws-secret" className="input mono" type="password" value={awsSecret}
                     onChange={e => setAwsSecret(e.target.value)} autoComplete="off" />
            </div>
          </div>
          <div className="form-group" style={{ marginTop: 14 }}>
            <label htmlFor="em-token" className="form-label">ElectricityMaps API Token</label>
            <input id="em-token" className="input mono" value={emToken}
                   onChange={e => setEmToken(e.target.value)} autoComplete="off" />
          </div>
        </SettingsSection>

        {/* Region config */}
        <SettingsSection icon={Globe} title="Region Configuration">
          <p className="settings-help">Select which regions GreenCloud monitors for spot prices and carbon data.</p>
          <div className="region-toggles">
            {REGIONS_LIST.map(r => (
              <div key={r} className={`region-toggle-row ${enabledRegions.has(r) ? 'enabled' : ''}`}>
                <span className="mono text-sm">{r}</span>
                <Toggle
                  id={`region-${r}`}
                  checked={enabledRegions.has(r)}
                  onChange={() => toggleRegion(r)}
                  label={`Toggle ${r}`}
                />
              </div>
            ))}
          </div>

          <div className="form-group" style={{ marginTop: 18 }}>
            <label htmlFor="default-mode" className="form-label">Default optimization mode</label>
            <select id="default-mode" className="select" value={defaultMode}
                    onChange={e => setDefaultMode(e.target.value)}>
              <option value="cost">Cost priority</option>
              <option value="balanced">Balanced</option>
              <option value="carbon">Carbon priority</option>
            </select>
          </div>
        </SettingsSection>

        {/* Notifications */}
        <SettingsSection icon={Bell} title="Notifications">
          <div className="toggle-rows">
            <div className="toggle-row">
              <div>
                <p className="toggle-label">Email notifications</p>
                <p className="toggle-sub">Get notified when jobs complete or fail</p>
              </div>
              <Toggle id="notif-email" checked={notifyEmail}
                      onChange={() => setNotifyEmail(v => !v)} label="Email notifications" />
            </div>
            <div className="toggle-row">
              <div>
                <p className="toggle-label">Slack notifications</p>
                <p className="toggle-sub">Post updates to a Slack channel</p>
              </div>
              <Toggle id="notif-slack" checked={notifySlack}
                      onChange={() => setNotifySlack(v => !v)} label="Slack notifications" />
            </div>
          </div>
          {notifySlack && (
            <div className="form-group" style={{ marginTop: 14 }}>
              <label htmlFor="slack-webhook" className="form-label">Slack Webhook URL</label>
              <input id="slack-webhook" className="input" placeholder="https://hooks.slack.com/…"
                     value={slackWebhook} onChange={e => setSlackWebhook(e.target.value)} />
            </div>
          )}
        </SettingsSection>

        {/* Scheduling policy */}
        <SettingsSection icon={Shield} title="Scheduling Policy">
          <div className="form-grid-2">
            <div className="form-group">
              <label htmlFor="max-retries" className="form-label">Max spot retries</label>
              <input id="max-retries" className="input" type="number" min="0" max="5"
                     value={maxRetries} onChange={e => setMaxRetries(e.target.value)} />
              <p className="field-hint">Number of times to retry on spot interruption</p>
            </div>
            <div className="form-group">
              <label htmlFor="spot-buffer" className="form-label">Spot buffer (hours)</label>
              <input id="spot-buffer" className="input" type="number" min="0" max="12"
                     value={spotBuffer} onChange={e => setSpotBuffer(e.target.value)} />
              <p className="field-hint">Extra time buffer before deadline for retries</p>
            </div>
          </div>
        </SettingsSection>

      </form>
    </main>
  );
}
