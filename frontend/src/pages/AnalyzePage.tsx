// Analyze page — SIH demo experience
// Procurement requirement → Extraction → Retrieval → Ranking → Evidence → Confidence → Compliance → Decision

import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Upload, FileText, Loader2, Check, Circle, ChevronDown, ChevronUp,
  ArrowRight, GitCompareArrows, Bookmark, Tag, Search, Brain,
  ShieldCheck, AlertTriangle, X, BookmarkCheck, Info, FileSearch,
} from 'lucide-react';
import { analyzeSpecification, uploadDocument, saveItem } from '../services/api';
import type { AnalysisResponse, StandardSummary, RecommendationItem, EvidenceItem } from '../types';
import { formatScore, formatProvenance, formatStatus } from '../lib/utils';

// ─── Constants ───────────────────────────────────────────────────────────────

const EXAMPLE_SPEC = `Procurement of aircraft woven carpet for aircraft interiors. The carpet should meet applicable Indian requirements for textile floor coverings and aircraft applications.`;

type Stage = 'idle' | 'processing' | 'done' | 'error';

const PIPELINE_STEPS = [
  { label: 'Reading specification', icon: FileText },
  { label: 'Extracting requirements', icon: Brain },
  { label: 'Identifying product category', icon: Search },
  { label: 'Retrieving candidate standards', icon: Search },
  { label: 'Ranking candidates', icon: Tag },
  { label: 'Assembling evidence', icon: ShieldCheck },
];

