// History page — search and analysis history

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { History, Search, ArrowRight } from 'lucide-react';
import { getHistory } from '../services/api';

interface HistoryItem {
  id: number;
  query: string;
  search_type: string;
  results_count: number;
  created_at: string;
}

export function HistoryPage() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getHistory(50)
      .then((data) => {
        setHistory(data);
        setError(null);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="fade-in max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-primary)]">Search History</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            Past queries, specification searches, and matching runs.
          </p>
        </div>
      </div>

      {error && (
        <div className="border border-red-200 bg-[var(--color-error-bg)] rounded-md p-4 text-sm text-[var(--color-error)] mb-6">
          {error}
        </div>
      )}

      {loading && (
        <div className="space-y-3">
          <div className="skeleton h-16 w-full" />
          <div className="skeleton h-16 w-full" />
          <div className="skeleton h-16 w-full" />
        </div>
      )}

      {!loading && history.length === 0 && (
        <div className="panel bg-white p-10 text-center text-[var(--color-text-muted)]">
          <History className="h-8 w-8 mx-auto text-[var(--color-border)] mb-2" />
          <p className="font-medium text-[var(--color-text)]">No search history yet.</p>
          <p className="text-sm mt-1 text-[var(--color-text-muted)]">
            Searches and specification analyses will automatically appear here.
          </p>
          <div className="mt-4">
            <Link to="/search" className="btn btn-primary text-sm">
              Start Searching
            </Link>
          </div>
        </div>
      )}

      {!loading && history.length > 0 && (
        <div className="panel bg-white divide-y divide-[var(--color-border)] overflow-hidden">
          {history.map((item) => (
            <div
              key={item.id}
              className="p-4 flex items-center justify-between gap-4 hover:bg-[var(--color-very-light-blue)] transition-colors"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-[var(--color-text-muted)] flex-shrink-0" />
                  <span className="font-medium text-[var(--color-text)] text-sm truncate">
                    "{item.query}"
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)] mt-1 pl-6">
                  <span>{item.results_count} standard{item.results_count === 1 ? '' : 's'} matched</span>
                  <span>•</span>
                  <span>{new Date(item.created_at).toLocaleString()}</span>
                </div>
              </div>

              <Link
                to={`/search?q=${encodeURIComponent(item.query)}`}
                className="btn btn-ghost !px-3 !py-1.5 text-xs text-[var(--color-primary)]"
              >
                Re-run <ArrowRight className="h-3 w-3 ml-1" />
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
