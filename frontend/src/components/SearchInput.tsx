// Search input component — core interaction

import { useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface SearchInputProps {
  variant?: 'hero' | 'compact';
  placeholder?: string;
  autoFocus?: boolean;
  onSearch?: (query: string) => void;
  defaultValue?: string;
}

export function SearchInput({
  variant = 'compact',
  placeholder = 'Search by standard number, title, product, technical term...',
  autoFocus = false,
  onSearch,
  defaultValue = '',
}: SearchInputProps) {
  const [query, setQuery] = useState(defaultValue);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    if (onSearch) {
      onSearch(trimmed);
    } else {
      navigate(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  };

  const isHero = variant === 'hero';

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div
        className={`flex items-stretch gap-2 overflow-hidden rounded-2xl border bg-white transition-all duration-200 ${
          isHero
            ? 'border-[var(--color-border)] shadow-sm focus-within:border-[var(--color-accent)] focus-within:ring-2 focus-within:ring-[#DBEAFE]'
            : 'border-[var(--color-border)] shadow-sm focus-within:border-[var(--color-accent)] focus-within:ring-2 focus-within:ring-[#DBEAFE]'
        }`}
      >
        <div className="flex items-center pl-4 pr-2" aria-hidden="true">
          <Search className="h-4 w-4 text-[var(--color-text-muted)]" />
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className={`flex-1 border-0 bg-white text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-muted)] ${
            isHero ? 'py-4 text-base' : 'py-2.5 text-sm'
          }`}
          aria-label="Search standards"
          autoFocus={autoFocus}
        />
        <button
          type="submit"
          className={`btn bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-medium)] active:bg-[var(--color-primary-dark)] ${isHero ? 'rounded-l-none rounded-r-2xl px-5' : 'rounded-l-none rounded-r-xl px-4'}`}
        >
          {isHero ? 'Find Standards' : 'Search'}
        </button>
      </div>
    </form>
  );
}
