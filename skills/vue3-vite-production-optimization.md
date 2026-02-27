Vue 3 Composition API with Vite production build optimization — code splitting, lazy loading, instant load times, bundle analysis, and deployment best practices.

# Vue 3 + Vite Production Build Optimization

## Table of Contents

1. [Vite Configuration for Production](#vite-config)
2. [Code Splitting and Lazy Loading](#code-splitting)
3. [Router-Level Code Splitting](#router-code-splitting)
4. [Component Lazy Loading](#component-lazy-loading)
5. [Asset Optimization](#asset-optimization)
6. [Chunk Strategy and Manual Chunks](#chunk-strategy)
7. [Compression: Gzip and Brotli](#compression)
8. [Environment Variables and Build Modes](#env-variables)
9. [PWA and Service Worker](#pwa)
10. [Bundle Analysis](#bundle-analysis)
11. [Performance Monitoring](#performance-monitoring)
12. [Vue 3 Composition API Performance Patterns](#vue3-performance)
13. [Vite Plugin Ecosystem](#vite-plugins)
14. [Nginx Serving Configuration](#nginx-serving)
15. [CI/CD Build Pipeline](#cicd)
16. [Common Pitfalls](#pitfalls)

---

## Vite Configuration for Production

### vite.config.ts — Complete Production Setup

```typescript
// vite.config.ts
import { defineConfig, type UserConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';
import { visualizer } from 'rollup-plugin-visualizer';
import viteCompression from 'vite-plugin-compression';

export default defineConfig(({ mode }): UserConfig => {
  const isProd = mode === 'production';

  return {
    plugins: [
      vue({
        // Enable reactive props destructure (Vue 3.4+)
        script: {
          defineModel: true,
          propsDestructure: true,
        },
      }),

      // Gzip compression
      isProd && viteCompression({
        algorithm: 'gzip',
        ext: '.gz',
        threshold: 1024,      // only compress files > 1KB
        deleteOriginFile: false,
      }),

      // Brotli compression (better than gzip, ~20% smaller)
      isProd && viteCompression({
        algorithm: 'brotliCompress',
        ext: '.br',
        threshold: 1024,
        deleteOriginFile: false,
      }),

      // Bundle analyzer (only when ANALYZE=true)
      process.env.ANALYZE && visualizer({
        open: true,
        filename: 'dist/stats.html',
        gzipSize: true,
        brotliSize: true,
      }),
    ].filter(Boolean),

    // Path aliases
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@components': resolve(__dirname, 'src/components'),
        '@composables': resolve(__dirname, 'src/composables'),
        '@views': resolve(__dirname, 'src/views'),
        '@stores': resolve(__dirname, 'src/stores'),
        '@utils': resolve(__dirname, 'src/utils'),
        '@assets': resolve(__dirname, 'src/assets'),
        '@api': resolve(__dirname, 'src/api'),
      },
    },

    // Build configuration
    build: {
      target: 'es2020',           // modern browsers only
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: isProd ? false : true,  // no sourcemaps in prod (smaller, no code exposure)
      minify: 'terser',           // 'terser' for best compression, 'esbuild' for speed

      terserOptions: {
        compress: {
          drop_console: isProd,    // remove console.log in production
          drop_debugger: isProd,   // remove debugger statements
          pure_funcs: isProd ? ['console.log', 'console.info', 'console.debug'] : [],
          passes: 2,               // extra compression pass
        },
        mangle: {
          safari10: true,          // Safari 10 compat
        },
      },

      // Rollup options
      rollupOptions: {
        output: {
          // Manual chunk splitting strategy
          manualChunks(id) {
            // Vue core — changes rarely, cache forever
            if (id.includes('node_modules/vue')
              || id.includes('node_modules/@vue')
              || id.includes('node_modules/vue-router')
              || id.includes('node_modules/pinia')
              || id.includes('node_modules/vuex')) {
              return 'vue-vendor';
            }

            // Socket.io client
            if (id.includes('node_modules/socket.io-client')
              || id.includes('node_modules/engine.io-client')) {
              return 'socket-vendor';
            }

            // UI libraries (if any)
            if (id.includes('node_modules/chart.js')
              || id.includes('node_modules/apexcharts')) {
              return 'charts-vendor';
            }

            // Date libraries
            if (id.includes('node_modules/dayjs')
              || id.includes('node_modules/date-fns')) {
              return 'date-vendor';
            }

            // All other node_modules
            if (id.includes('node_modules')) {
              return 'vendor';
            }
          },

          // File naming with content hashes for cache busting
          chunkFileNames: 'assets/js/[name]-[hash].js',
          entryFileNames: 'assets/js/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            const ext = assetInfo.name?.split('.').pop();
            if (/png|jpe?g|svg|gif|tiff|bmp|ico|webp|avif/i.test(ext || '')) {
              return 'assets/images/[name]-[hash][extname]';
            }
            if (/woff2?|eot|ttf|otf/i.test(ext || '')) {
              return 'assets/fonts/[name]-[hash][extname]';
            }
            if (ext === 'css') {
              return 'assets/css/[name]-[hash][extname]';
            }
            return 'assets/[name]-[hash][extname]';
          },
        },
      },

      // Chunk size warning limit
      chunkSizeWarningLimit: 500, // KB — warn if any chunk > 500KB

      // CSS code splitting
      cssCodeSplit: true,

      // Asset inlining threshold — inline small assets as base64
      assetsInlineLimit: 4096,    // 4KB — files smaller than this become base64 in JS
    },

    // CSS configuration
    css: {
      devSourcemap: true,
      preprocessorOptions: {
        // If using SCSS
        scss: {
          additionalData: `@use "@/styles/variables" as *;`,
        },
      },
    },

    // Server configuration (dev)
    server: {
      port: 5173,
      host: true,
      proxy: {
        '/api': {
          target: 'http://localhost:3000',
          changeOrigin: true,
        },
        '/socket.io': {
          target: 'http://localhost:3000',
          ws: true,
          changeOrigin: true,
        },
      },
    },

    // Preview server (test production build locally)
    preview: {
      port: 4173,
      host: true,
    },

    // Dependency optimization
    optimizeDeps: {
      include: [
        'vue',
        'vue-router',
        'pinia',
        'socket.io-client',
        'axios',
      ],
      exclude: [],
    },
  };
});
```

---

## Code Splitting and Lazy Loading

### Why Code Splitting Matters

Without code splitting, the entire app is one massive JavaScript bundle. The user downloads everything (admin pages, settings, rare features) just to see the landing page. Code splitting loads only what's needed.

```
❌ Without code splitting:
main.js — 2.5MB (everything)

✅ With code splitting:
main.js          — 80KB  (core app shell)
vue-vendor.js    — 120KB (Vue, Router, Pinia)
vendor.js        — 90KB  (other libs)
home.js          — 15KB  (home page — loaded on visit)
competition.js   — 45KB  (competition page — loaded on visit)
admin.js         — 60KB  (admin panel — loaded only for admins)
```

---

## Router-Level Code Splitting

### Lazy Routes — The Most Impactful Optimization

```typescript
// router/index.ts
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/DefaultLayout.vue'),
    children: [
      {
        path: '',
        name: 'Home',
        // Lazy load with webpackChunkName / rollup naming
        component: () => import('@/views/HomePage.vue'),
      },
      {
        path: 'competitions',
        name: 'Competitions',
        component: () => import('@/views/CompetitionsPage.vue'),
      },
      {
        path: 'competitions/:id',
        name: 'CompetitionDetail',
        component: () => import('@/views/CompetitionDetailPage.vue'),
        props: true,
      },
      {
        path: 'competitions/:id/live',
        name: 'CompetitionLive',
        // This page has Socket.io — it pulls in socket-vendor chunk only when needed
        component: () => import('@/views/CompetitionLivePage.vue'),
        props: true,
        meta: { requiresAuth: true },
      },
      {
        path: 'leaderboard',
        name: 'Leaderboard',
        component: () => import('@/views/LeaderboardPage.vue'),
      },
      {
        path: 'profile/:id?',
        name: 'Profile',
        component: () => import('@/views/ProfilePage.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },

  // Auth pages — separate layout, separate chunk
  {
    path: '/auth',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      {
        path: 'login',
        name: 'Login',
        component: () => import('@/views/auth/LoginPage.vue'),
      },
      {
        path: 'register',
        name: 'Register',
        component: () => import('@/views/auth/RegisterPage.vue'),
      },
    ],
  },

  // Admin — completely separate chunk, only loaded for admins
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/DashboardPage.vue'),
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/UsersPage.vue'),
      },
      {
        path: 'competitions',
        name: 'AdminCompetitions',
        component: () => import('@/views/admin/CompetitionsPage.vue'),
      },
    ],
  },

  // 404
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundPage.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition;
    if (to.hash) return { el: to.hash, behavior: 'smooth' };
    return { top: 0, behavior: 'smooth' };
  },
});

// Navigation guard for auth
router.beforeEach(async (to, from) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'Login', query: { redirect: to.fullPath } };
  }

  if (to.meta.requiresAdmin && authStore.user?.role !== 'admin') {
    return { name: 'Home' };
  }
});

export default router;
```

### Route-Level Prefetching

```typescript
// Prefetch routes the user is likely to visit
router.afterEach((to) => {
  // When user visits competitions list, prefetch detail page
  if (to.name === 'Competitions') {
    import('@/views/CompetitionDetailPage.vue');
  }
  // When user visits a competition, prefetch live page
  if (to.name === 'CompetitionDetail') {
    import('@/views/CompetitionLivePage.vue');
  }
});
```

---

## Component Lazy Loading

### defineAsyncComponent for Heavy Components

```typescript
// Only load chart component when it's actually rendered
import { defineAsyncComponent } from 'vue';

const ScoreChart = defineAsyncComponent({
  loader: () => import('@/components/charts/ScoreChart.vue'),
  loadingComponent: () => import('@/components/ui/ChartSkeleton.vue'),
  delay: 200,         // show loading after 200ms (prevents flash for fast loads)
  timeout: 10000,     // 10s timeout
  errorComponent: () => import('@/components/ui/ErrorFallback.vue'),
  onError(error, retry, fail, attempts) {
    if (attempts <= 3) {
      retry();        // auto-retry up to 3 times
    } else {
      fail();
    }
  },
});

// Simple lazy component (no loading/error handling)
const AdminPanel = defineAsyncComponent(() => import('@/components/AdminPanel.vue'));
const RichTextEditor = defineAsyncComponent(() => import('@/components/RichTextEditor.vue'));
```

### Conditional Lazy Loading

```vue
<script setup lang="ts">
import { defineAsyncComponent, ref } from 'vue';

const showChart = ref(false);

// Chart only loads when user clicks "Show Stats"
const ScoreChart = defineAsyncComponent(() => import('@/components/charts/ScoreChart.vue'));
</script>

<template>
  <button @click="showChart = true">Show Stats</button>
  <ScoreChart v-if="showChart" :data="chartData" />
</template>
```

### Intersection Observer — Load on Scroll into View

```vue
<script setup lang="ts">
import { ref, onMounted, defineAsyncComponent } from 'vue';

const containerRef = ref<HTMLElement>();
const isVisible = ref(false);

const HeavyComponent = defineAsyncComponent(() => import('@/components/HeavyComponent.vue'));

onMounted(() => {
  const observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        isVisible.value = true;
        observer.disconnect();
      }
    },
    { rootMargin: '200px' } // start loading 200px before visible
  );

  if (containerRef.value) {
    observer.observe(containerRef.value);
  }
});
</script>

<template>
  <div ref="containerRef" style="min-height: 200px;">
    <HeavyComponent v-if="isVisible" />
    <div v-else class="animate-pulse bg-zinc-200 dark:bg-zinc-800 rounded-2xl h-48" />
  </div>
</template>
```

---

## Asset Optimization

### Image Optimization

```typescript
// vite.config.ts — add image optimization plugin
import viteImagemin from 'vite-plugin-imagemin';

plugins: [
  isProd && viteImagemin({
    gifsicle: { optimizationLevel: 3 },
    mozjpeg: { quality: 80 },
    pngquant: { quality: [0.65, 0.9], speed: 4 },
    svgo: {
      plugins: [
        { name: 'removeViewBox', active: false },
        { name: 'removeEmptyAttrs', active: true },
      ],
    },
    webp: { quality: 80 },    // auto-generate WebP
    avif: { quality: 50 },    // auto-generate AVIF
  }),
],
```

### Responsive Images in Vue

```vue
<template>
  <picture>
    <source srcset="/images/hero.avif" type="image/avif" />
    <source srcset="/images/hero.webp" type="image/webp" />
    <img
      src="/images/hero.jpg"
      alt="Hero"
      loading="lazy"
      decoding="async"
      width="1200"
      height="600"
      class="w-full h-auto rounded-2xl"
    />
  </picture>
</template>
```

### Font Optimization

```css
/* Preload critical fonts in index.html */
/* <link rel="preload" href="/fonts/inter-var.woff2" as="font" type="font/woff2" crossorigin> */

/* Use font-display: swap to prevent FOIT */
@font-face {
  font-family: 'Inter';
  src: url('/fonts/inter-var.woff2') format('woff2');
  font-display: swap;
  font-weight: 100 900;
}
```

---

## Chunk Strategy and Manual Chunks

### Analyzing and Optimizing Chunks

```bash
# Build with analysis
ANALYZE=true npm run build

# Check chunk sizes
ls -lhS dist/assets/js/
```

### Dynamic Import Grouping

```typescript
// Group related components into the same chunk
// using Vite's glob import

// All competition page components in one chunk
const competitionModules = import.meta.glob('@/views/competition/*.vue');

// Explicitly named chunks
const CompetitionBracket = () => import(
  /* @vite-ignore */
  '@/components/competition/BracketView.vue'
);
```

---

## Compression: Gzip and Brotli

### Pre-compress During Build

```bash
npm install -D vite-plugin-compression
```

```typescript
// Already included in vite.config.ts above
// Output structure:
// dist/assets/js/main-abc123.js      — original
// dist/assets/js/main-abc123.js.gz   — gzip compressed
// dist/assets/js/main-abc123.js.br   — brotli compressed
```

### Nginx Serves Pre-compressed Files

```nginx
# Enable pre-compressed file serving
gzip_static on;        # serve .gz files if they exist
brotli_static on;      # serve .br files if they exist (requires ngx_brotli module)

# Fallback dynamic compression
gzip on;
gzip_comp_level 5;
gzip_min_length 256;
gzip_types
  text/plain
  text/css
  text/xml
  application/json
  application/javascript
  application/xml
  image/svg+xml;
```

---

## Environment Variables and Build Modes

```bash
# .env.production
VITE_API_URL=https://api.myapp.com
VITE_WS_URL=wss://api.myapp.com
VITE_APP_TITLE=Competition Platform
VITE_ENABLE_ANALYTICS=true

# .env.staging
VITE_API_URL=https://staging-api.myapp.com
VITE_WS_URL=wss://staging-api.myapp.com
VITE_APP_TITLE=Competition Platform (Staging)
VITE_ENABLE_ANALYTICS=false

# .env.development
VITE_API_URL=http://localhost:3000
VITE_WS_URL=ws://localhost:3000
VITE_APP_TITLE=Competition Platform (Dev)
VITE_ENABLE_ANALYTICS=false
```

```typescript
// Access in code (only VITE_ prefixed vars are exposed)
const apiUrl = import.meta.env.VITE_API_URL;
const isProd = import.meta.env.PROD;
const isDev = import.meta.env.DEV;
const mode = import.meta.env.MODE; // 'production', 'staging', 'development'
```

```bash
# Build for different environments
npx vite build --mode production
npx vite build --mode staging
```

---

## Bundle Analysis

```bash
# Install analyzer
npm install -D rollup-plugin-visualizer

# Run analysis
ANALYZE=true npm run build
# Opens dist/stats.html in browser with interactive treemap

# Quick size check
npx vite-bundle-visualizer
```

### Target Budget

| Chunk | Target | Max |
|-------|--------|-----|
| Entry (main.js) | < 50KB gzipped | 80KB |
| Vue vendor | < 50KB gzipped | 70KB |
| Route chunk | < 30KB gzipped | 50KB |
| Total initial load | < 150KB gzipped | 200KB |
| Largest single chunk | < 100KB gzipped | 150KB |

---

## Vue 3 Composition API Performance Patterns

### Avoid Unnecessary Re-renders

```vue
<script setup lang="ts">
import { ref, computed, shallowRef, triggerRef, markRaw } from 'vue';

// ✅ Use shallowRef for large objects that don't need deep reactivity
const largeDataset = shallowRef<ScoreEntry[]>([]);

function updateDataset(newData: ScoreEntry[]) {
  largeDataset.value = newData;  // only triggers when reference changes
  // If you mutate in-place, manually trigger:
  // triggerRef(largeDataset);
}

// ✅ Use markRaw for objects that should NEVER be reactive
import { Chart } from 'chart.js';
const chartInstance = ref<Chart | null>(null);

onMounted(() => {
  chartInstance.value = markRaw(new Chart(/* ... */));
});

// ✅ Computed caching — expensive computations run once
const sortedLeaderboard = computed(() => {
  return [...leaderboard.value].sort((a, b) => b.score - a.score);
});

// ❌ DON'T compute in template
// <div v-for="item in items.sort(...)" — sorts on EVERY render!

// ✅ Use v-once for static content
// <h1 v-once>{{ appTitle }}</h1>

// ✅ Use v-memo for list items that rarely change
// <div v-for="item in list" :key="item.id" v-memo="[item.score, item.rank]">
</script>
```

### Virtual Scrolling for Large Lists

```bash
npm install @tanstack/vue-virtual
```

```vue
<script setup lang="ts">
import { useVirtualizer } from '@tanstack/vue-virtual';
import { ref, computed } from 'vue';

const parentRef = ref<HTMLElement>();
const items = ref(Array.from({ length: 10000 }, (_, i) => ({
  id: i,
  name: `Player ${i + 1}`,
  score: Math.floor(Math.random() * 10000),
})));

const virtualizer = useVirtualizer({
  count: items.value.length,
  getScrollElement: () => parentRef.value,
  estimateSize: () => 48,  // estimated row height in px
  overscan: 10,             // render 10 extra items above/below viewport
});

const virtualItems = computed(() => virtualizer.value.getVirtualItems());
const totalHeight = computed(() => virtualizer.value.getTotalSize());
</script>

<template>
  <div ref="parentRef" class="h-96 overflow-auto">
    <div :style="{ height: `${totalHeight}px`, position: 'relative' }">
      <div
        v-for="virtualRow in virtualItems"
        :key="virtualRow.key"
        :style="{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: `${virtualRow.size}px`,
          transform: `translateY(${virtualRow.start}px)`,
        }"
      >
        <div class="flex items-center px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
          <span class="w-12 text-zinc-400">#{{ virtualRow.index + 1 }}</span>
          <span class="flex-1">{{ items[virtualRow.index].name }}</span>
          <span class="font-mono font-bold">{{ items[virtualRow.index].score }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
```

### API Request Deduplication

```typescript
// composables/useQuery.ts
import { ref, watch, onUnmounted } from 'vue';

const pendingRequests = new Map<string, Promise<any>>();

export function useQuery<T>(key: string, fetcher: () => Promise<T>, options = { immediate: true }) {
  const data = ref<T | null>(null);
  const error = ref<Error | null>(null);
  const isLoading = ref(false);

  async function execute() {
    // Deduplicate — if same request is in-flight, reuse it
    if (pendingRequests.has(key)) {
      try {
        data.value = await pendingRequests.get(key);
      } catch (err) {
        error.value = err as Error;
      }
      return;
    }

    isLoading.value = true;
    error.value = null;

    const promise = fetcher();
    pendingRequests.set(key, promise);

    try {
      data.value = await promise;
    } catch (err) {
      error.value = err as Error;
    } finally {
      isLoading.value = false;
      pendingRequests.delete(key);
    }
  }

  if (options.immediate) execute();

  return { data, error, isLoading, refetch: execute };
}
```

### Debounced Search

```typescript
// composables/useDebouncedRef.ts
import { ref, watch, type Ref } from 'vue';

export function useDebouncedRef<T>(initialValue: T, delay = 300): Ref<T> {
  const value = ref(initialValue) as Ref<T>;
  const debounced = ref(initialValue) as Ref<T>;
  let timer: ReturnType<typeof setTimeout>;

  watch(value, (newVal) => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      debounced.value = newVal;
    }, delay);
  });

  return debounced;
}
```

---

## Nginx Serving Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name myapp.com;

    root /var/www/myapp/dist;
    index index.html;

    # SSL (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/myapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/myapp.com/privkey.pem;

    # Pre-compressed files
    gzip_static on;
    brotli_static on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # SPA fallback — all routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache hashed assets forever (they have content hash in filename)
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Don't cache index.html (it references the latest hashed chunks)
    location = /index.html {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }

    # Don't cache service worker
    location = /sw.js {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /socket.io/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_buffering off;
    }
}
```

---

## CI/CD Build Pipeline

```bash
#!/bin/bash
# deploy.sh — zero-downtime frontend + backend deploy

set -e

APP_DIR=/var/www/myapp
DIST_DIR=$APP_DIR/dist

echo "=== Pulling latest code ==="
cd $APP_DIR
git pull origin main

echo "=== Installing dependencies ==="
npm ci

echo "=== Building frontend ==="
cd $APP_DIR/frontend
npm ci
npm run build

echo "=== Copying frontend build ==="
rm -rf $DIST_DIR
cp -r $APP_DIR/frontend/dist $DIST_DIR

echo "=== Running backend migrations ==="
cd $APP_DIR/backend
npm ci --production
npx sequelize-cli db:migrate --env production

echo "=== Reloading PM2 (zero-downtime) ==="
pm2 reload competition-api

echo "=== Verifying ==="
sleep 3
curl -f http://localhost:3000/health || (echo "Health check failed!" && exit 1)

echo "=== Deploy complete ==="
```

---

## Common Pitfalls

| Pitfall | Impact | Fix |
|---------|--------|-----|
| Not lazy loading routes | 2MB+ initial bundle | `() => import('@/views/Page.vue')` on every route |
| `import Chart from 'chart.js/auto'` | Imports entire Chart.js (500KB+) | Use tree-shakeable imports: `import { Chart, LineController, ... } from 'chart.js'` |
| Console.logs in production | Bundle size + info leak | `drop_console: true` in terser |
| No content hash in filenames | Users get cached stale JS | Default Vite config already does this — don't override |
| Caching index.html | Users see old app after deploy | Set `Cache-Control: no-store` for index.html |
| Not pre-compressing builds | Nginx compresses on-the-fly (CPU waste) | Use vite-plugin-compression |
| Sourcemaps in production | Exposes source code, larger deploy | `sourcemap: false` in production |
| Deep reactive objects | Excessive proxy overhead for large data | Use `shallowRef()` for big arrays |
| Watchers without cleanup | Memory leaks | Always handle in `onUnmounted` |
| Not using `v-memo` on list items | Re-renders all items on any change | `v-memo="[item.id, item.score]"` |
| Global CSS not purged | Unused CSS in bundle | Tailwind CSS v4 auto-purges |

---

### Quick Performance Checklist

- [ ] All routes are lazy loaded with `() => import()`
- [ ] Heavy components use `defineAsyncComponent`
- [ ] Bundle analyzed — no chunks > 150KB gzipped
- [ ] Console.log stripped in production
- [ ] No sourcemaps in production
- [ ] Pre-compressed .gz and .br files generated
- [ ] Nginx serves pre-compressed + caches /assets/ forever
- [ ] index.html is NOT cached
- [ ] Images optimized (WebP/AVIF with fallback)
- [ ] Fonts preloaded with `font-display: swap`
- [ ] `shallowRef()` used for large datasets
- [ ] Virtual scrolling for lists > 100 items
- [ ] API calls deduplicated
- [ ] Prefetch likely next routes

Total initial load target: **< 150KB gzipped** for instant perceived load.