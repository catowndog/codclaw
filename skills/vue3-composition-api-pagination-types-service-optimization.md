Comprehensive guide to implementing type-safe pagination in Vue 3 using the Composition API with TypeScript, including reusable composables, service layer optimization, caching strategies, and performance best practices.

## Table of Contents

1. [Overview](#overview)
2. [Core Pagination Types](#core-pagination-types)
3. [Advanced Generic Types](#advanced-generic-types)
4. [Pagination Composable](#pagination-composable)
5. [Service Layer Integration](#service-layer-integration)
6. [Caching & Optimization Strategies](#caching--optimization-strategies)
7. [Cursor-Based Pagination](#cursor-based-pagination)
8. [Infinite Scroll Pagination](#infinite-scroll-pagination)
9. [Server-Side Integration Patterns](#server-side-integration-patterns)
10. [Component Implementation](#component-implementation)
11. [Edge Cases & Error Handling](#edge-cases--error-handling)
12. [Performance Tips](#performance-tips)
13. [Testing Pagination](#testing-pagination)
14. [Anti-Patterns & Common Pitfalls](#anti-patterns--common-pitfalls)
15. [Real-World Scenarios](#real-world-scenarios)

---

## Overview

Pagination is fundamental to any data-heavy application. In Vue 3 with the Composition API and TypeScript, building a robust, reusable, and type-safe pagination system requires careful architecture of types, composables, and service layers. This skill covers offset-based pagination, cursor-based pagination, infinite scroll, and hybrid strategies — all optimized for performance at scale.

---

## Core Pagination Types

### Basic Pagination Request & Response Types

```typescript
// types/pagination.ts

/**
 * Sort direction enum for type safety
 */
export enum SortDirection {
  ASC = 'asc',
  DESC = 'desc',
}

/**
 * Core pagination request parameters sent to the API
 */
export interface PaginationParams {
  page: number;
  pageSize: number;
  sortBy?: string;
  sortDirection?: SortDirection;
}

/**
 * Extended pagination params with search and filtering
 */
export interface PaginationQueryParams extends PaginationParams {
  search?: string;
  filters?: Record<string, unknown>;
}

/**
 * Metadata returned from the server about the paginated dataset
 */
export interface PaginationMeta {
  currentPage: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
}

/**
 * Generic paginated API response wrapper
 */
export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

/**
 * State representing the current pagination context in the UI
 */
export interface PaginationState<T> {
  items: T[];
  meta: PaginationMeta;
  isLoading: boolean;
  error: string | null;
  params: PaginationQueryParams;
}
```

### Default Values Factory

```typescript
// types/pagination.ts (continued)

export const DEFAULT_PAGE_SIZE = 20;
export const DEFAULT_PAGE = 1;

export const ALLOWED_PAGE_SIZES = [10, 20, 50, 100] as const;
export type AllowedPageSize = (typeof ALLOWED_PAGE_SIZES)[number];

export function createDefaultPaginationParams(
  overrides?: Partial<PaginationQueryParams>
): PaginationQueryParams {
  return {
    page: DEFAULT_PAGE,
    pageSize: DEFAULT_PAGE_SIZE,
    sortBy: undefined,
    sortDirection: SortDirection.ASC,
    search: undefined,
    filters: undefined,
    ...overrides,
  };
}

export function createDefaultPaginationMeta(
  overrides?: Partial<PaginationMeta>
): PaginationMeta {
  return {
    currentPage: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    totalItems: 0,
    totalPages: 0,
    hasNextPage: false,
    hasPreviousPage: false,
    ...overrides,
  };
}

export function createDefaultPaginationState<T>(
  overrides?: Partial<PaginationState<T>>
): PaginationState<T> {
  return {
    items: [],
    meta: createDefaultPaginationMeta(),
    isLoading: false,
    error: null,
    params: createDefaultPaginationParams(),
    ...overrides,
  };
}
```

---

## Advanced Generic Types

### Typed Filter System

```typescript
// types/filters.ts

/**
 * Filter operator types for building complex queries
 */
export enum FilterOperator {
  EQUALS = 'eq',
  NOT_EQUALS = 'neq',
  GREATER_THAN = 'gt',
  GREATER_THAN_OR_EQUAL = 'gte',
  LESS_THAN = 'lt',
  LESS_THAN_OR_EQUAL = 'lte',
  CONTAINS = 'contains',
  STARTS_WITH = 'startsWith',
  ENDS_WITH = 'endsWith',
  IN = 'in',
  NOT_IN = 'notIn',
  BETWEEN = 'between',
  IS_NULL = 'isNull',
  IS_NOT_NULL = 'isNotNull',
}

/**
 * A single typed filter condition
 */
export interface FilterCondition<T = unknown> {
  field: string;
  operator: FilterOperator;
  value: T;
}

/**
 * Filter group supporting AND/OR logic
 */
export interface FilterGroup {
  logic: 'AND' | 'OR';
  conditions: (FilterCondition | FilterGroup)[];
}

/**
 * Type-safe sort configuration extracting keys from entity
 */
export type SortConfig<T> = {
  field: keyof T & string;
  direction: SortDirection;
};

/**
 * Full typed pagination request incorporating entity-aware sorting and filtering
 */
export interface TypedPaginationParams<T> extends PaginationParams {
  sort?: SortConfig<T>;
  filters?: FilterCondition[];
  filterGroup?: FilterGroup;
  search?: string;
  searchFields?: (keyof T & string)[];
}
```

### Service Response Mapping Types

```typescript
// types/api-mapping.ts

/**
 * Maps various backend pagination response formats to our standard format
 */
export interface RawApiPaginationResponse<T> {
  // Spring Boot style
  content?: T[];
  totalElements?: number;
  totalPages?: number;
  number?: number;
  size?: number;

  // Laravel style
  data?: T[];
  current_page?: number;
  per_page?: number;
  total?: number;
  last_page?: number;

  // Django REST Framework style
  results?: T[];
  count?: number;
  next?: string | null;
  previous?: string | null;

  // Generic
  items?: T[];
  meta?: Record<string, unknown>;
  pagination?: Record<string, unknown>;
}

/**
 * Adapter function type for normalizing API responses
 */
export type PaginationResponseAdapter<T, R = RawApiPaginationResponse<T>> = (
  raw: R
) => PaginatedResponse<T>;

/**
 * Pre-built adapters for common backend frameworks
 */
export const springBootAdapter = <T>(
  raw: RawApiPaginationResponse<T>
): PaginatedResponse<T> => ({
  data: raw.content ?? [],
  meta: {
    currentPage: (raw.number ?? 0) + 1, // Spring Boot is 0-indexed
    pageSize: raw.size ?? DEFAULT_PAGE_SIZE,
    totalItems: raw.totalElements ?? 0,
    totalPages: raw.totalPages ?? 0,
    hasNextPage: (raw.number ?? 0) + 1 < (raw.totalPages ?? 0),
    hasPreviousPage: (raw.number ?? 0) > 0,
  },
});

export const laravelAdapter = <T>(
  raw: RawApiPaginationResponse<T>
): PaginatedResponse<T> => ({
  data: raw.data ?? [],
  meta: {
    currentPage: raw.current_page ?? 1,
    pageSize: raw.per_page ?? DEFAULT_PAGE_SIZE,
    totalItems: raw.total ?? 0,
    totalPages: raw.last_page ?? 0,
    hasNextPage: (raw.current_page ?? 1) < (raw.last_page ?? 0),
    hasPreviousPage: (raw.current_page ?? 1) > 1,
  },
});

export const djangoAdapter = <T>(
  raw: RawApiPaginationResponse<T>
): PaginatedResponse<T> => {
  const pageSize = raw.results?.length ?? DEFAULT_PAGE_SIZE;
  const totalItems = raw.count ?? 0;
  const totalPages = Math.ceil(totalItems / pageSize);
  // Django doesn't return page number directly — infer from next/previous URLs
  const currentPage = raw.next
    ? parseInt(new URL(raw.next).searchParams.get('page') ?? '2') - 1
    : totalPages;

  return {
    data: raw.results ?? [],
    meta: {
      currentPage,
      pageSize,
      totalItems,
      totalPages,
      hasNextPage: raw.next !== null,
      hasPreviousPage: raw.previous !== null,
    },
  };
};
```

---

## Pagination Composable

### Core `usePagination` Composable

```typescript
// composables/usePagination.ts

import { ref, reactive, computed, watch, toRefs, type Ref, type ComputedRef } from 'vue';
import type {
  PaginatedResponse,
  PaginationMeta,
  PaginationQueryParams,
  PaginationState,
} from '@/types/pagination';
import {
  createDefaultPaginationParams,
  createDefaultPaginationMeta,
  DEFAULT_PAGE,
} from '@/types/pagination';

/**
 * Options for the usePagination composable
 */
export interface UsePaginationOptions<T> {
  /** Function that fetches a page of data */
  fetchFunction: (params: PaginationQueryParams) => Promise<PaginatedResponse<T>>;
  /** Initial pagination params */
  initialParams?: Partial<PaginationQueryParams>;
  /** Whether to fetch immediately on mount */
  immediate?: boolean;
  /** Debounce delay in ms for search input */
  searchDebounceMs?: number;
  /** Callback after successful fetch */
  onSuccess?: (response: PaginatedResponse<T>) => void;
  /** Callback after fetch error */
  onError?: (error: Error) => void;
  /** Transform items after fetch */
  transform?: (items: T[]) => T[];
  /** Reset page to 1 when filters/search change */
  resetPageOnFilterChange?: boolean;
}

/**
 * Return type of the usePagination composable
 */
export interface UsePaginationReturn<T> {
  // Reactive state
  items: Ref<T[]>;
  meta: Ref<PaginationMeta>;
  isLoading: Ref<boolean>;
  error: Ref<string | null>;
  params: PaginationQueryParams;

  // Computed
  isEmpty: ComputedRef<boolean>;
  isFirstPage: ComputedRef<boolean>;
  isLastPage: ComputedRef<boolean>;
  pageRange: ComputedRef<number[]>;
  showingFrom: ComputedRef<number>;
  showingTo: ComputedRef<number>;

  // Actions
  fetchPage: (page?: number) => Promise<void>;
  nextPage: () => Promise<void>;
  prevPage: () => Promise<void>;
  goToPage: (page: number) => Promise<void>;
  changePageSize: (size: number) => Promise<void>;
  search: (query: string) => Promise<void>;
  sort: (field: string, direction?: 'asc' | 'desc') => Promise<void>;
  applyFilters: (filters: Record<string, unknown>) => Promise<void>;
  refresh: () => Promise<void>;
  reset: () => Promise<void>;
}

/**
 * Main pagination composable
 */
export function usePagination<T>(
  options: UsePaginationOptions<T>
): UsePaginationReturn<T> {
  const {
    fetchFunction,
    initialParams,
    immediate = true,
    searchDebounceMs = 300,
    onSuccess,
    onError,
    transform,
    resetPageOnFilterChange = true,
  } = options;

  // --- Reactive State ---
  const items = ref<T[]>([]) as Ref<T[]>;
  const meta = ref<PaginationMeta>(createDefaultPaginationMeta());
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const params = reactive<PaginationQueryParams>(
    createDefaultPaginationParams(initialParams)
  );

  // --- Abort Controller for request cancellation ---
  let abortController: AbortController | null = null;

  // --- Debounce timer ---
  let searchTimer: ReturnType<typeof setTimeout> | null = null;

  // --- Computed Properties ---
  const isEmpty = computed(() => items.value.length === 0 && !isLoading.value);
  const isFirstPage = computed(() => meta.value.currentPage <= 1);
  const isLastPage = computed(
    () => meta.value.currentPage >= meta.value.totalPages
  );

  const showingFrom = computed(() => {
    if (meta.value.totalItems === 0) return 0;
    return (meta.value.currentPage - 1) * meta.value.pageSize + 1;
  });

  const showingTo = computed(() => {
    const to = meta.value.currentPage * meta.value.pageSize;
    return Math.min(to, meta.value.totalItems);
  });

  /**
   * Generates a visible page range for pagination UI
   * Shows at most 7 page buttons with ellipsis logic
   */
  const pageRange = computed((): number[] => {
    const total = meta.value.totalPages;
    const current = meta.value.currentPage;
    const maxVisible = 7;

    if (total <= maxVisible) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }

    const pages: number[] = [];
    const half = Math.floor(maxVisible / 2);
    let start = Math.max(1, current - half);
    let end = Math.min(total, start + maxVisible - 1);

    if (end - start < maxVisible - 1) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    // Ensure first and last pages are always included
    if (pages[0] !== 1) {
      pages[0] = 1;
      if (pages[1] !== 2) pages[1] = -1; // -1 represents ellipsis
    }
    if (pages[pages.length - 1] !== total) {
      pages[pages.length - 1] = total;
      if (pages[pages.length - 2] !== total - 1) {
        pages[pages.length - 2] = -1; // ellipsis
      }
    }

    return pages;
  });

  // --- Core Fetch Function ---
  async function fetchPage(page?: number): Promise<void> {
    // Cancel any in-flight request
    if (abortController) {
      abortController.abort();
    }
    abortController = new AbortController();

    if (page !== undefined) {
      params.page = page;
    }

    isLoading.value = true;
    error.value = null;

    try {
      const response = await fetchFunction({ ...params });

      // Apply transform if provided
      const transformedData = transform
        ? transform(response.data)
        : response.data;

      items.value = transformedData;
      meta.value = response.meta;

      onSuccess?.(response);
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        return; // Silently ignore aborted requests
      }
      const errorMessage =
        err instanceof Error ? err.message : 'An unknown error occurred';
      error.value = errorMessage;
      onError?.(err instanceof Error ? err : new Error(errorMessage));
    } finally {
      isLoading.value = false;
    }
  }

  // --- Navigation Actions ---
  async function nextPage(): Promise<void> {
    if (!isLastPage.value) {
      await fetchPage(params.page + 1);
    }
  }

  async function prevPage(): Promise<void> {
    if (!isFirstPage.value) {
      await fetchPage(params.page - 1);
    }
  }

  async function goToPage(page: number): Promise<void> {
    const clampedPage = Math.max(1, Math.min(page, meta.value.totalPages || 1));
    await fetchPage(clampedPage);
  }

  async function changePageSize(size: number): Promise<void> {
    params.pageSize = size;
    // Reset to page 1 when changing page size to avoid out-of-bounds
    await fetchPage(DEFAULT_PAGE);
  }

  // --- Search with Debounce ---
  async function search(query: string): Promise<void> {
    if (searchTimer) clearTimeout(searchTimer);

    return new Promise((resolve) => {
      searchTimer = setTimeout(async () => {
        params.search = query || undefined;
        if (resetPageOnFilterChange) {
          params.page = DEFAULT_PAGE;
        }
        await fetchPage();
        resolve();
      }, searchDebounceMs);
    });
  }

  // --- Sort ---
  async function sort(
    field: string,
    direction?: 'asc' | 'desc'
  ): Promise<void> {
    // Toggle direction if same field clicked again
    if (params.sortBy === field && !direction) {
      params.sortDirection =
        params.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      params.sortBy = field;
      params.sortDirection = direction ?? 'asc';
    }

    if (resetPageOnFilterChange) {
      params.page = DEFAULT_PAGE;
    }
    await fetchPage();
  }

  // --- Filters ---
  async function applyFilters(
    filters: Record<string, unknown>
  ): Promise<void> {
    params.filters = Object.keys(filters).length > 0 ? filters : undefined;
    if (resetPageOnFilterChange) {
      params.page = DEFAULT_PAGE;
    }
    await fetchPage();
  }

  // --- Refresh (re-fetch current page) ---
  async function refresh(): Promise<void> {
    await fetchPage();
  }

  // --- Reset to initial state ---
  async function reset(): Promise<void> {
    const defaults = createDefaultPaginationParams(initialParams);
    Object.assign(params, defaults);
    await fetchPage();
  }

  // --- Immediate fetch on mount ---
  if (immediate) {
    fetchPage();
  }

  return {
    items,
    meta,
    isLoading,
    error,
    params,
    isEmpty,
    isFirstPage,
    isLastPage,
    pageRange,
    showingFrom,
    showingTo,
    fetchPage,
    nextPage,
    prevPage,
    goToPage,
    changePageSize,
    search,
    sort,
    applyFilters,
    refresh,
    reset,
  };
}
```

---

## Service Layer Integration

### Generic Pagination Service

```typescript
// services/PaginationService.ts

import type {
  PaginatedResponse,
  PaginationQueryParams,
  PaginationResponseAdapter,
} from '@/types/pagination';
import { springBootAdapter } from '@/types/api-mapping';
import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';

/**
 * Configuration for the PaginationService
 */
export interface PaginationServiceConfig {
  /** Base URL for the API */
  baseURL: string;
  /** Custom Axios instance */
  axiosInstance?: AxiosInstance;
  /** Default request timeout in ms */
  timeout?: number;
  /** Response adapter function */
  adapter?: PaginationResponseAdapter<unknown>;
  /** Default headers */
  headers?: Record<string, string>;
}

/**
 * Serializes pagination params to query string format
 */
function serializeParams(params: PaginationQueryParams): Record<string, string | number> {
  const serialized: Record<string, string | number> = {
    page: params.page,
    pageSize: params.pageSize,
  };

  if (params.sortBy) {
    serialized.sortBy = params.sortBy;
    serialized.sortDirection = params.sortDirection ?? 'asc';
  }

  if (params.search) {
    serialized.search = params.search;
  }

  if (params.filters) {
    // Flatten filters to query params
    Object.entries(params.filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        serialized[`filter[${key}]`] = String(value);
      }
    });
  }

  return serialized;
}

/**
 * Generic paginated data fetching service
 */
export class PaginationService<T> {
  private client: AxiosInstance;
  private adapter: PaginationResponseAdapter<T>;

  constructor(config: PaginationServiceConfig) {
    this.client =
      config.axiosInstance ??
      axios.create({
        baseURL: config.baseURL,
        timeout: config.timeout ?? 10000,
        headers: {
          'Content-Type': 'application/json',
          ...config.headers,
        },
      });

    this.adapter =
      (config.adapter as PaginationResponseAdapter<T>) ?? springBootAdapter;
  }

  /**
   * Fetch a page of data
   */
  async fetchPage(
    endpoint: string,
    params: PaginationQueryParams,
    axiosConfig?: AxiosRequestConfig
  ): Promise<PaginatedResponse<T>> {
    const serializedParams = serializeParams(params);

    const response = await this.client.get(endpoint, {
      params: serializedParams,
      ...axiosConfig,
    });

    return this.adapter(response.data);
  }

  /**
   * Fetch page with request cancellation support
   */
  fetchPageWithCancel(
    endpoint: string,
    params: PaginationQueryParams
  ): { promise: Promise<PaginatedResponse<T>>; cancel: () => void } {
    const controller = new AbortController();

    const promise = this.fetchPage(endpoint, params, {
      signal: controller.signal,
    });

    return {
      promise,
      cancel: () => controller.abort(),
    };
  }
}
```

### Entity-Specific Service Example

```typescript
// services/UserService.ts

import { PaginationService } from './PaginationService';
import type { PaginatedResponse, PaginationQueryParams } from '@/types/pagination';

export interface User {
  id: number;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'moderator';
  status: 'active' | 'inactive' | 'suspended';
  createdAt: string;
  updatedAt: string;
}

export interface UserFilters {
  role?: User['role'];
  status?: User['status'];
  createdAfter?: string;
  createdBefore?: string;
}

class UserServiceClass {
  private paginationService: PaginationService<User>;

  constructor() {
    this.paginationService = new PaginationService<User>({
      baseURL: import.meta.env.VITE_API_BASE_URL,
    });
  }

  async getUsers(params: PaginationQueryParams): Promise<PaginatedResponse<User>> {
    return this.paginationService.fetchPage('/api/users', params);
  }

  async getUsersByRole(
    role: User['role'],
    params: PaginationQueryParams
  ): Promise<PaginatedResponse<User>> {
    return this.paginationService.fetchPage(`/api/users/role/${role}`, params);
  }

  async searchUsers(
    query: string,
    params: PaginationQueryParams
  ): Promise<PaginatedResponse<User>> {
    return this.paginationService.fetchPage('/api/users/search', {
      ...params,
      search: query,
    });
  }
}

export const UserService = new UserServiceClass();
```

---

## Caching & Optimization Strategies

### Page Cache Implementation

```typescript
// composables/usePaginationCache.ts

import { ref, type Ref } from 'vue';
import type { PaginatedResponse, PaginationQueryParams } from '@/types/pagination';

interface CacheEntry<T> {
  data: PaginatedResponse<T>;
  timestamp: number;
  params: PaginationQueryParams;
}

interface CacheOptions {
  /** Time-to-live in milliseconds (default: 5 minutes) */
  ttl?: number;
  /** Maximum number of cached pages */
  maxEntries?: number;
  /** Cache key prefix */
  keyPrefix?: string;
}

/**
 * Creates a deterministic cache key from pagination params
 */
function createCacheKey(prefix: string, params: PaginationQueryParams): string {
  const normalized = {
    p: params.page,
    ps: params.pageSize,
    sb: params.sortBy ?? '',
    sd: params.sortDirection ?? '',
    s: params.search ?? '',
    f: params.filters ? JSON.stringify(params.filters) : '',
  };
  return `${prefix}:${JSON.stringify(normalized)}`;
}

export function usePaginationCache<T>(options: CacheOptions = {}) {
  const { ttl = 5 * 60 * 1000, maxEntries = 50, keyPrefix = 'page' } = options;

  const cache = new Map<string, CacheEntry<T>>();
  const hitCount = ref(0);
  const missCount = ref(0);

  function get(params: PaginationQueryParams): PaginatedResponse<T> | null {
    const key = createCacheKey(keyPrefix, params);
    const entry = cache.get(key);

    if (!entry) {
      missCount.value++;
      return null;
    }

    // Check if entry has expired
    if (Date.now() - entry.timestamp > ttl) {
      cache.delete(key);
      missCount.value++;
      return null;
    }

    hitCount.value++;
    return entry.data;
  }

  function set(params: PaginationQueryParams, data: PaginatedResponse<T>): void {
    const key = createCacheKey(keyPrefix, params);

    // Evict oldest entries if cache is full
    if (cache.size >= maxEntries) {
      const oldestKey = cache.keys().next().value;
      if (oldestKey) cache.delete(oldestKey);
    }

    cache.set(key, {
      data: structuredClone(data), // Deep clone to prevent mutation
      timestamp: Date.now(),
      params: { ...params },
    });
  }

  function invalidate(params?: PaginationQueryParams): void {
    if (params) {
      const key = createCacheKey(keyPrefix, params);
      cache.delete(key);
    } else {
      cache.clear();
    }
  }

  function invalidateByPattern(pattern: string): void {
    for (const key of cache.keys()) {
      if (key.includes(pattern)) {
        cache.delete(key);
      }
    }
  }

  /**
   * Prefetch adjacent pages for smoother navigation
   */
  async function prefetch(
    currentParams: PaginationQueryParams,
    fetchFn: (params: PaginationQueryParams) => Promise<PaginatedResponse<T>>,
    totalPages: number
  ): Promise<void> {
    const pagesToPrefetch: number[] = [];

    // Prefetch next page
    if (currentParams.page < totalPages) {
      pagesToPrefetch.push(currentParams.page + 1);
    }

    // Prefetch previous page
    if (currentParams.page > 1) {
      pagesToPrefetch.push(currentParams.page - 1);
    }

    const prefetchPromises = pagesToPrefetch
      .filter((page) => {
        const params = { ...currentParams, page };
        return get(params) === null; // Only prefetch if not cached
      })
      .map(async (page) => {
        const params = { ...currentParams, page };
        try {
          const data = await fetchFn(params);
          set(params, data);
        } catch {
          // Silently fail prefetch — it's an optimization, not a requirement
        }
      });

    await Promise.allSettled(prefetchPromises);
  }

  return {
    get,
    set,
    invalidate,
    invalidateByPattern,
    prefetch,
    hitCount,
    missCount,
    cacheSize: computed(() => cache.size),
  };
}
```

### Using Cache with Pagination Composable

```typescript
// composables/useCachedPagination.ts

import { usePagination, type UsePaginationOptions, type UsePaginationReturn } from './usePagination';
import { usePaginationCache } from './usePaginationCache';
import type { PaginatedResponse, PaginationQueryParams } from '@/types/pagination';

export interface UseCachedPaginationOptions<T> extends UsePaginationOptions<T> {
  cacheKey?: string;
  cacheTtl?: number;
  enablePrefetch?: boolean;
}

export function useCachedPagination<T>(
  options: UseCachedPaginationOptions<T>
): UsePaginationReturn<T> & { invalidateCache: () => void } {
  const {
    fetchFunction,
    cacheKey = 'default',
    cacheTtl = 300000,
    enablePrefetch = true,
    ...paginationOptions
  } = options;

  const cache = usePaginationCache<T>({
    keyPrefix: cacheKey,
    ttl: cacheTtl,
  });

  // Wrap the fetch function with caching
  const cachedFetchFunction = async (
    params: PaginationQueryParams
  ): Promise<PaginatedResponse<T>> => {
    const cached = cache.get(params);
    if (cached) {
      // Trigger background prefetch even on cache hit
      if (enablePrefetch) {
        cache.prefetch(params, fetchFunction, cached.meta.totalPages);
      }
      return cached;
    }

    const result = await fetchFunction(params);
    cache.set(params, result);

    // Prefetch adjacent pages
    if (enablePrefetch) {
      cache.prefetch(params, fetchFunction, result.meta.totalPages);
    }

    return result;
  };

  const pagination = usePagination<T>({
    ...paginationOptions,
    fetchFunction: cachedFetchFunction,
  });

  return {
    ...pagination,
    invalidateCache: () => cache.invalidate(),
  };
}
```

---

## Cursor-Based Pagination

```typescript
// types/cursor-pagination.ts

export interface CursorPaginationParams {
  cursor?: string | null;
  limit: number;
  direction?: 'forward' | 'backward';
}

export interface CursorPaginatedResponse<T> {
  data: T[];
  pageInfo: {
    startCursor: string | null;
    endCursor: string | null;
    hasNextPage: boolean;
    hasPreviousPage: boolean;
  };
  totalCount?: number;
}

// composables/useCursorPagination.ts

import { ref, computed, type Ref, type ComputedRef } from 'vue';

export interface UseCursorPaginationOptions<T> {
  fetchFunction: (
    params: CursorPaginationParams
  ) => Promise<CursorPaginatedResponse<T>>;
  limit?: number;
  immediate?: boolean;
}

export interface UseCursorPaginationReturn<T> {
  items: Ref<T[]>;
  isLoading: Ref<boolean>;
  error: Ref<string | null>;
  hasNextPage: ComputedRef<boolean>;
  hasPreviousPage: ComputedRef<boolean>;
  fetchNext: () => Promise<void>;
  fetchPrevious: () => Promise<void>;
  refresh: () => Promise<void>;
}

export function useCursorPagination<T>(
  options: UseCursorPaginationOptions<T>
): UseCursorPaginationReturn<T> {
  const { fetchFunction, limit = 20, immediate = true } = options;

  const items = ref<T[]>([]) as Ref<T[]>;
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const cursors = ref<{
    start: string | null;
    end: string | null;
    hasNext: boolean;
    hasPrev: boolean;
  }>({
    start: null,
    end: null,
    hasNext: false,
    hasPrev: false,
  });

  const cursorHistory = ref<string[]>([]); // Track cursor positions for back navigation

  const hasNextPage = computed(() => cursors.value.hasNext);
  const hasPreviousPage = computed(() => cursors.value.hasPrev);

  async function fetchData(cursor?: string | null, direction: 'forward' | 'backward' = 'forward'): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await fetchFunction({ cursor, limit, direction });
      items.value = response.data;
      cursors.value = {
        start: response.pageInfo.startCursor,
        end: response.pageInfo.endCursor,
        hasNext: response.pageInfo.hasNextPage,
        hasPrev: response.pageInfo.hasPreviousPage,
      };
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Fetch error';
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchNext(): Promise<void> {
    if (!hasNextPage.value) return;
    if (cursors.value.end) {
      cursorHistory.value.push(cursors.value.start ?? '');
    }
    await fetchData(cursors.value.end, 'forward');
  }

  async function fetchPrevious(): Promise<void> {
    if (!hasPreviousPage.value) return;
    const prevCursor = cursorHistory.value.pop() ?? null;
    await fetchData(prevCursor, 'backward');
  }

  async function refresh(): Promise<void> {
    cursorHistory.value = [];
    await fetchData(null, 'forward');
  }

  if (immediate) {
    fetchData();
  }

  return {
    items,
    isLoading,
    error,
    hasNextPage,
    hasPreviousPage,
    fetchNext,
    fetchPrevious,
    refresh,
  };
}
```

---

## Infinite Scroll Pagination

```typescript
// composables/useInfiniteScroll.ts

import { ref, computed, onMounted, onUnmounted, type Ref, type ComputedRef } from 'vue';
import type { PaginatedResponse, PaginationQueryParams } from '@/types/pagination';
import { createDefaultPaginationParams } from '@/types/pagination';

export interface UseInfiniteScrollOptions<T> {
  fetchFunction: (params: PaginationQueryParams) => Promise<PaginatedResponse<T>>;
  initialParams?: Partial<PaginationQueryParams>;
  /** Distance from bottom (in px) to trigger next load */
  threshold?: number;
  /** Element to observe for scroll (defaults to window) */
  scrollTarget?: Ref<HTMLElement | null>;
  immediate?: boolean;
}

export interface UseInfiniteScrollReturn<T> {
  items: Ref<T[]>;
  isLoading: Ref<boolean>;
  isLoadingMore: Ref<boolean>;
  error: Ref<string | null>;
  hasMore: ComputedRef<boolean>;
  totalItems: ComputedRef<number>;
  loadMore: () => Promise<void>;
  refresh: () => Promise<void>;
  sentinelRef: Ref<HTMLElement | null>;
}

export function useInfiniteScroll<T>(
  options: UseInfiniteScrollOptions<T>
): UseInfiniteScrollReturn<T> {
  const {
    fetchFunction,
    initialParams,
    threshold = 200,
    scrollTarget,
    immediate = true,
  } = options;

  const items = ref<T[]>([]) as Ref<T[]>;
  const isLoading = ref(false);
  const isLoadingMore = ref(false);
  const error = ref<string | null>(null);
  const currentPage = ref(1);
  const totalPages = ref(0);
  const totalItemCount = ref(0);
  const sentinelRef = ref<HTMLElement | null>(null);

  const params = createDefaultPaginationParams(initialParams);

  const hasMore = computed(() => currentPage.value < totalPages.value);
  const totalItems = computed(() => totalItemCount.value);

  let observer: IntersectionObserver | null = null;

  async function fetchPageData(page: number, append = false): Promise<void> {
    const loadingRef = append ? isLoadingMore : isLoading;
    loadingRef.value = true;
    error.value = null;

    try {
      const response = await fetchFunction({ ...params, page });

      if (append) {
        items.value = [...items.value, ...response.data];
      } else {
        items.value = response.data;
      }

      currentPage.value = response.meta.currentPage;
      totalPages.value = response.meta.totalPages;
      totalItemCount.value = response.meta.totalItems;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Fetch failed';
    } finally {
      loadingRef.value = false;
    }
  }

  async function loadMore(): Promise<void> {
    if (isLoadingMore.value || !hasMore.value) return;
    await fetchPageData(currentPage.value + 1, true);
  }

  async function refresh(): Promise<void> {
    currentPage.value = 1;
    await fetchPageData(1, false);
  }

  // Intersection Observer setup for automatic loading
  function setupObserver(): void {
    if (!sentinelRef.value) return;

    observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry.isIntersecting && hasMore.value && !isLoadingMore.value) {
          loadMore();
        }
      },
      {
        root: scrollTarget?.value ?? null,
        rootMargin: `${threshold}px`,
        threshold: 0.1,
      }
    );

    observer.observe(sentinelRef.value);
  }

  onMounted(() => {
    if (immediate) {
      fetchPageData(1).then(() => {
        // Setup observer after initial data load
        setupObserver();
      });
    }
  });

  onUnmounted(() => {
    observer?.disconnect();
  });

  return {
    items,
    isLoading,
    isLoadingMore,
    error,
    hasMore,
    totalItems,
    loadMore,
    refresh,
    sentinelRef,
  };
}
```

---

## Server-Side Integration Patterns

### URL-Synced Pagination (Vue Router)

```typescript
// composables/useRouterPagination.ts

import { computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { usePagination, type UsePaginationOptions, type UsePaginationReturn } from './usePagination';
import type { PaginationQueryParams } from '@/types/pagination';

/**
 * Pagination composable that syncs state with URL query parameters.
 * Supports back/forward browser navigation and shareable URLs.
 */
export function useRouterPagination<T>(
  options: Omit<UsePaginationOptions<T>, 'immediate' | 'initialParams'>
): UsePaginationReturn<T> {
  const route = useRoute();
  const router = useRouter();

  // Parse initial params from URL
  const getParamsFromRoute = (): Partial<PaginationQueryParams> => ({
    page: route.query.page ? Number(route.query.page) : 1,
    pageSize: route.query.pageSize ? Number(route.query.pageSize) : 20,
    sortBy: (route.query.sortBy as string) ?? undefined,
    sortDirection: (route.query.sortDirection as 'asc' | 'desc') ?? undefined,
    search: (route.query.search as string) ?? undefined,
    filters: route.query.filters
      ? JSON.parse(decodeURIComponent(route.query.filters as string))
      : undefined,
  });

  const pagination = usePagination<T>({
    ...options,
    initialParams: getParamsFromRoute(),
    immediate: true,
  });

  // Sync params to URL when they change
  watch(
    () => ({ ...pagination.params }),
    (newParams) => {
      const query: Record<string, string> = {};

      if (newParams.page > 1) query.page = String(newParams.page);
      if (newParams.pageSize !== 20) query.pageSize = String(newParams.pageSize);
      if (newParams.sortBy) query.sortBy = newParams.sortBy;
      if (newParams.sortDirection) query.sortDirection = newParams.sortDirection;
      if (newParams.search) query.search = newParams.search;
      if (newParams.filters && Object.keys(newParams.filters).length > 0) {
        query.filters = encodeURIComponent(JSON.stringify(newParams.filters));
      }

      router.replace({ query });
    },
    { deep: true }
  );

  // React to browser back/forward navigation
  watch(
    () => route.query,
    () => {
      const routeParams = getParamsFromRoute();
      const currentParams = pagination.params;

      // Only refetch if params actually changed (prevent loops)
      if (
        routeParams.page !== currentParams.page ||
        routeParams.search !== currentParams.search
      ) {
        Object.assign(pagination.params, routeParams);
        pagination.fetchPage();
      }
    }
  );

  return pagination;
}
```

---

## Component Implementation

### Reusable Pagination Component

```vue
<!-- components/PaginationControls.vue -->
<template>
  <div class="pagination-controls" v-if="meta.totalPages > 1">
    <!-- Results info -->
    <div class="pagination-info">
      Showing {{ showingFrom }} to {{ showingTo }} of {{ meta.totalItems }} results
    </div>

    <!-- Page size selector -->
    <div class="page-size-selector">
      <label for="pageSize">Per page:</label>
      <select
        id="pageSize"
        :value="meta.pageSize"
        @change="$emit('changePageSize', Number(($event.target as HTMLSelectElement).value))"
      >
        <option v-for="size in pageSizes" :key="size" :value="size">
          {{ size }}
        </option>
      </select>
    </div>

    <!-- Navigation buttons -->
    <nav class="pagination-nav" aria-label="Pagination">
      <button
        class="pagination-btn"
        :disabled="isFirstPage || isLoading"
        @click="$emit('prevPage')"
        aria-label="Previous page"
      >
        ← Previous
      </button>

      <template v-for="page in pageRange" :key="page">
        <span v-if="page === -1" class="pagination-ellipsis">…</span>
        <button
          v-else
          class="pagination-btn"
          :class="{ active: page === meta.currentPage }"
          :disabled="isLoading"
          :aria-current="page === meta.currentPage ? 'page' : undefined"
          @click="$emit('goToPage', page)"
        >
          {{ page }}
        </button>
      </template>

      <button
        class="pagination-btn"
        :disabled="isLastPage || isLoading"
        @click="$emit('nextPage')"
        aria-label="Next page"
      >
        Next →
      </button>
    </nav>
  </div>
</template>

<script setup lang="ts">
import type { PaginationMeta } from '@/types/pagination';
import { ALLOWED_PAGE_SIZES } from '@/types/pagination';

interface Props {
  meta: PaginationMeta;
  pageRange: number[];
  showingFrom: number;
  showingTo: number;
  isFirstPage: boolean;
  isLastPage: boolean;
  isLoading: boolean;
  pageSizes?: number[];
}

const props = withDefaults(defineProps<Props>(), {
  pageSizes: () => [...ALLOWED_PAGE_SIZES],
});

defineEmits<{
  prevPage: [];
  nextPage: [];
  goToPage: [page: number];
  changePageSize: [size: number];
}>();
</script>
```

### Full Page Example

```vue
<!-- pages/UsersPage.vue -->
<template>
  <div class="users-page">
    <h1>Users Management</h1>

    <!-- Search & Filters -->
    <div class="toolbar">
      <input
        type="search"
        placeholder="Search users..."
        :value="params.search"
        @input="search(($event.target as HTMLInputElement).value)"
      />

      <select @change="applyFilters({ role: ($event.target as HTMLSelectElement).value })">
        <option value="">All Roles</option>
        <option value="admin">Admin</option>
        <option value="user">User</option>
        <option value="moderator">Moderator</option>
      </select>

      <button @click="refresh" :disabled="isLoading">↻ Refresh</button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading && items.length === 0" class="loading">
      <LoadingSpinner />
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="refresh">Retry</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="isEmpty" class="empty">
      <p>No users found.</p>
    </div>

    <!-- Data Table -->
    <table v-else class="data-table" :class="{ loading: isLoading }">
      <thead>
        <tr>
          <th @click="sort('name')" class="sortable">
            Name
            <SortIndicator :active="params.sortBy === 'name'" :direction="params.sortDirection" />
          </th>
          <th @click="sort('email')" class="sortable">Email</th>
          <th @click="sort('role')" class="sortable">Role</th>
          <th @click="sort('createdAt')" class="sortable">Created</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in items" :key="user.id">
          <td>{{ user.name }}</td>
          <td>{{ user.email }}</td>
          <td>{{ user.role }}</td>
          <td>{{ formatDate(user.createdAt) }}</td>
        </tr>
      </tbody>
    </table>

    <!-- Pagination Controls -->
    <PaginationControls
      :meta="meta"
      :page-range="pageRange"
      :showing-from="showingFrom"
      :showing-to="showingTo"
      :is-first-page="isFirstPage"
      :is-last-page="isLastPage"
      :is-loading="isLoading"
      @prev-page="prevPage"
      @next-page="nextPage"
      @go-to-page="goToPage"
      @change-page-size="changePageSize"
    />
  </div>
</template>

<script setup lang="ts">
import { useCachedPagination } from '@/composables/useCachedPagination';
import { UserService, type User } from '@/services/UserService';
import PaginationControls from '@/components/PaginationControls.vue';

const {
  items,
  meta,
  params,
  isLoading,
  error,
  isEmpty,
  isFirstPage,
  isLastPage,
  pageRange,
  showingFrom,
  showingTo,
  fetchPage,
  nextPage,
  prevPage,
  goToPage,
  changePageSize,
  search,
  sort,
  applyFilters,
  refresh,
} = useCachedPagination<User>({
  fetchFunction: (params) => UserService.getUsers(params),
  initialParams: { pageSize: 20, sortBy: 'createdAt', sortDirection: 'desc' },
  cacheKey: 'users',
  cacheTtl: 60000,
  enablePrefetch: true,
});

function formatDate(date: string): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(date));
}
</script>
```

---

## Edge Cases & Error Handling

### Common Edge Cases and Solutions

| Edge Case | Problem | Solution |
|-----------|---------|----------|
| Empty dataset | Division by zero in page calculations | Guard `totalPages = Math.max(1, Math.ceil(total / pageSize))` |
| Page out of bounds | User bookmarks page 50 but only 10 exist | Clamp to valid range, redirect to last page |
| Concurrent requests | Race condition between rapid page changes | AbortController cancels previous request |
| Stale cache | Data changes server-side | TTL-based invalidation + manual refresh |
| Zero page size | Infinite loop or API error | Validate `pageSize >= 1` |
| Network failure | Loading state stuck | `finally` block always resets loading |
| Large filter payloads | URL too long for query params | Use POST for complex filter requests |
| Total count changes | Items deleted while paginating | Re-validate current page on each response |

### Defensive Page Bound Checking

```typescript
function sanitizePage(page: number, totalPages: number): number {
  if (isNaN(page) || page < 1) return 1;
  if (totalPages > 0 && page > totalPages) return totalPages;
  return Math.floor(page); // Ensure integer
}

function sanitizePageSize(size: number): number {
  if (isNaN(size) || size < 1) return DEFAULT_PAGE_SIZE;
  if (size > 100) return 100; // Hard cap
  return Math.floor(size);
}
```

---

## Performance Tips

1. **Request Deduplication**: Use AbortController to cancel in-flight requests when a new one starts.
2. **Prefetching**: Background-fetch adjacent pages (n+1, n-1) during idle time.
3. **Virtual Scrolling**: For very large page sizes (100+ items), combine with `vue-virtual-scroller` to render only visible DOM elements.
4. **Debounced Search**: Always debounce search input (300ms is a good default).
5. **Structural Sharing**: When caching, use `structuredClone` only on write; reference cached data directly on read.
6. **Computed Meta**: Use `computed` for derived values (`showingFrom`, `showingTo`, `pageRange`) rather than storing them.
7. **Skeleton Loaders**: Show skeleton UI while loading instead of spinners for perceived performance.
8. **Optimistic Page Size**: Default to 20 items — it's a good balance between payload size and user experience.
9. **Backend Coordination**: Request only needed fields via `?fields=id,name,email` to reduce payload size.
10. **Stale-While-Revalidate**: Show cached data immediately, then update with fresh data in background.

```typescript
// Stale-while-revalidate pattern
async function fetchWithSWR(params: PaginationQueryParams): Promise<PaginatedResponse<T>> {
  const cached = cache.get(params);
  
  if (cached) {
    // Return stale data immediately
    items.value = cached.data;
    meta.value = cached.meta;
    
    // Revalidate in background
    fetchFunction(params).then((fresh) => {
      cache.set(params, fresh);
      items.value = fresh.data;
      meta.value = fresh.meta;
    }).catch(() => {}); // Silently ignore background refresh errors
    
    return cached;
  }
  
  return fetchFunction(params);
}
```

---

## Testing Pagination

```typescript
// __tests__/usePagination.spec.ts

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { nextTick } from 'vue';
import { usePagination } from '@/composables/usePagination';
import type { PaginatedResponse } from '@/types/pagination';

interface TestItem {
  id: number;
  name: string;
}

function createMockResponse(
  page: number,
  totalPages: number = 5,
  totalItems: number = 100
): PaginatedResponse<TestItem> {
  const pageSize = 20;
  return {
    data: Array.from({ length: pageSize }, (_, i) => ({
      id: (page - 1) * pageSize + i + 1,
      name: `Item ${(page - 1) * pageSize + i + 1}`,
    })),
    meta: {
      currentPage: page,
      pageSize,
      totalItems,
      totalPages,
      hasNextPage: page < totalPages,
      hasPreviousPage: page > 1,
    },
  };
}

describe('usePagination', () => {
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn().mockImplementation((params) =>
      Promise.resolve(createMockResponse(params.page))
    );
  });

  it('should load initial page on mount', async () => {
    const { items, meta, isLoading } = usePagination<TestItem>({
      fetchFunction: mockFetch,
    });

    // Initially loading
    expect(isLoading.value).toBe(true);

    await nextTick();
    await vi.waitFor(() => expect(isLoading.value).toBe(false));

    expect(items.value).toHaveLength(20);
    expect(meta.value.currentPage).toBe(1);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('should navigate to next page', async () => {
    const { nextPage, meta, items } = usePagination<TestItem>({
      fetchFunction: mockFetch,
    });

    await vi.waitFor(() => expect(meta.value.currentPage).toBe(1));

    await nextPage();

    expect(meta.value.currentPage).toBe(2);
    expect(items.value[0].id).toBe(21);
  });

  it('should not go past last page', async () => {
    mockFetch.mockResolvedValue(createMockResponse(5, 5));

    const { nextPage, meta, isLastPage } = usePagination<TestItem>({
      fetchFunction: mockFetch,
      initialParams: { page: 5 },
    });

    await vi.waitFor(() => expect(isLastPage.value).toBe(true));

    await nextPage();

    expect(meta.value.currentPage).toBe(5);
    // Should not have made an additional call
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('should reset page on search', async () => {
    const { search, params, meta } = usePagination<TestItem>({
      fetchFunction: mockFetch,
      searchDebounceMs: 0, // No debounce for testing
    });

    await vi.waitFor(() => expect(meta.value.currentPage).toBe(1));

    // Navigate to page 3 first
    params.page = 3;

    await search('test query');

    expect(params.page).toBe(1); // Reset to first page
    expect(params.search).toBe('test query');
  });

  it('should handle fetch errors gracefully', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));

    const { error, isLoading, items } = usePagination<TestItem>({
      fetchFunction: mockFetch,
    });

    await vi.waitFor(() => expect(isLoading.value).toBe(false));

    expect(error.value).toBe('Network error');
    expect(items.value).toHaveLength(0);
  });

  it('should apply transform to fetched items', async () => {
    const { items } = usePagination<TestItem>({
      fetchFunction: mockFetch,
      transform: (items) => items.map((item) => ({ ...item, name: item.name.toUpperCase() })),
    });

    await vi.waitFor(() => expect(items.value.length).toBeGreaterThan(0));

    expect(items.value[0].name).toBe('ITEM 1');
  });
});
```

---

## Anti-Patterns & Common Pitfalls

### ❌ Anti-Pattern 1: Mutating Reactive Params Directly in Template

```vue
<!-- BAD: Direct mutation causes multiple uncontrolled watches -->
<input v-model="params.search" />
<select v-model="params.page">
```

```vue
<!-- GOOD: Use action methods that handle side effects -->
<input :value="params.search" @input="search($event.target.value)" />
```

### ❌ Anti-Pattern 2: Not Cancelling Previous Requests

```typescript
// BAD: Race condition — old response can overwrite new one
async function fetchPage() {
  const response = await api.get('/items', { params });
  items.value = response.data;
}
```

```typescript
// GOOD: Cancel previous request
let controller: AbortController;
async function fetchPage() {
  controller?.abort();
  controller = new AbortController();
  const response = await api.get('/items', { params, signal: controller.signal });
  items.value = response.data;
}
```

### ❌ Anti-Pattern 3: Storing Derived State

```typescript
// BAD: Storing values that can be computed
const totalPages = ref(0);
const hasNext = ref(false);
const showingText = ref('');
```

```typescript
// GOOD: Use computed properties
const totalPages = computed(() => Math.ceil(meta.value.totalItems / meta.value.pageSize));
const hasNext = computed(() => meta.value.currentPage < totalPages.value);
```

### ❌ Anti-Pattern 4: No Loading State Cleanup on Error

```typescript
// BAD: Loading stays true forever if error occurs
isLoading.value = true;
const data = await fetchFunction(params); // throws
isLoading.value = false; // Never reached
```

```typescript
// GOOD: Use try-finally
isLoading.value = true;
try {
  const data = await fetchFunction(params);
} catch (err) {
  error.value = err.message;
} finally {
  isLoading.value = false; // Always runs
}
```

### ❌ Anti-Pattern 5: Fetching All Data Client-Side

```typescript
// BAD: Fetching everything and slicing in the browser
const allUsers = await api.get('/users'); // Returns 50,000 users
const page = allUsers.slice(start, end);
```

Always paginate on the server side. Client-side slicing defeats the entire purpose of pagination.

---

## Real-World Scenarios

### Scenario 1: E-Commerce Product Listing

```typescript
const {
  items: products,
  ...pagination
} = useCachedPagination<Product>({
  fetchFunction: (params) => ProductService.getProducts(params),
  initialParams: {
    pageSize: 24, // Grid-friendly number (2x12, 3x8, 4x6)
    sortBy: 'popularity',
    sortDirection: 'desc',
  },
  enablePrefetch: true,
  cacheTtl: 120000, // 2 minutes for product listings
});
```

### Scenario 2: Admin Dashboard with Heavy Filters

```typescript
const { items: orders, ...pagination } = useRouterPagination<Order>({
  fetchFunction: (params) => OrderService.query(params),
  searchDebounceMs: 500, // Longer debounce for complex queries
  onSuccess: (response) => {
    analytics.track('orders_page_viewed', {
      page: response.meta.currentPage,
      totalOrders: response.meta.totalItems,
    });
  },
});
```

### Scenario 3: Chat Messages with Infinite Scroll (Reverse)

```typescript
const { items: messages, loadMore, sentinelRef } = useInfiniteScroll<Message>({
  fetchFunction: (params) => ChatService.getMessages(chatId, {
    ...params,
    sortBy: 'createdAt',
    sortDirection: 'desc', // Newest first, load older on scroll up
  }),
  threshold: 100,
  initialParams: { pageSize: 50 },
});
```

### Scenario 4: Data Export with Pagination

```typescript
async function exportAllPages<T>(
  fetchFn: (params: PaginationQueryParams) => Promise<PaginatedResponse<T>>,
  params: Omit<PaginationQueryParams, 'page'>
): Promise<T[]> {
  const allItems: T[] = [];
  let currentPage = 1;
  let hasMore = true;

  while (hasMore) {
    const response = await fetchFn({ ...params, page: currentPage } as PaginationQueryParams);
    allItems.push(...response.data);
    hasMore = response.meta.hasNextPage;
    currentPage++;

    // Safety valve — prevent infinite loops
    if (currentPage > 1000) {
      console.warn('Export safety limit reached');
      break;
    }
  }

  return allItems;
}
```

---

## Summary

Building a robust pagination system in Vue 3 with the Composition API and TypeScript involves:

1. **Strong typing** of all request/response shapes with generics
2. **Reusable composables** (`usePagination`, `useInfiniteScroll`, `useCursorPagination`) that encapsulate all state and logic
3. **Service layer abstraction** with response adapters for backend flexibility
4. **Caching and prefetching** to minimize network requests and improve UX
5. **URL synchronization** for shareable, bookmarkable paginated views
6. **Defensive programming** with abort controllers, error boundaries, and input validation
7. **Accessible components** with proper ARIA attributes and keyboard navigation

This architecture scales from simple lists to complex admin dashboards with thousands of records, maintaining type safety and performance throughout.