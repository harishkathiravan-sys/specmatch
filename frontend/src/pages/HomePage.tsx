// Home page — search-first, real data

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, FileSearch, Search, ShieldCheck, FileText, TrendingUp } from 'lucide-react';
import { SearchInput } from '../components/SearchInput';
import { StandardCard } from '../components/StandardCard';
import { getDatasetStats, searchStandards } from '../services/api';
import type { DatasetStats, SearchResultItem } from '../types';

export function HomePage() {
  const [stats, setStats] = useState<DatasetStats | null>(null);
  const [demoResults, setDemoResults] = useState<SearchResultItem[] | null>(null);
  const [demoLoading, setDemoLoading] = useState(true);
  const [demoError, setDemoError] = useState<string | null>(null);

  useEffect(() => {
    getDatasetStats().then(setStats).catch(() => {});
    searchStandards({ q: 'aircraft woven carpet', page_size: 3 })
      .then((res) => setDemoResults(res.items))
      .catch((e) => setDemoError(e.message))
      .finally(() => setDemoLoading(false));
  }, []);

  return (
    <div className="fade-in space-y-8 text-[var(--color-text)]">
      <section className="relative overflow-hidden rounded-[20px] border border-[var(--color-border)] bg-white px-5 py-8 sm:px-8 md:px-10 md:py-12 shadow-sm">
        <div className="relative">
          <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-light-blue)] px-3 py-1 text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--color-primary-medium)]">
            Procurement standards intelligence
          </div>

          <h1 className="mt-5 max-w-3xl text-3xl font-semibold tracking-tight text-[var(--color-primary)] md:text-5xl">
            Find the right Indian Standards for complex sourcing decisions.
          </h1>

          <p className="mt-4 max-w-2xl text-sm text-[var(--color-text-secondary)] md:text-base">
            Search the BIS corpus, analyze tender requirements, and understand exactly why a standard is recommended.
          </p>

          <div className="mt-8 max-w-3xl">
            <SearchInput variant="hero" autoFocus />
            <p className="mt-3 text-xs text-[var(--color-text-muted)]">
              Example: “Textile floor coverings — Aircraft Woven Carpet” or “IS 19763”
            </p>
          </div>

          <div className="mt-8 flex flex-col sm:flex-row items-start gap-3">
            <Link to="/analyze" className="btn btn-primary text-base px-6 py-3 shadow-md">
              <FileSearch className="h-5 w-5" aria-hidden="true" />
              Analyze a Specification
            </Link>
            <Link to="/standards" className="btn btn-secondary border-[var(--color-border)] text-[var(--color-primary)] hover:bg-[var(--color-light-blue)] px-5 py-3">
              <Search className="h-4 w-4" aria-hidden="true" />
              Browse Standards
            </Link>
          </div>
        </div>
      </section>

      {stats && (
        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-[var(--color-border)] bg-white p-5 shadow-sm">
            <div className="text-2xl font-semibold text-[var(--color-primary)]">{stats.total_standards.toLocaleString()}</div>
            <div className="mt-1 text-xs text-[var(--color-text-secondary)]">Published standards</div>
          </div>
          <div className="rounded-2xl border border-[var(--color-border)] bg-white p-5 shadow-sm">
            <div className="text-2xl font-semibold text-[var(--color-primary)]">{stats.unique_families.toLocaleString()}</div>
            <div className="mt-1 text-xs text-[var(--color-text-secondary)]">Standard families</div>
          </div>
          <div className="rounded-2xl border border-[var(--color-border)] bg-white p-5 shadow-sm">
            <div className="text-2xl font-semibold text-[var(--color-primary)]">{stats.year_range ? `${stats.year_range.min}–${stats.year_range.max}` : '—'}</div>
            <div className="mt-1 text-xs text-[var(--color-text-secondary)]">Publication range</div>
          </div>
          <div className="rounded-2xl border border-[var(--color-border)] bg-white p-5 shadow-sm">
            <div className="text-2xl font-semibold text-[var(--color-primary)]">{stats.types_distribution.length}</div>
            <div className="mt-1 text-xs text-[var(--color-text-secondary)]">Standard types</div>
          </div>
        </section>
      )}

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4">
          <div className="rounded-2xl border border-[var(--color-border)] bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2 text-base font-semibold text-[var(--color-primary)]">
              <TrendingUp className="h-4 w-4 text-[var(--color-primary-medium)]" />
              Analysis workflow
            </div>
            <ol className="space-y-3 text-sm text-[var(--color-text-secondary)]">
              {[
                ['Procurement requirement', 'Describe your need or upload a tender document.'],
                ['Detected requirements', 'The system extracts the product, technical terms, and constraints.'],
                ['Top standards', 'Relevant standards are retrieved and ranked against the live BIS corpus.'],
                ['Evidence', 'Each recommendation explains the match and source provenance.'],
              ].map(([title, desc], i) => (
                <li key={title} className="flex gap-3">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary)] text-[11px] font-semibold text-white">
                    {i + 1}
                  </span>
                  <div>
                    <div className="font-medium text-[var(--color-text)]">{title}</div>
                    <div className="mt-0.5 text-xs text-[var(--color-text-muted)]">{desc}</div>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-800">
            <div className="mb-1 flex items-center gap-2 font-semibold text-amber-700">
              <ShieldCheck className="h-4 w-4" />
              Data integrity
            </div>
            SpecMatch uses the BIS corpus with explicit provenance and verification cues. When compliance data is not yet authoritatively loaded, it is clearly labeled rather than assumed.
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--color-border)] bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-[var(--color-primary)]">Live example from the corpus</h2>
            <Link to="/analyze" className="inline-flex items-center gap-1 text-xs text-[var(--color-accent)] hover:text-[var(--color-primary-medium)]">
              Try the full analysis <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {demoLoading ? (
            <div className="space-y-3">
              <div className="skeleton h-28" />
              <div className="skeleton h-28" />
            </div>
          ) : demoError ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-4 text-sm text-red-800">
              Could not load example: {demoError}
            </div>
          ) : (
            <div className="space-y-3">
              {demoResults?.map((item, i) => (
                <StandardCard key={item.standard_id} standard={item} rank={i + 1} />
              ))}
              {(!demoResults || demoResults.length === 0) && (
                <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-very-light-blue)] p-4 text-sm text-[var(--color-text-muted)]">
                  No example standards found.
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          { icon: FileText, title: 'Spec analysis', text: 'Turn tender text into a precise shortlist of relevant BIS standards.' },
          { icon: Search, title: 'Hybrid retrieval', text: 'Combine lexical recall with semantic ranking for better coverage and precision.' },
          { icon: ShieldCheck, title: 'Evidence-first', text: 'Each result explains the match and keeps provenance visible to buyers and teams.' },
        ].map(({ icon: Icon, title, text }) => (
          <div key={title} className="rounded-2xl border border-[var(--color-border)] bg-white p-5 shadow-sm">
            <div className="mb-3 inline-flex rounded-xl bg-[var(--color-light-blue)] p-2 text-[var(--color-primary-medium)]">
              <Icon className="h-4 w-4" />
            </div>
            <h3 className="text-base font-semibold text-[var(--color-primary)]">{title}</h3>
            <p className="mt-2 text-sm text-[var(--color-text-secondary)]">{text}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
