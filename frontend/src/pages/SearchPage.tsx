// Search page — real search with filters

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SlidersHorizontal, X } from 'lucide-react';
import { SearchInput } from '../components/SearchInput';
import { StandardCard } from '../components/StandardCard';
import { searchStandards, getFilterOptions, saveItem } from '../services/api';
import type { SearchResponse, FilterOptions, StandardSummary } from '../types';

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Selected filters
  const [sector, setSector] = useState(searchParams.get('sector') || '');
  const [typeOfStandard, setTypeOfStandard] = useState(searchParams.get('type_of_standard') || '');
  const [yearFrom, setYearFrom] = useState(searchParams.get('year_from') || '');
  const [yearTo, setYearTo] = useState(searchParams.get('year_to') || '');
  const [family, setFamily] = useState(searchParams.get('standard_family') || '');
  const [page, setPage] = useState(Number(searchParams.get('page')) || 1);

  useEffect(() => {
    getFilterOptions().then(setFilters).catch(() => {});
  }, []);

  const runSearch = useCallback(async (searchQuery: string, filters: Record<string, string>, pageNum: number) => {
    if (!searchQuery.trim()) {
      setResults(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await searchStandards({
        q: searchQuery,
        page: pageNum,
        page_size: 10,
        sector: filters.sector || undefined,
        type_of_standard: filters.type || undefined,
        year_from: filters.yearFrom ? Number(filters.yearFrom) : undefined,
        year_to: filters.yearTo ? Number(filters.yearTo) : undefined,
        standard_family: filters.family || undefined,
      });
      setResults(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load from URL params
  useEffect(() => {
    if (initialQuery) {
      runSearch(initialQuery, {
        sector,
        type: typeOfStandard,
        yearFrom,
        yearTo,
        family,
      }, page);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyFilters = () => {
    const params: Record<string, string> = {};
    if (query) params.q = query;
    if (sector) params.sector = sector;
    if (typeOfStandard) params.type_of_standard = typeOfStandard;
    if (yearFrom) params.year_from = yearFrom;
    if (yearTo) params.year_to = yearTo;
    if (family) params.standard_family = family;
    setSearchParams(params);
    setPage(1);
    runSearch(query, { sector, type: typeOfStandard, yearFrom, yearTo, family }, 1);
  };

  const clearFilters = () => {
    setSector('');
    setTypeOfStandard('');
    setYearFrom('');
    setYearTo('');
    setFamily('');
    setPage(1);
    if (query) {
      setSearchParams({ q: query });
      runSearch(query, {}, 1);
    }
  };

  const handleSave = async (standard: StandardSummary) => {
    try {
      await saveItem('standard', standard.standard_id, JSON.stringify({
        standard_number: standard.standard_number,
        title: standard.title,
      }), standard.standard_number);
    } catch (e) {
      console.error('Failed to save:', e);
    }
  };

  const goToPage = (p: number) => {
    setPage(p);
    runSearch(query, { sector, type: typeOfStandard, yearFrom, yearTo, family }, p);
  };

  const hasActiveFilters = sector || typeOfStandard || yearFrom || yearTo || family;

  return (
    <div className="fade-in">
      <div className="max-w-3xl">
        <h1 className="text-xl font-semibold text-[var(--color-primary)] mb-4">Search Standards</h1>
        <SearchInput
          defaultValue={query}
          onSearch={(q) => {
            setQuery(q);
            setSearchParams({ q });
            setPage(1);
            runSearch(q, { sector, type: typeOfStandard, yearFrom, yearTo, family }, 1);
          }}
        />
      </div>

      {/* Filter bar */}
      {filters && (
        <div className="mt-4">
          <button
            className="btn btn-outline text-sm"
            onClick={() => setShowFilters(!showFilters)}
            aria-expanded={showFilters}
          >
            <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
            Filters
            {hasActiveFilters && (
              <span className="badge badge-verified ml-1">Active</span>
            )}
          </button>

          {showFilters && (
            <div className="mt-3 panel p-4 bg-white border border-[var(--color-border)] rounded-xl">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1" htmlFor="f-sector">Sector</label>
                  <select id="f-sector" className="input !py-1.5 text-sm" value={sector} onChange={(e) => setSector(e.target.value)}>
                    <option value="">Any</option>
                    {filters.sectors.map((s) => (
                      <option key={s.value} value={s.value}>{s.value} ({s.count})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1" htmlFor="f-type">Type</label>
                  <select id="f-type" className="input !py-1.5 text-sm" value={typeOfStandard} onChange={(e) => setTypeOfStandard(e.target.value)}>
                    <option value="">Any</option>
                    {filters.types.map((t) => (
                      <option key={t.value} value={t.value}>{t.value} ({t.count})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1" htmlFor="f-year-from">Year from</label>
                  <select id="f-year-from" className="input !py-1.5 text-sm" value={yearFrom} onChange={(e) => setYearFrom(e.target.value)}>
                    <option value="">Any</option>
                    {filters.years.map((y) => (
                      <option key={y.value} value={y.value}>{y.value}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1" htmlFor="f-year-to">Year to</label>
                  <select id="f-year-to" className="input !py-1.5 text-sm" value={yearTo} onChange={(e) => setYearTo(e.target.value)}>
                    <option value="">Any</option>
                    {filters.years.map((y) => (
                      <option key={y.value} value={y.value}>{y.value}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1" htmlFor="f-family">Family</label>
                  <select id="f-family" className="input !py-1.5 text-sm" value={family} onChange={(e) => setFamily(e.target.value)}>
                    <option value="">Any</option>
                    {filters.families.slice(0, 30).map((f) => (
                      <option key={f.value} value={f.value}>{f.value}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="mt-3 flex items-center gap-2">
                <button className="btn btn-primary text-sm" onClick={applyFilters}>Apply Filters</button>
                <button className="btn btn-ghost text-sm text-[var(--color-text-secondary)]" onClick={clearFilters}>
                  <X className="h-3.5 w-3.5" /> Clear
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Results */}
      <div className="mt-6">
        {error && (
          <div className="border border-red-200 bg-[var(--color-error-bg)] rounded-md p-4 text-sm text-[var(--color-error)]">
            {error}
          </div>
        )}

        {loading && (
          <div className="space-y-3">
            <div className="skeleton h-28" />
            <div className="skeleton h-28" />
            <div className="skeleton h-28" />
          </div>
        )}

        {!loading && !error && results && (
          <div>
            <div className="text-sm text-[var(--color-text-muted)] mb-4">
              {results.pagination.total.toLocaleString()} result{results.pagination.total === 1 ? '' : 's'} for "{results.query}"
            </div>

            {results.items.length === 0 ? (
              <div className="border border-[var(--color-border)] rounded-md p-8 text-center bg-white">
                <p className="text-[var(--color-text)] font-medium">No standards were found with sufficient evidence for this requirement.</p>
                <div className="mt-4 flex flex-col items-center gap-2 text-sm text-[var(--color-text-muted)]">
                  <span>Try:</span>
                  <ul className="text-left space-y-1">
                    <li>• Broadening your search terms</li>
                    <li>• Using a product category or technical term</li>
                    <li>• Removing active filters</li>
                  </ul>
                </div>
                <button className="btn btn-outline mt-4 text-sm" onClick={clearFilters}>Clear Filters</button>
              </div>
            ) : (
              <div className="space-y-3">
                {results.items.map((item) => (
                  <StandardCard
                    key={item.standard_id}
                    standard={item}
                    rank={undefined}
                    onSave={handleSave}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {results.pagination.total_pages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-2">
                <button
                  className="btn btn-outline text-sm"
                  disabled={page <= 1}
                  onClick={() => goToPage(page - 1)}
                >
                  Previous
                </button>
                <span className="text-sm text-[var(--color-text-muted)]">
                  Page {page} of {results.pagination.total_pages}
                </span>
                <button
                  className="btn btn-outline text-sm"
                  disabled={page >= results.pagination.total_pages}
                  onClick={() => goToPage(page + 1)}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        )}

        {!loading && !error && !results && (
          <div className="border border-[var(--color-border)] rounded-md p-8 text-center bg-white text-[var(--color-text-muted)]">
            Enter a query above to search the standards corpus.
          </div>
        )}
      </div>
    </div>
  );
}
