import { useState, useRef, useEffect } from 'react';
import api from '../api/client';

interface DataSource {
  id: string;
  name: string;
  source_type: string;
}

interface UploadResult {
  batch_id: string;
  row_count: number;
  records_created: number;
  errors: number;
  warnings: number;
}

export default function Upload() {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [sourceId, setSourceId] = useState('');
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Load data sources for this org via the admin-created ones
    // We'll fetch from records to get available sources
    api.get('/batches/').then(r => {
      // Extract unique sources from batch history
    }).catch(() => {});
  }, []);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { setError('Please select a file'); return; }
    if (!sourceId.trim()) { setError('Please enter a Data Source ID'); return; }

    const fd = new FormData();
    fd.append('file', file);
    fd.append('data_source_id', sourceId.trim());

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const r = await api.post('/ingest/upload/', fd);
      setResult(r.data);
    } catch (e: any) {
      setError(e.response?.data?.error || 'Upload failed. Check the console for details.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: 640, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Upload Data</h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: '2rem' }}>
        Upload a CSV export from SAP, your utility portal, or Concur travel.
        Find your Data Source ID in the Django admin panel.
      </p>

      <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.5rem' }}>
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={labelStyle}>Data Source ID (UUID from admin)</label>
          <input value={sourceId} onChange={e => setSourceId(e.target.value)}
            placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
            style={inputStyle} />
          <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 4 }}>
            Go to http://localhost:8000/admin → Data Sources → click a source → copy the UUID from the URL
          </p>
        </div>

        <div style={{ marginBottom: '1.25rem' }}>
          <label style={labelStyle}>CSV File</label>
          <input ref={fileRef} type="file" accept=".csv,.txt,.tsv"
            style={{ display: 'block', fontSize: 14 }} />
        </div>

        {error && (
          <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, color: '#dc2626', fontSize: 13, marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <button onClick={handleUpload} disabled={loading} style={{
          padding: '10px 24px', background: loading ? '#94a3b8' : '#1e293b',
          color: 'white', border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 14, fontWeight: 500,
        }}>
          {loading ? 'Uploading and parsing…' : 'Upload and ingest'}
        </button>
      </div>

      {result && (
        <div style={{ marginTop: '1.5rem', padding: '1.5rem', background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 12 }}>
          <h3 style={{ margin: '0 0 1rem', color: '#15803d' }}>✓ Ingestion complete</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: 14 }}>
            <Stat label="Rows processed" value={result.row_count} />
            <Stat label="Records created" value={result.records_created} />
            <Stat label="Parse errors" value={result.errors} highlight={result.errors > 0} />
            <Stat label="Auto-flagged (warnings)" value={result.warnings} highlight={result.warnings > 0} />
          </div>
          <p style={{ fontSize: 12, color: '#6b7280', marginTop: '1rem', marginBottom: 0 }}>
            Batch ID: {result.batch_id}
          </p>
        </div>
      )}

      <div style={{ marginTop: '2rem', padding: '1.25rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 10 }}>
        <h3 style={{ margin: '0 0 0.75rem', fontSize: 14, fontWeight: 600 }}>Sample files for testing</h3>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: 13, color: '#475569', lineHeight: '1.8' }}>
          <li><code>sample_data/sap_fuel_sample.csv</code> → use SAP data source ID</li>
          <li><code>sample_data/utility_sample.csv</code> → use UTILITY data source ID</li>
          <li><code>sample_data/travel_sample.csv</code> → use TRAVEL data source ID</li>
        </ul>
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = { display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 6, color: '#374151' };
const inputStyle: React.CSSProperties = { width: '100%', padding: '10px 12px', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 14, boxSizing: 'border-box' };

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div style={{ padding: '8px 12px', background: 'white', borderRadius: 6, border: '1px solid #dcfce7' }}>
      <div style={{ fontSize: 18, fontWeight: 700, color: highlight ? '#dc2626' : '#15803d' }}>{value}</div>
      <div style={{ fontSize: 12, color: '#6b7280' }}>{label}</div>
    </div>
  );
}