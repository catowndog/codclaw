A comprehensive prompt engineering guide and design system for generating beautiful, modern, production-ready UI components using Tailwind CSS v4 and Vue 3 Composition API.

---

## Table of Contents

1. [Overview](#overview)
2. [Master Design Prompt Template](#master-design-prompt-template)
3. [Tailwind CSS v4 — Key Changes and New Features](#tailwind-css-v4--key-changes-and-new-features)
4. [Vue 3 Composition API Patterns](#vue-3-composition-api-patterns)
5. [Design Principles and Aesthetics](#design-principles-and-aesthetics)
6. [SVG Icon Generation Guidelines](#svg-icon-generation-guidelines)
7. [Color System and Theming](#color-system-and-theming)
8. [Typography System](#typography-system)
9. [Layout Patterns](#layout-patterns)
10. [Alignment and Spacing Consistency](#alignment-and-spacing-consistency)
11. [Component Library — Full Examples](#component-library--full-examples)
12. [Animation and Micro-Interactions](#animation-and-micro-interactions)
13. [Responsive Design Strategy](#responsive-design-strategy)
14. [Dark Mode Implementation](#dark-mode-implementation)
15. [Accessibility Guidelines](#accessibility-guidelines)
16. [Performance Optimization](#performance-optimization)
17. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
18. [Advanced Prompt Techniques](#advanced-prompt-techniques)
19. [Real-World Page Templates](#real-world-page-templates)

---

## Overview

This skill provides a battle-tested, extremely detailed prompt system for instructing AI code generators to produce visually stunning, pixel-perfect UI components using **Tailwind CSS v4** (the CSS-first configuration release) and **Vue 3 Composition API** (`<script setup>`). Every prompt template, design decision, and code example follows modern best practices as of 2024–2025.

---

## Master Design Prompt Template

Use this as the **base prompt** before any component generation request. Copy, adapt, and extend it:

```
You are an elite UI/UX engineer and frontend developer specializing in modern web interfaces.

TECHNOLOGY STACK (strict, no deviations):
- Vue 3.4+ with <script setup lang="ts"> (Composition API ONLY, never Options API)
- Tailwind CSS v4 (CSS-first configuration, @theme directive, no tailwind.config.js)
- TypeScript (strict mode, proper typing for all props, emits, refs)
- Custom inline SVG icons generated from scratch (no external icon libraries required)
- VueUse composables where helpful (useColorMode, useMediaQuery, etc.)

DESIGN PHILOSOPHY:
- Modern, clean, premium aesthetic inspired by Linear, Vercel, Stripe, Apple
- Generous whitespace — never cramped layouts
- Subtle depth via layered shadows, not flat or overly skeuomorphic
- NO gratuitous gradients — prefer solid colors, subtle tonal shifts, or very soft single-tone gradients only when essential (e.g., a faint bg tint). Never use rainbow or multi-color gradients for decoration
- Micro-interactions on every interactive element (hover, focus, active states)
- Glass morphism used sparingly for accent panels/modals (backdrop-blur WITHOUT gradient overlays)
- Smooth transitions (150ms–300ms ease-out for UI, 500ms+ for page transitions)
- Color palette: neutral base (zinc/slate/stone) + one vibrant accent color as solid fills
- Typography: tight letter-spacing for headings, relaxed for body text
- Border radius: consistent (use rounded-xl or rounded-2xl, never mix sizes randomly)
- Every component must be fully responsive (mobile-first approach)
- Dark mode support is MANDATORY (use Tailwind dark: variant)
- STRICT ALIGNMENT: all page sections (header, sidebar, main content) must share consistent left/right padding and alignment anchors — nothing should appear visually offset or crooked

SVG ICON RULES:
- Generate all icons as inline SVG directly in templates — do NOT rely on icon libraries
- Every icon must use currentColor for fill or stroke so it inherits text color from parent
- Standard icon sizes: size-4 (16px), size-5 (20px), size-6 (24px), size-8 (32px)
- Use stroke-based icons with stroke-width="1.5" or stroke-width="2" for a clean modern look
- All SVGs must include viewBox="0 0 24 24" (24x24 grid standard)
- Add aria-hidden="true" to decorative icons; add role="img" + aria-label to meaningful icons
- Keep SVG paths simple and minimal — avoid unnecessary complexity
- Use stroke-linecap="round" and stroke-linejoin="round" for friendly, modern appearance

TAILWIND CSS v4 RULES:
- Use the new CSS-based configuration with @theme { } in your CSS file
- Use the new @utility directive for custom utilities
- Use built-in container queries where appropriate
- Use new color-mix() and oklch() color functions
- Use the new variant() syntax
- Do NOT use tailwind.config.js — v4 is CSS-first
- Use the new @theme inline references like --color-primary
- Use logical properties where appropriate (ms-*, me-*, ps-*, pe-*)

VUE 3 COMPOSITION API RULES:
- Always <script setup lang="ts">
- Use defineProps with TypeScript interface/type
- Use defineEmits with typed events
- Use defineModel() for v-model bindings
- Use ref(), computed(), watch(), watchEffect()
- Use provide/inject for deep state sharing
- Extract reusable logic into composables (use* naming convention)
- Use template refs with useTemplateRef() or ref<HTMLElement>()
- Components must be self-contained SFCs (.vue files)

CODE QUALITY:
- Clean, readable, well-commented code
- Semantic HTML (nav, main, section, article, aside, header, footer)
- ARIA attributes for all interactive elements
- Proper focus management and keyboard navigation
- No inline styles — Tailwind classes only
- Extract repeated class combinations into component-level abstractions
- Use descriptive variable and function names

OUTPUT FORMAT:
- Single .vue SFC file per component unless composable extraction is needed
- Include all necessary TypeScript types/interfaces
- Include example usage in comments if the component has complex props
- Show the required @theme CSS if custom theme tokens are needed
```

---

## Tailwind CSS v4 — Key Changes and New Features

Tailwind CSS v4 introduces a fundamentally different configuration model. Understanding these changes is critical for generating correct code.

### CSS-First Configuration

```css
/* app.css — This replaces tailwind.config.js entirely */
@import "tailwindcss";

@theme {
  /* Colors using oklch for perceptually uniform colors */
  --color-primary-50: oklch(0.97 0.01 250);
  --color-primary-100: oklch(0.93 0.02 250);
  --color-primary-200: oklch(0.87 0.04 250);
  --color-primary-300: oklch(0.77 0.08 250);
  --color-primary-400: oklch(0.65 0.14 250);
  --color-primary-500: oklch(0.55 0.19 250);
  --color-primary-600: oklch(0.47 0.19 250);
  --color-primary-700: oklch(0.39 0.16 250);
  --color-primary-800: oklch(0.33 0.13 250);
  --color-primary-900: oklch(0.27 0.10 250);
  --color-primary-950: oklch(0.20 0.07 250);

  /* Accent color — solid, no gradient */
  --color-accent: oklch(0.72 0.21 330);
  --color-accent-hover: oklch(0.65 0.24 330);

  /* Surface colors for cards, panels — flat solid fills */
  --color-surface: oklch(0.99 0.00 0);
  --color-surface-elevated: oklch(1.00 0.00 0);
  --color-surface-overlay: oklch(0.98 0.005 250 / 0.8);

  /* Semantic colors */
  --color-success: oklch(0.65 0.18 145);
  --color-warning: oklch(0.75 0.18 75);
  --color-error: oklch(0.60 0.22 25);
  --color-info: oklch(0.65 0.16 250);

  /* Typography */
  --font-sans: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
  --font-display: 'Inter Tight', 'Inter', sans-serif;

  /* Custom letter spacing */
  --tracking-tighter: -0.04em;
  --tracking-display: -0.035em;

  /* Shadows — layered for depth */
  --shadow-soft: 0 1px 2px oklch(0.2 0 0 / 0.04), 0 2px 8px oklch(0.2 0 0 / 0.03);
  --shadow-medium: 0 2px 4px oklch(0.2 0 0 / 0.04), 0 4px 16px oklch(0.2 0 0 / 0.06);
  --shadow-large: 0 4px 8px oklch(0.2 0 0 / 0.04), 0 8px 32px oklch(0.2 0 0 / 0.08);
  --shadow-glow: 0 0 20px oklch(0.55 0.19 250 / 0.3);

  /* Animations */
  --animate-fade-in: fade-in 0.5s ease-out;
  --animate-slide-up: slide-up 0.4s ease-out;
  --animate-scale-in: scale-in 0.3s ease-out;

  /* Border radius tokens */
  --radius-card: 1rem;
  --radius-button: 0.75rem;
  --radius-input: 0.625rem;
  --radius-badge: 9999px;

  /* Layout alignment tokens — use these everywhere for consistent padding */
  --spacing-page-x: 1.5rem;  /* 24px — base horizontal page padding */
  --spacing-page-x-lg: 2rem;  /* 32px — larger screens */

  /* Spacing scale extensions */
  --spacing-18: 4.5rem;
  --spacing-88: 22rem;
  --spacing-128: 32rem;
}

/* Custom keyframes */
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes scale-in {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

/* Custom utilities */
@utility text-balance {
  text-wrap: balance;
}

@utility glass {
  background: oklch(1 0 0 / 0.6);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
}

@utility glass-dark {
  background: oklch(0.15 0.01 250 / 0.7);
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
}
```

### New v4 Variant Syntax and Features

```css
/* Container queries — built into v4 */
@utility card-grid {
  display: grid;
  gap: 1.5rem;
  @container (min-width: 640px) {
    grid-template-columns: repeat(2, 1fr);
  }
  @container (min-width: 1024px) {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

**Important v4 differences to remember:**

| Feature | v3 | v4 |
|---|---|---|
| Configuration | `tailwind.config.js` | `@theme { }` in CSS |
| Custom colors | `extend: { colors: {} }` | `--color-*` in `@theme` |
| Custom utilities | Plugin API | `@utility` directive |
| Content detection | `content: [...]` | Automatic detection |
| PostCSS setup | `postcss.config.js` with plugins | Just `@import "tailwindcss"` |
| Color functions | hex/rgb/hsl | oklch() recommended |
| Container queries | Plugin needed | Built-in `@container` |

---

## Vue 3 Composition API Patterns

### Standard Component Structure

```vue
<script setup lang="ts">
import { ref, computed, watch, onMounted, type PropType } from 'vue'

// ============================================
// Types
// ============================================
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  loading?: boolean
  disabled?: boolean
  iconPosition?: 'left' | 'right'
  fullWidth?: boolean
}

// ============================================
// Props & Emits
// ============================================
const props = withDefaults(defineProps<ButtonProps>(), {
  variant: 'primary',
  size: 'md',
  loading: false,
  disabled: false,
  iconPosition: 'left',
  fullWidth: false,
})

const emit = defineEmits<{
  click: [event: MouseEvent]
}>()

// ============================================
// State
// ============================================
const buttonRef = ref<HTMLButtonElement>()
const isPressed = ref(false)

// ============================================
// Computed
// ============================================
const variantClasses = computed(() => {
  const variants: Record<string, string> = {
    primary: `
      bg-primary-500 text-white
      hover:bg-primary-600 active:bg-primary-700
      shadow-soft hover:shadow-medium
      dark:bg-primary-400 dark:hover:bg-primary-300 dark:text-primary-950
    `,
    secondary: `
      bg-zinc-100 text-zinc-900
      hover:bg-zinc-200 active:bg-zinc-300
      dark:bg-zinc-800 dark:text-zinc-100
      dark:hover:bg-zinc-700
    `,
    ghost: `
      bg-transparent text-zinc-600
      hover:bg-zinc-100 active:bg-zinc-200
      dark:text-zinc-400 dark:hover:bg-zinc-800
    `,
    danger: `
      bg-error text-white
      hover:bg-red-600 active:bg-red-700
      shadow-soft hover:shadow-medium
    `,
    outline: `
      bg-transparent text-zinc-700 border border-zinc-300
      hover:bg-zinc-50 active:bg-zinc-100
      dark:text-zinc-300 dark:border-zinc-600
      dark:hover:bg-zinc-800
    `,
  }
  return variants[props.variant]
})

const sizeClasses = computed(() => {
  const sizes: Record<string, string> = {
    xs: 'px-2.5 py-1 text-xs gap-1',
    sm: 'px-3 py-1.5 text-sm gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-5 py-2.5 text-base gap-2',
    xl: 'px-6 py-3 text-base gap-2.5',
  }
  return sizes[props.size]
})

// ============================================
// Methods
// ============================================
function handleClick(event: MouseEvent) {
  if (props.disabled || props.loading) return
  emit('click', event)
}
</script>

<template>
  <button
    ref="buttonRef"
    :class="[
      // Base styles — NO gradients, solid bg only
      'inline-flex items-center justify-center font-medium',
      'rounded-button transition-all duration-200 ease-out',
      'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
      'cursor-pointer select-none',
      // Active press effect
      'active:scale-[0.97]',
      // Dynamic classes
      variantClasses,
      sizeClasses,
      { 'w-full': fullWidth },
    ]"
    :disabled="disabled || loading"
    @click="handleClick"
  >
    <!-- Loading spinner — inline SVG, no library needed -->
    <svg
      v-if="loading"
      class="animate-spin -ms-0.5 size-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>

    <!-- Left icon slot -->
    <slot v-if="iconPosition === 'left' && !loading" name="icon-left" />

    <!-- Slot content -->
    <span><slot /></span>

    <!-- Right icon slot -->
    <slot v-if="iconPosition === 'right' && !loading" name="icon-right" />
  </button>
</template>
```

### Composable Pattern

```typescript
// composables/useTheme.ts
import { ref, computed, watchEffect } from 'vue'

type ThemeMode = 'light' | 'dark' | 'system'

const mode = ref<ThemeMode>('system')

export function useTheme() {
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)')

  const isDark = computed(() => {
    if (mode.value === 'system') {
      return systemPrefersDark.matches
    }
    return mode.value === 'dark'
  })

  watchEffect(() => {
    document.documentElement.classList.toggle('dark', isDark.value)
  })

  function setTheme(newMode: ThemeMode) {
    mode.value = newMode
    localStorage.setItem('theme', newMode)
  }

  function toggleTheme() {
    setTheme(isDark.value ? 'light' : 'dark')
  }

  // Initialize from localStorage
  const saved = localStorage.getItem('theme') as ThemeMode | null
  if (saved) mode.value = saved

  return {
    mode,
    isDark,
    setTheme,
    toggleTheme,
  }
}
```

---

## Design Principles and Aesthetics

### The "Premium Software" Look

To achieve a Linear/Vercel/Stripe-quality interface, follow these rules religiously:

1. **Whitespace is your best friend** — Use `p-6`, `p-8`, `gap-6`, `gap-8`, `space-y-6` generously. Never let content feel cramped. Landing page hero sections should use `py-24` or `py-32`.

2. **Layered shadows create depth** — Never use a single box-shadow. Combine a tight, dark shadow with a wider, lighter one:
   ```
   shadow-[0_1px_3px_rgba(0,0,0,0.08),0_4px_16px_rgba(0,0,0,0.04)]
   ```

3. **NO intrusive gradients** — This is a core rule. Avoid `bg-gradient-to-*` with multiple vivid colors. If a gradient is absolutely needed (e.g., a subtle hero background tint), use a **single-hue, near-invisible** gradient like `from-zinc-50 to-white`. Buttons, cards, badges, nav bars — all must use **solid background colors**. Gradients on text are acceptable sparingly for hero headlines only if the effect is tasteful.

4. **Subtle borders separate content** — Use `border border-zinc-200/60 dark:border-zinc-700/50` instead of harsh `border-gray-300`.

5. **Consistent border radius** — Pick ONE radius scale and stick to it. Cards = `rounded-2xl`, Buttons = `rounded-xl`, Inputs = `rounded-lg`, Badges = `rounded-full`.

6. **Muted backgrounds with clear surfaces** — Page bg: `bg-zinc-50 dark:bg-zinc-950`. Card bg: `bg-white dark:bg-zinc-900`. This creates natural layering without gradients.

7. **Color restraint** — Use your accent color for CTAs and key interactive elements ONLY. Everything else should be neutral zinc/slate tones. Solid fills, no gradients.

8. **Typography hierarchy** — Maximum 3 font sizes per section. Headings: `text-3xl font-semibold tracking-tight`. Body: `text-base text-zinc-600`. Caption: `text-sm text-zinc-400`.

9. **Hover states must feel alive** — Combine color shift + shadow increase + subtle translateY:
   ```
   hover:shadow-medium hover:-translate-y-0.5 transition-all duration-200
   ```

10. **Loading states everywhere** — Skeleton screens, spinners, progress bars. Never leave the user staring at empty space.

11. **Iconography consistency** — Generate inline SVG icons from scratch. Size icons at `size-4` for inline, `size-5` for buttons, `size-6` for section headers, `size-8`+ for feature showcases. All icons use `currentColor`.

12. **Pixel-perfect alignment** — Header content, sidebar content, and the main scrollable area must share the **exact same horizontal padding** so that text and elements on different rows always line up vertically. Use a shared padding variable/class (e.g., `px-6`) applied identically across header and main. See the [Alignment and Spacing Consistency](#alignment-and-spacing-consistency) section.

---

## SVG Icon Generation Guidelines

All icons should be generated as **inline SVG** directly in the template. This eliminates external icon library dependencies and gives full control over styling.

### Icon Design Rules

1. **Canvas**: Always `viewBox="0 0 24 24"` — the universal 24×24 grid
2. **Style**: Stroke-based (outlined) icons by default; use `fill="none"` and `stroke="currentColor"`
3. **Stroke width**: `stroke-width="1.5"` for a refined look, `stroke-width="2"` for bolder UI contexts
4. **Line caps**: Always `stroke-linecap="round" stroke-linejoin="round"` for a friendly, modern aesthetic
5. **Color**: Always use `currentColor` — never hardcode colors in SVG paths
6. **Sizing via Tailwind**: Apply `class="size-4"` / `size-5` / `size-6` on the `<svg>` element
7. **Accessibility**: Decorative icons get `aria-hidden="true"`; meaningful icons get `role="img"` + `aria-label`

### Common Icon Templates

Generate these from scratch whenever needed — copy the SVG pattern and adjust paths:

```html
<!-- ✕ Close / X icon -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M18 6L6 18M6 6l12 12" />
</svg>

<!-- ☰ Menu / Hamburger icon -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M4 6h16M4 12h16M4 18h16" />
</svg>

<!-- ▶ Chevron right -->
<svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M9 18l6-6-6-6" />
</svg>

<!-- ▼ Chevron down -->
<svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M6 9l6 6 6-6" />
</svg>

<!-- 🔍 Search / Magnifying glass -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <circle cx="11" cy="11" r="7" />
  <path d="M21 21l-4.35-4.35" />
</svg>

<!-- 🏠 Home -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1" />
</svg>

<!-- ⚙ Settings / Gear -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z" />
  <circle cx="12" cy="12" r="3" />
</svg>

<!-- 👤 User / Person -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
  <circle cx="12" cy="7" r="4" />
</svg>

<!-- 🔔 Bell / Notification -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
  <path d="M13.73 21a2 2 0 01-3.46 0" />
</svg>

<!-- ✓ Check / Checkmark -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M20 6L9 17l-5-5" />
</svg>

<!-- ➕ Plus -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M12 5v14M5 12h14" />
</svg>

<!-- 📊 Bar chart -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M18 20V10M12 20V4M6 20v-6" />
</svg>

<!-- ↗ Trending up -->
<svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M23 6l-9.5 9.5-5-5L1 18" />
  <path d="M17 6h6v6" />
</svg>

<!-- ↘ Trending down -->
<svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M23 18l-9.5-9.5-5 5L1 6" />
  <path d="M17 18h6v-6" />
</svg>

<!-- 📋 Clipboard / Copy -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
</svg>

<!-- 🗑 Trash / Delete -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14" />
  <path d="M10 11v6M14 11v6" />
</svg>

<!-- ✏ Edit / Pencil -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M17 3a2.85 2.85 0 114 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
</svg>

<!-- ☀ Sun (light mode) -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <circle cx="12" cy="12" r="5" />
  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
</svg>

<!-- 🌙 Moon (dark mode) -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
</svg>

<!-- → Arrow right -->
<svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M5 12h14M12 5l7 7-7 7" />
</svg>

<!-- ⬇ Download -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
</svg>

<!-- 🔗 External link -->
<svg class="size-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" />
</svg>
```

### Creating Custom SVG Icons

When a project needs a unique icon not listed above, follow this pattern:

```vue
<script setup lang="ts">
// Define icon as a simple render function or inline SVG in template
// For reusable icons, create a small component:
</script>

<template>
  <!-- Custom "dashboard" icon example — built from simple shapes -->
  <svg
    class="size-5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <!-- Top-left rectangle -->
    <rect x="3" y="3" width="8" height="8" rx="1" />
    <!-- Top-right rectangle -->
    <rect x="13" y="3" width="8" height="4" rx="1" />
    <!-- Bottom-left rectangle -->
    <rect x="3" y="13" width="8" height="4" rx="1" />
    <!-- Bottom-right rectangle -->
    <rect x="13" y="9" width="8" height="8" rx="1" />
  </svg>
</template>
```

### Reusable Icon Wrapper Component

For projects with many icons, create a thin wrapper:

```vue
<!-- components/SvgIcon.vue -->
<script setup lang="ts">
interface SvgIconProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  strokeWidth?: number
  label?: string  // If set, icon is meaningful (not decorative)
}

const props = withDefaults(defineProps<SvgIconProps>(), {
  size: 'md',
  strokeWidth: 1.5,
})

const sizeMap: Record<string, string> = {
  xs: 'size-3',
  sm: 'size-4',
  md: 'size-5',
  lg: 'size-6',
  xl: 'size-8',
}
</script>

<template>
  <svg
    :class="[sizeMap[size], 'shrink-0']"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    :aria-hidden="!label"
    :role="label ? 'img' : undefined"
    :aria-label="label"
  >
    <slot />
  </svg>
</template>
```

Usage:
```html
<SvgIcon size="sm">
  <path d="M20 6L9 17l-5-5" />
</SvgIcon>

<SvgIcon size="lg" label="Notifications">
  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
  <path d="M13.73 21a2 2 0 01-3.46 0" />
</SvgIcon>
```

---

## Color System and Theming

### Recommended Premium Color Palettes

**Palette 1 — "Midnight Indigo" (SaaS Dashboard)**
```css
@theme {
  --color-primary-500: oklch(0.55 0.20 265);  /* Deep indigo — solid fill */
  --color-accent: oklch(0.75 0.15 165);        /* Teal accent — solid fill */
  --color-surface: oklch(0.99 0.002 265);      /* Barely tinted white — flat */
}
```

**Palette 2 — "Electric Violet" (Creative/Design Tool)**
```css
@theme {
  --color-primary-500: oklch(0.55 0.25 300);   /* Vivid purple — solid fill */
  --color-accent: oklch(0.80 0.20 85);         /* Warm amber accent — solid fill */
  --color-surface: oklch(0.985 0.005 300);
}
```

**Palette 3 — "Ocean Depth" (Finance/Fintech)**
```css
@theme {
  --color-primary-500: oklch(0.50 0.12 230);   /* Deep blue — solid fill */
  --color-accent: oklch(0.70 0.18 150);        /* Green for positive — solid fill */
  --color-surface: oklch(0.99 0.003 230);
}
```

**Palette 4 — "Obsidian" (Developer Tools / Dark-first)**
```css
@theme {
  --color-primary-500: oklch(0.70 0.15 145);   /* Green terminal vibes — solid fill */
  --color-accent: oklch(0.75 0.12 55);         /* Warm orange accent — solid fill */
  --color-surface: oklch(0.13 0.01 260);       /* Dark surface — flat */
  --color-surface-elevated: oklch(0.17 0.01 260);
}
```

### Gradient Policy

| Context | Allowed? | Example |
|---|---|---|
| Buttons | ❌ No | Use solid `bg-primary-500` |
| Cards | ❌ No | Use solid `bg-white dark:bg-zinc-900` |
| Navigation | ❌ No | Use solid or transparent bg |
| Badges/Tags | ❌ No | Use solid tinted backgrounds |
| Page background | ⚠️ Barely | Only single-hue: `from-zinc-50 to-white` |
| Hero headline text | ⚠️ Sparingly | `bg-clip-text` with subtle two-tone only |
| CTA banner background | ⚠️ Sparingly | Very subtle single-hue shift, not rainbow |
| Decorative blobs | ⚠️ Only if blurred | Background `blur-3xl opacity-20` accent blobs |

---

## Typography System

```css
@theme {
  --font-sans: 'Inter Variable', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-display: 'Cal Sans', 'Inter Tight', 'Inter', sans-serif;
  --font-mono: 'Geist Mono', 'JetBrains Mono', 'Fira Code', monospace;

  --text-display: 4rem;         /* 64px — hero headings */
  --text-display--line-height: 1.05;
  --text-display--letter-spacing: -0.04em;

  --text-headline: 2.5rem;      /* 40px — section headings */
  --text-headline--line-height: 1.15;
  --text-headline--letter-spacing: -0.03em;

  --text-title: 1.5rem;         /* 24px — card titles */
  --text-title--line-height: 1.3;
  --text-title--letter-spacing: -0.02em;
}
```

### Typographic Scale in Practice

```html
<!-- Hero heading — NO gradient text unless absolutely necessary -->
<h1 class="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tighter text-zinc-900 dark:text-white text-balance">
  Build faster.<br />
  <span class="text-primary-500">Ship smarter.</span>
</h1>

<!-- Section heading -->
<h2 class="text-3xl sm:text-4xl font-semibold tracking-tight text-zinc-900 dark:text-white">
  Everything you need
</h2>

<!-- Subtitle / supporting text -->
<p class="mt-4 text-lg text-zinc-500 dark:text-zinc-400 max-w-2xl text-balance leading-relaxed">
  A beautifully designed component system with thoughtful defaults
  and flexible customization options.
</p>
```

---

## Alignment and Spacing Consistency

### The Golden Rule: Shared Padding Anchors

The most common layout bug in dashboards is **misaligned content between the header and the main area**. The header's left content edge and the main content's left edge MUST be identical.

#### Problem Visualization

```
❌ WRONG — Header and content have different left offsets:

┌──────────────────────────────────┐
│ [Sidebar] │  ← Header (px-4)    │  ← left edge at 16px
│           │                      │
│           │    ← Content (px-6)  │  ← left edge at 24px ← MISALIGNED!
│           │                      │
└──────────────────────────────────┘

✅ CORRECT — Header and content share the same left padding:

┌──────────────────────────────────┐
│ [Sidebar] │← Header (px-6)      │  ← left edge at 24px
│           │                      │
│           │← Content (px-6)      │  ← left edge at 24px ← ALIGNED!
│           │                      │
└──────────────────────────────────┘
```

#### Implementation Rules

1. **Define ONE padding constant** for the content area and use it on BOTH the header and the main content wrapper:
   ```html
   <!-- Use the SAME px-6 on both -->
   <header class="... px-6">
   <main class="...">
     <div class="px-6 py-8">
   ```

2. **Never nest extra padding containers** inside one but not the other. If main has `<div class="mx-auto max-w-7xl px-6">`, then the header must also have `px-6` with the same container structure.

3. **For max-width constrained layouts**, apply `max-w-7xl` and `mx-auto` to BOTH header inner content and main inner content, or to neither.

4. **Sidebar width must not push content differently** — use `w-64` (fixed) for sidebar and let the content area fill the rest with `flex-1`.

5. **When the sidebar collapses on mobile**, both header and main content should revert to the same full-width padding.

### Alignment Verification Checklist

- [ ] Header `px-*` value matches main content `px-*` value
- [ ] If using `max-w-*` + `mx-auto` in main, same wrapper exists in header
- [ ] Sidebar width is fixed (`w-64`), not percentage-based
- [ ] On mobile, when sidebar is hidden, header and main share the same `px-4` or `px-6`
- [ ] No extra `ml-*` or `pl-*` on the main area that isn't also on the header
- [ ] Test visually: draw an imaginary vertical line from the first header element — it should touch the first content element below

---

## Component Library — Full Examples

### Card Component

```vue
<script setup lang="ts">
interface CardProps {
  variant?: 'default' | 'interactive' | 'featured' | 'glass'
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<CardProps>(), {
  variant: 'default',
  padding: 'md',
})

const paddingMap: Record<string, string> = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
}

const variantMap: Record<string, string> = {
  default: `
    bg-white dark:bg-zinc-900
    border border-zinc-200/70 dark:border-zinc-800
    shadow-soft
  `,
  interactive: `
    bg-white dark:bg-zinc-900
    border border-zinc-200/70 dark:border-zinc-800
    shadow-soft hover:shadow-medium
    hover:-translate-y-0.5 hover:border-zinc-300 dark:hover:border-zinc-700
    transition-all duration-200 cursor-pointer
  `,
  featured: `
    bg-primary-500 text-white
    shadow-large shadow-primary-500/20
    border border-primary-400/30
  `,
  glass: `
    glass dark:glass-dark
    border border-white/20 dark:border-zinc-700/40
    shadow-large
  `,
}
</script>

<template>
  <div
    :class="[
      'rounded-2xl overflow-hidden',
      variantMap[variant],
      paddingMap[padding],
    ]"
  >
    <slot />
  </div>
</template>
```

### Input Component

```vue
<script setup lang="ts">
import { computed } from 'vue'

interface InputProps {
  label?: string
  placeholder?: string
  type?: string
  error?: string
  hint?: string
  disabled?: boolean
}

const props = withDefaults(defineProps<InputProps>(), {
  type: 'text',
})

const model = defineModel<string>({ default: '' })

const inputClasses = computed(() => [
  // Base — solid bg, no gradients
  'w-full rounded-lg border bg-white px-3.5 py-2.5 text-sm text-zinc-900',
  'outline-none transition-all duration-200',
  'placeholder:text-zinc-400',
  // Dark mode
  'dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-500',
  // Focus
  'focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500',
  'dark:focus:ring-primary-400/20 dark:focus:border-primary-400',
  // Error state
  props.error
    ? 'border-error/50 focus:ring-error/20 focus:border-error'
    : 'border-zinc-300 dark:border-zinc-700',
  // Disabled
  props.disabled && 'opacity-50 cursor-not-allowed bg-zinc-50 dark:bg-zinc-800',
])
</script>

<template>
  <div class="space-y-1.5">
    <!-- Label -->
    <label v-if="label" class="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
      {{ label }}
    </label>

    <!-- Input wrapper -->
    <div class="relative">
      <!-- Leading icon slot -->
      <div v-if="$slots['icon-left']" class="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-zinc-400">
        <slot name="icon-left" />
      </div>

      <input
        v-model="model"
        :type="type"
        :placeholder="placeholder"
        :disabled="disabled"
        :class="[inputClasses, $slots['icon-left'] && 'ps-10']"
        :aria-invalid="!!error"
        :aria-describedby="error ? 'input-error' : hint ? 'input-hint' : undefined"
      />
    </div>

    <!-- Error message -->
    <p v-if="error" id="input-error" class="text-sm text-error flex items-center gap-1">
      <svg class="size-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
      </svg>
      {{ error }}
    </p>

    <!-- Hint text -->
    <p v-else-if="hint" id="input-hint" class="text-sm text-zinc-400 dark:text-zinc-500">
      {{ hint }}
    </p>
  </div>
</template>
```

### Modal / Dialog Component

```vue
<script setup lang="ts">
import { watch, ref, onMounted, onUnmounted } from 'vue'

interface ModalProps {
  title?: string
  description?: string
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
}

const props = withDefaults(defineProps<ModalProps>(), {
  size: 'md',
})

const isOpen = defineModel<boolean>('open', { default: false })

const panelRef = ref<HTMLElement>()

const sizeMap: Record<string, string> = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)]',
}

watch(isOpen, (open) => {
  if (open) {
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

function handleBackdropClick() {
  isOpen.value = false
}

function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape') isOpen.value = false
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <!-- Backdrop — solid dark overlay, no gradient -->
        <div
          class="absolute inset-0 bg-black/40 backdrop-blur-sm dark:bg-black/60"
          @click="handleBackdropClick"
        />

        <!-- Panel -->
        <Transition
          enter-active-class="duration-300 ease-out"
          enter-from-class="opacity-0 scale-95 translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="duration-200 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="isOpen"
            ref="panelRef"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="title ? 'modal-title' : undefined"
            :class="[
              'relative w-full rounded-2xl bg-white shadow-large',
              'dark:bg-zinc-900 dark:border dark:border-zinc-800',
              'animate-scale-in',
              sizeMap[size],
            ]"
          >
            <!-- Header -->
            <div v-if="title || $slots.header" class="flex items-start justify-between p-6 pb-0">
              <div>
                <h2 v-if="title" id="modal-title" class="text-lg font-semibold text-zinc-900 dark:text-white">
                  {{ title }}
                </h2>
                <p v-if="description" class="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                  {{ description }}
                </p>
              </div>
              <button
                class="rounded-lg p-1.5 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 dark:hover:text-zinc-300 transition-colors"
                @click="isOpen = false"
                aria-label="Close dialog"
              >
                <!-- Inline close icon SVG -->
                <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div class="p-6">
              <slot />
            </div>

            <!-- Footer -->
            <div v-if="$slots.footer" class="flex items-center justify-end gap-3 border-t border-zinc-200 dark:border-zinc-800 px-6 py-4">
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
```

### Navigation / Header Component

```vue
<script setup lang="ts">
import { ref } from 'vue'

interface NavItem {
  label: string
  href: string
  children?: NavItem[]
}

const props = defineProps<{
  logo?: string
  items: NavItem[]
}>()

const isMobileMenuOpen = ref(false)
const scrolled = ref(false)

if (typeof window !== 'undefined') {
  window.addEventListener('scroll', () => {
    scrolled.value = window.scrollY > 10
  })
}
</script>

<template>
  <header
    :class="[
      'fixed top-0 inset-x-0 z-40 transition-all duration-300',
      scrolled
        ? 'bg-white/80 dark:bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-200/50 dark:border-zinc-800/50 shadow-sm'
        : 'bg-transparent',
    ]"
  >
    <nav class="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
      <!-- Logo -->
      <a href="/" class="flex items-center gap-2.5 font-display text-xl font-bold tracking-tight text-zinc-900 dark:text-white">
        <div class="size-8 rounded-lg bg-primary-500 flex items-center justify-center text-white text-sm font-bold">
          A
        </div>
        <span>Acme</span>
      </a>

      <!-- Desktop navigation -->
      <div class="hidden md:flex items-center gap-1">
        <a
          v-for="item in items"
          :key="item.label"
          :href="item.href"
          class="px-3.5 py-2 text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
        >
          {{ item.label }}
        </a>
      </div>

      <!-- CTA buttons — solid bg, no gradient -->
      <div class="hidden md:flex items-center gap-3">
        <a href="/login" class="text-sm font-medium text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white transition-colors">
          Sign in
        </a>
        <a
          href="/signup"
          class="inline-flex items-center rounded-xl bg-primary-500 px-4 py-2 text-sm font-medium text-white shadow-soft hover:bg-primary-600 hover:shadow-medium active:scale-[0.97] transition-all duration-200"
        >
          Get Started
        </a>
      </div>

      <!-- Mobile menu toggle — inline SVG icons -->
      <button
        class="md:hidden rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
        @click="isMobileMenuOpen = !isMobileMenuOpen"
        :aria-label="isMobileMenuOpen ? 'Close menu' : 'Open menu'"
      >
        <!-- Menu icon -->
        <svg v-if="!isMobileMenuOpen" class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
        <!-- Close icon -->
        <svg v-else class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M18 6L6 18M6 6l12 12" />
        </svg>
      </button>
    </nav>

    <!-- Mobile menu -->
    <Transition
      enter-active-class="duration-200 ease-out"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="isMobileMenuOpen"
        class="md:hidden border-t border-zinc-200/50 dark:border-zinc-800/50 bg-white/95 dark:bg-zinc-950/95 backdrop-blur-xl"
      >
        <div class="space-y-1 px-4 py-4">
          <a
            v-for="item in items"
            :key="item.label"
            :href="item.href"
            class="block rounded-lg px-3 py-2.5 text-base font-medium text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white transition-colors"
          >
            {{ item.label }}
          </a>
          <div class="pt-4 space-y-2 border-t border-zinc-200 dark:border-zinc-800 mt-4">
            <a href="/login" class="block rounded-lg px-3 py-2.5 text-base font-medium text-zinc-600 dark:text-zinc-400">Sign in</a>
            <a href="/signup" class="block rounded-xl bg-primary-500 px-3 py-2.5 text-base font-medium text-white text-center shadow-soft">Get Started</a>
          </div>
        </div>
      </div>
    </Transition>
  </header>
</template>
```

---

## Animation and Micro-Interactions

### Transition Cheat Sheet

```vue
<!-- Fade -->
<Transition
  enter-active-class="duration-200 ease-out"
  enter-from-class="opacity-0"
  leave-active-class="duration-150 ease-in"
  leave-to-class="opacity-0"
>

<!-- Slide up + fade -->
<Transition
  enter-active-class="duration-300 ease-out"
  enter-from-class="opacity-0 translate-y-4"
  leave-active-class="duration-200 ease-in"
  leave-to-class="opacity-0 translate-y-2"
>

<!-- Scale + fade (for modals, dropdowns) -->
<Transition
  enter-active-class="duration-200 ease-out"
  enter-from-class="opacity-0 scale-95"
  leave-active-class="duration-150 ease-in"
  leave-to-class="opacity-0 scale-95"
>

<!-- Staggered list animation -->
<TransitionGroup
  enter-active-class="duration-300 ease-out"
  enter-from-class="opacity-0 translate-y-4"
  leave-active-class="duration-200 ease-in"
  leave-to-class="opacity-0 translate-x-8"
  move-class="duration-300 ease-out"
>
  <div v-for="(item, i) in items" :key="item.id" :style="{ transitionDelay: `${i * 50}ms` }">
```

### Interactive Hover Classes

```html
<!-- Card lift effect -->
class="hover:-translate-y-1 hover:shadow-large transition-all duration-300"

<!-- Button press -->
class="active:scale-[0.97] transition-transform duration-100"

<!-- Glow on hover (solid glow, not gradient) -->
class="hover:shadow-[0_0_24px_rgba(99,102,241,0.25)] transition-shadow duration-300"

<!-- Border color animation -->
class="border border-transparent hover:border-primary-500/50 transition-colors duration-200"

<!-- Underline slide-in for nav links -->
class="relative after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0 hover:after:w-full after:bg-primary-500 after:transition-all after:duration-300"

<!-- Background fill on hover — solid color, no gradient -->
class="hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors duration-150"
```

---

## Responsive Design Strategy

### Breakpoint Usage Guidelines

| Breakpoint | Class prefix | Use case |
|---|---|---|
| < 640px | (default) | Mobile phones — single column, stacked layout |
| 640px+ | `sm:` | Large phones / small tablets — minor adjustments |
| 768px+ | `md:` | Tablets — switch to 2-column layouts |
| 1024px+ | `lg:` | Laptops — full navigation, 3-column grids |
| 1280px+ | `xl:` | Desktops — max content width, generous spacing |
| 1536px+ | `2xl:` | Large monitors — wider containers |

### Responsive Pattern Examples

```html
<!-- Responsive grid that adapts from 1 to 4 columns -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6">

<!-- Typography scaling -->
<h1 class="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tighter">

<!-- Responsive padding -->
<section class="px-4 sm:px-6 lg:px-8 py-16 sm:py-24 lg:py-32">

<!-- Hide/show based on screen -->
<div class="hidden lg:block">  <!-- Desktop sidebar -->
<div class="lg:hidden">        <!-- Mobile menu button -->

<!-- Responsive flex direction -->
<div class="flex flex-col md:flex-row md:items-center gap-4 md:gap-8">
```

---

## Dark Mode Implementation

### Strategy

Always use Tailwind's `dark:` variant. Apply the class strategy where the `dark` class is toggled on `<html>`.

```html
<!-- Example of complete dark mode coverage — all solid colors, no gradients -->
<div class="
  bg-white             dark:bg-zinc-900
  text-zinc-900        dark:text-zinc-100
  border-zinc-200      dark:border-zinc-800
  shadow-soft          dark:shadow-none
  placeholder:text-zinc-400  dark:placeholder:text-zinc-500
  ring-primary-500/20  dark:ring-primary-400/20
">
```

### Common Dark Mode Pitfalls

- **Forgetting border colors** — They look jarring in dark mode if not adjusted
- **Pure black backgrounds** — Use `zinc-950` or `zinc-900`, never `bg-black`
- **Shadow visibility** — Shadows barely show on dark bg; reduce or replace with subtle borders
- **Image contrast** — Add `dark:brightness-90` to images
- **White text opacity** — Use `text-zinc-100` or `text-zinc-200`, not always `text-white`
- **Gradients that looked fine in light mode** — They often look garish in dark mode; another reason to avoid gradients entirely

---

## Accessibility Guidelines

Every generated component MUST follow these rules:

1. **All interactive elements** need `focus-visible:` styles (outline or ring)
2. **Buttons** must have visible focus indicators: `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500`
3. **Form inputs** must have associated `<label>` elements
4. **Modals** must trap focus, have `role="dialog"`, `aria-modal="true"`, and close on Escape
5. **SVG icons without text** need `aria-hidden="true"` (decorative) or `role="img"` + `aria-label` (meaningful)
6. **Color alone** must NOT convey information — add icons/text alongside
7. **Minimum contrast ratios**: 4.5:1 for normal text, 3:1 for large text
8. **Touch targets**: minimum 44×44px on mobile (`min-h-11 min-w-11`)
9. **Skip links** on pages with navigation
10. **Reduced motion**: `motion-reduce:transition-none motion-reduce:animate-none`

```html
<!-- Screen reader only text -->
<span class="sr-only">Close dialog</span>

<!-- Reduced motion support -->
<div class="transition-all duration-300 motion-reduce:transition-none">

<!-- Skip to content link -->
<a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:top-4 focus:left-4 focus:rounded-lg focus:bg-primary-500 focus:px-4 focus:py-2 focus:text-white">
  Skip to content
</a>

<!-- Meaningful icon with label -->
<svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Notifications">
  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" />
  <path d="M13.73 21a2 2 0 01-3.46 0" />
</svg>
```

---

## Performance Optimization

1. **Use `v-show` instead of `v-if`** for elements that toggle frequently (dropdowns, tooltips)
2. **Inline SVG icons** are faster than importing icon library components — no extra JS bundle for icons
3. **Lazy-load below-fold sections** with `defineAsyncComponent`
4. **Virtual scrolling** for lists with 100+ items
5. **Use CSS transitions, not JS animations** wherever possible
6. **Avoid layout thrashing** — don't mix reads and writes to DOM in the same frame
7. **Use `will-change-transform`** on elements that animate (sparingly)
8. **Image optimization** — use `<img loading="lazy" decoding="async">`
9. **Avoid gradient repaints** — solid colors are cheaper to render than gradients, especially on mobile

---

## Anti-Patterns to Avoid

| ❌ Anti-Pattern | ✅ Correct Approach |
|---|---|
| Options API (`data()`, `methods`) | `<script setup>` with Composition API |
| `tailwind.config.js` in v4 | `@theme {}` in CSS file |
| Inline styles | Tailwind utility classes |
| `!important` overrides | Proper specificity management |
| Mixing border-radius sizes | Consistent radius tokens |
| Pure black `#000` backgrounds | `zinc-950` or `zinc-900` |
| Missing dark mode variants | `dark:` on every color/bg/border/shadow utility |
| No hover/focus states | Always define interaction states |
| Huge class strings without structure | Group logically with line breaks or computed |
| `any` TypeScript types | Proper interfaces and generics |
| `v-html` with user content | Sanitized or slot-based rendering |
| Multi-color gradients on buttons/cards | Solid `bg-*` colors everywhere |
| `bg-gradient-to-r from-X to-Y` on UI controls | Flat solid fills: `bg-primary-500` |
| Importing icon libraries for basic icons | Inline SVG with `currentColor` |
| Different `px-*` on header vs main content | Same shared `px-6` on both |
| Header content inside `max-w-7xl` but main content not (or vice versa) | Both use identical container structure |
| Extra `ml-64` on main but not on header | Both live inside `flex-1` next to sidebar |

---

## Advanced Prompt Techniques

### Specifying Design References

Add to your prompt for extra precision:

```
DESIGN REFERENCE:
- Layout inspiration: Linear.app (clean sidebar + content layout)
- Card style: Stripe Dashboard (subtle shadows, flat solid fills, tight spacing)
- Color vibe: Vercel (monochrome + single accent, NO gradients)
- Typography mood: Cal.com (bold, tight-tracked headings)
- Animation feel: Framer (smooth, spring-like, purposeful)
- Icons: Custom inline SVG only — no icon libraries

GRADIENT POLICY: NO gradients anywhere. All backgrounds, buttons, badges, cards, and
  navigation elements must use solid flat colors. The only exception is a barely-visible
  single-tone page background tint (e.g., from-zinc-50 to-white).

ALIGNMENT POLICY: The header bar and the main content area must share the exact same
  horizontal padding (px-6). Both must use identical max-width containers if any are used.
  Draw an imaginary vertical line from the leftmost header element — it must align perfectly
  with the leftmost content element in main.

SPECIFIC REQUIREMENTS:
- Hero section with bold solid-color text (accent colored span, not gradient text)
- Feature grid with icon-top cards and hover lift effect (inline SVG icons)
- Pricing table with recommended plan highlighted via solid accent bg
- Testimonial carousel with avatar + quote
- FAQ accordion with smooth open/close transition
- Footer with 4-column link layout + newsletter signup
```

### Requesting Multiple Variants

```
Generate this component with THREE variants:
1. Minimal — bare minimum styling, very clean, flat colors only
2. Rich — layered shadows, glass effects, still NO gradients
3. Playful — rounded-full shapes, vivid solid colors, emoji accents

Each variant should be a separate Vue SFC file.
All icons must be inline SVG, no icon library imports.
```

### Requesting a Full Page

```
Generate a COMPLETE landing page as a single Vue SFC with the following sections:
1. Sticky header with blur backdrop on scroll
2. Hero with headline, subtext, CTA button, and abstract SVG illustration (generated from scratch)
3. Logo cloud (6 partner logos as simple inline SVGs in grayscale, hover → color)
4. 3-column feature grid with custom inline SVG icons
5. Split section (text left, image/mockup right) with scroll-triggered entrance
6. Pricing (3 tiers, center one highlighted with solid accent bg — NOT a gradient)
7. Testimonials (3 cards, staggered layout)
8. CTA banner (solid accent background, centered text + button — NO gradient)
9. Footer (4 columns, bottom bar with copyright)

RULES:
- Use ONLY Tailwind CSS v4 utilities and Vue 3 <script setup lang="ts">
- Every section must be responsive and support dark mode
- All transitions should be smooth and purposeful
- ZERO gradients — all backgrounds are solid colors
- All icons are inline SVG with currentColor, no external icon library
- Every section shares the same horizontal padding for perfect vertical alignment
```

---

## Real-World Page Templates

### Dashboard Layout Structure

**CRITICAL: Header and main content share the same `px-6` padding so content is perfectly aligned.**

```vue
<script setup lang="ts">
import { ref } from 'vue'

const sidebarOpen = ref(true)
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
    <!-- Sidebar — fixed width, no gradients -->
    <aside
      :class="[
        'fixed inset-y-0 start-0 z-30 w-64 border-e border-zinc-200 dark:border-zinc-800',
        'bg-white dark:bg-zinc-900 transition-transform duration-300',
        'lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
      ]"
    >
      <!-- Sidebar header — same height as top header for alignment -->
      <div class="flex h-16 items-center gap-2.5 border-b border-zinc-200 dark:border-zinc-800 px-6">
        <div class="size-8 rounded-lg bg-primary-500 flex items-center justify-center text-white text-sm font-bold">
          A
        </div>
        <span class="font-display text-lg font-bold tracking-tight text-zinc-900 dark:text-white">Acme</span>
      </div>

      <!-- Sidebar navigation -->
      <nav class="flex-1 overflow-y-auto p-4 space-y-1">
        <a href="#" class="flex items-center gap-3 rounded-xl bg-primary-500/10 px-3 py-2.5 text-sm font-medium text-primary-600 dark:text-primary-400">
          <!-- Dashboard icon — inline SVG -->
          <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="3" y="3" width="8" height="8" rx="1" />
            <rect x="13" y="3" width="8" height="4" rx="1" />
            <rect x="3" y="13" width="8" height="4" rx="1" />
            <rect x="13" y="9" width="8" height="8" rx="1" />
          </svg>
          Dashboard
        </a>
        <a href="#" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors">
          <!-- Analytics icon -->
          <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 20V10M12 20V4M6 20v-6" />
          </svg>
          Analytics
        </a>
        <a href="#" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors">
          <!-- Users icon -->
          <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          Users
        </a>
        <a href="#" class="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors">
          <!-- Settings icon -->
          <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          Settings
        </a>
      </nav>
    </aside>

    <!-- Main content area — flex-1 takes remaining space after sidebar -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <!--
        ╔══════════════════════════════════════════════════════════╗
        ║  CRITICAL ALIGNMENT: Header uses px-6                   ║
        ║  Main content below also uses px-6                      ║
        ║  This ensures left edges are PERFECTLY aligned           ║
        ╚══════════════════════════════════════════════════════════╝
      -->

      <!-- Top header bar — px-6 matches main content padding -->
      <header class="sticky top-0 z-20 flex h-16 shrink-0 items-center gap-4 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl px-6">
        <!-- Mobile sidebar toggle -->
        <button
          class="lg:hidden rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800 transition-colors"
          @click="sidebarOpen = !sidebarOpen"
          aria-label="Toggle sidebar"
        >
          <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <!-- Page title (left-aligned, starts at the same x as content below) -->
        <h1 class="text-lg font-semibold text-zinc-900 dark:text-white">Dashboard</h1>

        <div class="flex-1" />

        <!-- Header right actions -->
        <div class="flex items-center gap-2">
          <!-- Search -->
          <button class="rounded-lg p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 dark:hover:text-zinc-300 dark:hover:bg-zinc-800 transition-colors" aria-label="Search">
            <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.35-4.35" />
            </svg>
          </button>
          <!-- Notifications -->
          <button class="rounded-lg p-2 text-zinc-400 hover:text-zinc-600 hover:bg-zinc-100 dark:hover:text-zinc-300 dark:hover:bg-zinc-800 transition-colors" aria-label="Notifications">
            <svg class="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 01-3.46 0" />
            </svg>
          </button>
          <!-- Avatar -->
          <div class="size-8 rounded-full bg-zinc-200 dark:bg-zinc-700" />
        </div>
      </header>

      <!-- Scrollable content — px-6 matches header padding exactly -->
      <main id="main" class="flex-1 overflow-y-auto">
        <div class="px-6 py-8">
          <!--
            Content starts here — its left edge is exactly
            aligned with the "Dashboard" title in the header above
            because both use px-6 inside the same flex-1 container.
          -->
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>
```

### Stat Card for Dashboard

```vue
<script setup lang="ts">
interface StatCardProps {
  title: string
  value: string
  change: number
  changeLabel: string
}

const props = defineProps<StatCardProps>()

const isPositive = props.change >= 0
</script>

<template>
  <!-- Solid bg, no gradient — flat card design -->
  <div class="rounded-2xl border border-zinc-200/70 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6 shadow-soft">
    <div class="flex items-center justify-between">
      <p class="text-sm font-medium text-zinc-500 dark:text-zinc-400">{{ title }}</p>
      <div class="rounded-xl bg-zinc-100 dark:bg-zinc-800 p-2.5">
        <!-- Icon slot — use inline SVG from parent -->
        <slot name="icon">
          <!-- Default chart icon -->
          <svg class="size-5 text-zinc-600 dark:text-zinc-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 20V10M12 20V4M6 20v-6" />
          </svg>
        </slot>
      </div>
    </div>

    <p class="mt-3 text-3xl font-bold tracking-tight text-zinc-900 dark:text-white">
      {{ value }}
    </p>

    <div class="mt-2 flex items-center gap-1.5">
      <span
        :class="[
          'inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium',
          isPositive
            ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
            : 'bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400',
        ]"
      >
        <!-- Trend icon — inline SVG -->
        <svg v-if="isPositive" class="size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M23 6l-9.5 9.5-5-5L1 18" /><path d="M17 6h6v6" />
        </svg>
        <svg v-else class="size-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M23 18l-9.5-9.5-5 5L1 6" /><path d="M17 18h6v-6" />
        </svg>
        {{ Math.abs(change) }}%
      </span>
      <span class="text-xs text-zinc-400 dark:text-zinc-500">{{ changeLabel }}</span>
    </div>
  </div>
</template>
```

---

## Summary Checklist

Before considering any generated UI component "complete", verify:

- [ ] Uses `<script setup lang="ts">` with proper TypeScript types
- [ ] All props have defaults via `withDefaults`
- [ ] Tailwind v4 `@theme` CSS is used (no `tailwind.config.js`)
- [ ] Responsive on all breakpoints (mobile-first)
- [ ] Dark mode classes on every color/bg/border/shadow utility
- [ ] Hover, focus-visible, active, and disabled states defined
- [ ] Proper semantic HTML (`<nav>`, `<main>`, `<section>`, etc.)
- [ ] ARIA attributes on interactive elements
- [ ] Smooth transitions (150–300ms ease-out)
- [ ] Consistent border-radius tokens
- [ ] Layered shadows for depth
- [ ] Reduced motion support (`motion-reduce:`)
- [ ] No inline styles
- [ ] No `any` types
- [ ] Generous whitespace
- [ ] Accent color used sparingly
- [ ] Text is balanced and readable (`text-balance`, `max-w-prose`)
- [ ] **All icons are inline SVG** with `currentColor`, `viewBox="0 0 24 24"`, proper `stroke-linecap/linejoin` — no icon library imports
- [ ] **Icons have proper accessibility**: `aria-hidden="true"` for decorative, `role="img"` + `aria-label` for meaningful
- [ ] **ZERO intrusive gradients** — all buttons, cards, badges, nav, and UI controls use solid background colors
- [ ] **Header and main content are perfectly aligned** — same `px-*` value on both, identical container structure
- [ ] **Sidebar width is fixed** (`w-64`), content area uses `flex-1`
- [ ] Loading and empty states handled

This prompt system, when used consistently, will produce UI components that match the quality of world-class design teams — with crisp alignment, clean flat aesthetics, and fully self-contained SVG iconography.