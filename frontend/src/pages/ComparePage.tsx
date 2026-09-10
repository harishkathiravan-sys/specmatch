// Compare page — side-by-side standards comparison

import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { ArrowLeft, X, Plus } from 'lucide-react';
import { getStandardDetail, compareStandards } from '../services/api';
import { formatProvenance, formatStatus } from '../lib/utils';
import type { StandardDetail } from '../types';

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const idsParam = searchParams.get('ids') || '';
  const initialIds = idsParam ? idsParam.split(',').filter(Boolean) : [];

  const [standardIds, setStandardIds] = useState<string[]>(initialIds);
  const [standards, setStandards] = useState<(StandardDetail | null)[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addInput, setAddInput] = useState('');

  const [serverDifferences, setServerDifferences] = useState<{ field: string; values: Record<string, string | null> }[]>([]);

  useEffect(() => {
    if (standardIds.length === 0) {
      setStandards([]);
      setServerDifferences([]);
      return;
    }
    setLoading(true);
    setError(null);
    // Prefer server-side compare for 2-3 ids (returns diff summary)
    if (standardIds.length >= 2) {
      compareStandards(standardIds)
        .then((res) => {
          setStandards(res.standards.map((s) => s as unknown as StandardDetail));
          setServerDifferences(res.differences || []);
        })
        .catch(() => {
          // Fallback to per-standard fetch if compare endpoint fails
          Promise.all(standardIds.map((id) => getStandardDetail(id).catch(() => null)))
            .then((results) => {
              setStandards(results);
              setServerDifferences([]);
            })
            .catch((e) => setError((e as Error).message));
        })
        .finally(() => setLoading(false));
    } else {
      Promise.all(standardIds.map((id) => getStandardDetail(id).catch(() => null)))
        .then((results) => {
          setStandards(results);
          setServerDifferences([]);
        })
        .catch((e) => setError((e as Error).message))
        .finally(() => setLoading(false));
    }
  }, [standardIds]);

  const updateUrl = (ids: string[]) => {
    if (ids.length > 0) {
      setSearchParams({ ids: ids.join(',') });
    } else {
      setSearchParams({});
    }
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = addInput.trim();
    if (!trimmed || standardIds.includes(trimmed) || standardIds.length >= 3) return;
    const newIds = [...standardIds, trimmed];
    setStandardIds(newIds);
    updateUrl(newIds);
    setAddInput('');
  };

  const handleRemove = (index: number) => {
    const newIds = standardIds.filter((_, i) => i !== index);
    setStandardIds(newIds);
    updateUrl(newIds);
  };

  const validStandards = standards.filter((s): s is StandardDetail => s !== null);

  const attributes = [
    { label: 'Standard Number', get: (s: StandardDetail) => s.standard_number },
    { label: 'Title', get: (s: StandardDetail) => s.title },
    { label: 'Publication Year', get: (s: StandardDetail) => s.publication_year ? String(s.publication_year) : '—' },
    { label: 'Publication Date', get: (s: StandardDetail) => s.publication_date || s.date_of_publish_raw || '—' },
    { label: 'Standard Type', get: (s: StandardDetail) => s.type_of_standard || '—' },
    { label: 'Degree of Equivalence', get: (s: StandardDetail) => s.degree_of_equivalence || '—' },
    { label: 'Status', get: (s: StandardDetail) => formatStatus(s.current_status).label },
    { label: 'Sector', get: (s: StandardDetail) => s.sector || 'Not available' },
    { label: 'Department', get: (s: StandardDetail) => s.department || 'Not available' },
    { label: 'Committee', get: (s: StandardDetail) => s.committee || 'Not available' },
    { label: 'Product Category', get: (s: StandardDetail) => s.product_category || 'Not available' },
    { label: 'Standard Family', get: (s: StandardDetail) => s.standard_family_key || '—' },
    { label: 'Scope', get: (s: StandardDetail) => s.scope && s.scope !== 'NOT_AVAILABLE' ? s.scope : s.scope_inferred || 'Scope information is not available in the current dataset.' },
    { label: 'QCO Applicability', get: (s: StandardDetail) => s.qco_validation_status === 'NEEDS_GOVERNMENT_SOURCE' ? 'QCO applicability has not been validated in the current dataset.' : s.qco_mandatory_status || 'Not validated' },
    { label: 'Certification Status', get: (s: StandardDetail) => s.cert_validation_status === 'NEEDS_AUTHORITATIVE_BIS_SOURCE' ? 'Certification information has not been authoritatively enriched in the current dataset.' : s.certification_status || 'Not verified' },
    { label: 'Amendments', get: (s: StandardDetail) => s.amendment_validation_status === 'NEEDS_AUTHORITATIVE_ENRICHMENT' ? 'Amendment information has not been authoritatively enriched in the current dataset.' : s.amendment_number || 'None loaded' },
    { label: 'Provenance', get: (s: StandardDetail) => formatProvenance(s.validation_status).label },
  ];

  return (
    <div className="fade-in max-w-6xl">
      <Link to="/standards" className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-primary)] mb-4">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to directory
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-primary)]">Compare Standards</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">
            Compare 2 to 3 standards side by side across technical metadata and compliance status.
          </p>
        </div>

        {standardIds.length < 3 && (
          <form onSubmit={handleAdd} className="flex items-center gap-2">
            <input
              type="text"
              placeholder="e.g. IS 19763:2026"
              className="input !py-1.5 text-sm w-48 bg-white border border-[var(--color-border)] text-[var(--color-text)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] focus:ring-[var(--color-accent)]/20"
              value={addInput}
              onChange={(e) => setAddInput(e.target.value)}
            />
            <button type="submit" className="btn btn-outline text-[var(--color-primary)] border-[var(--color-border)] hover:bg-[var(--color-light-blue)]">
              <Plus className="h-4 w-4" /> Add Standard
            </button>
          </form>
        )}
      </div>

      {error && (
        <div className="border border-red-200 bg-[var(--color-error-bg)] rounded-md p-4 text-sm text-[var(--color-error)] mb-6">
          {error}
        </div>
      )}

      {loading && (
        <div className="space-y-4">
          <div className="skeleton h-16 w-full" />
          <div className="skeleton h-64 w-full" />
        </div>
      )}

      {!loading && validStandards.length === 0 && (
        <div className="panel bg-white border border-[var(--color-border)] rounded-2xl p-8 text-center text-[var(--color-text-secondary)]">
          <p className="font-medium text-[var(--color-text)]">No standards selected for comparison.</p>
          <p className="text-sm mt-1">Enter standard numbers above or click "Compare" from any standard card or detail page.</p>
        </div>
      )}

      {!loading && validStandards.length > 0 && serverDifferences.length > 0 && (
        <div className="mb-3 panel bg-[var(--color-warning-bg)] border border-[var(--color-warning)] rounded-2xl p-3">
          <div className="text-xs font-semibold text-[var(--color-warning)] mb-1">Differences detected (server-side)</div>
          <ul className="text-xs text-[var(--color-warning)] space-y-0.5">
            {serverDifferences.map((d) => (
              <li key={d.field}><span className="font-medium">{d.field}:</span> {Object.entries(d.values).map(([k, v]) => `${k}=${v ?? '—'}`).join(' · ')}</li>
            ))}
          </ul>
        </div>
      )}

      {!loading && validStandards.length > 0 && (
        <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden">
          <table className="data-table">
            <thead>
              <tr>
                <th className="w-48 bg-[var(--color-very-light-blue)] text-[var(--color-primary-medium)] font-medium">Attribute</th>
                {validStandards.map((std, idx) => (
                  <th key={std.standard_id} className="min-w-[240px] max-w-[320px]">
                    <div className="flex items-center justify-between">
                      <Link
                        to={`/standards/${encodeURIComponent(std.standard_number)}`}
                        className="text-[var(--color-primary)] font-semibold hover:underline"
                      >
                        {std.standard_number}
                      </Link>
                      <button
                        onClick={() => handleRemove(idx)}
                        className="text-[var(--color-text-muted)] hover:text-[var(--color-error)] p-1 rounded"
                        title="Remove from comparison"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {attributes.map((attr) => {
                // Check if all standards have identical values
                const values = validStandards.map((s) => attr.get(s));
                const isDifferent = new Set(values).size > 1;

                return (
                  <tr key={attr.label} className={isDifferent ? 'bg-[var(--color-very-light-blue)]/50' : ''}>
                    <td className="font-medium text-[var(--color-text-secondary)] bg-[var(--color-very-light-blue)]/30 whitespace-nowrap px-4 py-2">
                      {attr.label}
                      {isDifferent && validStandards.length > 1 && (
                        <span className="ml-1.5 text-[10px] text-[var(--color-primary)] bg-[var(--color-light-blue)]/20 px-1.5 py-0.2 rounded font-normal">
                          Differs
                        </span>
                      )}
                    </td>
                    {validStandards.map((std) => (
                      <td key={std.standard_id} className="text-[var(--color-text)] text-sm px-4 py-2">
                        {attr.get(std)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