// Evidence type → human label with grouping
const EVIDENCE_GROUPS: Record<string, { label: string; group: string }> = {
  title_match: { label: 'Title evidence', group: 'title' },
  keyword_match: { label: 'Technical evidence', group: 'technical' },
  metadata_match: { label: 'Context evidence', group: 'context' },
  context_match: { label: 'Context evidence', group: 'context' },
  retrieval_match: { label: 'Retrieval signal', group: 'retrieval' },
  retrieval_signal: { label: 'Retrieval signal', group: 'retrieval' },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function confidenceBadge(conf: string): string {
  if (conf === 'high') return 'badge badge-verified';
  if (conf === 'medium') return 'badge badge-warning';
  return 'badge badge-muted';
}

function evidenceStrengthIcon(strength: string): string {
  if (strength === 'strong') return '✓';
  if (strength === 'moderate') return '○';
  return '·';
}

// ─── Save Confirmation Banner ────────────────────────────────────────────────

function SaveConfirmation({ standard, onDismiss }: { standard: string; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 4000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div className="flex items-center gap-2 rounded-lg border border-[var(--color-success)] bg-[var(--color-success-bg)] px-3 py-2 text-sm text-[var(--color-success)] fade-in">
      <BookmarkCheck className="h-4 w-4 shrink-0" />
      <span><strong>{standard}</strong> saved successfully.</span>
      <Link to="/saved" className="underline text-xs ml-1">View Saved</Link>
      <button onClick={onDismiss} className="ml-auto opacity-50 hover:opacity-100" aria-label="Dismiss">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// ─── Enhanced Recommendation Card ────────────────────────────────────────────
// phase6 is optional — when present, extra intelligence is rendered inline
// inside the existing card design (no redesign, backwards-compatible).

function EnhancedRecommendationCard({
  rec,
  onSave,
  rank,
  phase6,
}: {
  rec: RecommendationItem;
  onSave: (s: StandardSummary) => void;
  rank: number;
  phase6?: Record<string, unknown> | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const std = rec.standard;
  const prov = formatProvenance(std.validation_status);
  const statusFmt = formatStatus(std.current_status);
  const p6 = phase6 as unknown as {
    requirement_coverage?: { score: number; matched: string[]; unmatched: string[]; details: Record<string, string> };
    contradictions?: Array<{ type: string; reason: string; severity: string; penalty: number }>;
    why_this_standard?: string[];
    compliance?: Record<string, unknown>;
    lifecycle?: Record<string, unknown>;
    confidence?: string;
    confidence_score?: number;
    confidence_reasons?: string[];
    evidence_strength?: string;
  } | null;
  const hasP6 = !!p6 && (!!p6.why_this_standard?.length || !!p6.requirement_coverage || !!p6.contradictions?.length || !!p6.evidence_strength);

  // Group evidence items
  const grouped: Record<string, EvidenceItem[]> = {};
  for (const ev of rec.evidence) {
    const group = EVIDENCE_GROUPS[ev.type]?.group || 'other';
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(ev);
  }
  const groupOrder = ['title', 'technical', 'context', 'retrieval', 'other'];

  return (
    <article className="border border-[var(--color-border)] rounded-2xl bg-white overflow-hidden hover:border-[var(--color-primary)]/40 transition-all shadow-sm">
      {/* Card header: rank, standard number, scores */}
      <div className="p-5">
        <div className="flex items-start gap-3">
          {/* Rank badge */}
          <span className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--color-primary)] text-white text-xs font-bold flex items-center justify-center">
            {rank}
          </span>

          <div className="flex-1 min-w-0">
            {/* Standard number */}
            <Link
              to={`/standards/${encodeURIComponent(std.standard_number)}`}
              className="text-base font-bold text-[var(--color-primary)] hover:underline"
            >
              {std.standard_number}
            </Link>

            {/* Title */}
            <p className="mt-1 text-sm text-[var(--color-text)] leading-snug">{std.title}</p>

            {/* Badges row */}
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
              <span className={confidenceBadge(rec.confidence.confidence)}>
                {rec.confidence.confidence.charAt(0).toUpperCase() + rec.confidence.confidence.slice(1)} confidence
              </span>
              {std.type_of_standard && <span className="badge badge-muted">{std.type_of_standard}</span>}
              {std.publication_year && <span className="badge badge-muted">{std.publication_year}</span>}
              <span className={statusFmt.className}>{statusFmt.label}</span>
              <span className={prov.className}>{prov.label}</span>
            </div>
          </div>

          {/* Scores panel */}
          <div className="flex-shrink-0 text-right">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-very-light-blue)] px-3 py-2">
              <div className="text-lg font-bold text-[var(--color-primary)]">
                {formatScore(rec.relevance_score)}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--color-text-muted)] font-medium">Match</div>
            </div>
          </div>
        </div>

        {/* Why recommended */}
        <div className="mt-3 flex items-start gap-2 text-sm">
          <Info className="h-4 w-4 text-[var(--color-accent)] shrink-0 mt-0.5" />
          <div>
            <span className="font-medium text-[var(--color-text)]">Why recommended: </span>
            <span className="text-[var(--color-text-secondary)]">
              {rec.confidence.confidence_reason || 'Retrieved by the hybrid search pipeline.'}
            </span>
          </div>
        </div>

        {/* Compliance note */}
        {rec.confidence.compliance_display && (
          <div className="mt-2 flex items-start gap-2 text-xs text-[var(--color-text-muted)]">
            <ShieldCheck className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span>Compliance: <span className="text-[var(--color-text-secondary)]">{rec.confidence.compliance_display}</span> — verify against authoritative sources.</span>
          </div>
        )}

        {/* Phase 6: evidence strength + requirement coverage + contradictions */}
        {p6 && hasP6 && (
          <div className="mt-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-very-light-blue)]/60 p-3 space-y-2">
            {p6.evidence_strength && (
              <div className="flex items-center gap-2 text-xs">
                <span className="font-semibold text-[var(--color-text)]">Evidence strength:</span>
                <span className={`px-1.5 py-0.5 rounded text-[11px] font-medium border ${p6.evidence_strength === 'strong' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : p6.evidence_strength === 'moderate' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-50 text-slate-600 border-slate-200'}`}>{p6.evidence_strength}</span>
                {p6.requirement_coverage && (
                  <span className="ml-2 text-[11px] text-[var(--color-text-muted)]">Coverage {(p6.requirement_coverage.score * 100).toFixed(0)}% · {p6.requirement_coverage.matched.length} matched · {p6.requirement_coverage.unmatched.length} unmatched</span>
                )}
              </div>
            )}
            {p6.why_this_standard && p6.why_this_standard.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">Why this standard</div>
                <ul className="mt-1 space-y-0.5">
                  {p6.why_this_standard.map((r, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-[var(--color-text)]"><span className="text-emerald-600 mt-0.5">✓</span><span>{r}</span></li>
                  ))}
                </ul>
              </div>
            )}
            {p6.contradictions && p6.contradictions.length > 0 && (
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-wider text-amber-700">Mismatches detected</div>
                <ul className="mt-1 space-y-0.5">
                  {p6.contradictions.map((c, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-amber-800"><AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" /><span><span className="font-medium">{c.type}:</span> {c.reason} <span className="text-[10px] text-amber-700">({c.severity})</span></span></li>
                  ))}
                </ul>
              </div>
            )}
            {p6.confidence_reasons && p6.confidence_reasons.length > 0 && (
              <div className="text-[11px] text-[var(--color-text-muted)]">
                <span className="font-medium">Confidence:</span> {p6.confidence_reasons.join(' · ')}
              </div>
            )}
          </div>
        )}

        {/* Evidence count + retrieval methods */}
        <div className="mt-3 flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5" />
            {rec.evidence.length} evidence signal{rec.evidence.length !== 1 ? 's' : ''}
          </span>
          {rec.retrieval_methods.length > 0 && (
            <span className="flex items-center gap-1">
              <Search className="h-3.5 w-3.5" />
              {rec.retrieval_methods.join(' + ')}
            </span>
          )}
        </div>
      </div>

      {/* Expandable evidence panel */}
      {rec.evidence.length > 0 && (
        <div className="border-t border-[var(--color-border)]">
          <button
            className="w-full px-5 py-2.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-primary)] flex items-center gap-1.5 transition-colors font-medium"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            {expanded ? 'Hide evidence details' : 'View evidence details'}
          </button>
          {expanded && (
            <div className="px-5 pb-4 space-y-3 fade-in">
              {groupOrder.map((group) => {
                const items = grouped[group];
                if (!items || items.length === 0) return null;
                return (
                  <div key={group}>
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1.5">
                      {EVIDENCE_GROUPS[items[0].type]?.label || group}
                    </div>
                    <div className="space-y-1">
                      {items.map((ev, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs">
                          <span className={`mt-0.5 shrink-0 w-4 text-center ${
                            ev.strength === 'strong' ? 'text-[var(--color-success)] font-bold' :
                            ev.strength === 'moderate' ? 'text-[var(--color-text-secondary)]' :
                            'text-[var(--color-text-muted)]'
                          }`}>
                            {evidenceStrengthIcon(ev.strength)}
                          </span>
                          <span className="text-[var(--color-text)] leading-relaxed">{ev.text}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Action bar */}
      <div className="px-5 py-2.5 border-t border-[var(--color-border)] bg-[var(--color-very-light-blue)]/50 flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Link
            to={`/standards/${encodeURIComponent(std.standard_number)}`}
            className="btn btn-ghost !px-2.5 !py-1 text-xs font-medium"
          >
            View Standard <ArrowRight className="h-3 w-3 ml-0.5" />
          </Link>
          <Link
            to={`/compare?ids=${encodeURIComponent(std.standard_number)}`}
            className="btn btn-ghost !px-2.5 !py-1 text-xs font-medium"
          >
            <GitCompareArrows className="h-3 w-3 mr-0.5" /> Compare
          </Link>
        </div>
        <button
          className="btn btn-ghost !px-2.5 !py-1 text-xs font-medium"
          onClick={() => onSave(std)}
          aria-label={`Save ${std.standard_number}`}
        >
          <Bookmark className="h-3 w-3 mr-0.5" /> Save
        </button>
      </div>
    </article>
  );
}

// ─── Requirements Panel ──────────────────────────────────────────────────────

function RequirementsPanel({ result }: { result: AnalysisResponse }) {
  const requirements = result.requirements;
  const keywords = result.keywords;
  const categories = result.categories;
  const sr = result.structured_requirements;
  const inj = result.injection_check;

  return (
    <div className="panel bg-white border border-[var(--color-border)] rounded-2xl overflow-hidden shadow-sm">
      <div className="panel-header bg-[var(--color-very-light-blue)] border-b border-[var(--color-border)] px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold text-[var(--color-primary)] text-sm">
            <Brain className="h-4 w-4" />
            Detected Requirements
          </div>
          {result.dataset_version && (
            <span className="text-[11px] text-[var(--color-text-muted)]">Dataset {result.dataset_version}</span>
          )}
        </div>
      </div>
      <div className="p-4 space-y-4">
        {/* Injection warning — honest, non-blocking */}
        {inj?.injection_detected && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 flex items-start gap-2 text-xs text-amber-800">
            <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span>Potential prompt injection detected ({inj.threat_type}) — input was sanitized before analysis. Retrieval remains deterministic.</span>
          </div>
        )}
        {/* Structured requirements — deterministic */}
        {sr && (sr.product || sr.application || sr.domain) && (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">Structured interpretation</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {sr.product && <div><span className="font-medium text-[var(--color-text)]">Product:</span> <span className="text-[var(--color-text-secondary)]">{sr.product}</span></div>}
              {sr.application && <div><span className="font-medium text-[var(--color-text)]">Application:</span> <span className="text-[var(--color-text-secondary)]">{sr.application}</span></div>}
              {sr.domain && <div><span className="font-medium text-[var(--color-text)]">Domain:</span> <span className="text-[var(--color-text-secondary)]">{sr.domain}</span></div>}
              {sr.industry && <div><span className="font-medium text-[var(--color-text)]">Industry:</span> <span className="text-[var(--color-text-secondary)]">{sr.industry}</span></div>}
            </div>
            {(sr.materials?.length > 0 || sr.performance_requirements?.length > 0 || sr.environmental_conditions?.length > 0) && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {[...(sr.materials || []), ...(sr.performance_requirements || []), ...(sr.environmental_conditions || [])].slice(0, 8).map((t) => (
                  <span key={t} className="px-1.5 py-0.5 rounded bg-slate-100 text-[11px] text-slate-700 border border-slate-200">{t}</span>
                ))}
              </div>
            )}
          </div>
        )}
        {/* Extracted requirement sentences */}
        {requirements.length > 0 && (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">Extracted specification</div>
            <div className="space-y-1.5">
              {requirements.map((req, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-[var(--color-text)]">
                  <span className="text-[var(--color-primary)] mt-0.5 font-semibold">•</span>
                  <span>{typeof req === 'string' ? req : JSON.stringify(req)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Categories */}
        {categories.length > 0 && (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">Product / domain categories</div>
            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => (
                <span key={cat} className="badge badge-verified">{cat}</span>
              ))}
            </div>
          </div>
        )}

        {/* Keywords */}
        {keywords.length > 0 && (
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">Technical terms</div>
            <div className="flex flex-wrap gap-1.5">
              {keywords.map((kw) => (
                <span key={kw} className="px-2 py-0.5 rounded-full bg-[var(--color-light-blue)] text-[11px] font-medium text-[var(--color-primary-medium)] border border-[var(--color-border)]">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Compliance / lifecycle summaries — honest "Not available..." when missing */}
        {(result.compliance_summary || result.lifecycle_summary) && (
          <div className="pt-3 border-t border-[var(--color-border)] space-y-1.5 text-xs">
            {result.compliance_summary && (
              <div className="flex items-start gap-1.5 text-[var(--color-text-muted)]"><ShieldCheck className="h-3.5 w-3.5 mt-0.5 shrink-0" /><span><span className="font-medium text-[var(--color-text-secondary)]">Compliance:</span> {result.compliance_summary}</span></div>
            )}
            {result.lifecycle_summary && (
              <div className="flex items-start gap-1.5 text-[var(--color-text-muted)]"><Info className="h-3.5 w-3.5 mt-0.5 shrink-0" /><span><span className="font-medium text-[var(--color-text-secondary)]">Lifecycle:</span> {result.lifecycle_summary}</span></div>
            )}
          </div>
        )}

        {/* Retrieval stats + timing */}
        {result.retrieval && (
          <div className="pt-3 border-t border-[var(--color-border)]">
            <div className="text-[11px] text-[var(--color-text-muted)]">
              Corpus search: {result.retrieval.lexical_candidates} lexical candidates → {result.retrieval.fused_candidates} after fusion
              {result.retrieval.semantic_candidates > 0 && <> · {result.retrieval.semantic_candidates} semantic matches</>}
              {result.timing_ms?.total && <> · {(result.timing_ms.total).toFixed(0)} ms total</>}
              {result.phase6_enabled && <span className="ml-1 text-emerald-700 font-medium">· Phase 6 intelligence enabled</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export function AnalyzePage() {
  const [text, setText] = useState('');
  const [stage, setStage] = useState<Stage>('idle');
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(-1);
  const [fileName, setFileName] = useState<string | null>(null);
  const [savedConfirm, setSavedConfirm] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const runPipeline = async (input: string, uploaded?: File) => {
    if (!input.trim() && !uploaded) {
      setError('Please enter a procurement requirement or upload a document to proceed.');
      return;
    }
    if (!uploaded) {
      // A fresh text analysis must not reuse a previously uploaded document.
      setSelectedFile(null);
      setFileName(null);
    }
    setStage('processing');
    setError(null);
    setResult(null);
    setActiveStep(0);
    setSavedConfirm(null);
    // Animate pipeline steps
    const stepTimer = setInterval(() => {
      setActiveStep((prev) => {
        if (prev < PIPELINE_STEPS.length - 1) return prev + 1;
        return prev;
      });
    }, 500);

    try {
      let res: AnalysisResponse;
      if (uploaded) {
        res = await uploadDocument(uploaded);
      } else {
        res = await analyzeSpecification(input);
      }
      clearInterval(stepTimer);
      setActiveStep(PIPELINE_STEPS.length - 1);
      // Brief pause on last step before showing results
      setTimeout(() => {
        setResult(res);
        setStage('done');
      }, 300);
    } catch (e) {
      clearInterval(stepTimer);
      setError((e as Error).message || 'An unexpected error occurred. Please try again.');
      setStage('error');
    }
  };

  const handleAnalyze = () => {
    // Prefer pasted text; otherwise analyze the uploaded document.
    runPipeline(text, text.trim() ? undefined : selectedFile || undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleAnalyze();
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const allowed = ['.pdf', '.docx', '.txt'];
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowed.includes(ext)) {
      setError(`Unsupported file type: ${ext}. Allowed formats: PDF, DOCX, TXT.`);
      setStage('error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('File is too large. Maximum size is 10 MB.');
      setStage('error');
      return;
    }
    setSelectedFile(file);
    setFileName(file.name);
    runPipeline('', file);
    // Reset the input so re-uploading the same file still triggers onChange
    e.target.value = '';
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setFileName(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setError(null);
    setStage((prev) => (prev === 'error' ? 'idle' : prev));
  };

  const handleSave = async (standard: StandardSummary) => {
    try {
      await saveItem('standard', standard.standard_id, JSON.stringify({
        standard_number: standard.standard_number,
        title: standard.title,
      }), standard.standard_number);
      setSavedConfirm(standard.standard_number);
    } catch (e) {
      console.error('Failed to save:', e);
    }
  };

  const enhancedRecs = result?.recommendations_enhanced;
  const hasEnhanced = enhancedRecs && enhancedRecs.length > 0;
  const hasAnyRecs = hasEnhanced || (result?.recommendations && result.recommendations.length > 0);

  return (
    <div className="fade-in max-w-4xl">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[var(--color-primary)]">Analyze Specification</h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">
          Enter a procurement requirement to identify applicable BIS standards with evidence and confidence.
        </p>
      </div>

      {/* ─── Section A: Procurement specification input ─── */}
      <div className="panel bg-white border border-[var(--color-border)] rounded-2xl p-5 shadow-sm">
        <label htmlFor="spec-text" className="block text-sm font-medium text-[var(--color-text)] mb-2">
          Procurement requirement
        </label>
        <textarea
          id="spec-text"
          className="input min-h-[120px] bg-white border border-[var(--color-border)] text-[var(--color-text)] placeholder-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-accent)] focus:ring-[var(--color-accent)]/20 resize-y"
          placeholder="Describe your procurement need, or paste a tender specification..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={stage === 'processing'}
        />
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <button
            className="btn btn-ghost text-xs text-[var(--color-primary)]"
            onClick={() => setText(EXAMPLE_SPEC)}
            disabled={stage === 'processing'}
          >
            Use example specification
          </button>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={handleFileUpload}
              id="file-upload"
            />
            {fileName ? (
              <span className="flex items-center gap-1.5 max-w-[220px]">
                <span className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-light-blue)] px-2.5 py-1.5 text-xs font-medium text-[var(--color-primary)] truncate">
                  <FileText className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{fileName}</span>
                </span>
                <button
                  className="btn btn-ghost !px-1.5 !py-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-error)]"
                  onClick={handleClearFile}
                  disabled={stage === 'processing'}
                  aria-label="Clear selected file"
                  title="Clear selected file"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            ) : (
              <label
                htmlFor="file-upload"
                className={`btn btn-outline text-[var(--color-primary)] border-[var(--color-border)] hover:bg-[var(--color-light-blue)] ${stage === 'processing' ? 'opacity-50 pointer-events-none' : ''}`}
              >
                <Upload className="h-4 w-4" />
                Upload document
              </label>
            )}
            <button
              className="btn btn-primary"
              onClick={handleAnalyze}
              disabled={stage === 'processing' || (!text.trim() && !selectedFile)}
            >
              {stage === 'processing' ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              Analyze
            </button>
          </div>
        </div>
        <p className="mt-2 text-[11px] text-[var(--color-text-muted)]">
          Ctrl+Enter to analyze · Supports PDF, DOCX, TXT up to 10 MB
        </p>
      </div>

      {/* ─── Error state ─── */}
      {error && stage === 'error' && (
        <div className="mt-4 border border-red-200 bg-[var(--color-error-bg)] rounded-2xl p-4 flex items-start gap-3 fade-in">
          <AlertTriangle className="h-5 w-5 text-[var(--color-error)] shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-[var(--color-error)]">Analysis failed</p>
            <p className="text-sm text-[var(--color-error)]/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* ─── Section C: Processing pipeline ─── */}
      {stage === 'processing' && (
        <div className="mt-6 panel bg-white border border-[var(--color-border)] rounded-2xl p-5 shadow-sm fade-in">
          <div className="flex items-center gap-2 text-sm font-semibold text-[var(--color-primary)] mb-4">
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing specification
          </div>
          <ol className="space-y-2.5">
            {PIPELINE_STEPS.map(({ label, icon: Icon }, i) => {
              const state = i < activeStep ? 'done' : i === activeStep ? 'active' : 'pending';
              return (
                <li key={label} className="flex items-center gap-3 text-sm">
                  <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                    {state === 'done' ? (
                      <Check className="h-4 w-4 text-[var(--color-success)]" aria-hidden="true" />
                    ) : state === 'active' ? (
                      <Loader2 className="h-4 w-4 text-[var(--color-primary)] animate-spin" aria-hidden="true" />
                    ) : (
                      <Circle className="h-4 w-4 text-[var(--color-border)]" aria-hidden="true" />
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Icon className={`h-3.5 w-3.5 ${
                      state === 'active' ? 'text-[var(--color-primary)]' :
                      state === 'done' ? 'text-[var(--color-success)]' :
                      'text-[var(--color-text-muted)]'
                    }`} />
                    <span className={
                      state === 'active' ? 'text-[var(--color-text)] font-medium' :
                      state === 'done' ? 'text-[var(--color-text-secondary)]' :
                      'text-[var(--color-text-muted)]'
                    }>
                      {label}
                    </span>
                    {state === 'done' && (
                      <span className="text-[10px] text-[var(--color-success)]">done</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {/* ─── Results (Sections B-G) ─── */}
      {stage === 'done' && result && (
        <div className="mt-6 space-y-5 fade-in">
          {/* Save confirmation */}
          {savedConfirm && (
            <SaveConfirmation standard={savedConfirm} onDismiss={() => setSavedConfirm(null)} />
          )}

          {/* Section D: Detected requirements */}
          <RequirementsPanel result={result} />

          {/* Section E: Recommended standards */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-[var(--color-primary)]">
                Recommended Standards
              </h2>
              {(hasEnhanced) && (
                <span className="text-xs text-[var(--color-text-muted)]">
                  {enhancedRecs!.length} result{enhancedRecs!.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>

            {!hasAnyRecs && (
              <div className="panel bg-white border border-[var(--color-border)] rounded-2xl p-8 text-center">
                <Search className="h-8 w-8 text-[var(--color-border)] mx-auto mb-3" />
                <p className="text-[var(--color-text)] font-medium">No matching standards found</p>
                <p className="text-sm text-[var(--color-text-muted)] mt-1 max-w-md mx-auto">
                  The corpus did not contain a standard with sufficient evidence for this requirement.
                  Try broadening the specification or using more specific technical terms.
                </p>
              </div>
            )}

            {hasEnhanced && (() => {
              // Build Phase 6 lookup by standard_id for inline intelligence
              const p6ById = new Map<string, Record<string, unknown>>();
              for (const p of (result.phase6_recommendations || [])) {
                const sid = (p as unknown as { standard?: { standard_id: string } })?.standard?.standard_id
                  || (p as unknown as { standard_id: string })?.standard_id;
                if (sid) p6ById.set(sid, p as unknown as Record<string, unknown>);
              }
              return (
                <div className="space-y-4">
                  {enhancedRecs!.slice(0, 10).map((rec, i) => (
                    <EnhancedRecommendationCard
                      key={rec.standard.standard_id}
                      rec={rec}
                      rank={rec.rank || i + 1}
                      onSave={handleSave}
                      phase6={p6ById.get(rec.standard.standard_id) || null}
                    />
                  ))}
                </div>
              );
            })()}

            {/* Legacy fallback */}
            {!hasEnhanced && result.recommendations.length > 0 && (
              <div className="space-y-3">
                {result.recommendations.slice(0, 5).map((item: any, i: number) => (
                  <div key={item.standard_id || i} className="border border-[var(--color-border)] rounded-2xl bg-white p-4">
                    <div className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-7 h-7 rounded-full bg-[var(--color-primary)] text-white text-xs font-bold flex items-center justify-center">
                        {i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <Link
                          to={`/standards/${encodeURIComponent(item.standard_number)}`}
                          className="font-semibold text-[var(--color-primary)] hover:underline text-sm"
                        >
                          {item.standard_number}
                        </Link>
                        <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">{item.title}</p>
                      </div>
                      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-very-light-blue)] px-2.5 py-1.5 text-center flex-shrink-0">
                        <div className="text-sm font-bold text-[var(--color-primary)]">{formatScore(item.match_score)}</div>
                        <div className="text-[9px] uppercase text-[var(--color-text-muted)]">Match</div>
                      </div>
                    </div>
                    <div className="mt-2.5 flex items-center gap-2">
                      <Link
                        to={`/standards/${encodeURIComponent(item.standard_number)}`}
                        className="btn btn-ghost !px-2.5 !py-1 text-xs"
                      >
                        View Standard <ArrowRight className="h-3 w-3 ml-0.5" />
                      </Link>
                      <Link
                        to={`/compare?ids=${encodeURIComponent(item.standard_number)}`}
                        className="btn btn-ghost !px-2.5 !py-1 text-xs"
                      >
                        <GitCompareArrows className="h-3 w-3 mr-0.5" /> Compare
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section F: Provenance disclaimer */}
          <div className="panel bg-[var(--color-very-light-blue)] border border-[var(--color-border)] rounded-2xl p-4">
            <div className="flex items-start gap-2 text-xs text-[var(--color-text-muted)]">
              <ShieldCheck className="h-4 w-4 shrink-0 mt-0.5 text-[var(--color-primary)]" />
              <div>
                <span className="font-medium text-[var(--color-text-secondary)]">Data provenance and compliance: </span>
                SpecMatch uses the BIS corpus with explicit provenance labeling. Scores reflect retrieval relevance, not
                regulatory applicability. Always verify compliance requirements against authoritative BIS publications,
                QCOs, and certification mandates before procurement decisions.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── Idle state ─── */}
      {stage === 'idle' && (
        <div className="mt-6 panel border border-dashed border-[var(--color-border)] rounded-2xl p-8 text-center">
          <FileSearch className="h-10 w-10 text-[var(--color-border)] mx-auto mb-3" />
          <p className="text-sm font-medium text-[var(--color-text-secondary)]">
            Enter a procurement specification above to identify relevant BIS standards.
          </p>
          <p className="text-xs text-[var(--color-text-muted)] mt-1 max-w-lg mx-auto">
            The system will extract requirements, search the standards corpus, and return ranked
            recommendations with evidence and confidence assessment.
          </p>
          <div className="mt-4 flex items-center justify-center gap-4 text-xs text-[var(--color-text-muted)]">
            <span className="flex items-center gap-1"><FileText className="h-3.5 w-3.5" /> Text input</span>
            <span className="flex items-center gap-1"><Upload className="h-3.5 w-3.5" /> File upload</span>
            <span className="flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" /> Evidence-based</span>
          </div>
        </div>
      )}
    </div>
  );
}
