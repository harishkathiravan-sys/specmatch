// Methodology & About page — architecture, provenance, data policy

import { ShieldCheck, Database, Layers, AlertTriangle } from 'lucide-react';

export function MethodologyPage() {
  return (
    <div className="fade-in max-w-4xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-primary)]">Methodology & Architecture</h1>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">
          SpecMatch architecture, retrieval pipeline, confidence modeling, and data integrity policy.
        </p>
      </div>

      {/* Overview */}
      <section className="panel bg-white p-6">
        <div className="flex items-center gap-2.5 text-base font-semibold text-[var(--color-primary)] mb-3">
          <Database className="h-5 w-5 text-[var(--color-primary)]" />
          What is SpecMatch?
        </div>
        <p className="text-sm text-[var(--color-text)] leading-relaxed">
          <strong>SpecMatch</strong> is a procurement standards decision-support platform designed to accurately match
          procurement specifications and tender requirements against the <strong>Bureau of Indian Standards (BIS)</strong> corpus.
          Instead of treating standard recommendation as a generic text-generation problem, SpecMatch combines deterministic
          identifier resolution, lexical indexing, semantic retrieval, and explicit evidence extraction.
        </p>
      </section>

      {/* Architecture & Pipeline */}
      <section className="panel bg-white p-6">
        <div className="flex items-center gap-2.5 text-base font-semibold text-[var(--color-primary)] mb-4">
          <Layers className="h-5 w-5 text-[var(--color-primary)]" />
          Retrieval & Recommendation Pipeline
        </div>
        
        <div className="space-y-4">
          <div className="border-l-2 border-[var(--color-primary)] pl-4 py-1">
            <h4 className="font-semibold text-sm text-[var(--color-primary)]">1. Requirement Ingestion & Normalization</h4>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Specifications are parsed, decomposed into distinct functional statements, and stripped of tender boilerplate.
              Technical product entities and constraint phrases are extracted.
            </p>
          </div>

          <div className="border-l-2 border-[var(--color-primary)] pl-4 py-1">
            <h4 className="font-semibold text-sm text-[var(--color-primary)]">2. Hybrid Retrieval (Lexical + Full-Text FTS5)</h4>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Queries are evaluated against SQLite FTS5 / BM25 indexes covering standard identifiers, titles, normalized keywords,
              and inferred subject classifications across 24,132 published standards.
            </p>
          </div>

          <div className="border-l-2 border-[var(--color-primary)] pl-4 py-1">
            <h4 className="font-semibold text-sm text-[var(--color-primary)]">3. Candidate Scoring & Term Matching</h4>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Candidate standards are scored via term matching, title overlap, and token coverage. Ranks reflect concrete
              lexical and semantic signals rather than opaque generative probabilities.
            </p>
          </div>

          <div className="border-l-2 border-[var(--color-primary)] pl-4 py-1">
            <h4 className="font-semibold text-sm text-[var(--color-primary)]">4. Transparent Evidence Assembly</h4>
            <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
              Every recommended standard includes the specific terms matched, standard family relationships, and source provenance.
            </p>
          </div>
        </div>
      </section>

      {/* Data Integrity & Provenance Policy */}
      <section className="panel bg-white p-6">
        <div className="flex items-center gap-2.5 text-base font-semibold text-[var(--color-primary)] mb-3">
          <ShieldCheck className="h-5 w-5 text-[var(--color-primary)]" />
          Strict Data Integrity & Provenance Rules
        </div>
        <p className="text-sm text-[var(--color-text)] leading-relaxed mb-4">
          To maintain trust with engineering and procurement teams, SpecMatch strictly differentiates between official
          source data, derived metadata, and unvalidated placeholders:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-[var(--color-very-light-blue)] border border-[var(--color-border)] rounded">
            <span className="badge badge-verified mb-1">Source-Derived</span>
            <p className="text-[var(--color-text-secondary)] mt-1">
              Standard numbers, official titles, publication dates, and publication status originating from the BIS inventory.
            </p>
          </div>

          <div className="p-3 bg-[var(--color-very-light-blue)] border border-[var(--color-border)] rounded">
            <span className="badge badge-warning mb-1">Inferred / Derived</span>
            <p className="text-[var(--color-text-secondary)] mt-1">
              Standard families, keywords, and subject matter classifications produced by deterministic parsing algorithms.
            </p>
          </div>

          <div className="p-3 bg-[var(--color-very-light-blue)] border border-[var(--color-border)] rounded">
            <span className="badge badge-muted mb-1">Synthetic Data</span>
            <p className="text-[var(--color-text-secondary)] mt-1">
              Synthetic benchmark queries, tender templates, and training pairs used for system evaluation.
            </p>
          </div>

          <div className="p-3 bg-[var(--color-very-light-blue)] border border-[var(--color-border)] rounded">
            <span className="badge badge-error mb-1">Needs Authoritative Enrichment</span>
            <p className="text-[var(--color-text-secondary)] mt-1">
              Quality Control Orders (QCOs), certification schemes, and amendments not yet loaded from official government gazettes.
            </p>
          </div>
        </div>
      </section>

      {/* Compliance Disclaimer */}
      <section className="panel p-6 border-amber-300 bg-amber-50/40" id="limitations">
        <div className="flex items-center gap-2 text-amber-900 font-semibold text-sm mb-2">
          <AlertTriangle className="h-4 w-4 text-amber-700" />
          Compliance & Legal Disclaimer
        </div>
        <p className="text-xs text-amber-900/80 leading-relaxed">
          SpecMatch is a standards discovery and procurement decision-support system. Recommendations should always be
          reviewed against authoritative Bureau of Indian Standards (BIS) publications, applicable government notifications,
          Quality Control Orders (QCOs), and certification mandates before making procurement or contractual commitments.
          SpecMatch does not claim official BIS endorsement.
        </p>
      </section>
    </div>
  );
}
