'use client';

import { FormEvent, useMemo, useState } from 'react';

type ApiKeyDraft = {
  label: string;
  allowedOrigins: string;
  allowedIps: string;
  scopes: string;
  expires: string;
  notes: string;
};

const initialDraft: ApiKeyDraft = {
  label: '',
  allowedOrigins: '',
  allowedIps: '',
  scopes: 'interactions:read',
  expires: '',
  notes: '',
};

function makeKeyValue() {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return `med_${Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')}`;
}

function splitCommaSeparated(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export default function HomePage() {
  const [draft, setDraft] = useState<ApiKeyDraft>(initialDraft);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied'>('idle');

  const originCount = useMemo(() => splitCommaSeparated(draft.allowedOrigins).length, [draft.allowedOrigins]);
  const ipCount = useMemo(() => splitCommaSeparated(draft.allowedIps).length, [draft.allowedIps]);
  const scopeCount = useMemo(() => splitCommaSeparated(draft.scopes).length, [draft.scopes]);

  const updateDraft = <K extends keyof ApiKeyDraft>(field: K, value: ApiKeyDraft[K]) => {
    setDraft((current) => ({ ...current, [field]: value }));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreatedKey(makeKeyValue());
    setCopyStatus('idle');
  };

  const handleCopyKey = async () => {
    if (!createdKey || typeof navigator === 'undefined') {
      return;
    }

    await navigator.clipboard.writeText(createdKey);
    setCopyStatus('copied');
  };

  const handleReset = () => {
    setDraft(initialDraft);
    setCreatedKey(null);
    setCopyStatus('idle');
  };

  return (
    <main className="page-shell api-key-shell">
      <section className="api-key-layout">
        <div className="api-key-form-card">
          <div className="api-key-heading-row">
            <div className="api-key-heading">
              <p className="eyebrow">API access</p>
              <h1>Create API Key</h1>
              <p className="hero-copy">Keys are shown once. We store only the hash.</p>
            </div>

            <button className="secondary-button compact" type="button" onClick={handleReset}>
              Start over
            </button>
          </div>

          <form className="api-key-form" onSubmit={handleSubmit}>
            <label>
              <span>Label</span>
              <input
                type="text"
                placeholder="e.g. EHR staging, production"
                value={draft.label}
                onChange={(event) => updateDraft('label', event.target.value)}
              />
            </label>

            <label>
              <span>Allowed Origins</span>
              <input
                type="text"
                placeholder="https://app.example.com"
                value={draft.allowedOrigins}
                onChange={(event) => updateDraft('allowedOrigins', event.target.value)}
              />
              <small>Comma-separated. Leave empty for unrestricted.</small>
            </label>

            <label>
              <span>Allowed IPs</span>
              <input
                type="text"
                placeholder="203.0.113.10"
                value={draft.allowedIps}
                onChange={(event) => updateDraft('allowedIps', event.target.value)}
              />
              <small>Comma-separated. Leave empty for unrestricted.</small>
            </label>

            <label>
              <span>Scopes</span>
              <input
                type="text"
                placeholder="interactions:read"
                value={draft.scopes}
                onChange={(event) => updateDraft('scopes', event.target.value)}
              />
            </label>

            <label>
              <span>Expires</span>
              <input
                type="text"
                placeholder="2027-12-31T23:59:59Z"
                value={draft.expires}
                onChange={(event) => updateDraft('expires', event.target.value)}
              />
              <small>ISO-8601 timestamp. Leave empty for no expiration.</small>
            </label>

            <label className="api-key-notes">
              <span>Notes</span>
              <textarea
                rows={4}
                placeholder="Internal notes about this key..."
                value={draft.notes}
                onChange={(event) => updateDraft('notes', event.target.value)}
              />
            </label>

            <button className="primary-button api-key-submit" type="submit">
              Create Key
            </button>
          </form>
        </div>

        <aside className="api-key-summary-card" aria-label="Key summary preview">
          <div className="summary-panel">
            <p className="panel-label">Preview</p>
            <h2>Access policy summary</h2>
            <p>
              Label: {draft.label.trim() || 'Untitled key'}
              <br />
              Origins: {originCount || 'unrestricted'}
              <br />
              IPs: {ipCount || 'unrestricted'}
              <br />
              Scopes: {scopeCount || 'none'}
            </p>
          </div>

          <div className="summary-panel">
            <p className="panel-label">Key visibility</p>
            <h2>{createdKey ? 'One-time secret generated' : 'Secret will appear here'}</h2>
            <p>{createdKey ? 'The secret is stored in memory only and is not shown in full.' : 'Create the key to generate the token.'}</p>
            {createdKey ? (
              <>
                <p aria-label="Masked API key">{`${createdKey.slice(0, 8)}••••••••••••••••••••••••${createdKey.slice(-6)}`}</p>
                <button className="secondary-button compact" type="button" onClick={handleCopyKey}>
                  {copyStatus === 'copied' ? 'Copied' : 'Copy secret'}
                </button>
              </>
            ) : null}
          </div>
        </aside>
      </section>
    </main>
  );
}
