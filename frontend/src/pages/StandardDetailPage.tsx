// Standard Detail page — full technical record with provenance

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Bookmark, GitCompareArrows, ArrowLeft, FileText } from 'lucide-react';
import { getStandardDetail, saveItem } from '../services/api';
import { ProvenanceBadge } from '../components/ProvenanceBadge';
import {
  formatStatus,
  formatProvenance,
} from '../lib/utils';
import type { StandardDetail } from '../types';

function MetadataRow({ label, value, notes }: { label: string; value?: string | number | null; notes?: string }) {
  if (!value || value === 'NOT_AVAILABLE') return null;
  return (
    <div className="flex py-1.5 border-b border-[var(--color-border)] last:border-0">
      <dt className="w-40 flex-shrink-0 text-sm text-[var(--color-text-muted)]">{label}</dt>
      <dd className="text-sm text-[var(--color-text)]">
        {value}
        {notes && <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{notes}</div>}
      </dd>
    </div>
  );
}

export function StandardDetailPage() {
  const { standardNumber } = useParams();
  const [standard, setStandard] = useState<StandardDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!standardNumber) return;
    setLoading(true);
    getStandardDetail(decodeURIComponent(standardNumber))
      .then((data) => {
        setStandard(data);
        setError(null);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [standardNumber]);

  const handleSave = async () => {
    if (!standard) return;
    try {
      await saveItem(
        'standard',
        standard.standard_id,
        JSON.stringify({ standard_number: standard.standard_number, title: standard.title }),
        standard.standard_number,
      );
      setSaved(true);
    } catch (e) {
      console.error('Failed to save:', e);
    }
  };

  if (loading) {
    return (
      <div className="fade-in space-y-4 max-w-4xl">
        <div className="skeleton h-8 w-64" />
        <div className="skeleton h-4 w-96" />
        <div className="skeleton h-64" />
      </div>
    );
  }

  if (error || !standard) {
    return (
      <div className="fade-in max-w-4xl">
        <div className="border border-red-200 bg-[var(--color-error-bg)] rounded-md p-4 text-sm text-[var(--color-error)]">
          {error || 'Standard not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in max-w-5xl">
      <Link to="/standards" className="inline-flex items-center gap-1 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-primary)] mb-4">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to directory
      </Link>

      {/* Header */}
      <div className="border-b border-[var(--color-border)] pb-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[var(--color-primary)]">{standard.standard_number}</h1>
            <p className="mt-1 text-[var(--color-text)] text-lg leading-snug">{standard.title}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {standard.type_of_standard && <span className="badge badge-muted">{standard.type_of_standard}</span>}
              {standard.publication_year && <span className="badge badge-muted">{standard.publication_year}</span>}
              <span className={formatStatus(standard.current_status).className}>
                {formatStatus(standard.current_status).label}
              </span>
              <ProvenanceBadge status={standard.validation_status} />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <button className="btn btn-outline text-sm" onClick={handleSave}>
              <Bookmark className={`h-4 w-4 ${saved ? 'fill-[var(--color-primary)] text-[var(--color-primary)]' : ''}`} />
              {saved ? 'Saved' : 'Save'}
            </button>
            <Link to={`/compare?ids=${encodeURIComponent(standard.standard_number)}`} className="btn btn-outline text-sm">
              <GitCompareArrows className="h-4 w-4" /> Compare
            </Link>
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: metadata */}
        <div className="lg:col-span-2 space-y-6">
          {/* Overview */}
          <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Overview</div>
            <div className="panel-body p-4">
              <dl>
                <MetadataRow label="Standard number" value={standard.standard_number} />
                <MetadataRow label="Title" value={standard.title} />
                <MetadataRow label="Publication year" value={standard.publication_year} />
                <MetadataRow label="Publication date" value={standard.publication_date} />
                <MetadataRow label="Type" value={standard.type_of_standard} />
                <MetadataRow label="Degree of equivalence" value={standard.degree_of_equivalence} />
                <MetadataRow label="Inventory status" value={standard.inventory_status} />
                <MetadataRow label="Current status" value={standard.current_status === 'UNKNOWN_CURRENT_STATUS' ? 'Not independently verified' : standard.current_status} />
                <MetadataRow label="Part" value={standard.part} />
                <MetadataRow label="Section" value={standard.section} />
              </dl>
            </div>
          </div>

          {/* Scope */}
          <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Scope</div>
            <div className="panel-body p-4">
              {standard.scope && standard.scope !== 'NOT_AVAILABLE' ? (
                <p className="text-sm text-[var(--color-text)]">{standard.scope}</p>
              ) : standard.scope_inferred ? (
                <>
                  <p className="text-sm text-amber-700">
                    Scope information is not available in the current dataset.
                  </p>
                  <div className="mt-2 text-xs text-[var(--color-text-muted)]">
                    <strong className="text-[var(--color-text-secondary)]">Inference based on title:</strong> {standard.scope_inferred}
                  </div>
                  <div className="mt-2">
                    <ProvenanceBadge status={standard.product_category_inferred} label="Inferred" />
                  </div>
                </>
              ) : (
                <p className="text-sm text-[var(--color-text-muted)]">
                  Scope information is not available in the current dataset.
                </p>
              )}
            </div>
          </div>

          {/* Derived info */}
          {(standard.product_category || standard.sector || standard.committee) && (
            <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
              <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Classifications</div>
              <div className="panel-body p-4">
                <dl>
                  <MetadataRow label="Product category" value={standard.product_category} />
                  <MetadataRow label="Sector" value={standard.sector} />
                  <MetadataRow label="Committee" value={standard.committee} />
                  <MetadataRow label="Department" value={standard.department} />
                </dl>
                <p className="mt-2 text-xs text-[var(--color-text-muted)]">
                  These classifications are derived from identifier parsing and are not official BIS classifications.
                </p>
              </div>
            </div>
          )}

          {/* Keywords */}
          {standard.derived_keywords && (
            <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
              <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Derived keywords</div>
              <div className="panel-body p-4">
                <div className="flex flex-wrap gap-1.5">
                  {standard.derived_keywords.split(';').map((kw) => (
                    <span key={kw} className="px-2 py-0.5 rounded bg-[var(--color-very-light-blue)] text-xs text-[var(--color-text-secondary)] border border-[var(--color-border)]">
                      {kw.trim()}
                    </span>
                  ))}
                </div>
                <p className="mt-2 text-xs text-[var(--color-text-muted)]">
                  Keywords derived from the standard title. Not an authoritative technical classification.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right: compliance + related */}
        <div className="space-y-6">
          {/* QCO */}
          <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Quality Control Order</div>
            <div className="panel-body p-4">
              {standard.qco_validation_status === 'NEEDS_GOVERNMENT_SOURCE' || standard.qco_mandatory_status === 'NOT_VALIDATED' ? (
                <>
                  <p className="text-sm text-amber-800">
                    QCO applicability has not been validated in the current dataset.
                  </p>
                  <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                    No government QCO source has been loaded for this standard. This does not mean a QCO does not apply —
                    it means applicability has not been verified.
                  </p>
                </>
              ) : (
                <p className="text-sm text-[var(--color-text)]">{standard.qco_mandatory_status || 'Not validated'}</p>
              )}
              <div className="mt-3">
                <ProvidenceBadge status={standard.qco_validation_status} label="Status" />
              </div>
            </div>
          </div>

          {/* Certification */}
          <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Certification</div>
            <div className="panel-body p-4">
              {standard.cert_validation_status === 'NEEDS_AUTHORITATIVE_BIS_SOURCE' || standard.certification_status === 'NOT_VALIDATED' ? (
                <>
                  <p className="text-sm text-amber-800">
                    Certification information has not been authoritatively enriched in the current dataset.
                  </p>
                  <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                    BIS certification status for this standard has not been verified against authoritative sources.
                  </p>
                </>
              ) : (
                <p className="text-sm text-[var(--color-text)]">{standard.certification_status || 'Not verified'}</p>
              )}
              <div className="mt-3">
                <ProvidenceBadge status={standard.cert_validation_status} label="Status" />
              </div>
            </div>
          </div>

          {/* Amendments */}
          <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
            <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Amendments</div>
            <div className="panel-body p-4">
              {standard.amendment_validation_status === 'NEEDS_AUTHORITATIVE_ENRICHMENT' || standard.amendment_status === 'NOT_VALIDATED' ? (
                <>
                  <p className="text-sm text-amber-800">
                    Amendment information has not been authoritatively enriched in the current dataset.
                  </p>
                  <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                    The absence of verified amendment data should not be interpreted as confirmation that no amendments exist.
                  </p>
                </>
              ) : standard.amendment_number ? (
                <p className="text-sm text-[var(--color-text)]">{standard.amendment_number}</p>
              ) : null}
              <div className="mt-3">
                <ProvidenceBadge status={standard.amendment_validation_status} label="Status" />
              </div>
            </div>
          </div>

          {/* Related family */}
          {standard.family_members && standard.family_members.length > 0 && (
            <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
              <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Related by family</div>
              <div className="panel-body p-4">
                <div className="text-xs text-[var(--color-text-muted)] mb-2">
                  Derived from standard identifier family parsing. Not an official BIS relationship.
                </div>
                <ul className="space-y-1">
                  {standard.family_members.map((s) => (
                    <li key={s.standard_id}>
                      <Link
                        to={`/standards/${encodeURIComponent(s.standard_number)}`}
                        className="text-sm text-[var(--color-primary)] hover:underline"
                      >
                        {s.standard_number}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Relationships */}
          {standard.relationships && standard.relationships.length > 0 && (
            <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
              <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] font-semibold text-[var(--color-primary)]">Relationships</div>
              <div className="panel-body p-4">
                {standard.relationships.map((rel, i) => (
                  <div key={i} className="py-1.5 border-b border-[var(--color-border)] last:border-0">
                    <div className="text-xs font-medium text-[var(--color-text)]">{rel.relationship_type.replaceAll('_', ' ')}</div>
                    <div className="text-xs text-[var(--color-text-muted)] mt-0.5">
                      {rel.evidence || rel.derivation_method || ''}
                    </div>
                    <div className="mt-1">
                      <ProvidenceBadge status={rel.validation_status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Evidence panel (for search context) */}
      {standard.derived_keywords && (
        <div className="mt-6 panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
          <button
            className="panel-header w-full text-left cursor-pointer hover:bg-[var(--color-very-light-blue)] transition-colors bg-[var(--color-very-light-blue)]"
            onClick={() => setShowEvidence(!showEvidence)}
            aria-expanded={showEvidence}
          >
            <span className="flex items-center gap-2 text-[var(--color-primary)]">
              <FileText className="h-4 w-4 text-[var(--color-primary)]" /> Evidence & Retrieval Signals
            </span>
            <span className="text-[var(--color-text-muted)]">{showEvidence ? '−' : '+'}</span>
          </button>
          {showEvidence && (
            <div className="panel-body p-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <div className="text-xs font-medium text-[var(--color-text-secondary)] mb-2">Derived search terms</div>
                  <div className="flex flex-wrap gap-1.5">
                    {standard.derived_keywords.split(';').map((kw) => (
                      <span key={kw} className="px-1.5 py-0.5 rounded bg-[var(--color-very-light-blue)] text-[11px] text-[var(--color-text-secondary)] border border-[var(--color-border)]">
                        {kw.trim()}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium text-[var(--color-text-secondary)] mb-2">Provenance</div>
                  <div className="space-y-1.5 text-xs text-[var(--color-text-secondary)]">
                    <div><span className="text-[var(--color-text-muted)]">Source:</span> {standard.source || 'Not specified'}</div>
                    <div><span className="text-[var(--color-text-muted)]">Source type:</span> {standard.source_type || 'Not specified'}</div>
                    <div><span className="text-[var(--color-text-muted)]">Record type:</span> {standard.record_type || 'Not specified'}</div>
                    <div><span className="text-[var(--color-text-muted)]">Validation:</span> {standard.validation_status}</div>
                    <div><span className="text-[var(--color-text-muted)]">Enrichment:</span> {standard.enrichment_status || 'Not specified'}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Small helper to display provenance badge
function ProvidenceBadge({ status, label }: { status?: string | null; label?: string }) {
  if (!status) return null;
  const info = formatProvenance(status);
  return <span className={info.className}>{label || info.label}</span>;
}
