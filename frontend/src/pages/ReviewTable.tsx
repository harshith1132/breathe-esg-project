import { useState, useEffect } from 'react';
import api from '../api/client';

interface ReviewRecord {
  id: string;
  scope: number;
  category: string;
  activity_date: string | null;
  period_start: string | null;
  period_end: string | null;
  quantity_raw: string;
  unit_raw: string;
  quantity_normalized: string;
  unit_normalized: string;
  co2e_kg: string | null;
  review_status: string;
  is_estimated: boolean;
  flagged_reasons: string[];
  data_source_name: string;
  batch_filename: string;
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: '#f59e0b',
  FLAGGED: '#ef4444',
  APPROVED: '#10b981',
  REJECTED: '#6b7280',
};

export default function ReviewTable() {
  const [records, setRecords] = useState<ReviewRecord[]>([]);
  const [filter, setFilter] = useState('PENDING');
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api.get(`/records/?review_status=${filter}&ordering=-created_at`)
      .then(r => setRecords(r.data.results || []))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter]);

  const approve = async (id: string) => {
    await api.post(`/records/${id}/approve/`);
    load();
  };

  const reject = async (id: string) => {
    const note = prompt('Reason for rejection (optional):');
    if (note !== null) {
      await api.post(`/records/${id}/reject/`, { notes: note });
      load();
    }
  };

  const flag = async (id: string) => {
    const reason = prompt('Flag reason:');
    if (reason !== null) {
      await api.post(`/records/${id}/flag/`, { reason });
      load();
    }
  };

  const counts: Record<string, number> = {};
  ['PENDING', 'FLAGGED', 'APPROVED', 'REJECTED'].forEach(s => {
    counts[s] = records.length;
  });

  return (
    <div style={{ padding: '2rem', maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: '1.5rem' }}>Review Queue</h1>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '1.5rem' }}>
        {['PENDING', 'FLAGGED', 'APPROVED', 'REJECTED'].map(s => (
          <button key={s} onClick={() => setFilter(s)} style={{
            padding: '8px 16px', borderRadius: 8,
            border: `1px solid ${filter === s ? '#1e293b' : '#e5e7eb'}`,
            background: filter === s ? '#1e293b' : 'white',
            color: filter === s ? 'white' : '#374151',
            cursor: 'pointer', fontSize: 13, fontWeight: 500,
          }}>{s}</button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: '#6b7280' }}>Loading…</p>
      ) : records.length === 0 ? (
        <div style={{ padding: '3rem', textAlign: 'center', background: 'white', borderRadius: 12, border: '1px solid #e5e7eb', color: '#9ca3af' }}>
          No {filter.toLowerCase()} records
        </div>
      ) : (
        <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 12, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                <th style={th}>Source / File</th>
                <th style={th}>Scope / Category</th>
                <th style={th}>Period</th>
                <th style={{ ...th, textAlign: 'right' }}>Qty (raw)</th>
                <th style={{ ...th, textAlign: 'right' }}>kgCO₂e</th>
                <th style={th}>Status</th>
                <th style={th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map(r => (
                <tr key={r.id} style={{ borderBottom: '1px solid #f3f4f6' }}
                  onClick={() => setSelected(selected === r.id ? null : r.id)}>
                  <td style={td}>
                    <div style={{ fontWeight: 500 }}>{r.data_source_name || '—'}</div>
                    <div style={{ color: '#9ca3af', fontSize: 11, marginTop: 2 }}>{r.batch_filename}</div>
                  </td>
                  <td style={td}>
                    <div>Scope {r.scope}</div>
                    <div style={{ color: '#6b7280', fontSize: 11, marginTop: 2 }}>{r.category}</div>
                  </td>
                  <td style={td}>
                    {r.activity_date || (r.period_start ? `${r.period_start} → ${r.period_end}` : '—')}
                  </td>
                  <td style={{ ...td, textAlign: 'right' }}>
                    {r.quantity_raw} {r.unit_raw}
                    {r.is_estimated && <span title="Value is estimated" style={{ color: '#f59e0b', marginLeft: 4 }}>~</span>}
                  </td>
                  <td style={{ ...td, textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
                    {r.co2e_kg ? Number(r.co2e_kg).toLocaleString(undefined, { maximumFractionDigits: 1 }) : '—'}
                  </td>
                  <td style={td}>
                    <span style={{
                      padding: '3px 10px', borderRadius: 12, fontSize: 11, fontWeight: 500,
                      background: STATUS_COLORS[r.review_status] + '20',
                      color: STATUS_COLORS[r.review_status],
                    }}>{r.review_status}</span>
                    {r.flagged_reasons?.length > 0 && (
                      <div style={{ fontSize: 11, color: '#ef4444', marginTop: 4, maxWidth: 200 }}>
                        ⚠ {r.flagged_reasons[0]}
                      </div>
                    )}
                  </td>
                  <td style={{ ...td, whiteSpace: 'nowrap' }} onClick={e => e.stopPropagation()}>
                    {r.review_status !== 'APPROVED' && (
                      <button onClick={() => approve(r.id)} style={actionBtn('#10b981')}>Approve</button>
                    )}
                    {r.review_status !== 'REJECTED' && (
                      <button onClick={() => reject(r.id)} style={actionBtn('#6b7280')}>Reject</button>
                    )}
                    {r.review_status !== 'FLAGGED' && (
                      <button onClick={() => flag(r.id)} style={actionBtn('#ef4444')}>Flag</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontWeight: 500, color: '#6b7280', fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.05em' };
const td: React.CSSProperties = { padding: '12px 16px', verticalAlign: 'top' };
const actionBtn = (color: string): React.CSSProperties => ({
  marginRight: 4, padding: '4px 10px', background: color, color: 'white',
  border: 'none', borderRadius: 5, cursor: 'pointer', fontSize: 11, fontWeight: 500,
});