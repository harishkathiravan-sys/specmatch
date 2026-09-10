// Main application layout with navigation

import { NavLink, Link, Outlet } from 'react-router-dom';
import { Bookmark, History, Search, FileSearch, ScrollText, Info } from 'lucide-react';
import { Logo } from '../components/Logo';

const navItems = [
  { to: '/search', label: 'Search', icon: Search },
  { to: '/analyze', label: 'Analyze', icon: FileSearch },
  { to: '/standards', label: 'Standards', icon: ScrollText },
  { to: '/saved', label: 'Saved', icon: Bookmark },
  { to: '/history', label: 'History', icon: History },
];

export function Layout() {
  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-text)]">
      <header className="sticky top-0 z-20 border-b border-[var(--color-border)] bg-[var(--color-primary)] text-white">
        <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/" aria-label="SpecMatch home" className="flex items-center">
            <Logo variant="light" />
          </Link>

          <nav className="hidden items-center gap-2 md:flex" aria-label="Main navigation">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `rounded-xl border px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'border-white/30 bg-white/10 text-white'
                      : 'border-transparent text-white/80 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <span className="flex items-center gap-1.5">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {label}
                </span>
              </NavLink>
            ))}
          </nav>

          <div className="hidden items-center md:flex">
            <Link
              to="/methodology"
              className="inline-flex items-center gap-1 rounded-xl border border-white px-3 py-2 text-sm text-white transition-colors hover:bg-white/10"
            >
              <Info className="h-4 w-4" aria-hidden="true" />
              Methodology
            </Link>
          </div>

          <nav className="fixed bottom-0 left-0 right-0 z-30 flex justify-around border-t border-[var(--color-border)] bg-white py-2 md:hidden" aria-label="Mobile navigation">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex flex-col items-center gap-0.5 px-3 py-1 text-[11px] ${isActive ? 'text-[var(--color-primary)]' : 'text-[var(--color-text-muted)]'}`
                }
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="flex-1 pb-20 md:pb-10">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <Outlet />
        </div>
      </main>

      <footer className="border-t border-[var(--color-border)] bg-white">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-6 text-xs text-[var(--color-text-muted)] sm:flex-row sm:px-6">
          <div className="flex items-center gap-2">
            <Logo size="sm" />
            <span className="text-[var(--color-text-secondary)]">Standards Intelligence for Procurement</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/methodology" className="hover:text-[var(--color-primary)]">Methodology</Link>
            <Link to="/methodology#limitations" className="hover:text-[var(--color-primary)]">Limitations</Link>
            <span className="text-[var(--color-text-muted)]">Dataset V0.3 · 24,132 standards</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
