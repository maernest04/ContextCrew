import { useState } from 'react';

export default function App() {
  const [status, setStatus] = useState('Not checked');
  const [checking, setChecking] = useState(false);

  async function checkBackend() {
    setChecking(true);
    try {
      const response = await fetch('/healthz');
      if (!response.ok) throw new Error('Request failed');
      const data = await response.json();
      setStatus(data.status === 'ok' && data.mode === 'ephemeral-spike'
        ? 'Connected · ephemeral spike' : 'Unexpected backend response');
    } catch {
      setStatus('Unavailable · start the Phase 0 API');
    } finally {
      setChecking(false);
    }
  }

  return <main>
    <p className="eyebrow">CONTEXTCREW / PHASE 0</p>
    <h1>Shared context.<br />Separate agents.</h1>
    <p>Interoperability scaffold for exchanging synthetic project updates through MCP.</p>
    <section aria-labelledby="backend-heading">
      <h2 id="backend-heading">Backend connection</h2>
      <p role="status">{status}</p>
      <button onClick={checkBackend} disabled={checking}>
        {checking ? 'Checking…' : 'Check connection'}
      </button>
    </section>
    <p className="note">No room dashboard or sign-in yet. Use the MCP bridge for the spike;
      records disappear when the backend restarts. Share synthetic data only.</p>
  </main>;
}
