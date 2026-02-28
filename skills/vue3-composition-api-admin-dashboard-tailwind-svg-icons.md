A comprehensive guide to building production-ready admin dashboard UIs using Vue 3 Composition API, Tailwind CSS best practices, and custom SVG icon systems for admin interfaces.

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Project Setup & Configuration](#project-setup--configuration)
3. [Tailwind CSS Configuration for Admin Dashboards](#tailwind-css-configuration-for-admin-dashboards)
4. [Composition API Fundamentals for Dashboards](#composition-api-fundamentals-for-dashboards)
5. [Composables for Admin Features](#composables-for-admin-features)
6. [SVG Icon System](#svg-icon-system)
7. [Dashboard Layout Components](#dashboard-layout-components)
8. [Data Tables & Lists](#data-tables--lists)
9. [Charts & Widgets](#charts--widgets)
10. [Forms & Validation](#forms--validation)
11. [Navigation & Routing](#navigation--routing)
12. [State Management with Pinia](#state-management-with-pinia)
13. [Performance Optimization](#performance-optimization)
14. [Security Considerations](#security-considerations)
15. [Common Pitfalls & Troubleshooting](#common-pitfalls--troubleshooting)

---

## Overview & Architecture

An admin dashboard built with Vue 3 Composition API and Tailwind CSS follows a modular, component-driven architecture. The key principles are:

- **Composable-first logic**: Extract reusable business logic into composables
- **Utility-first styling**: Use Tailwind CSS utility classes with component abstraction
- **SVG-native icons**: Use inline SVGs for crisp, customizable, and performant icons
- **Type-safe development**: Leverage TypeScript for robust admin interfaces
- **Lazy loading**: Split routes and heavy components for fast initial loads

### Recommended Folder Structure

```
src/
├── assets/
│   ├── icons/               # Raw SVG icon files
│   └── styles/
│       └── tailwind.css
├── components/
│   ├── common/              # Buttons, Modals, Dropdowns
│   ├── dashboard/           # Dashboard-specific widgets
│   ├── icons/               # SVG icon components
│   ├── layout/              # Sidebar, Header, Footer
│   ├── tables/              # DataTable, TablePagination
│   └── forms/               # FormInput, FormSelect, etc.
├── composables/
│   ├── useAuth.ts
│   ├── useDashboard.ts
│   ├── useDataTable.ts
│   ├── useSidebar.ts
│   ├── useTheme.ts
│   └── useNotification.ts
├── layouts/
│   ├── AdminLayout.vue
│   ├── AuthLayout.vue
│   └── BlankLayout.vue
├── pages/
│   ├── Dashboard.vue
│   ├── Users.vue
│   ├── Settings.vue
│   └── auth/
│       ├── Login.vue
│       └── ForgotPassword.vue
├── router/
│   └── index.ts
├── stores/
│   ├── auth.ts
│   ├── ui.ts
│   └── notifications.ts
├── types/
│   ├── dashboard.ts
│   ├── user.ts
│   └── icons.ts
├── utils/
│   ├── formatters.ts
│   ├── validators.ts
│   └── api.ts
├── App.vue
└── main.ts
```

---

## Project Setup & Configuration

### Initial Setup

```bash
npm create vite@latest admin-dashboard -- --template vue-ts
cd admin-dashboard
npm install
npm install -D tailwindcss @tailwindcss/forms @tailwindcss/typography postcss autoprefixer
npm install vue-router@4 pinia @vueuse/core
npm install axios chart.js vue-chartjs
npx tailwindcss init -p
```

### Vite Configuration (vite.config.ts)

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import svgLoader from 'vite-svg-loader'

export default defineConfig({
  plugins: [
    vue(),
    svgLoader({
      svgoConfig: {
        plugins: [
          { name: 'removeViewBox', active: false },
          { name: 'removeDimensions', active: true },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@icons': resolve(__dirname, 'src/assets/icons'),
      '@components': resolve(__dirname, 'src/components'),
      '@composables': resolve(__dirname, 'src/composables'),
      '@stores': resolve(__dirname, 'src/stores'),
      '@types': resolve(__dirname, 'src/types'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'chart': ['chart.js', 'vue-chartjs'],
          'vendor': ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
})
```

---

## Tailwind CSS Configuration for Admin Dashboards

### tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Admin-specific color palette
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        sidebar: {
          DEFAULT: '#1e293b',
          hover: '#334155',
          active: '#0f172a',
          text: '#94a3b8',
          'text-active': '#f8fafc',
        },
        dashboard: {
          bg: '#f1f5f9',
          card: '#ffffff',
          border: '#e2e8f0',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      spacing: {
        'sidebar': '260px',
        'sidebar-collapsed': '72px',
        'header': '64px',
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05)',
        'sidebar': '2px 0 8px -2px rgb(0 0 0 / 0.1)',
        'dropdown': '0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.04)',
      },
      animation: {
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
        'spin-slow': 'spin 3s linear infinite',
        'pulse-dot': 'pulseDot 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },
      screens: {
        'xs': '475px',
        '3xl': '1920px',
      },
      transitionProperty: {
        'width': 'width',
        'spacing': 'margin, padding',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms')({
      strategy: 'class',
    }),
    require('@tailwindcss/typography'),
  ],
}
```

### Base Tailwind CSS Styles (src/assets/styles/tailwind.css)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    @apply scroll-smooth antialiased;
  }
  body {
    @apply bg-dashboard-bg text-slate-800 dark:bg-slate-900 dark:text-slate-200;
  }
  /* Custom scrollbar for admin dashboards */
  ::-webkit-scrollbar {
    @apply w-1.5;
  }
  ::-webkit-scrollbar-track {
    @apply bg-transparent;
  }
  ::-webkit-scrollbar-thumb {
    @apply bg-slate-300 dark:bg-slate-600 rounded-full;
  }
  ::-webkit-scrollbar-thumb:hover {
    @apply bg-slate-400 dark:bg-slate-500;
  }
}

@layer components {
  .btn {
    @apply inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5
           text-sm font-medium transition-all duration-200
           focus:outline-none focus:ring-2 focus:ring-offset-2
           disabled:opacity-50 disabled:cursor-not-allowed;
  }
  .btn-primary {
    @apply btn bg-primary-600 text-white hover:bg-primary-700
           focus:ring-primary-500 active:bg-primary-800;
  }
  .btn-secondary {
    @apply btn bg-white text-slate-700 border border-slate-300
           hover:bg-slate-50 focus:ring-primary-500
           dark:bg-slate-800 dark:text-slate-200 dark:border-slate-600;
  }
  .btn-danger {
    @apply btn bg-red-600 text-white hover:bg-red-700
           focus:ring-red-500 active:bg-red-800;
  }
  .btn-ghost {
    @apply btn bg-transparent text-slate-600 hover:bg-slate-100
           focus:ring-slate-300 dark:text-slate-400 dark:hover:bg-slate-800;
  }
  .card {
    @apply bg-dashboard-card dark:bg-slate-800 rounded-xl border border-dashboard-border
           dark:border-slate-700 shadow-card;
  }
  .card-hover {
    @apply card hover:shadow-card-hover transition-shadow duration-200;
  }
  .input-field {
    @apply form-input w-full rounded-lg border-slate-300 bg-white px-3.5 py-2.5
           text-sm text-slate-800 placeholder-slate-400
           focus:border-primary-500 focus:ring-primary-500
           dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200
           dark:placeholder-slate-500 dark:focus:border-primary-500;
  }
  .badge {
    @apply inline-flex items-center rounded-full px-2.5 py-0.5
           text-xs font-medium;
  }
  .badge-success {
    @apply badge bg-emerald-100 text-emerald-800
           dark:bg-emerald-900/30 dark:text-emerald-400;
  }
  .badge-warning {
    @apply badge bg-amber-100 text-amber-800
           dark:bg-amber-900/30 dark:text-amber-400;
  }
  .badge-danger {
    @apply badge bg-red-100 text-red-800
           dark:bg-red-900/30 dark:text-red-400;
  }
  .badge-info {
    @apply badge bg-blue-100 text-blue-800
           dark:bg-blue-900/30 dark:text-blue-400;
  }
}
```

---

## Composition API Fundamentals for Dashboards

### Core Principles

1. **Reactive state** via `ref()` and `reactive()`
2. **Computed properties** for derived dashboard data
3. **Watchers** for side effects (API calls, localStorage sync)
4. **Lifecycle hooks** for data fetching and cleanup
5. **Composables** for shared logic across components

### Basic Dashboard Page Example

```vue
<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useDashboard } from '@/composables/useDashboard'
import { useAuth } from '@/composables/useAuth'
import StatsCard from '@/components/dashboard/StatsCard.vue'
import RevenueChart from '@/components/dashboard/RevenueChart.vue'
import RecentOrders from '@/components/dashboard/RecentOrders.vue'
import ActivityFeed from '@/components/dashboard/ActivityFeed.vue'
import IconTrendUp from '@/components/icons/IconTrendUp.vue'
import IconUsers from '@/components/icons/IconUsers.vue'
import IconShoppingCart from '@/components/icons/IconShoppingCart.vue'
import IconDollarSign from '@/components/icons/IconDollarSign.vue'

// Composables
const { user } = useAuth()
const {
  stats,
  revenueData,
  recentOrders,
  activities,
  isLoading,
  error,
  dateRange,
  fetchDashboardData,
  refreshStats,
} = useDashboard()

// Local state
const selectedPeriod = ref<'7d' | '30d' | '90d' | '1y'>('30d')

// Computed
const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
})

const statsCards = computed(() => [
  {
    title: 'Total Revenue',
    value: stats.value?.revenue ?? 0,
    change: stats.value?.revenueChange ?? 0,
    format: 'currency',
    icon: IconDollarSign,
    color: 'blue',
  },
  {
    title: 'Total Users',
    value: stats.value?.users ?? 0,
    change: stats.value?.usersChange ?? 0,
    format: 'number',
    icon: IconUsers,
    color: 'emerald',
  },
  {
    title: 'Orders',
    value: stats.value?.orders ?? 0,
    change: stats.value?.ordersChange ?? 0,
    format: 'number',
    icon: IconShoppingCart,
    color: 'purple',
  },
  {
    title: 'Conversion Rate',
    value: stats.value?.conversionRate ?? 0,
    change: stats.value?.conversionChange ?? 0,
    format: 'percentage',
    icon: IconTrendUp,
    color: 'amber',
  },
])

// Watchers
watch(selectedPeriod, (newPeriod) => {
  fetchDashboardData(newPeriod)
})

// Lifecycle
onMounted(() => {
  fetchDashboardData(selectedPeriod.value)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">
          {{ greeting }}, {{ user?.firstName }}
        </h1>
        <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Here's what's happening with your projects today.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <select
          v-model="selectedPeriod"
          class="input-field w-auto"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="1y">Last year</option>
        </select>
        <button
          class="btn-primary"
          @click="refreshStats"
        >
          <IconRefresh class="h-4 w-4" />
          Refresh
        </button>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatsCard
        v-for="stat in statsCards"
        :key="stat.title"
        v-bind="stat"
        :loading="isLoading"
      />
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
      <div class="xl:col-span-2">
        <RevenueChart
          :data="revenueData"
          :loading="isLoading"
          :period="selectedPeriod"
        />
      </div>
      <div>
        <ActivityFeed
          :activities="activities"
          :loading="isLoading"
        />
      </div>
    </div>

    <!-- Recent Orders -->
    <RecentOrders
      :orders="recentOrders"
      :loading="isLoading"
    />

    <!-- Error State -->
    <div
      v-if="error"
      class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-900/20"
    >
      <p class="text-sm text-red-700 dark:text-red-400">{{ error }}</p>
    </div>
  </div>
</template>
```

---

## Composables for Admin Features

### useDashboard Composable

```typescript
// src/composables/useDashboard.ts
import { ref, reactive, computed } from 'vue'
import { useApi } from './useApi'
import type { DashboardStats, RevenueData, Order, Activity } from '@/types/dashboard'

export function useDashboard() {
  const { get, isLoading, error } = useApi()

  const stats = ref<DashboardStats | null>(null)
  const revenueData = ref<RevenueData[]>([])
  const recentOrders = ref<Order[]>([])
  const activities = ref<Activity[]>([])
  const dateRange = reactive({
    start: new Date(),
    end: new Date(),
  })

  async function fetchDashboardData(period: string = '30d') {
    try {
      const [statsRes, revenueRes, ordersRes, activitiesRes] = await Promise.all([
        get<DashboardStats>(`/api/dashboard/stats?period=${period}`),
        get<RevenueData[]>(`/api/dashboard/revenue?period=${period}`),
        get<Order[]>('/api/dashboard/orders/recent?limit=10'),
        get<Activity[]>('/api/dashboard/activities?limit=20'),
      ])

      stats.value = statsRes
      revenueData.value = revenueRes
      recentOrders.value = ordersRes
      activities.value = activitiesRes
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
    }
  }

  async function refreshStats() {
    await fetchDashboardData()
  }

  const totalRevenue = computed(() => {
    return revenueData.value.reduce((sum, item) => sum + item.amount, 0)
  })

  return {
    stats,
    revenueData,
    recentOrders,
    activities,
    isLoading,
    error,
    dateRange,
    totalRevenue,
    fetchDashboardData,
    refreshStats,
  }
}
```

### useDataTable Composable

```typescript
// src/composables/useDataTable.ts
import { ref, computed, watch, type Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'

export interface TableColumn {
  key: string
  label: string
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
  formatter?: (value: any, row: any) => string
}

export interface TableOptions {
  fetchFn: (params: FetchParams) => Promise<PaginatedResponse<any>>
  columns: TableColumn[]
  defaultSort?: { key: string; direction: 'asc' | 'desc' }
  perPageOptions?: number[]
  searchable?: boolean
  syncWithUrl?: boolean
}

interface FetchParams {
  page: number
  perPage: number
  search: string
  sortBy: string
  sortDirection: 'asc' | 'desc'
  filters: Record<string, any>
}

interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  perPage: number
  lastPage: number
}

export function useDataTable<T extends Record<string, any>>(options: TableOptions) {
  const route = useRoute()
  const router = useRouter()

  // State
  const data = ref<T[]>([]) as Ref<T[]>
  const isLoading = ref(false)
  const total = ref(0)
  const page = ref(Number(route.query.page) || 1)
  const perPage = ref(Number(route.query.perPage) || 10)
  const search = ref((route.query.search as string) || '')
  const sortBy = ref(options.defaultSort?.key || '')
  const sortDirection = ref<'asc' | 'desc'>(options.defaultSort?.direction || 'asc')
  const selectedRows = ref<Set<string | number>>(new Set())
  const filters = ref<Record<string, any>>({})

  // Computed
  const lastPage = computed(() => Math.ceil(total.value / perPage.value))
  const hasNextPage = computed(() => page.value < lastPage.value)
  const hasPrevPage = computed(() => page.value > 1)
  const isAllSelected = computed(() =>
    data.value.length > 0 && data.value.every((row) => selectedRows.value.has(row.id))
  )
  const selectedCount = computed(() => selectedRows.value.size)

  const paginationRange = computed(() => {
    const range: (number | string)[] = []
    const delta = 2
    const left = Math.max(2, page.value - delta)
    const right = Math.min(lastPage.value - 1, page.value + delta)

    range.push(1)
    if (left > 2) range.push('...')
    for (let i = left; i <= right; i++) range.push(i)
    if (right < lastPage.value - 1) range.push('...')
    if (lastPage.value > 1) range.push(lastPage.value)

    return range
  })

  // Methods
  async function fetchData() {
    isLoading.value = true
    try {
      const response = await options.fetchFn({
        page: page.value,
        perPage: perPage.value,
        search: search.value,
        sortBy: sortBy.value,
        sortDirection: sortDirection.value,
        filters: filters.value,
      })

      data.value = response.data as T[]
      total.value = response.total

      if (options.syncWithUrl) {
        router.replace({
          query: {
            ...route.query,
            page: String(page.value),
            perPage: String(perPage.value),
            search: search.value || undefined,
            sortBy: sortBy.value || undefined,
            sortDir: sortDirection.value,
          },
        })
      }
    } catch (error) {
      console.error('Failed to fetch table data:', error)
    } finally {
      isLoading.value = false
    }
  }

  const debouncedSearch = useDebounceFn(() => {
    page.value = 1
    fetchData()
  }, 300)

  function goToPage(p: number) {
    if (p >= 1 && p <= lastPage.value) {
      page.value = p
      fetchData()
    }
  }

  function changeSort(key: string) {
    if (sortBy.value === key) {
      sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortBy.value = key
      sortDirection.value = 'asc'
    }
    page.value = 1
    fetchData()
  }

  function toggleSelectAll() {
    if (isAllSelected.value) {
      selectedRows.value.clear()
    } else {
      data.value.forEach((row) => selectedRows.value.add(row.id))
    }
  }

  function toggleSelectRow(id: string | number) {
    if (selectedRows.value.has(id)) {
      selectedRows.value.delete(id)
    } else {
      selectedRows.value.add(id)
    }
  }

  function clearSelection() {
    selectedRows.value.clear()
  }

  function setFilter(key: string, value: any) {
    filters.value[key] = value
    page.value = 1
    fetchData()
  }

  function resetFilters() {
    filters.value = {}
    search.value = ''
    page.value = 1
    fetchData()
  }

  // Watch search input
  watch(search, () => {
    debouncedSearch()
  })

  watch(perPage, () => {
    page.value = 1
    fetchData()
  })

  return {
    // State
    data,
    isLoading,
    total,
    page,
    perPage,
    search,
    sortBy,
    sortDirection,
    selectedRows,
    filters,
    // Computed
    lastPage,
    hasNextPage,
    hasPrevPage,
    isAllSelected,
    selectedCount,
    paginationRange,
    // Methods
    fetchData,
    goToPage,
    changeSort,
    toggleSelectAll,
    toggleSelectRow,
    clearSelection,
    setFilter,
    resetFilters,
  }
}
```

### useSidebar Composable

```typescript
// src/composables/useSidebar.ts
import { ref, computed, watch } from 'vue'
import { useMediaQuery, useLocalStorage } from '@vueuse/core'

export function useSidebar() {
  const isLargeScreen = useMediaQuery('(min-width: 1024px)')
  const isCollapsed = useLocalStorage('sidebar-collapsed', false)
  const isMobileOpen = ref(false)

  const sidebarWidth = computed(() => {
    if (!isLargeScreen.value) return '0px'
    return isCollapsed.value ? '72px' : '260px'
  })

  function toggle() {
    if (isLargeScreen.value) {
      isCollapsed.value = !isCollapsed.value
    } else {
      isMobileOpen.value = !isMobileOpen.value
    }
  }

  function closeMobile() {
    isMobileOpen.value = false
  }

  // Close mobile sidebar on route change
  watch(isLargeScreen, (isLarge) => {
    if (isLarge) {
      isMobileOpen.value = false
    }
  })

  return {
    isCollapsed,
    isMobileOpen,
    isLargeScreen,
    sidebarWidth,
    toggle,
    closeMobile,
  }
}
```

### useTheme Composable

```typescript
// src/composables/useTheme.ts
import { ref, watch, onMounted } from 'vue'
import { useLocalStorage, usePreferredDark } from '@vueuse/core'

type Theme = 'light' | 'dark' | 'system'

export function useTheme() {
  const prefersDark = usePreferredDark()
  const storedTheme = useLocalStorage<Theme>('admin-theme', 'system')
  const isDark = ref(false)

  function applyTheme() {
    if (storedTheme.value === 'system') {
      isDark.value = prefersDark.value
    } else {
      isDark.value = storedTheme.value === 'dark'
    }

    if (isDark.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function setTheme(theme: Theme) {
    storedTheme.value = theme
    applyTheme()
  }

  function toggleTheme() {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  watch(prefersDark, () => {
    if (storedTheme.value === 'system') {
      applyTheme()
    }
  })

  onMounted(applyTheme)

  return {
    isDark,
    theme: storedTheme,
    setTheme,
    toggleTheme,
  }
}
```

---

## SVG Icon System

### Strategy Overview

For admin dashboards, a custom inline SVG icon system is superior to icon fonts because:

| Feature | SVG Icons | Icon Fonts |
|---------|-----------|------------|
| Tree-shaking | ✅ Yes | ❌ No |
| CSS Styling | ✅ Full control | ⚠️ Limited |
| Accessibility | ✅ Native | ⚠️ Requires ARIA |
| Performance | ✅ Only used icons | ❌ Entire font |
| Multi-color | ✅ Yes | ❌ Single color |
| Crisp rendering | ✅ Always | ⚠️ Sometimes blurry |

### Approach 1: Individual SVG Components (Recommended)

Create each icon as a Vue component for maximum tree-shaking and type safety.

```vue
<!-- src/components/icons/IconDashboard.vue -->
<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="iconClass"
    :aria-hidden="!ariaLabel"
    :aria-label="ariaLabel"
    role="img"
  >
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | number
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
})

const sizeMap: Record<string, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
  xl: 'w-8 h-8',
}

const iconClass = computed(() => {
  if (typeof props.size === 'number') {
    return ''
  }
  return sizeMap[props.size] || sizeMap.md
})
</script>
```

### Approach 2: Dynamic Icon Component with Icon Registry

```typescript
// src/components/icons/icon-paths.ts
// Store SVG paths for all icons — enables dynamic rendering
export const iconPaths: Record<string, string> = {
  dashboard: `<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>`,

  users: `<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>`,

  settings: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>`,

  'chevron-down': `<polyline points="6 9 12 15 18 9"/>`,

  'chevron-right': `<polyline points="9 18 15 12 9 6"/>`,

  search: `<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>`,

  bell: `<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>`,

  menu: `<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>`,

  x: `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>`,

  check: `<polyline points="20 6 9 17 4 12"/>`,

  'arrow-up': `<line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>`,

  'arrow-down': `<line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>`,

  plus: `<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>`,

  trash: `<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>`,

  edit: `<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>`,

  'log-out': `<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>`,

  'trending-up': `<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>`,

  'dollar-sign': `<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>`,

  'shopping-cart': `<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>`,

  refresh: `<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>`,

  filter: `<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>`,

  download: `<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>`,

  eye: `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`,

  'more-vertical': `<circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>`,
}
```

### Dynamic Icon Component

```vue
<!-- src/components/icons/AppIcon.vue -->
<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="computedSize"
    :height="computedSize"
    viewBox="0 0 24 24"
    fill="none"
    :stroke="color"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="[sizeClass, className]"
    :aria-hidden="!ariaLabel"
    :aria-label="ariaLabel"
    :role="ariaLabel ? 'img' : 'presentation'"
    v-html="svgContent"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { iconPaths } from './icon-paths'

interface Props {
  name: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | number
  color?: string
  strokeWidth?: number
  ariaLabel?: string
  className?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  color: 'currentColor',
  strokeWidth: 2,
  className: '',
})

const sizeValues: Record<string, number> = {
  xs: 12,
  sm: 16,
  md: 20,
  lg: 24,
  xl: 32,
}

const sizeClasses: Record<string, string> = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6',
  xl: 'w-8 h-8',
}

const computedSize = computed(() => {
  if (typeof props.size === 'number') return props.size
  return sizeValues[props.size] || 20
})

const sizeClass = computed(() => {
  if (typeof props.size === 'number') return ''
  return sizeClasses[props.size] || sizeClasses.md
})

const svgContent = computed(() => {
  const path = iconPaths[props.name]
  if (!path) {
    console.warn(`[AppIcon] Icon "${props.name}" not found in icon registry.`)
    return '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'
  }
  return path
})
</script>
```

### Usage Examples

```vue
<template>
  <!-- Individual icon component approach -->
  <IconDashboard size="lg" />
  <IconUsers class="text-blue-500" />

  <!-- Dynamic icon component approach -->
  <AppIcon name="dashboard" size="lg" />
  <AppIcon name="users" color="#3b82f6" :stroke-width="1.5" />
  <AppIcon name="settings" size="sm" class="text-slate-500 hover:text-slate-700" />

  <!-- In buttons -->
  <button class="btn-primary">
    <AppIcon name="plus" size="sm" />
    Add User
  </button>

  <!-- In navigation -->
  <nav>
    <a
      v-for="item in navItems"
      :key="item.name"
      :href="item.href"
      class="flex items-center gap-3 px-3 py-2 rounded-lg text-sidebar-text hover:text-sidebar-text-active hover:bg-sidebar-hover"
    >
      <AppIcon :name="item.icon" size="md" />
      <span>{{ item.label }}</span>
    </a>
  </nav>
</template>
```

### Approach 3: SVG Sprite System (For Large Icon Sets)

```typescript
// scripts/generate-sprite.ts
// Run with: npx tsx scripts/generate-sprite.ts
import fs from 'fs'
import path from 'path'
import { optimize } from 'svgo'

const ICONS_DIR = path.resolve('src/assets/icons')
const OUTPUT = path.resolve('public/icons-sprite.svg')

const icons = fs.readdirSync(ICONS_DIR).filter(f => f.endsWith('.svg'))

let symbols = ''

for (const file of icons) {
  const name = path.basename(file, '.svg')
  const raw = fs.readFileSync(path.join(ICONS_DIR, file), 'utf-8')
  const optimized = optimize(raw, {
    plugins: [
      { name: 'removeViewBox', active: false },
      { name: 'removeDimensions', active: true },
      { name: 'removeXMLNS', active: true },
    ],
  })

  const content = optimized.data
    .replace(/<svg[^>]*>/, '')
    .replace('</svg>', '')

  symbols += `  <symbol id="icon-${name}" viewBox="0 0 24 24">${content}</symbol>\n`
}

const sprite = `<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n${symbols}</svg>`
fs.writeFileSync(OUTPUT, sprite)
console.log(`Generated sprite with ${icons.length} icons`)
```

```vue
<!-- Sprite-based Icon component -->
<template>
  <svg
    :class="sizeClass"
    :aria-hidden="!ariaLabel"
    :aria-label="ariaLabel"
  >
    <use :href="`/icons-sprite.svg#icon-${name}`" />
  </svg>
</template>
```

---

## Dashboard Layout Components

### AdminLayout.vue

```vue
<!-- src/layouts/AdminLayout.vue -->
<script setup lang="ts">
import { useSidebar } from '@/composables/useSidebar'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'

const { isCollapsed, isMobileOpen, sidebarWidth, toggle, closeMobile } = useSidebar()
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-dashboard-bg dark:bg-slate-900">
    <!-- Sidebar -->
    <AppSidebar
      :is-collapsed="isCollapsed"
      :is-mobile-open="isMobileOpen"
      @close-mobile="closeMobile"
    />

    <!-- Mobile overlay -->
    <Transition
      enter-active-class="transition-opacity duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-300"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isMobileOpen"
        class="fixed inset-0 z-20 bg-black/50 lg:hidden"
        @click="closeMobile"
      />
    </Transition>

    <!-- Main Content Area -->
    <div
      class="flex flex-1 flex-col overflow-hidden transition-[margin] duration-300"
      :style="{ marginLeft: sidebarWidth }"
    >
      <AppHeader @toggle-sidebar="toggle" />

      <main class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
        <RouterView v-slot="{ Component, route }">
          <Transition
            name="fade"
            mode="out-in"
          >
            <component
              :is="Component"
              :key="route.path"
            />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
```

### AppSidebar.vue

```vue
<!-- src/components/layout/AppSidebar.vue -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/icons/AppIcon.vue'

interface NavItem {
  label: string
  icon: string
  to?: string
  children?: NavItem[]
  badge?: string | number
}

const props = defineProps<{
  isCollapsed: boolean
  isMobileOpen: boolean
}>()

const emit = defineEmits<{
  closeMobile: []
}>()

const route = useRoute()
const expandedGroups = ref<Set<string>>(new Set())

const navigation: NavItem[] = [
  { label: 'Dashboard', icon: 'dashboard', to: '/' },
  {
    label: 'Users',
    icon: 'users',
    children: [
      { label: 'All Users', icon: 'users', to: '/users' },
      { label: 'Roles', icon: 'shield', to: '/users/roles' },
      { label: 'Permissions', icon: 'lock', to: '/users/permissions' },
    ],
  },
  { label: 'Orders', icon: 'shopping-cart', to: '/orders', badge: 12 },
  { label: 'Analytics', icon: 'trending-up', to: '/analytics' },
  { label: 'Settings', icon: 'settings', to: '/settings' },
]

function isActive(to: string): boolean {
  return route.path === to || route.path.startsWith(to + '/')
}

function toggleGroup(label: string) {
  if (expandedGroups.value.has(label)) {
    expandedGroups.value.delete(label)
  } else {
    expandedGroups.value.add(label)
  }
}

const sidebarClasses = computed(() => [
  'fixed inset-y-0 left-0 z-30 flex flex-col bg-sidebar shadow-sidebar',
  'transition-all duration-300 ease-in-out',
  props.isCollapsed ? 'w-sidebar-collapsed' : 'w-sidebar',
  props.isMobileOpen
    ? 'translate-x-0'
    : '-translate-x-full lg:translate-x-0',
])
</script>

<template>
  <aside :class="sidebarClasses">
    <!-- Logo -->
    <div class="flex h-header items-center gap-3 border-b border-white/10 px-4">
      <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-600">
        <AppIcon name="dashboard" size="sm" class="text-white" />
      </div>
      <Transition
        enter-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        leave-active-class="transition-opacity duration-100"
        leave-to-class="opacity-0"
      >
        <span
          v-if="!isCollapsed"
          class="text-lg font-bold text-white whitespace-nowrap"
        >
          AdminPanel
        </span>
      </Transition>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 overflow-y-auto px-3 py-4">
      <ul class="space-y-1">
        <li v-for="item in navigation" :key="item.label">
          <!-- Simple link -->
          <RouterLink
            v-if="item.to && !item.children"
            :to="item.to"
            :class="[
              'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
              isActive(item.to)
                ? 'bg-sidebar-active text-sidebar-text-active'
                : 'text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active',
            ]"
            @click="emit('closeMobile')"
          >
            <AppIcon
              :name="item.icon"
              size="md"
              class="shrink-0"
            />
            <span v-if="!isCollapsed" class="truncate">{{ item.label }}</span>
            <span
              v-if="item.badge && !isCollapsed"
              class="ml-auto inline-flex items-center rounded-full bg-primary-600 px-2 py-0.5 text-xs font-medium text-white"
            >
              {{ item.badge }}
            </span>
          </RouterLink>

          <!-- Group with children -->
          <template v-if="item.children">
            <button
              :class="[
                'group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                'text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active',
              ]"
              @click="toggleGroup(item.label)"
            >
              <AppIcon :name="item.icon" size="md" class="shrink-0" />
              <span v-if="!isCollapsed" class="flex-1 truncate text-left">{{ item.label }}</span>
              <AppIcon
                v-if="!isCollapsed"
                name="chevron-right"
                size="sm"
                :class="[
                  'shrink-0 transition-transform duration-200',
                  expandedGroups.has(item.label) ? 'rotate-90' : '',
                ]"
              />
            </button>
            <Transition
              enter-active-class="transition-all duration-200 ease-out"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-96 opacity-100"
              leave-active-class="transition-all duration-150 ease-in"
              leave-from-class="max-h-96 opacity-100"
              leave-to-class="max-h-0 opacity-0"
            >
              <ul
                v-show="expandedGroups.has(item.label) && !isCollapsed"
                class="mt-1 space-y-1 overflow-hidden pl-10"
              >
                <li v-for="child in item.children" :key="child.label">
                  <RouterLink
                    :to="child.to!"
                    :class="[
                      'block rounded-lg px-3 py-2 text-sm transition-colors',
                      isActive(child.to!)
                        ? 'text-sidebar-text-active font-medium'
                        : 'text-sidebar-text hover:text-sidebar-text-active',
                    ]"
                    @click="emit('closeMobile')"
                  >
                    {{ child.label }}
                  </RouterLink>
                </li>
              </ul>
            </Transition>
          </template>
        </li>
      </ul>
    </nav>

    <!-- User section -->
    <div class="border-t border-white/10 p-3">
      <button
        class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-text hover:bg-sidebar-hover hover:text-sidebar-text-active transition-colors"
      >
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600 text-xs font-bold text-white">
          JD
        </div>
        <div v-if="!isCollapsed" class="flex-1 truncate text-left">
          <p class="font-medium text-sidebar-text-active">John Doe</p>
          <p class="text-xs text-sidebar-text">Administrator</p>
        </div>
        <AppIcon v-if="!isCollapsed" name="log-out" size="sm" class="shrink-0" />
      </button>
    </div>
  </aside>
</template>
```

### AppHeader.vue

```vue
<!-- src/components/layout/AppHeader.vue -->
<script setup lang="ts">
import { ref } from 'vue'
import { useTheme } from '@/composables/useTheme'
import AppIcon from '@/components/icons/AppIcon.vue'

const emit = defineEmits<{
  toggleSidebar: []
}>()

const { isDark, toggleTheme } = useTheme()
const showNotifications = ref(false)
const showProfile = ref(false)
const searchQuery = ref('')
</script>

<template>
  <header class="sticky top-0 z-10 flex h-header items-center gap-4 border-b border-dashboard-border bg-dashboard-card/80 px-4 backdrop-blur-sm dark:border-slate-700 dark:bg-slate-800/80 sm:px-6">
    <!-- Menu toggle -->
    <button
      class="btn-ghost -ml-2 !p-2"
      aria-label="Toggle sidebar"
      @click="emit('toggleSidebar')"
    >
      <AppIcon name="menu" size="md" />
    </button>

    <!-- Search -->
    <div class="relative hidden flex-1 sm:block sm:max-w-md">
      <AppIcon
        name="search"
        size="sm"
        class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
      />
      <input
        v-model="searchQuery"
        type="search"
        placeholder="Search anything..."
        class="input-field pl-10"
      />
      <kbd class="absolute right-3 top-1/2 -translate-y-1/2 hidden rounded border border-slate-300 px-1.5 py-0.5 text-xs text-slate-400 lg:inline dark:border-slate-600">
        ⌘K
      </kbd>
    </div>

    <div class="ml-auto flex items-center gap-2">
      <!-- Theme toggle -->
      <button
        class="btn-ghost !p-2"
        :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        <AppIcon :name="isDark ? 'sun' : 'moon'" size="md" />
      </button>

      <!-- Notifications -->
      <div class="relative">
        <button
          class="btn-ghost relative !p-2"
          @click="showNotifications = !showNotifications"
        >
          <AppIcon name="bell" size="md" />
          <span class="absolute right-1 top-1 flex h-2.5 w-2.5">
            <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75" />
            <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
          </span>
        </button>
      </div>

      <!-- Profile -->
      <button class="flex items-center gap-2 rounded-lg p-1.5 hover:bg-slate-100 dark:hover:bg-slate-700">
        <img
          src="https://ui-avatars.com/api/?name=John+Doe&background=3b82f6&color=fff&size=32"
          alt="Profile"
          class="h-8 w-8 rounded-full"
        />
      </button>
    </div>
  </header>
</template>
```

---

## Data Tables & Lists

### DataTable Component

```vue
<!-- src/components/tables/DataTable.vue -->
<script setup lang="ts" generic="T extends Record<string, any>">
import AppIcon from '@/components/icons/AppIcon.vue'
import type { TableColumn } from '@/composables/useDataTable'

interface Props {
  columns: TableColumn[]
  data: T[]
  loading?: boolean
  sortBy?: string
  sortDirection?: 'asc' | 'desc'
  selectedRows?: Set<string | number>
  isAllSelected?: boolean
  emptyTitle?: string
  emptyDescription?: string
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  sortBy: '',
  sortDirection: 'asc',
  emptyTitle: 'No data found',
  emptyDescription: 'Try adjusting your search or filters.',
})

const emit = defineEmits<{
  sort: [key: string]
  selectAll: []
  selectRow: [id: string | number]
}>()
</script>

<template>
  <div class="card overflow-hidden">
    <!-- Table header with slot for filters -->
    <div
      v-if="$slots.header"
      class="border-b border-dashboard-border px-4 py-3 dark:border-slate-700 sm:px-6"
    >
      <slot name="header" />
    </div>

    <!-- Table -->
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead class="border-b border-dashboard-border bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50">
          <tr>
            <!-- Selection checkbox -->
            <th
              v-if="selectedRows"
              class="w-12 px-4 py-3"
            >
              <input
                type="checkbox"
                class="form-checkbox h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                :checked="isAllSelected"
                @change="emit('selectAll')"
              />
            </th>
            <th
              v-for="col in columns"
              :key="col.key"
              :class="[
                'px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400',
                col.sortable ? 'cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200' : '',
                col.align === 'center' && 'text-center',
                col.align === 'right' && 'text-right',
              ]"
              :style="col.width ? { width: col.width } : undefined"
              @click="col.sortable && emit('sort', col.key)"
            >
              <div class="flex items-center gap-1.5" :class="col.align === 'right' && 'justify-end'">
                {{ col.label }}
                <template v-if="col.sortable && sortBy === col.key">
                  <AppIcon
                    :name="sortDirection === 'asc' ? 'arrow-up' : 'arrow-down'"
                    size="xs"
                    class="text-primary-600"
                  />
                </template>
              </div>
            </th>
            <!-- Actions column -->
            <th
              v-if="$slots.actions"
              class="w-20 px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
              Actions
            </th>
          </tr>
        </thead>

        <tbody class="divide-y divide-dashboard-border dark:divide-slate-700">
          <!-- Loading state -->
          <template v-if="loading">
            <tr v-for="i in 5" :key="`skeleton-${i}`">
              <td
                v-if="selectedRows"
                class="px-4 py-3"
              >
                <div class="h-4 w-4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
              </td>
              <td
                v-for="col in columns"
                :key="`skeleton-${i}-${col.key}`"
                class="px-4 py-3"
              >
                <div class="h-4 w-3/4 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
              </td>
              <td v-if="$slots.actions" class="px-4 py-3">
                <div class="ml-auto h-4 w-8 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
              </td>
            </tr>
          </template>

          <!-- Data rows -->
          <template v-else-if="data.length > 0">
            <tr
              v-for="(row, index) in data"
              :key="row.id ?? index"
              class="group transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50"
            >
              <td
                v-if="selectedRows"
                class="px-4 py-3"
              >
                <input
                  type="checkbox"
                  class="form-checkbox h-4 w-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                  :checked="selectedRows.has(row.id)"
                  @change="emit('selectRow', row.id)"
                />
              </td>
              <td
                v-for="col in columns"
                :key="col.key"
                :class="[
                  'px-4 py-3 text-slate-700 dark:text-slate-300',
                  col.align === 'center' && 'text-center',
                  col.align === 'right' && 'text-right',
                ]"
              >
                <slot
                  :name="`cell-${col.key}`"
                  :value="row[col.key]"
                  :row="row"
                  :column="col"
                >
                  {{ col.formatter ? col.formatter(row[col.key], row) : row[col.key] }}
                </slot>
              </td>
              <td
                v-if="$slots.actions"
                class="px-4 py-3 text-right"
              >
                <slot name="actions" :row="row" :index="index" />
              </td>
            </tr>
          </template>

          <!-- Empty state -->
          <tr v-else>
            <td
              :colspan="columns.length + (selectedRows ? 1 : 0) + ($slots.actions ? 1 : 0)"
              class="px-4 py-12 text-center"
            >
              <div class="flex flex-col items-center">
                <AppIcon name="search" size="xl" class="text-slate-300 dark:text-slate-600 mb-3" />
                <p class="text-sm font-medium text-slate-900 dark:text-white">{{ emptyTitle }}</p>
                <p class="mt-1 text-sm text-slate-500">{{ emptyDescription }}</p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div
      v-if="$slots.pagination"
      class="border-t border-dashboard-border px-4 py-3 dark:border-slate-700 sm:px-6"
    >
      <slot name="pagination" />
    </div>
  </div>
</template>
```

---

## StatsCard Component

```vue
<!-- src/components/dashboard/StatsCard.vue -->
<script setup lang="ts">
import { computed, type Component } from 'vue'
import AppIcon from '@/components/icons/AppIcon.vue'

interface Props {
  title: string
  value: number
  change: number
  format: 'currency' | 'number' | 'percentage'
  icon: Component
  color: 'blue' | 'emerald' | 'purple' | 'amber' | 'red'
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const colorClasses: Record<string, { bg: string; icon: string }> = {
  blue:    { bg: 'bg-blue-100 dark:bg-blue-900/30', icon: 'text-blue-600 dark:text-blue-400' },
  emerald: { bg: 'bg-emerald-100 dark:bg-emerald-900/30', icon: 'text-emerald-600 dark:text-emerald-400' },
  purple:  { bg: 'bg-purple-100 dark:bg-purple-900/30', icon: 'text-purple-600 dark:text-purple-400' },
  amber:   { bg: 'bg-amber-100 dark:bg-amber-900/30', icon: 'text-amber-600 dark:text-amber-400' },
  red:     { bg: 'bg-red-100 dark:bg-red-900/30', icon: 'text-red-600 dark:text-red-400' },
}

const formattedValue = computed(() => {
  if (props.loading) return '—'
  switch (props.format) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(props.value)
    case 'percentage':
      return `${props.value.toFixed(1)}%`
    case 'number':
    default:
      return new Intl.NumberFormat('en-US').format(props.value)
  }
})

const isPositiveChange = computed(() => props.change >= 0)
</script>

<template>
  <div class="card-hover p-5">
    <div class="flex items-start justify-between">
      <div class="space-y-2">
        <p class="text-sm font-medium text-slate-500 dark:text-slate-400">
          {{ title }}
        </p>
        <div v-if="loading" class="h-8 w-24 animate-pulse rounded bg-slate-200 dark:bg-slate-700" />
        <p v-else class="text-2xl font-bold text-slate-900 dark:text-white">
          {{ formattedValue }}
        </p>
      </div>
      <div :class="['rounded-xl p-3', colorClasses[color].bg]">
        <component
          :is="icon"
          :class="['h-6 w-6', colorClasses[color].icon]"
        />
      </div>
    </div>
    <div v-if="!loading" class="mt-3 flex items-center gap-1.5 text-sm">
      <span
        :class="[
          'flex items-center gap-0.5 font-medium',
          isPositiveChange ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400',
        ]"
      >
        <AppIcon
          :name="isPositiveChange ? 'trending-up' : 'trending-down'"
          size="sm"
        />
        {{ Math.abs(change) }}%
      </span>
      <span class="text-slate-500 dark:text-slate-400">vs last period</span>
    </div>
  </div>
</template>
```

---

## Forms & Validation

### useFormValidation Composable

```typescript
// src/composables/useFormValidation.ts
import { ref, reactive, computed, type Ref } from 'vue'

type ValidationRule = (value: any) => string | true
type ValidationRules = Record<string, ValidationRule[]>

export function useFormValidation<T extends Record<string, any>>(
  initialValues: T,
  rules: ValidationRules
) {
  const values = reactive({ ...initialValues }) as T
  const errors = reactive<Record<string, string>>({})
  const touched = reactive<Record<string, boolean>>({})
  const isSubmitting = ref(false)

  const isValid = computed(() => {
    return Object.keys(rules).every((key) => !errors[key])
  })

  const isDirty = computed(() => {
    return Object.keys(initialValues).some(
      (key) => values[key as keyof T] !== initialValues[key as keyof T]
    )
  })

  function validateField(field: string): boolean {
    const fieldRules = rules[field]
    if (!fieldRules) return true

    for (const rule of fieldRules) {
      const result = rule(values[field as keyof T])
      if (result !== true) {
        errors[field] = result
        return false
      }
    }

    errors[field] = ''
    return true
  }

  function validateAll(): boolean {
    let allValid = true
    for (const field of Object.keys(rules)) {
      touched[field] = true
      if (!validateField(field)) {
        allValid = false
      }
    }
    return allValid
  }

  function setFieldValue(field: keyof T, value: any) {
    ;(values as any)[field] = value
    if (touched[field as string]) {
      validateField(field as string)
    }
  }

  function touchField(field: string) {
    touched[field] = true
    validateField(field)
  }

  function reset() {
    Object.assign(values, initialValues)
    Object.keys(errors).forEach((key) => (errors[key] = ''))
    Object.keys(touched).forEach((key) => (touched[key] = false))
  }

  async function handleSubmit(onSubmit: (values: T) => Promise<void>) {
    if (!validateAll()) return

    isSubmitting.value = true
    try {
      await onSubmit({ ...values })
    } finally {
      isSubmitting.value = false
    }
  }

  return {
    values,
    errors,
    touched,
    isValid,
    isDirty,
    isSubmitting,
    validateField,
    validateAll,
    setFieldValue,
    touchField,
    reset,
    handleSubmit,
  }
}

// Common validation rules
export const validators = {
  required: (message = 'This field is required'): ValidationRule =>
    (value) => (value != null && value !== '' ? true : message),

  email: (message = 'Invalid email address'): ValidationRule =>
    (value) => (!value || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? true : message),

  minLength: (min: number, message?: string): ValidationRule =>
    (value) => (!value || value.length >= min ? true : message || `Minimum ${min} characters`),

  maxLength: (max: number, message?: string): ValidationRule =>
    (value) => (!value || value.length <= max ? true : message || `Maximum ${max} characters`),

  pattern: (regex: RegExp, message = 'Invalid format'): ValidationRule =>
    (value) => (!value || regex.test(value) ? true : message),

  numeric: (message = 'Must be a number'): ValidationRule =>
    (value) => (!value || !isNaN(Number(value)) ? true : message),
}
```

### FormField Component

```vue
<!-- src/components/forms/FormField.vue -->
<script setup lang="ts">
interface Props {
  label: string
  error?: string
  required?: boolean
  hint?: string
  id?: string
}

defineProps<Props>()
</script>

<template>
  <div class="space-y-1.5">
    <label
      :for="id"
      class="block text-sm font-medium text-slate-700 dark:text-slate-300"
    >
      {{ label }}
      <span v-if="required" class="text-red-500">*</span>
    </label>
    <slot />
    <p v-if="error" class="text-sm text-red-600 dark:text-red-400">
      {{ error }}
    </p>
    <p v-else-if="hint" class="text-sm text-slate-500 dark:text-slate-400">
      {{ hint }}
    </p>
  </div>
</template>
```

---

## State Management with Pinia

### Auth Store

```typescript
// src/stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/utils/api'

interface User {
  id: string
  email: string
  firstName: string
  lastName: string
  role: string
  avatar?: string
  permissions: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter()
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('auth-token'))
  const isLoading = ref(false)

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const fullName = computed(() =>
    user.value ? `${user.value.firstName} ${user.value.lastName}` : ''
  )
  const initials = computed(() =>
    user.value
      ? `${user.value.firstName[0]}${user.value.lastName[0]}`.toUpperCase()
      : ''
  )

  function hasPermission(permission: string): boolean {
    return user.value?.permissions.includes(permission) ?? false
  }

  function hasRole(role: string): boolean {
    return user.value?.role === role
  }

  async function login(email: string, password: string) {
    isLoading.value = true
    try {
      const response = await api.post('/auth/login', { email, password })
      token.value = response.data.token
      user.value = response.data.user
      localStorage.setItem('auth-token', response.data.token)
      api.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`
      await router.push('/')
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('auth-token')
    delete api.defaults.headers.common['Authorization']
    await router.push('/auth/login')
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
      const response = await api.get('/auth/me')
      user.value = response.data
    } catch {
      await logout()
    }
  }

  return {
    user,
    token,
    isLoading,
    isAuthenticated,
    fullName,
    initials,
    hasPermission,
    hasRole,
    login,
    logout,
    fetchUser,
  }
})
```

---

## Performance Optimization

### Best Practices Checklist

| Technique | Implementation |
|-----------|---------------|
| Route-level code splitting | `() => import('./pages/Users.vue')` |
| Virtual scrolling for long lists | Use `@tanstack/vue-virtual` |
| Debounce search inputs | `useDebounceFn` from `@vueuse/core` |
| Memoize expensive computations | `computed()` with minimal dependencies |
| Image lazy loading | `loading="lazy"` attribute |
| Component lazy loading | `defineAsyncComponent()` |
| SVG icon tree-shaking | Import only used icons |
| Tailwind CSS purging | Enabled by default in v3+ |
| Keep-alive for tabs | `<KeepAlive>` with `include` |

### Lazy-loaded Route Configuration

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/layouts/AdminLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/pages/Dashboard.vue'),
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/pages/Users.vue'),
          meta: { permission: 'users.view' },
        },
        {
          path: 'users/:id',
          name: 'user-detail',
          component: () => import('@/pages/UserDetail.vue'),
          props: true,
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/pages/Settings.vue'),
          meta: { permission: 'settings.manage' },
        },
      ],
    },
    {
      path: '/auth',
      component: () => import('@/layouts/AuthLayout.vue'),
      children: [
        {
          path: 'login',
          name: 'login',
          component: () => import('@/pages/auth/Login.vue'),
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/pages/NotFound.vue'),
    },
  ],
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  if (to.meta.permission && !authStore.hasPermission(to.meta.permission as string)) {
    return next({ name: 'dashboard' })
  }

  next()
})

export default router
```

---

## Security Considerations

### Key Security Practices

1. **Never store sensitive data in localStorage** — use httpOnly cookies for tokens when possible
2. **Sanitize HTML content** — never use `v-html` with user-generated content without sanitization
3. **Implement CSRF protection** — include CSRF tokens in API requests
4. **Use Content Security Policy headers** — restrict inline scripts and styles
5. **Rate-limit API calls** — implement client-side throttling
6. **Permission-based rendering** — hide UI elements users cannot access

### Permission Directive

```typescript
// src/directives/vPermission.ts
import type { Directive } from 'vue'
import { useAuthStore } from '@/stores/auth'

export const vPermission: Directive<HTMLElement, string | string[]> = {
  mounted(el, binding) {
    const authStore = useAuthStore()
    const permissions = Array.isArray(binding.value) ? binding.value : [binding.value]
    const hasPermission = permissions.some((p) => authStore.hasPermission(p))

    if (!hasPermission) {
      el.style.display = 'none'
      // Or: el.parentNode?.removeChild(el)
    }
  },
}

// Usage in template:
// <button v-permission="'users.delete'" class="btn-danger">Delete</button>
// <div v-permission="['analytics.view', 'analytics.export']">...</div>
```

### XSS Protection Helper

```typescript
// src/utils/sanitize.ts
export function sanitizeHtml(html: string): string {
  const div = document.createElement('div')
  div.textContent = html
  return div.innerHTML
}

export function escapeHtml(str: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  }
  return str.replace(/[&<>"']/g, (m) => map[m])
}
```

---

## Common Pitfalls & Troubleshooting

### Pitfall 1: Reactivity Lost with Destructuring

```typescript
// ❌ BAD — loses reactivity
const { count } = reactive({ count: 0 })

// ✅ GOOD — use toRefs
const state = reactive({ count: 0 })
const { count } = toRefs(state)

// ✅ GOOD — or just use ref
const count = ref(0)
```

### Pitfall 2: SVG Icons Not Inheriting Color

```vue
<!-- ❌ BAD — hardcoded fill/stroke won't respond to CSS -->
<svg fill="#000" stroke="#000">...</svg>

<!-- ✅ GOOD — use currentColor -->
<svg fill="none" stroke="currentColor">...</svg>

<!-- Then control color with Tailwind -->
<AppIcon name="users" class="text-blue-500" />
```

### Pitfall 3: Tailwind Classes Not Working on Dynamic Values

```vue
<!-- ❌ BAD — dynamic class construction is NOT tree-shaken -->
<div :class="`bg-${color}-500`">

<!-- ✅ GOOD — use a lookup object with full class names -->
<script setup>
const colorMap = {
  blue: 'bg-blue-500',
  red: 'bg-red-500',
  green: 'bg-green-500',
}
</script>
<div :class="colorMap[color]">
```

### Pitfall 4: Watch Not Triggering for Deep Objects

```typescript
// ❌ BAD — won't detect nested changes
watch(filters, () => fetchData())

// ✅ GOOD — use deep option
watch(filters, () => fetchData(), { deep: true })

// ✅ BETTER — watch specific paths
watch(
  () => filters.value.status,
  () => fetchData()
)
```

### Pitfall 5: Memory Leaks with Event Listeners

```typescript
// ❌ BAD — listener not cleaned up
onMounted(() => {
  window.addEventListener('resize', handleResize)
})

// ✅ GOOD — clean up in onUnmounted
onMounted(() => {
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

// ✅ BEST — use VueUse which handles cleanup automatically
import { useEventListener } from '@vueuse/core'
useEventListener(window, 'resize', handleResize)
```

### Pitfall 6: Excessive Re-renders in Large Tables

```typescript
// ❌ BAD — creating new objects every render cycle
const formattedData = computed(() =>
  data.value.map(item => ({ ...item, formatted: format(item) }))
)

// ✅ GOOD — use shallowRef for flat data or markRaw for non-reactive objects
import { shallowRef, triggerRef } from 'vue'
const tableData = shallowRef<Item[]>([])

function updateData(newData: Item[]) {
  tableData.value = newData
  triggerRef(tableData)
}
```

### Pitfall 7: Tailwind Dark Mode Flicker on Load

```html
<!-- Add this to index.html <head> BEFORE any CSS loads -->
<script>
  if (localStorage.getItem('admin-theme') === 'dark' ||
      (!localStorage.getItem('admin-theme') &&
       window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark')
  }
</script>
```

---

## Comprehensive SVG Icon Generation Script

For generating admin-specific icons programmatically:

```typescript
// scripts/generate-icons.ts
import fs from 'fs'
import path from 'path'

interface IconDefinition {
  name: string
  viewBox: string
  paths: string
}

const adminIcons: IconDefinition[] = [
  {
    name: 'dashboard-analytics',
    viewBox: '0 0 24 24',
    paths: `
      <path d="M3 3v18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
      <path d="M7 16l4-8 4 4 5-9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    `,
  },
  {
    name: 'user-shield',
    viewBox: '0 0 24 24',
    paths: `
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" stroke="currentColor" stroke-width="2" fill="none"/>
      <circle cx="12" cy="9" r="3" stroke="currentColor" stroke-width="2" fill="none"/>
      <path d="M5.5 19.5c1.5-3 3.8-4.5 6.5-4.5s5 1.5 6.5 4.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/>
    `,
  },
]

function generateVueComponent(icon: IconDefinition): string {
  const componentName = icon.name
    .split('-')
    .map(s => s.charAt(0).toUpperCase() + s.slice(1))
    .join('')

  return `<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="${icon.viewBox}"
    :class="sizeClass"
    aria-hidden="true"
  >
    ${icon.paths.trim()}
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}>(), { size: 'md' })

const sizeMap: Record<string, string> = {
  xs: 'w-3 h-3', sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-6 h-6', xl: 'w-8 h-8',
}
const sizeClass = computed(() => sizeMap[props.size])
</script>
`
}

// Generate files
const outputDir = path.resolve('src/components/icons')
fs.mkdirSync(outputDir, { recursive: true })

for (const icon of adminIcons) {
  const componentName = 'Icon' + icon.name
    .split('-')
    .map(s => s.charAt(0).toUpperCase() + s.slice(1))
    .join('')

  const filePath = path.join(outputDir, `${componentName}.vue`)
  fs.writeFileSync(filePath, generateVueComponent(icon))
  console.log(`Generated: ${componentName}.vue`)
}

// Generate barrel export
const exports = adminIcons.map((icon) => {
  const name = 'Icon' + icon.name
    .split('-')
    .map(s => s.charAt(0).toUpperCase() + s.slice(1))
    .join('')
  return `export { default as ${name} } from './${name}.vue'`
}).join('\n')

fs.writeFileSync(path.join(outputDir, 'index.ts'), exports + '\n')
console.log('Generated: index.ts barrel export')
```

---

## Summary of Best Practices

1. **Composition API**: Always use `<script setup>` for concise, type-safe components
2. **Composables**: Extract shared logic (auth, tables, sidebar, theme) into reusable composables
3. **Tailwind**: Configure a design system via `tailwind.config.js`, use `@layer components` for repeated patterns, never construct class names dynamically
4. **SVG Icons**: Use inline SVGs with `currentColor` for full CSS control; prefer individual components for tree-shaking or a path registry for flexibility
5. **Performance**: Lazy-load routes and heavy components, debounce user inputs, use `shallowRef` for flat data
6. **Security**: Guard routes with navigation guards, use permission directives, sanitize user input
7. **Dark Mode**: Use Tailwind's `class` strategy with a system-aware composable and an inline script to prevent flash
8. **State**: Use Pinia stores for global state (auth, notifications, UI) and local `ref`/`reactive` for component state
9. **TypeScript**: Type all props, emits, composable returns, and API responses for robust maintenance
10. **Accessibility**: Include proper ARIA attributes on icons, form fields, and interactive elements