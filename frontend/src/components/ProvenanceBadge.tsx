// Provenance badge component

import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { formatProvenance } from '../lib/utils';

interface ProvenanceBadgeProps {
  status: string | null | undefined;
  label?: string;
}

export function ProvenanceBadge({ status, label }: ProvenanceBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const info = formatProvenance(status);

  return (
    <span
      className="inline-flex items-center gap-1 cursor-help relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
      tabIndex={0}
      role="note"
      aria-label={info.tooltip}
    >
      <span className={info.className}>{label || info.label}</span>
      <HelpCircle className="h-3 w-3 text-[var(--color-text-muted)]" aria-hidden="true" />
      {showTooltip && (
        <span className="absolute bottom-full left-0 mb-1 w-56 rounded-md border border-[var(--color-border)] bg-white p-2 text-xs text-[var(--color-text-secondary)] shadow-sm z-10">
          {info.tooltip}
        </span>
      )}
    </span>
  );
}
