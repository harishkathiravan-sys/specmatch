// API service layer for SpecMatch backend

import type {
  AnalysisResponse,
  DatasetStats,
  FilterOptions,
  HealthResponse,
  SavedItem,
  SearchResponse,
  SearchResultItem,
  StandardDetail,
  StandardListResponse,
} from '../types';

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }

  return res.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}

// Health
export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

// Standards
export interface StandardsListParams {
  page?: number;
  page_size?: number;
  sector?: string;
  department?: string;
  committee?: string;
  type_of_standard?: string;
  year_from?: number;
  year_to?: number;
  status?: string;
  family?: string;
  sort_by?: string;
  sort_dir?: string;
}

export async function getStandards(
  params: StandardsListParams = {},
): Promise<StandardListResponse> {
  const qs = buildQuery({ ...params });
  return request<StandardListResponse>(`/standards${qs}`);
}

export async function getStandardDetail(
  standardNumber: string,
): Promise<StandardDetail> {
  const encoded = encodeURIComponent(standardNumber);
  return request<StandardDetail>(`/standards/${encoded}`);
}

export async function getFilterOptions(): Promise<FilterOptions> {
  return request<FilterOptions>('/standards/filters');
}

export async function getDatasetStats(): Promise<DatasetStats> {
  return request<DatasetStats>('/standards/stats');
}

// Search
export interface SearchParams {
  q: string;
  page?: number;
  page_size?: number;
  sector?: string;
  department?: string;
  committee?: string;
  type_of_standard?: string;
  year_from?: number;
  year_to?: number;
  status?: string;
  standard_family?: string;
}

export async function searchStandards(params: SearchParams): Promise<SearchResponse> {
  const qs = buildQuery({ ...params });
  const response = await request<RawSearchResponse>(`/search${qs}`);

  return {
    ...response,
    items: response.items.map((item): SearchResultItem => {
      if ('standard' in item) {
        const standard = item.standard.data
          ? { ...item.standard.data, ...item.standard }
          : item.standard;
        return {
          ...standard,
          match_score: item.relevance_score ?? 0,
          match_type: item.match_type ?? standard.match_type,
          matching_terms: item.matching_terms ?? standard.matching_terms ?? [],
          rank: item.rank,
        } as SearchResultItem;
      }
      return item;
    }),
  };
}

interface RawSearchResponse extends Omit<SearchResponse, 'items'> {
  items: Array<SearchResultItem | {
    standard: Partial<SearchResultItem> & { data?: Partial<SearchResultItem> };
    relevance_score?: number | null;
    match_type: string;
    matching_terms?: string[];
    rank?: number;
  }>;
}

// Analyze
export async function analyzeSpecification(text: string): Promise<AnalysisResponse> {
  return request<AnalysisResponse>('/analyze', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export async function uploadDocument(file: File): Promise<AnalysisResponse & { file_name: string; file_size: number }> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE_URL}/analyze/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }
  return res.json();
}

// Saved items
export async function getSavedItems(): Promise<SavedItem[]> {
  return request<SavedItem[]>('/standards/saved/list');
}

export async function saveItem(
  itemType: string,
  itemId: string,
  itemData?: string,
  label?: string,
): Promise<{ id: number; message: string }> {
  return request<{ id: number; message: string }>('/standards/saved', {
    method: 'POST',
    body: JSON.stringify({ item_type: itemType, item_id: itemId, item_data: itemData, label }),
  });
}

export async function deleteSavedItem(id: number): Promise<{ message: string }> {
  return request<{ message: string }>(`/standards/saved/${id}`, { method: 'DELETE' });
}

// History
export async function getHistory(limit = 50): Promise<{ query: string; search_type: string; results_count: number; created_at: string; id: number }[]> {
  return request<{ query: string; search_type: string; results_count: number; created_at: string; id: number }[]>(
    `/standards/history/list?limit=${limit}`,
  );
}

// Compare
export async function compareStandards(standardIds: string[]): Promise<{ standards: import('../types').StandardDetail[]; differences: { field: string; values: Record<string, string | null> }[] }> {
  return request<{ standards: import('../types').StandardDetail[]; differences: { field: string; values: Record<string, string | null> }[] }>('/standards/compare', {
    method: 'POST',
    body: JSON.stringify({ standard_ids: standardIds }),
  });
}
