// Standards directory — browsable, paginated table

import { useEffect, useState, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { getStandards, getFilterOptions } from '../services/api';
import { formatStatus } from '../lib/utils';
import type { StandardSummary, StandardListResponse, FilterOptions } from '../types';

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: 'standard_number', label: 'Standard Number' },
  { value: 'title', label: 'Title' },
  { value: 'publication_year', label: 'Publication Year' },
  { value: 'type_of_standard', label: 'Type' },
];

export function StandardsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<StandardListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterOptions | null>(null);

  const [page, setPage] = useState(Number(searchParams.get('page')) || 1);
  const [sector, setSector] = useState(searchParams.get('sector') || '');
  const [typeOfStandard, setTypeOfStandard] = useState(searchParams.get('type_of_standard') || '');
  const [sortBy, setSortBy] = useState(searchParams.get('sort_by') || 'standard_number');
  const [sortDir, setSortDir] = useState(searchParams.get('sort_dir') || 'asc');

  useEffect(() => {
    getFilterOptions().then(setFilters).catch(() => {});
  }, []);

  const loadData = useCallback(async (
    p: number,
    s: string,
    t: string,
    sort: string,
    dir: string,
  ) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getStandards({
        page: p,
        page_size: 25,
        sector: s || undefined,
        type_of_standard: t || undefined,
        sort_by: sort,
        sort_dir: dir,
      });
      setData(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(page, sector, typeOfStandard, sortBy, sortDir);
  }, [page, sector, typeOfStandard, sortBy, sortDir, loadData]);

  const updateUrl = (p: number, s: string, t: string, sort: string, dir: string) => {
    const params: Record<string, string> = {};
    if (p > 1) params.page = String(p);
    if (s) params.sector = s;
    if (t) params.type_of_standard = t;
    if (sort !== 'standard_number') params.sort_by = sort;
    if (dir !== 'asc') params.sort_dir = dir;
    setSearchParams(params);
  };

  const handleFilterChange = (newSector: string, newType: string) => {
    setSector(newSector);
    setTypeOfStandard(newType);
    setPage(1);
    updateUrl(1, newSector, newType, sortBy, sortDir);
  };

  const toggleSort = (field: string) => {
    const newDir = sortBy === field && sortDir === 'asc' ? 'desc' : 'asc';
    setSortBy(field);
    setSortDir(newDir);
    setPage(1);
    updateUrl(1, sector, typeOfStandard, field, newDir);
  };

  const goToPage = (p: number) => {
    setPage(p);
    updateUrl(p, sector, typeOfStandard, sortBy, sortDir);
  };

  return (
    <div className="fade-in">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-primary)]">Standards Directory</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-0.5">
            {data ? `${data.pagination.total.toLocaleString()} published standards` : 'Loading corpus...'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-[var(--color-text-muted)]" htmlFor="sort-by">Sort</label>
          <select
            id="sort-by"
            className="input !py-1 !px-2 text-sm w-auto"
            value={sortBy}
            onChange={(e) => toggleSort(e.target.value)}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label} {sortBy === o.value ? (sortDir === 'asc' ? '↑' : '↓') : ''}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Filters */}
      {filters && (
        <div className="flex flex-wrap gap-3 mb-4">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[var(--color-text-muted)]" htmlFor="dir-sector">Sector</label>
            <select
              id="dir-sector"
              className="input !py-1 !px-2 text-sm w-48"
              value={sector}
              onChange={(e) => handleFilterChange(e.target.value, typeOfStandard)}
            >
              <option value="">All sectors</option>
              {filters.sectors.map((s) => (
                <option key={s.value} value={s.value}>{s.value} ({s.count})</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[var(--color-text-muted)]" htmlFor="dir-type">Type</label>
            <select
              id="dir-type"
              className="input !py-1 !px-2 text-sm w-48"
              value={typeOfStandard}
              onChange={(e) => handleFilterChange(sector, e.target.value)}
            >
              <option value="">All types</option>
              {filters.types.map((t) => (
                <option key={t.value} value={t.value}>{t.value} ({t.count})</option>
              ))}
            </select>
          </div>
          {(sector || typeOfStandard) && (
            <div className="flex items-end">
              <button className="btn btn-ghost text-xs" onClick={() => handleFilterChange('', '')}>
                Clear filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="border border-red-200 bg-[var(--color-error-bg)] rounded-md p-4 text-sm text-[var(--color-error)]">{error}</div>
      )}

      {/* Table */}
      <div className="panel overflow-hidden bg-white">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Standard Number</th>
                <th>Title</th>
                <th>Type</th>
                <th>Year</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    <td><div className="skeleton h-4 w-24" /></td>
                    <td><div className="skeleton h-4 w-64" /></td>
                    <td><div className="skeleton h-4 w-20" /></td>
                    <td><div className="skeleton h-4 w-12" /></td>
                    <td><div className="skeleton h-4 w-16" /></td>
                  </tr>
                ))
              ) : (
                data?.items.map((s: StandardSummary) => (
                  <tr key={s.standard_id}>
                    <td>
                      <Link
                        to={`/standards/${encodeURIComponent(s.standard_number)}`}
                        className="text-[var(--color-primary)] font-medium hover:underline whitespace-nowrap"
                      >
                        {s.standard_number}
                      </Link>
                    </td>
                    <td className="max-w-md">
                      <div className="line-clamp-2 text-[var(--color-text)]">{s.title}</div>
                    </td>
                    <td className="whitespace-nowrap text-[var(--color-text-secondary)]">{s.type_of_standard || '—'}</td>
                    <td className="whitespace-nowrap text-[var(--color-text-secondary)]">{s.publication_year || '—'}</td>
                    <td className="whitespace-nowrap">
                      <span className={formatStatus(s.current_status).className}>
                        {formatStatus(s.current_status).label}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && data && data.pagination.total_pages > 1 && (
          <div className="px-4 py-3 border-t border-[var(--color-border)] flex items-center justify-between text-sm">
            <span className="text-[var(--color-text-muted)]">
              Showing {(page - 1) * data.pagination.page_size + 1}–
              {Math.min(page * data.pagination.page_size, data.pagination.total)} of {data.pagination.total.toLocaleString()}
            </span>
            <div className="flex items-center gap-2">
              <button
                className="btn btn-outline !py-1 text-xs"
                disabled={page <= 1}
                onClick={() => goToPage(page - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              <span className="text-[var(--color-text-secondary)]">Page {page} of {data.pagination.total_pages}</span>
              <button
                className="btn btn-outline !py-1 text-xs"
                disabled={page >= data.pagination.total_pages}
                onClick={() => goToPage(page + 1)}
                aria-label="Next page"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
