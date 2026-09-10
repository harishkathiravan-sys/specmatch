// Utility helper functions

import type { StandardSummary } from '../types';

/**
 * Format a provenance status into a human-readable label.
 */
export function formatProvenance(status: string | null | undefined): {
  label: string;
  className: string;
  tooltip: string;
} {
  if (!status) {
    return {
      label: 'Unknown',
      className: 'badge badge-muted',
      tooltip: 'Provenance not specified in dataset.',
    };
  }

  const upper = status.toUpperCase();
  if (upper.includes('SOURCE_DERIVED') || upper.includes('OFFICIAL')) {
    return {
      label: 'Source-derived',
      className: 'badge badge-verified',
      tooltip: 'Information derived directly from the source inventory.',
    };
  }
  if (upper.includes('SYNTHETIC')) {
    return {
      label: 'Synthetic',
      className: 'badge badge-muted',
      tooltip: 'Synthetic training/evaluation data. Not authoritative.',
    };
  }
  if (
    upper.includes('INFERRED') ||
    upper.includes('DERIVED') ||
    upper.includes('NEEDS') ||
    upper.includes('NOT_VALIDATED') ||
    upper.includes('PENDING')
  ) {
    return {
      label: 'Needs verification',
      className: 'badge badge-warning',
      tooltip: 'Inferred or not yet authoritatively enriched. Verify against authoritative sources.',
    };
  }
  return {
    label: status,
    className: 'badge badge-muted',
    tooltip: `Status: ${status}`,
  };
}

/**
 * Format a compliance status into a human-readable badge.
 */
export function formatCompliance(status: string | null | undefined): {
  label: string;
  className: string;
} {
  if (!status) {
    return { label: 'Not validated', className: 'badge badge-muted' };
  }
  const upper = status.toUpperCase();
  if (upper.includes('VALIDATED') && !upper.includes('NOT')) {
    return { label: 'Verified', className: 'badge badge-verified' };
  }
  if (upper.includes('NEEDS') || upper.includes('ENRICHMENT') || upper.includes('NOT_VALIDATED')) {
    return {
      label: 'Not validated',
      className: 'badge badge-warning',
    };
  }
  return { label: status, className: 'badge badge-muted' };
}

/**
 * Format the current status of a standard.
 */
export function formatStatus(status: string | null | undefined): {
  label: string;
  className: string;
} {
  if (!status || status === 'NOT_AVAILABLE') {
    return { label: 'Not available', className: 'badge badge-muted' };
  }
  const upper = status.toUpperCase();
  if (upper.includes('UNKNOWN') || upper.includes('NOT_VALIDATED')) {
    return { label: 'Status unknown', className: 'badge badge-warning' };
  }
  return { label: status, className: 'badge badge-muted' };
}

/**
 * Convert a match score (0-1) to a percentage string.
 */
export function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/**
 * Determine confidence level based on score.
 */
export function confidenceLevel(score: number): {
  label: string;
  className: string;
  reason: string;
} {
  if (score >= 0.7) {
    return {
      label: 'High confidence',
      className: 'badge badge-verified',
      reason: 'Strong title and terminology match. Multiple retrieval signals agree.',
    };
  }
  if (score >= 0.4) {
    return {
      label: 'Moderate confidence',
      className: 'badge badge-warning',
      reason: 'Relevant technical terminology detected, but applicability requires verification.',
    };
  }
  return {
    label: 'Low confidence',
    className: 'badge badge-muted',
    reason: 'Potentially related standard found, but available evidence is insufficient to establish applicability.',
  };
}

/**
 * Format a standard number for display.
 */
export function formatStandardNumber(standard: StandardSummary): string {
  return standard.standard_number || 'Unknown';
}

/**
 * Get reliability message for enrichment status.
 */
export function enrichmentMessage(enrichmentStatus: string | null | undefined): string | null {
  if (!enrichmentStatus) return null;
  const upper = enrichmentStatus.toUpperCase();
  if (upper.includes('DERIVED')) {
    return 'This field is derived from the standard identifier/title and is not an official BIS classification.';
  }
  return null;
}
