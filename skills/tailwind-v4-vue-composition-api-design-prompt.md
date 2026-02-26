A comprehensive prompt engineering guide and design system for generating beautiful, modern, production-ready UI components using Tailwind CSS v4 and Vue 3 Composition API.

---

## Table of Contents

1. [Overview](#overview)
2. [Master Design Prompt Template](#master-design-prompt-template)
3. [Tailwind CSS v4 — Key Changes and New Features](#tailwind-css-v4--key-changes-and-new-features)
4. [Vue 3 Composition API Patterns](#vue-3-composition-api-patterns)
5. [Design Principles and Aesthetics](#design-principles-and-aesthetics)
6. [Color System and Theming](#color-system-and-theming)
7. [Typography System](#typography-system)
8. [Layout Patterns](#layout-patterns)
9. [Component Library — Full Examples](#component-library--full-examples)
10. [Animation and Micro-Interactions](#animation-and-micro-interactions)
11. [Responsive Design Strategy](#responsive-design-strategy)
12. [Dark Mode Implementation](#dark-mode-implementation)
13. [Accessibility Guidelines](#accessibility-guidelines)
14. [Performance Optimization](#performance-optimization)
15. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
16. [Advanced Prompt Techniques](#advanced-prompt-techniques)
17. [Real-World Page Templates](#real-world-page-templates)

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
- Lucide Icons (via lucide-vue-next) or Heroicons for iconography
- VueUse composables where helpful (useColorMode, useMediaQuery, etc.)

DESIGN PHILOSOPHY:
- Modern, clean, premium aesthetic inspired by Linear, Vercel, Stripe, Apple
- Generous whitespace — never cramped layouts
- Subtle depth via layered shadows, not flat or overly skeuomorphic
- Micro-interactions on every interactive element (hover, focus, active states)
- Glass morphism used sparingly for accent panels/modals
- Smooth transitions (150ms–300ms ease-out for UI, 500ms+ for page transitions)
- Color palette: neutral base (zinc/slate/stone) + one vibrant accent color
- Typography: tight letter-spacing for headings, relaxed for body text
- Border radius: consistent (use rounded-xl or rounded-2xl, never mix sizes randomly)
- Every component must be fully responsive (mobile-first approach)
- Dark mode support is MANDATORY (use Tailwind dark: variant)

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

  /* Accent color */
  --color-accent: oklch(0.72 0.21 330);
  --color-accent-hover: oklch(0.65 0.24 330);

  /* Surface colors for cards, panels */
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
import { useMotion } from '@vueuse/motion'
import { Icon } from 'lucide-vue-next'

// ============================================
// Types
// ============================================
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  loading?: boolean
  disabled?: boolean
  icon?: Component
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
      // Base styles
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
    <!-- Loading spinner -->
    <svg
      v-if="loading"
      class="animate-spin -ms-0.5 size-4"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>

    <!-- Left icon -->
    <component
      :is="icon"
      v-if="icon && iconPosition === 'left' && !loading"
      class="size-4 shrink-0"
    />

    <!-- Slot content -->
    <span><slot /></span>

    <!-- Right icon -->
    <component
      :is="icon"
      v-if="icon && iconPosition === 'right' && !loading"
      class="size-4 shrink-0"
    />
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

3. **Subtle borders separate content** — Use `border border-zinc-200/60 dark:border-zinc-700/50` instead of harsh `border-gray-300`.

4. **Consistent border radius** — Pick ONE radius scale and stick to it. Cards = `rounded-2xl`, Buttons = `rounded-xl`, Inputs = `rounded-lg`, Badges = `rounded-full`.

5. **Muted backgrounds with clear surfaces** — Page bg: `bg-zinc-50 dark:bg-zinc-950`. Card bg: `bg-white dark:bg-zinc-900`. This creates natural layering.

6. **Color restraint** — Use your accent color for CTAs and key interactive elements ONLY. Everything else should be neutral zinc/slate tones.

7. **Typography hierarchy** — Maximum 3 font sizes per section. Headings: `text-3xl font-semibold tracking-tight`. Body: `text-base text-zinc-600`. Caption: `text-sm text-zinc-400`.

8. **Hover states must feel alive** — Combine color shift + shadow increase + subtle translateY:
   ```
   hover:shadow-medium hover:-translate-y-0.5 transition-all duration-200
   ```

9. **Loading states everywhere** — Skeleton screens, spinners, progress bars. Never leave the user staring at empty space.

10. **Iconography consistency** — Use ONE icon library. Size icons at `size-4` for inline, `size-5` for buttons, `size-6` for section headers, `size-8`+ for feature showcases.

---

## Color System and Theming

### Recommended Premium Color Palettes

**Palette 1 — "Midnight Indigo" (SaaS Dashboard)**
```css
@theme {
  --color-primary-500: oklch(0.55 0.20 265);  /* Deep indigo */
  --color-accent: oklch(0.75 0.15 165);        /* Teal accent */
  --color-surface: oklch(0.99 0.002 265);      /* Barely tinted white */
}
```

**Palette 2 — "Electric Violet" (Creative/Design Tool)**
```css
@theme {
  --color-primary-500: oklch(0.55 0.25 300);   /* Vivid purple */
  --color-accent: oklch(0.80 0.20 85);         /* Warm amber accent */
  --color-surface: oklch(0.985 0.005 300);
}
```

**Palette 3 — "Ocean Depth" (Finance/Fintech)**
```css
@theme {
  --color-primary-500: oklch(0.50 0.12 230);   /* Deep blue */
  --color-accent: oklch(0.70 0.18 150);        /* Green for positive */
  --color-surface: oklch(0.99 0.003 230);
}
```

**Palette 4 — "Obsidian" (Developer Tools / Dark-first)**
```css
@theme {
  --color-primary-500: oklch(0.70 0.15 145);   /* Green terminal vibes */
  --color-accent: oklch(0.75 0.12 55);         /* Warm orange accent */
  --color-surface: oklch(0.13 0.01 260);       /* Dark surface */
  --color-surface-elevated: oklch(0.17 0.01 260);
}
```

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
<!-- Hero heading -->
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
    bg-gradient-to-br from-primary-500 to-primary-700
    text-white shadow-large shadow-primary-500/20
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
  icon?: Component
}

const props = withDefaults(defineProps<InputProps>(), {
  type: 'text',
})

const model = defineModel<string>({ default: '' })

const inputClasses = computed(() => [
  // Base
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
  // Icon padding
  props.icon && 'ps-10',
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
      <!-- Leading icon -->
      <div v-if="icon" class="pointer-events-none absolute inset-y-0 start-0 flex items-center ps-3 text-zinc-400">
        <component :is="icon" class="size-4" />
      </div>

      <input
        v-model="model"
        :type="type"
        :placeholder="placeholder"
        :disabled="disabled"
        :class="inputClasses"
        :aria-invalid="!!error"
        :aria-describedby="error ? 'input-error' : hint ? 'input-hint' : undefined"
      />
    </div>

    <!-- Error message -->
    <p v-if="error" id="input-error" class="text-sm text-error flex items-center gap-1">
      <svg class="size-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
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
import { watch, ref, onMounted } from 'vue'

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
        <!-- Backdrop -->
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
                <svg class="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12" />
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
import { ref, computed } from 'vue'
import { Menu, X, ChevronDown } from 'lucide-vue-next'

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

      <!-- CTA buttons -->
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

      <!-- Mobile menu toggle -->
      <button
        class="md:hidden rounded-lg p-2 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
        @click="isMobileMenuOpen = !isMobileMenuOpen"
        :aria-label="isMobileMenuOpen ? 'Close menu' : 'Open menu'"
      >
        <component :is="isMobileMenuOpen ? X : Menu" class="size-5" />
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

<!-- Glow on hover -->
class="hover:shadow-[0_0_24px_rgba(99,102,241,0.25)] transition-shadow duration-300"

<!-- Background slide effect -->
class="relative overflow-hidden before:absolute before:inset-0 before:bg-primary-500 before:translate-x-[-100%] hover:before:translate-x-0 before:transition-transform before:duration-300"

<!-- Border color animation -->
class="border border-transparent hover:border-primary-500/50 transition-colors duration-200"

<!-- Underline slide-in for nav links -->
class="relative after:absolute after:bottom-0 after:left-0 after:h-0.5 after:w-0 hover:after:w-full after:bg-primary-500 after:transition-all after:duration-300"
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
<!-- Example of complete dark mode coverage -->
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

---

## Accessibility Guidelines

Every generated component MUST follow these rules:

1. **All interactive elements** need `focus-visible:` styles (outline or ring)
2. **Buttons** must have visible focus indicators: `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500`
3. **Form inputs** must have associated `<label>` elements
4. **Modals** must trap focus, have `role="dialog"`, `aria-modal="true"`, and close on Escape
5. **Icons without text** need `aria-label` or `sr-only` text
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
```

---

## Performance Optimization

1. **Use `v-show` instead of `v-if`** for elements that toggle frequently (dropdowns, tooltips)
2. **Use `<component :is>` with `shallowRef`** for dynamic icon components
3. **Lazy-load below-fold sections** with `defineAsyncComponent`
4. **Virtual scrolling** for lists with 100+ items
5. **Use CSS transitions, not JS animations** wherever possible
6. **Avoid layout thrashing** — don't mix reads and writes to DOM in the same frame
7. **Use `will-change-transform`** on elements that animate (sparingly)
8. **Image optimization** — use `<img loading="lazy" decoding="async">`

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
| Missing dark mode variants | `dark:` on every color utility |
| No hover/focus states | Always define interaction states |
| Huge class strings without structure | Group logically with line breaks or computed |
| `any` TypeScript types | Proper interfaces and generics |
| `v-html` with user content | Sanitized or slot-based rendering |

---

## Advanced Prompt Techniques

### Specifying Design References

Add to your prompt for extra precision:

```
DESIGN REFERENCE:
- Layout inspiration: Linear.app (clean sidebar + content layout)
- Card style: Stripe Dashboard (subtle shadows, tight spacing)
- Color vibe: Vercel (monochrome + single accent)
- Typography mood: Cal.com (bold, tight-tracked headings)
- Animation feel: Framer (smooth, spring-like, purposeful)

SPECIFIC REQUIREMENTS:
- Hero section with animated gradient text
- Feature grid with icon-top cards and hover lift effect
- Pricing table with recommended plan highlighted
- Testimonial carousel with avatar + quote
- FAQ accordion with smooth open/close transition
- Footer with 4-column link layout + newsletter signup
```

### Requesting Multiple Variants

```
Generate this component with THREE variants:
1. Minimal — bare minimum styling, very clean
2. Rich — layered shadows, gradients, glass effects
3. Playful — rounded-full shapes, vivid colors, emoji accents

Each variant should be a separate Vue SFC file.
```

### Requesting a Full Page

```
Generate a COMPLETE landing page as a single Vue SFC with the following sections:
1. Sticky header with blur backdrop on scroll
2. Hero with headline, subtext, CTA button, and abstract SVG illustration
3. Logo cloud (6 partner logos in grayscale, hover → color)
4. 3-column feature grid with icons
5. Split section (text left, image/mockup right) with scroll-triggered entrance
6. Pricing (3 tiers, center one highlighted)
7. Testimonials (3 cards, staggered layout)
8. CTA banner (gradient background, centered text + button)
9. Footer (4 columns, bottom bar with copyright)

Use ONLY Tailwind CSS v4 utilities and Vue 3 <script setup lang="ts">.
Every section must be responsive and support dark mode.
All transitions should be smooth and purposeful.
```

---

## Real-World Page Templates

### Dashboard Layout Structure

```vue
<script setup lang="ts">
import { ref } from 'vue'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const sidebarOpen = ref(true)
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-zinc-50 dark:bg-zinc-950">
    <!-- Sidebar -->
    <aside
      :class="[
        'fixed inset-y-0 start-0 z-30 w-64 border-e border-zinc-200 dark:border-zinc-800',
        'bg-white dark:bg-zinc-900 transition-transform duration-300',
        'lg:static lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
      ]"
    >
      <Sidebar />
    </aside>

    <!-- Main content area -->
    <div class="flex flex-1 flex-col overflow-hidden">
      <!-- Top header bar -->
      <header class="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl px-6">
        <Header @toggle-sidebar="sidebarOpen = !sidebarOpen" />
      </header>

      <!-- Scrollable content -->
      <main id="main" class="flex-1 overflow-y-auto">
        <div class="mx-auto max-w-7xl px-6 py-8">
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
import { TrendingUp, TrendingDown } from 'lucide-vue-next'

interface StatCardProps {
  title: string
  value: string
  change: number
  changeLabel: string
  icon: Component
}

const props = defineProps<StatCardProps>()

const isPositive = props.change >= 0
</script>

<template>
  <div class="rounded-2xl border border-zinc-200/70 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6 shadow-soft">
    <div class="flex items-center justify-between">
      <p class="text-sm font-medium text-zinc-500 dark:text-zinc-400">{{ title }}</p>
      <div class="rounded-xl bg-zinc-100 dark:bg-zinc-800 p-2.5">
        <component :is="icon" class="size-5 text-zinc-600 dark:text-zinc-400" />
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
        <component :is="isPositive ? TrendingUp : TrendingDown" class="size-3" />
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
- [ ] Icons are consistently sized
- [ ] Loading and empty states handled

This prompt system, when used consistently, will produce UI components that match the quality of world-class design teams.