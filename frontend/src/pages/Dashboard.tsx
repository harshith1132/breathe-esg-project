import { useEffect, useState } from 'react';
import api from '../api/client';

interface Summary {
  approved_by_scope: { scope: number; total_co2e: number; record_count: number }[];
  pending_count: number;
  flagged_count: number;
  approved_count: number;
  rejected_count: number;
  total_co2e_approved: number;
}

const SCOPE_LABELS: Record<number, string> = {
  1: 'Scope 1 — Direct (fuel combustion)',
  2: 'Scope 2 — Purchased electricity',
  3: 'Scope 3 — Value chain (travel, procurement)',
};

const SCOPE_COLORS: Record<number, string> = {
  1: '#f97316', 2: '#3b82f6', 3: '#8b5cf6',
};

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);

  useEffect(() => {
    api.get('/records/summary/').then(r => setSummary(r.data)).catch(console.error);
  }, []);

  const total = summary?.total_co2e_approved || 0;

  return (
    <div style={{ padding: '2rem', maxWidth: 960, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Emissions Overview</h1>
      <p style={{ color: '#6b7280', fontSize: 14, marginBottom: '2rem' }}>
        Approved records only. Pending and flagged records are excluded from totals.
      </p>

      {summary && (
        <>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
            <StatCard label="Total CO₂e (approved)" value={`${Number(total).toLocaleString(undefined, { maximumFractionDigits: 0 })} kg`} color="#10b981" />
            <StatCard label="Pending review" value={String(summary.pending_count)} color="#f59e0b" />
            <StatCard label="Flagged" value={String(summary.flagged_count)} color="#ef4444" />
            <StatCard label="Approved" value={String(summary.approved_count)} color="#10b981" />
            <StatCard label="Rejected" value={String(summary.rejected_count)} color="#6b7280" />
          </div>

          <div style={{ background: 'white', border: '1px solid #e5e7eb', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #f3f4f6' }}>
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Approved emissions by scope (kgCO₂e)</h2>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={{ padding: '12px 20px', textAlign: 'left', fontWeight: 500, color: '#6b7280' }}>Scope</th>
                  <th style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 500, color: '#6b7280' }}>kgCO₂e</th>
                  <th style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 500, color: '#6b7280' }}>Records</th>
                  <th style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 500, color: '#6b7280' }}>% of total</th>
                </tr>
              </thead>
              <tbody>
                {summary.approved_by_scope.length === 0 ? (
                  <tr><td colSpan={4} style={{ padding: '2rem', textAlign: 'center', color: '#9ca3af' }}>No approved records yet</td></tr>
                ) : (
                  summary.approved_by_scope.map(row => (
                    <tr key={row.scope} style={{ borderTop: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '14px 20px' }}>
                        <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: SCOPE_COLORS[row.scope], marginRight: 8 }} />
                        {SCOPE_LABELS[row.scope]}
                      </td>
                      <td style={{ padding: '14px 20px', textAlign: 'right', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
                        {Number(row.total_co2e).toLocaleString(undefined, { maximumFractionDigits: 1 })}
                      </td>
                      <td style={{ padding: '14px 20px', textAlign: 'right', color: '#6b7280' }}>{row.record_count}</td>
                      <td style={{ padding: '14px 20px', textAlign: 'right', color: '#6b7280' }}>
                        {total > 0 ? `${((row.total_co2e / total) * 100).toFixed(1)}%` : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ padding: '1.25rem 1.5rem', background: 'white', border: '1px solid #e5e7eb', borderRadius: 10, minWidth: 160, flex: 1 }}>
      <div style={{ fontSize: 26, fontWeight: 700, color }}>{value}</div>
      <div style={{ color: '#6b7280', fontSize: 13, marginTop: 4 }}>{label}</div>
    </div>
  );
}