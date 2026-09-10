// SpecMatch wordmark logo

export function Logo({ size = 'md', variant }: { size?: 'sm' | 'md' | 'lg'; variant?: 'dark' | 'light' }) {
  const fontSizes = {
    sm: { container: 'text-base', icon: 'h-5 w-5', font: 'text-[15px]' },
    md: { container: 'text-lg', icon: 'h-6 w-6', font: 'text-lg' },
    lg: { container: 'text-2xl', icon: 'h-8 w-8', font: 'text-2xl' },
  }[size];

  // Auto-detect: if no variant provided, use dark (navy on white) as default for footer/light backgrounds
  // Header will pass variant="light" for white on navy
  const isLight = variant === 'light';

  return (
    <div className={`flex items-center gap-2 ${fontSizes.container}`}>
      <div
        className="flex items-center justify-center rounded"
        style={{
          background: isLight ? '#FFFFFF' : 'var(--color-primary)',
          width: size === 'lg' ? 36 : 28,
          height: size === 'lg' ? 36 : 28,
        }}
        aria-hidden="true"
      >
        {/* Simple spec/document + check alignment mark */}
        <svg
          className={fontSizes.icon}
          viewBox="0 0 24 24"
          fill="none"
          stroke={isLight ? 'var(--color-primary)' : 'white'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="8" y1="12" x2="12" y2="12" />
          <line x1="8" y1="16" x2="14" y2="16" />
        </svg>
      </div>
      <span className={`${fontSizes.font} font-semibold tracking-tight`} style={{ color: isLight ? '#FFFFFF' : 'var(--color-primary)' }}>
        Spec<span style={{ color: isLight ? '#FFFFFF' : 'var(--color-primary)' }}>Match</span>
      </span>
      {isLight && <span className="hidden sm:inline text-[11px] font-normal tracking-wide text-white/80 ml-1">Standards Intelligence for Procurement</span>}
    </div>
  );
}
