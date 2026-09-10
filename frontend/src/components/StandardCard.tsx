// Standard card — used in search results and recommendations

import { Link } from 'react-router-dom';
import { ArrowRight, Bookmark, GitCompareArrows } from 'lucide-react';
import type { SearchResultItem, StandardSummary } from '../types';
import {
  confidenceLevel,
  formatProvenance,
  formatScore,
  formatStatus,
} from '../lib/utils';

interface StandardCardProps {
  standard: SearchResultItem | StandardSummary;
  rank?: number;
  showScore?: boolean;
  onSave?: (standard: StandardSummary) => void;
}

export function StandardCard({ standard, rank, showScore = true, onSave }: StandardCardProps) {
  const isSearchItem = 'match_score' in standard;
  const score = isSearchItem ? (standard as SearchResultItem).match_score : 0.5;
  const matchingTerms = isSearchItem ? (standard as SearchResultItem).matching_terms ?? [] : [];
  const snippet = isSearchItem ? (standard as SearchResultItem).snippet : undefined;
  const conf = confidenceLevel(score);
  const prov = formatProvenance(standard.validation_status);

  return (
    <article className="group fade-in overflow-hidden rounded-2xl border border-[var(--color-border)] bg-white shadow-sm transition-all duration-200 hover:border-[var(--color-primary)]/30 hover:shadow-md">
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            {rank !== undefined && (
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-light-blue)] text-[11px] font-bold text-[var(--color-primary)]">
                {rank}
              </span>
            )}
            <Link
              to={`/standards/${encodeURIComponent(standard.standard_number)}`}
              className="truncate text-sm font-semibold text-[var(--color-primary)] hover:text-[var(--color-primary-medium)] hover:underline"
            >
              {standard.standard_number}
            </Link>
          </div>
          {showScore && isSearchItem && (
            <span className="badge bg-[var(--color-success-bg)] text-[var(--color-success)] border border-[#BBF7D0] shrink-0">Match: {formatScore(score)}</span>
          )}
        </div>

        <p className="mt-2 text-sm font-medium leading-snug text-[var(--color-text)]">
          {standard.title}
        </p>

        {snippet && (
          <p
            className="mt-2 text-xs leading-relaxed text-[var(--color-text-secondary)]"
            dangerouslySetInnerHTML={{ __html: snippet }}
          />
        )}

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {standard.type_of_standard && (
            <span className="badge badge-muted">{standard.type_of_standard}</span>
          )}
          {standard.publication_year && (
            <span className="badge badge-muted">{standard.publication_year}</span>
          )}
          <span className={formatStatus(standard.current_status).className}>
            {formatStatus(standard.current_status).label}
          </span>
          <span className={prov.className}>{prov.label}</span>
        </div>

        {matchingTerms.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--color-text-muted)]">Matched</span>
            {matchingTerms.map((term) => (
              <span
                key={term}
                className="rounded-full border border-[var(--color-border)] bg-[var(--color-very-light-blue)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-text-secondary)]"
              >
                {term}
              </span>
            ))}
          </div>
        )}

        {isSearchItem && (
          <div className="mt-3">
            <span className={conf.className}>{conf.label}</span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-[var(--color-border)] bg-[var(--color-very-light-blue)] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Link
            to={`/standards/${encodeURIComponent(standard.standard_number)}`}
            className="btn btn-ghost !px-2 !py-1 text-xs"
          >
            View Standard <ArrowRight className="h-3 w-3" />
          </Link>
          <Link
            to={`/compare?ids=${encodeURIComponent(standard.standard_number)}`}
            className="btn btn-ghost !px-2 !py-1 text-xs"
          >
            <GitCompareArrows className="h-3 w-3" /> Compare
          </Link>
        </div>
        {onSave && (
          <button
            className="btn btn-ghost !px-2 !py-1 text-xs"
            onClick={() => onSave(standard)}
            aria-label={`Save ${standard.standard_number}`}
          >
            <Bookmark className="h-3 w-3" /> Save
          </button>
        )}
      </div>
    </article>
  );
}
