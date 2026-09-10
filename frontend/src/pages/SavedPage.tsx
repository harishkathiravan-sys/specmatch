// Saved page — list of bookmarked standards and analyses

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, Trash2, ArrowRight } from 'lucide-react';
import { getSavedItems, deleteSavedItem } from '../services/api';
import type { SavedItem } from '../types';

export function SavedPage() {
  const [items, setItems] = useState<SavedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSaved = () => {
    setLoading(true);
    getSavedItems()
      .then((data) => {
        setItems(data);
        setError(null);
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSaved();
  }, []);

  const handleDelete = async (id: number) => {
    try {
      await deleteSavedItem(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch (e) {
      console.error('Failed to delete saved item:', e);
    }
  };

  return (
    <div className="fade-in max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-primary)]">Saved Items</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-0.5">
            Standards, recommendations, and analyses saved for quick reference.
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
          <div className="skeleton h-20 w-full" />
          <div className="skeleton h-20 w-full" />
        </div>
      )}

      {!loading && items.length === 0 && (
        <div className="panel bg-white p-10 text-center text-[var(--color-text-muted)]">
          <Bookmark className="h-8 w-8 mx-auto text-[var(--color-border)] mb-2" />
          <p className="font-medium text-[var(--color-text)]">No saved items yet.</p>
          <p className="text-sm mt-1 text-[var(--color-text-muted)]">
            Click the "Save" button on any standard card or details page to bookmark it here.
          </p>
          <div className="mt-4">
            <Link to="/standards" className="btn btn-primary text-sm">
              Browse Standards
            </Link>
          </div>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="space-y-3">
          {items.map((item) => {
            let parsedData: { standard_number?: string; title?: string } = {};
            if (item.item_data) {
              try {
                parsedData = JSON.parse(item.item_data);
              } catch {
                // Ignore parse errors
              }
            }

            const standardNum = parsedData.standard_number || item.label || item.item_id;

            return (
              <div
                key={item.id}
                className="panel bg-white p-4 flex items-center justify-between gap-4 hover:border-[var(--color-primary)]/30 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="badge badge-muted capitalize">{item.item_type}</span>
                    <Link
                      to={`/standards/${encodeURIComponent(standardNum)}`}
                      className="text-base font-semibold text-[var(--color-primary)] hover:underline truncate"
                    >
                      {standardNum}
                    </Link>
                  </div>
                  {parsedData.title && (
                    <p className="text-sm text-[var(--color-text)] mt-1 line-clamp-1">
                      {parsedData.title}
                    </p>
                  )}
                  <div className="text-xs text-[var(--color-text-muted)] mt-1">
                    Saved on {new Date(item.created_at).toLocaleDateString()}
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <Link
                    to={`/standards/${encodeURIComponent(standardNum)}`}
                    className="btn btn-ghost !px-2.5 !py-1 text-xs"
                  >
                    View <ArrowRight className="h-3 w-3 ml-1" />
                  </Link>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="btn btn-ghost !px-2.5 !py-1 text-xs text-[var(--color-error)] hover:bg-[var(--color-error-bg)]"
                    title="Remove item"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
