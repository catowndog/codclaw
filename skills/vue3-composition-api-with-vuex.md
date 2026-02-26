A comprehensive guide to integrating Vue 3 Composition API with Vuex 4 for state management, covering store setup, composables, module patterns, TypeScript support, and migration strategies.

# Vue 3 Composition API with Vuex — Complete Guide

## Table of Contents

1. [Introduction & Overview](#introduction--overview)
2. [Installation & Setup](#installation--setup)
3. [Core Concepts: Vuex in Composition API](#core-concepts-vuex-in-composition-api)
4. [Accessing Store with `useStore()`](#accessing-store-with-usestore)
5. [State](#state)
6. [Getters](#getters)
7. [Mutations](#mutations)
8. [Actions](#actions)
9. [Modules](#modules)
10. [Namespaced Modules](#namespaced-modules)
11. [Creating Composables for Vuex](#creating-composables-for-vuex)
12. [TypeScript Integration](#typescript-integration)
13. [Advanced Patterns](#advanced-patterns)
14. [Testing](#testing)
15. [Performance Optimization](#performance-optimization)
16. [Common Pitfalls & Troubleshooting](#common-pitfalls--troubleshooting)
17. [Migration from Options API to Composition API](#migration-from-options-api-to-composition-api)
18. [Vuex vs Pinia — When to Use What](#vuex-vs-pinia--when-to-use-what)
19. [Real-World Application Example](#real-world-application-example)
20. [Best Practices Summary](#best-practices-summary)

---

## Introduction & Overview

Vuex 4 is the official state management library compatible with Vue 3. While Vuex was originally designed with the Options API in mind (using `mapState`, `mapGetters`, `mapMutations`, `mapActions` helpers), the Composition API requires a different approach. The `useStore()` composable hook replaces all of those map helpers and gives you direct access to the store instance inside the `setup()` function.

### Key differences between Options API and Composition API with Vuex

| Feature | Options API | Composition API |
|---------|-------------|-----------------|
| Store access | `this.$store` | `useStore()` |
| State mapping | `mapState()` | `store.state.xxx` or `computed(() => store.state.xxx)` |
| Getters mapping | `mapGetters()` | `computed(() => store.getters.xxx)` |
| Mutations | `mapMutations()` | `store.commit('xxx')` |
| Actions | `mapActions()` | `store.dispatch('xxx')` |
| Reactivity | Automatic | Must use `computed()` for reactivity |

---

## Installation & Setup

### Installing Vuex 4

```bash
# npm
npm install vuex@4

# yarn
yarn add vuex@4

# pnpm
pnpm add vuex@4
```

### Creating the Store

Create a file `src/store/index.js` (or `.ts` for TypeScript):

```javascript
// src/store/index.js
import { createStore } from 'vuex'

const store = createStore({
  state() {
    return {
      count: 0,
      user: null,
      todos: [],
      isLoading: false,
      error: null
    }
  },

  getters: {
    doubleCount(state) {
      return state.count * 2
    },
    completedTodos(state) {
      return state.todos.filter(todo => todo.completed)
    },
    getTodoById: (state) => (id) => {
      return state.todos.find(todo => todo.id === id)
    },
    isAuthenticated(state) {
      return state.user !== null
    }
  },

  mutations: {
    INCREMENT(state) {
      state.count++
    },
    DECREMENT(state) {
      state.count--
    },
    SET_COUNT(state, payload) {
      state.count = payload
    },
    SET_USER(state, user) {
      state.user = user
    },
    SET_TODOS(state, todos) {
      state.todos = todos
    },
    ADD_TODO(state, todo) {
      state.todos.push(todo)
    },
    REMOVE_TODO(state, id) {
      state.todos = state.todos.filter(todo => todo.id !== id)
    },
    TOGGLE_TODO(state, id) {
      const todo = state.todos.find(todo => todo.id === id)
      if (todo) {
        todo.completed = !todo.completed
      }
    },
    SET_LOADING(state, isLoading) {
      state.isLoading = isLoading
    },
    SET_ERROR(state, error) {
      state.error = error
    }
  },

  actions: {
    async fetchTodos({ commit }) {
      commit('SET_LOADING', true)
      commit('SET_ERROR', null)
      try {
        const response = await fetch('https://jsonplaceholder.typicode.com/todos?_limit=10')
        const todos = await response.json()
        commit('SET_TODOS', todos)
      } catch (error) {
        commit('SET_ERROR', error.message)
      } finally {
        commit('SET_LOADING', false)
      }
    },

    async login({ commit }, credentials) {
      commit('SET_LOADING', true)
      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(credentials)
        })
        const user = await response.json()
        commit('SET_USER', user)
        return user
      } catch (error) {
        commit('SET_ERROR', error.message)
        throw error
      } finally {
        commit('SET_LOADING', false)
      }
    },

    logout({ commit }) {
      commit('SET_USER', null)
    },

    incrementAsync({ commit }, delay = 1000) {
      return new Promise(resolve => {
        setTimeout(() => {
          commit('INCREMENT')
          resolve()
        }, delay)
      })
    }
  }
})

export default store
```

### Registering the Store in the Application

```javascript
// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import store from './store'

const app = createApp(App)
app.use(store)
app.mount('#app')
```

---

## Accessing Store with `useStore()`

The `useStore()` composable is the primary way to interact with Vuex inside the Composition API's `setup()` function.

```vue
<script setup>
import { useStore } from 'vuex'

// Get the store instance
const store = useStore()

// Now you have access to:
// store.state     — reactive state
// store.getters   — computed getters
// store.commit()  — commit mutations
// store.dispatch() — dispatch actions
</script>
```

### Important: `useStore()` must be called inside `setup()`

```javascript
// ❌ WRONG — outside of setup
const store = useStore()

export default {
  setup() {
    // ❌ WRONG — store is undefined here
  }
}

// ✅ CORRECT
export default {
  setup() {
    const store = useStore()
    // use store here
  }
}

// ✅ CORRECT — with <script setup>
// <script setup>
// import { useStore } from 'vuex'
// const store = useStore()
// </script>
```

---

## State

### Accessing State Reactively

To maintain reactivity when accessing state, you **must** wrap state access in `computed()`:

```vue
<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

// ✅ Reactive — will update when state changes
const count = computed(() => store.state.count)
const user = computed(() => store.state.user)
const todos = computed(() => store.state.todos)
const isLoading = computed(() => store.state.isLoading)

// ❌ NOT reactive — will NOT update when state changes
const staticCount = store.state.count
</script>

<template>
  <div>
    <p>Count: {{ count }}</p>
    <p>User: {{ user?.name }}</p>
    <p>Loading: {{ isLoading }}</p>
    <ul>
      <li v-for="todo in todos" :key="todo.id">{{ todo.title }}</li>
    </ul>
  </div>
</template>
```

### Why `computed()` is Required

In the Options API, `mapState` internally creates computed properties. In the Composition API, you must do this explicitly. If you use `store.state.count` without wrapping it in `computed()`, you get the primitive value at that moment — it won't track changes.

```javascript
// Demonstration of the reactivity difference
const store = useStore()

// This is just a number (e.g., 0). It won't change.
const notReactive = store.state.count

// This is a computed ref that tracks store.state.count
const reactive = computed(() => store.state.count)

// Access the value with .value in script
console.log(reactive.value) // 0

// In template, Vue auto-unwraps refs, so {{ reactive }} works directly
```

### Using `toRefs` with Vuex State (Advanced Technique)

You can destructure state reactively using a helper, but be cautious — this creates a direct reference:

```javascript
import { computed, toRef } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

// toRef creates a ref that syncs with the source
// BUT it's read-only in practice (you shouldn't mutate state directly)
const count = toRef(store.state, 'count')
```

> **Warning**: While `toRef` works, mutations to this ref bypass Vuex's mutation tracking. Always use `commit()` to change state.

---

## Getters

### Accessing Getters

Getters are accessed similarly to state — use `computed()` for reactivity:

```vue
<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

// Simple getter
const doubleCount = computed(() => store.getters.doubleCount)

// Getter that returns a function (parameterized getter)
const getTodoById = (id) => store.getters.getTodoById(id)

// Alternative: make the parameterized getter reactive for a specific ID
const specificTodo = computed(() => store.getters.getTodoById(5))

const completedTodos = computed(() => store.getters.completedTodos)
const isAuthenticated = computed(() => store.getters.isAuthenticated)
</script>

<template>
  <div>
    <p>Double: {{ doubleCount }}</p>
    <p>Authenticated: {{ isAuthenticated }}</p>
    <p>Completed: {{ completedTodos.length }}</p>
    <!-- Parameterized getter usage -->
    <p>Todo #5: {{ getTodoById(5)?.title }}</p>
  </div>
</template>
```

### Accessing Namespaced Getters

```javascript
// For a module with namespace 'cart'
const cartItems = computed(() => store.getters['cart/items'])
const cartTotal = computed(() => store.getters['cart/totalPrice'])
```

---

## Mutations

### Committing Mutations

```vue
<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

const count = computed(() => store.state.count)

// Simple commit
function increment() {
  store.commit('INCREMENT')
}

function decrement() {
  store.commit('DECREMENT')
}

// Commit with payload
function setCount(value) {
  store.commit('SET_COUNT', value)
}

// Commit with object-style
function setCountObject(value) {
  store.commit({
    type: 'SET_COUNT',
    amount: value
  })
}

// Commit in inline handler
function toggleTodo(id) {
  store.commit('TOGGLE_TODO', id)
}
</script>

<template>
  <div>
    <p>{{ count }}</p>
    <button @click="increment">+</button>
    <button @click="decrement">-</button>
    <button @click="setCount(0)">Reset</button>
    <button @click="store.commit('INCREMENT')">Inline Commit</button>
  </div>
</template>
```

### Mutation Naming Convention

Always use `UPPER_SNAKE_CASE` for mutation type names — this is the widely adopted Vuex convention:

```javascript
// constants/mutation-types.js
export const SET_USER = 'SET_USER'
export const SET_LOADING = 'SET_LOADING'
export const ADD_ITEM = 'ADD_ITEM'
export const REMOVE_ITEM = 'REMOVE_ITEM'
export const UPDATE_ITEM = 'UPDATE_ITEM'

// store/index.js
import { SET_USER, SET_LOADING } from './constants/mutation-types'

const store = createStore({
  mutations: {
    [SET_USER](state, user) {
      state.user = user
    },
    [SET_LOADING](state, isLoading) {
      state.isLoading = isLoading
    }
  }
})
```

---

## Actions

### Dispatching Actions

```vue
<script setup>
import { computed, onMounted } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

const todos = computed(() => store.state.todos)
const isLoading = computed(() => store.state.isLoading)
const error = computed(() => store.state.error)

// Dispatch on component mount
onMounted(() => {
  store.dispatch('fetchTodos')
})

// Dispatch with payload
async function handleLogin() {
  try {
    const user = await store.dispatch('login', {
      email: 'user@example.com',
      password: 'password'
    })
    console.log('Logged in as:', user.name)
  } catch (err) {
    console.error('Login failed:', err.message)
  }
}

// Dispatch with object-style
function fetchWithOptions() {
  store.dispatch({
    type: 'fetchTodos',
    filter: 'active'
  })
}

// Dispatch async action
async function incrementLater() {
  await store.dispatch('incrementAsync', 2000)
  console.log('Incremented after 2 seconds')
}
</script>

<template>
  <div>
    <div v-if="isLoading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <ul v-else>
      <li v-for="todo in todos" :key="todo.id">{{ todo.title }}</li>
    </ul>
    <button @click="handleLogin">Login</button>
    <button @click="incrementLater">Increment Later</button>
  </div>
</template>
```

### Chaining Multiple Actions

```javascript
async function fullWorkflow() {
  await store.dispatch('login', credentials)
  await store.dispatch('fetchTodos')
  await store.dispatch('fetchUserProfile')
}
```

---

## Modules

### Creating Vuex Modules

Modules allow you to split your store into logical units:

```javascript
// store/modules/auth.js
const authModule = {
  state() {
    return {
      user: null,
      token: null,
      isAuthenticated: false
    }
  },

  getters: {
    currentUser(state) {
      return state.user
    },
    isLoggedIn(state) {
      return state.isAuthenticated
    }
  },

  mutations: {
    SET_USER(state, user) {
      state.user = user
      state.isAuthenticated = !!user
    },
    SET_TOKEN(state, token) {
      state.token = token
    },
    CLEAR_AUTH(state) {
      state.user = null
      state.token = null
      state.isAuthenticated = false
    }
  },

  actions: {
    async login({ commit }, credentials) {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
      })
      const data = await response.json()
      commit('SET_USER', data.user)
      commit('SET_TOKEN', data.token)
      localStorage.setItem('token', data.token)
      return data.user
    },

    logout({ commit }) {
      commit('CLEAR_AUTH')
      localStorage.removeItem('token')
    },

    async checkAuth({ commit }) {
      const token = localStorage.getItem('token')
      if (!token) return

      try {
        const response = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        })
        const user = await response.json()
        commit('SET_USER', user)
        commit('SET_TOKEN', token)
      } catch {
        commit('CLEAR_AUTH')
        localStorage.removeItem('token')
      }
    }
  }
}

export default authModule
```

```javascript
// store/modules/todos.js
const todosModule = {
  state() {
    return {
      items: [],
      filter: 'all', // 'all' | 'active' | 'completed'
      isLoading: false
    }
  },

  getters: {
    filteredTodos(state) {
      switch (state.filter) {
        case 'active':
          return state.items.filter(t => !t.completed)
        case 'completed':
          return state.items.filter(t => t.completed)
        default:
          return state.items
      }
    },
    todosCount(state) {
      return state.items.length
    },
    activeTodosCount(state) {
      return state.items.filter(t => !t.completed).length
    }
  },

  mutations: {
    SET_TODOS(state, todos) {
      state.items = todos
    },
    ADD_TODO(state, todo) {
      state.items.push(todo)
    },
    REMOVE_TODO(state, id) {
      state.items = state.items.filter(t => t.id !== id)
    },
    TOGGLE_TODO(state, id) {
      const todo = state.items.find(t => t.id === id)
      if (todo) todo.completed = !todo.completed
    },
    SET_FILTER(state, filter) {
      state.filter = filter
    },
    SET_LOADING(state, val) {
      state.isLoading = val
    }
  },

  actions: {
    async fetchTodos({ commit }) {
      commit('SET_LOADING', true)
      try {
        const res = await fetch('/api/todos')
        const todos = await res.json()
        commit('SET_TODOS', todos)
      } finally {
        commit('SET_LOADING', false)
      }
    },
    async addTodo({ commit }, title) {
      const res = await fetch('/api/todos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, completed: false })
      })
      const todo = await res.json()
      commit('ADD_TODO', todo)
    }
  }
}

export default todosModule
```

### Registering Modules

```javascript
// store/index.js
import { createStore } from 'vuex'
import authModule from './modules/auth'
import todosModule from './modules/todos'

const store = createStore({
  // Root state
  state() {
    return {
      appName: 'My App',
      version: '1.0.0'
    }
  },

  modules: {
    auth: authModule,
    todos: todosModule
  }
})

export default store
```

### Accessing Module State in Composition API

```vue
<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

// Module state is nested under the module name
const user = computed(() => store.state.auth.user)
const isLoggedIn = computed(() => store.state.auth.isAuthenticated)
const todos = computed(() => store.state.todos.items)
const filter = computed(() => store.state.todos.filter)

// Without namespacing, getters/mutations/actions are in global namespace
const currentUser = computed(() => store.getters.currentUser)
const filteredTodos = computed(() => store.getters.filteredTodos)

function login(credentials) {
  store.dispatch('login', credentials)
}

function addTodo(title) {
  store.dispatch('addTodo', title)
}
</script>
```

---

## Namespaced Modules

Namespacing prevents naming collisions between modules:

```javascript
// store/modules/cart.js
const cartModule = {
  namespaced: true, // <— Enable namespacing

  state() {
    return {
      items: [],
      discount: 0
    }
  },

  getters: {
    totalItems(state) {
      return state.items.reduce((sum, item) => sum + item.quantity, 0)
    },
    totalPrice(state) {
      const subtotal = state.items.reduce(
        (sum, item) => sum + item.price * item.quantity, 0
      )
      return subtotal * (1 - state.discount / 100)
    },
    // Accessing root state and root getters
    itemsWithUserInfo(state, getters, rootState, rootGetters) {
      const user = rootState.auth.user
      return state.items.map(item => ({
        ...item,
        addedBy: user?.name || 'Anonymous'
      }))
    }
  },

  mutations: {
    ADD_ITEM(state, product) {
      const existing = state.items.find(i => i.id === product.id)
      if (existing) {
        existing.quantity++
      } else {
        state.items.push({ ...product, quantity: 1 })
      }
    },
    REMOVE_ITEM(state, productId) {
      state.items = state.items.filter(i => i.id !== productId)
    },
    UPDATE_QUANTITY(state, { productId, quantity }) {
      const item = state.items.find(i => i.id === productId)
      if (item) item.quantity = quantity
    },
    CLEAR_CART(state) {
      state.items = []
    },
    SET_DISCOUNT(state, discount) {
      state.discount = discount
    }
  },

  actions: {
    addToCart({ commit, state }, product) {
      const inCart = state.items.find(i => i.id === product.id)
      if (inCart && inCart.quantity >= product.stock) {
        throw new Error('Not enough stock')
      }
      commit('ADD_ITEM', product)
    },

    async checkout({ commit, state, rootState }, paymentInfo) {
      const user = rootState.auth.user
      if (!user) throw new Error('Must be logged in')

      const order = {
        items: state.items,
        userId: user.id,
        payment: paymentInfo
      }

      const res = await fetch('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order)
      })

      if (res.ok) {
        commit('CLEAR_CART')
        // Dispatch action in another namespace
        // { root: true } allows calling root-level or other module actions
      }
    },

    // Action that dispatches to root or other modules
    addAndNotify({ dispatch, commit }, product) {
      commit('ADD_ITEM', product)
      // Dispatch a root-level action
      dispatch('showNotification', {
        message: `${product.name} added to cart`
      }, { root: true })
    }
  }
}

export default cartModule
```

### Accessing Namespaced Modules in Composition API

```vue
<script setup>
import { computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

// State — always accessed by module path regardless of namespace
const cartItems = computed(() => store.state.cart.items)
const discount = computed(() => store.state.cart.discount)

// Getters — prepend namespace path
const totalItems = computed(() => store.getters['cart/totalItems'])
const totalPrice = computed(() => store.getters['cart/totalPrice'])

// Mutations — prepend namespace path
function addItem(product) {
  store.commit('cart/ADD_ITEM', product)
}

function removeItem(productId) {
  store.commit('cart/REMOVE_ITEM', productId)
}

function clearCart() {
  store.commit('cart/CLEAR_CART')
}

// Actions — prepend namespace path
async function addToCart(product) {
  try {
    await store.dispatch('cart/addToCart', product)
  } catch (err) {
    console.error(err.message)
  }
}

async function checkout(paymentInfo) {
  await store.dispatch('cart/checkout', paymentInfo)
}
</script>
```

---

## Creating Composables for Vuex

The most powerful pattern — create reusable composables that encapsulate store logic:

### Basic Store Composable

```javascript
// composables/useCounter.js
import { computed } from 'vue'
import { useStore } from 'vuex'

export function useCounter() {
  const store = useStore()

  const count = computed(() => store.state.count)
  const doubleCount = computed(() => store.getters.doubleCount)

  function increment() {
    store.commit('INCREMENT')
  }

  function decrement() {
    store.commit('DECREMENT')
  }

  function setCount(value) {
    store.commit('SET_COUNT', value)
  }

  async function incrementAsync(delay) {
    await store.dispatch('incrementAsync', delay)
  }

  return {
    count,
    doubleCount,
    increment,
    decrement,
    setCount,
    incrementAsync
  }
}
```

### Auth Composable

```javascript
// composables/useAuth.js
import { computed } from 'vue'
import { useStore } from 'vuex'

export function useAuth() {
  const store = useStore()

  const user = computed(() => store.state.auth.user)
  const isAuthenticated = computed(() => store.state.auth.isAuthenticated)
  const token = computed(() => store.state.auth.token)

  async function login(email, password) {
    return store.dispatch('auth/login', { email, password })
  }

  async function logout() {
    return store.dispatch('auth/logout')
  }

  async function checkAuth() {
    return store.dispatch('auth/checkAuth')
  }

  return {
    user,
    isAuthenticated,
    token,
    login,
    logout,
    checkAuth
  }
}
```

### Cart Composable

```javascript
// composables/useCart.js
import { computed } from 'vue'
import { useStore } from 'vuex'

export function useCart() {
  const store = useStore()

  const items = computed(() => store.state.cart.items)
  const totalItems = computed(() => store.getters['cart/totalItems'])
  const totalPrice = computed(() => store.getters['cart/totalPrice'])
  const isEmpty = computed(() => store.state.cart.items.length === 0)

  function addItem(product) {
    store.dispatch('cart/addToCart', product)
  }

  function removeItem(productId) {
    store.commit('cart/REMOVE_ITEM', productId)
  }

  function updateQuantity(productId, quantity) {
    store.commit('cart/UPDATE_QUANTITY', { productId, quantity })
  }

  function clear() {
    store.commit('cart/CLEAR_CART')
  }

  async function checkout(paymentInfo) {
    return store.dispatch('cart/checkout', paymentInfo)
  }

  return {
    items,
    totalItems,
    totalPrice,
    isEmpty,
    addItem,
    removeItem,
    updateQuantity,
    clear,
    checkout
  }
}
```

### Using Composables in Components

```vue
<script setup>
import { useAuth } from '@/composables/useAuth'
import { useCart } from '@/composables/useCart'

const { user, isAuthenticated, logout } = useAuth()
const { totalItems, totalPrice } = useCart()
</script>

<template>
  <header>
    <nav>
      <span v-if="isAuthenticated">
        Welcome, {{ user.name }}!
        <button @click="logout">Logout</button>
      </span>
      <router-link to="/cart">
        Cart ({{ totalItems }}) — ${{ totalPrice.toFixed(2) }}
      </router-link>
    </nav>
  </header>
</template>
```

### Generic Helper: `useState` and `useGetters`

Create utility composables that mimic `mapState` and `mapGetters`:

```javascript
// composables/vuexHelpers.js
import { computed } from 'vue'
import { useStore } from 'vuex'

/**
 * Maps vuex state properties to computed refs
 * @param {string} namespace - Optional module namespace
 * @param {string[]} properties - State property names
 */
export function useState(namespace, properties) {
  const store = useStore()

  // If no namespace provided, shift arguments
  if (typeof namespace !== 'string') {
    properties = namespace
    namespace = null
  }

  const stateObj = {}
  properties.forEach(prop => {
    stateObj[prop] = computed(() => {
      if (namespace) {
        return store.state[namespace][prop]
      }
      return store.state[prop]
    })
  })

  return stateObj
}

/**
 * Maps vuex getters to computed refs
 * @param {string} namespace - Optional module namespace
 * @param {string[]} getterNames - Getter names
 */
export function useGetters(namespace, getterNames) {
  const store = useStore()

  if (typeof namespace !== 'string') {
    getterNames = namespace
    namespace = null
  }

  const gettersObj = {}
  getterNames.forEach(name => {
    const key = namespace ? `${namespace}/${name}` : name
    gettersObj[name] = computed(() => store.getters[key])
  })

  return gettersObj
}

/**
 * Maps vuex mutations to callable functions
 */
export function useMutations(namespace, mutationNames) {
  const store = useStore()

  if (typeof namespace !== 'string') {
    mutationNames = namespace
    namespace = null
  }

  const mutationsObj = {}
  mutationNames.forEach(name => {
    const key = namespace ? `${namespace}/${name}` : name
    mutationsObj[name] = (payload) => store.commit(key, payload)
  })

  return mutationsObj
}

/**
 * Maps vuex actions to callable functions
 */
export function useActions(namespace, actionNames) {
  const store = useStore()

  if (typeof namespace !== 'string') {
    actionNames = namespace
    namespace = null
  }

  const actionsObj = {}
  actionNames.forEach(name => {
    const key = namespace ? `${namespace}/${name}` : name
    actionsObj[name] = (payload) => store.dispatch(key, payload)
  })

  return actionsObj
}
```

### Usage of Helper Composables

```vue
<script setup>
import { useState, useGetters, useActions } from '@/composables/vuexHelpers'

// Root state
const { count, isLoading } = useState(['count', 'isLoading'])

// Namespaced state
const { items, filter } = useState('todos', ['items', 'filter'])

// Namespaced getters
const { filteredTodos, todosCount } = useGetters('todos', ['filteredTodos', 'todosCount'])

// Namespaced actions
const { fetchTodos, addTodo } = useActions('todos', ['fetchTodos', 'addTodo'])
</script>
```

---

## TypeScript Integration

### Typed Store Setup

```typescript
// store/types.ts
export interface User {
  id: number
  name: string
  email: string
  avatar?: string
}

export interface Todo {
  id: number
  title: string
  completed: boolean
  userId: number
}

export interface CartItem {
  id: number
  name: string
  price: number
  quantity: number
  stock: number
}

// Root state
export interface RootState {
  appName: string
  version: string
}

// Module states
export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
}

export interface TodosState {
  items: Todo[]
  filter: 'all' | 'active' | 'completed'
  isLoading: boolean
}

export interface CartState {
  items: CartItem[]
  discount: number
}

// Combined state (with modules)
export interface State extends RootState {
  auth: AuthState
  todos: TodosState
  cart: CartState
}
```

### Typed `useStore()`

```typescript
// store/index.ts
import { createStore, Store, useStore as baseUseStore } from 'vuex'
import { InjectionKey } from 'vue'
import { State } from './types'
import authModule from './modules/auth'
import todosModule from './modules/todos'
import cartModule from './modules/cart'

// Define injection key
export const key: InjectionKey<Store<State>> = Symbol()

const store = createStore<State>({
  state(): RootState {
    return {
      appName: 'My Typed App',
      version: '1.0.0'
    }
  },
  modules: {
    auth: authModule,
    todos: todosModule,
    cart: cartModule
  }
})

// Typed useStore composable
export function useStore(): Store<State> {
  return baseUseStore(key)
}

export default store
```

### Register with Injection Key

```typescript
// main.ts
import { createApp } from 'vue'
import App from './App.vue'
import store, { key } from './store'

const app = createApp(App)
app.use(store, key) // Pass the key here
app.mount('#app')
```

### Using Typed Store

```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useStore } from '@/store' // Import from YOUR store file, not from 'vuex'

const store = useStore()

// TypeScript now knows the shape of state
const appName = computed(() => store.state.appName) // string
const user = computed(() => store.state.auth.user)  // User | null
const todos = computed(() => store.state.todos.items) // Todo[]

// TypeScript will catch errors:
// store.state.nonExistent // ❌ Error: Property 'nonExistent' does not exist
</script>
```

### Typed Module Definition

```typescript
// store/modules/auth.ts
import { Module } from 'vuex'
import { AuthState, RootState, User } from '../types'

const authModule: Module<AuthState, RootState> = {
  namespaced: true,

  state(): AuthState {
    return {
      user: null,
      token: null,
      isAuthenticated: false,
    }
  },

  getters: {
    currentUser(state): User | null {
      return state.user
    },
    isLoggedIn(state): boolean {
      return state.isAuthenticated
    },
    displayName(state): string {
      return state.user?.name ?? 'Guest'
    }
  },

  mutations: {
    SET_USER(state, user: User | null) {
      state.user = user
      state.isAuthenticated = user !== null
    },
    SET_TOKEN(state, token: string | null) {
      state.token = token
    },
    CLEAR_AUTH(state) {
      state.user = null
      state.token = null
      state.isAuthenticated = false
    }
  },

  actions: {
    async login({ commit }, credentials: { email: string; password: string }) {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      })
      const data: { user: User; token: string } = await response.json()
      commit('SET_USER', data.user)
      commit('SET_TOKEN', data.token)
      return data.user
    }
  }
}

export default authModule
```

---

## Advanced Patterns

### Subscribing to Mutations and Actions

```vue
<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

let unsubscribeMutation
let unsubscribeAction

onMounted(() => {
  // Subscribe to mutations
  unsubscribeMutation = store.subscribe((mutation, state) => {
    console.log(`Mutation: ${mutation.type}`, mutation.payload)

    // Example: persist state to localStorage on every mutation
    localStorage.setItem('appState', JSON.stringify(state))
  })

  // Subscribe to actions
  unsubscribeAction = store.subscribeAction({
    before: (action, state) => {
      console.log(`Before action: ${action.type}`)
    },
    after: (action, state) => {
      console.log(`After action: ${action.type}`)
    },
    error: (action, state, error) => {
      console.error(`Action ${action.type} failed:`, error)
      // Send to error tracking service
    }
  })
})

onUnmounted(() => {
  // Always unsubscribe to prevent memory leaks
  unsubscribeMutation?.()
  unsubscribeAction?.()
})
</script>
```

### Dynamic Module Registration

```javascript
// composables/useDynamicModule.js
import { onMounted, onUnmounted } from 'vue'
import { useStore } from 'vuex'

export function useDynamicModule(moduleName, moduleDefinition) {
  const store = useStore()

  onMounted(() => {
    // Register the module only if it doesn't exist
    if (!store.hasModule(moduleName)) {
      store.registerModule(moduleName, moduleDefinition)
    }
  })

  onUnmounted(() => {
    // Optionally unregister when component unmounts
    if (store.hasModule(moduleName)) {
      store.unregisterModule(moduleName)
    }
  })

  return store
}
```

```vue
<script setup>
import { computed } from 'vue'
import { useDynamicModule } from '@/composables/useDynamicModule'

const adminModule = {
  namespaced: true,
  state: () => ({
    dashboardData: null,
    users: []
  }),
  mutations: {
    SET_DASHBOARD(state, data) { state.dashboardData = data },
    SET_USERS(state, users) { state.users = users }
  },
  actions: {
    async fetchDashboard({ commit }) {
      const res = await fetch('/api/admin/dashboard')
      commit('SET_DASHBOARD', await res.json())
    }
  }
}

const store = useDynamicModule('admin', adminModule)

const dashboardData = computed(() => store.state.admin?.dashboardData)
</script>
```

### Plugin-Based Persistence

```javascript
// store/plugins/persistence.js
export function createPersistencePlugin(options = {}) {
  const { key = 'vuex-state', paths = null, storage = localStorage } = options

  return (store) => {
    // Load persisted state
    const savedState = storage.getItem(key)
    if (savedState) {
      try {
        const parsed = JSON.parse(savedState)
        store.replaceState({ ...store.state, ...parsed })
      } catch (e) {
        console.warn('Failed to load persisted state:', e)
      }
    }

    // Subscribe to save state on mutations
    store.subscribe((mutation, state) => {
      try {
        let stateToPersist = state
        if (paths) {
          stateToPersist = paths.reduce((result, path) => {
            const keys = path.split('.')
            let value = state
            for (const k of keys) {
              value = value[k]
            }
            result[path] = value
            return result
          }, {})
        }
        storage.setItem(key, JSON.stringify(stateToPersist))
      } catch (e) {
        console.warn('Failed to persist state:', e)
      }
    })
  }
}

// Usage in store
import { createPersistencePlugin } from './plugins/persistence'

const store = createStore({
  // ...
  plugins: [
    createPersistencePlugin({
      key: 'my-app-state',
      paths: ['auth.token', 'cart.items']
    })
  ]
})
```

### Watching Store Changes

```vue
<script setup>
import { watch, computed } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

// Watch specific state
watch(
  () => store.state.auth.isAuthenticated,
  (isAuth, wasAuth) => {
    if (isAuth && !wasAuth) {
      console.log('User just logged in!')
      // router.push('/dashboard')
    }
    if (!isAuth && wasAuth) {
      console.log('User just logged out!')
      // router.push('/login')
    }
  }
)

// Watch a getter
watch(
  () => store.getters['cart/totalItems'],
  (newTotal) => {
    if (newTotal > 10) {
      alert('You have more than 10 items in your cart!')
    }
  }
)

// Watch deep state
watch(
  () => store.state.cart.items,
  (newItems) => {
    console.log('Cart items changed:', newItems)
  },
  { deep: true }
)
</script>
```

---

## Testing

### Testing Composables with Vuex

```javascript
// tests/composables/useAuth.test.js
import { createStore } from 'vuex'
import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { useAuth } from '@/composables/useAuth'

function createTestStore(initialState = {}) {
  return createStore({
    modules: {
      auth: {
        namespaced: true,
        state() {
          return {
            user: null,
            token: null,
            isAuthenticated: false,
            ...initialState
          }
        },
        mutations: {
          SET_USER(state, user) {
            state.user = user
            state.isAuthenticated = !!user
          },
          CLEAR_AUTH(state) {
            state.user = null
            state.token = null
            state.isAuthenticated = false
          }
        },
        actions: {
          login: jest.fn(),
          logout({ commit }) {
            commit('CLEAR_AUTH')
          }
        }
      }
    }
  })
}

// Helper component to test composable
function withSetup(composableFn) {
  let result
  const TestComponent = defineComponent({
    setup() {
      result = composableFn()
      return () => null
    }
  })
  return { TestComponent, result: () => result }
}

describe('useAuth', () => {
  it('returns initial unauthenticated state', () => {
    const store = createTestStore()
    const { TestComponent, result } = withSetup(useAuth)

    mount(TestComponent, {
      global: { plugins: [store] }
    })

    const { user, isAuthenticated } = result()
    expect(user.value).toBeNull()
    expect(isAuthenticated.value).toBe(false)
  })

  it('reflects authenticated state', () => {
    const store = createTestStore({
      user: { id: 1, name: 'John' },
      isAuthenticated: true
    })
    const { TestComponent, result } = withSetup(useAuth)

    mount(TestComponent, {
      global: { plugins: [store] }
    })

    const { user, isAuthenticated } = result()
    expect(user.value).toEqual({ id: 1, name: 'John' })
    expect(isAuthenticated.value).toBe(true)
  })

  it('logout clears auth state', async () => {
    const store = createTestStore({
      user: { id: 1, name: 'John' },
      isAuthenticated: true
    })
    const { TestComponent, result } = withSetup(useAuth)

    mount(TestComponent, {
      global: { plugins: [store] }
    })

    const { logout, isAuthenticated } = result()
    await logout()
    expect(isAuthenticated.value).toBe(false)
  })
})
```

### Testing Components with Vuex Store

```javascript
// tests/components/TodoList.test.js
import { mount } from '@vue/test-utils'
import { createStore } from 'vuex'
import TodoList from '@/components/TodoList.vue'

function createMockStore(state = {}) {
  return createStore({
    state() {
      return {
        todos: {
          items: [
            { id: 1, title: 'Test 1', completed: false },
            { id: 2, title: 'Test 2', completed: true }
          ],
          isLoading: false,
          ...state
        }
      }
    },
    getters: {
      'todos/filteredTodos': (state) => state.todos.items,
      'todos/todosCount': (state) => state.todos.items.length
    },
    actions: {
      'todos/fetchTodos': jest.fn(),
      'todos/addTodo': jest.fn()
    },
    mutations: {
      'todos/TOGGLE_TODO': jest.fn()
    }
  })
}

describe('TodoList', () => {
  it('renders todos', () => {
    const store = createMockStore()
    const wrapper = mount(TodoList, {
      global: { plugins: [store] }
    })

    expect(wrapper.findAll('li')).toHaveLength(2)
    expect(wrapper.text()).toContain('Test 1')
    expect(wrapper.text()).toContain('Test 2')
  })

  it('shows loading state', () => {
    const store = createMockStore({ isLoading: true, items: [] })
    const wrapper = mount(TodoList, {
      global: { plugins: [store] }
    })

    expect(wrapper.text()).toContain('Loading')
  })
})
```

---

## Performance Optimization

### 1. Avoid Unnecessary Computations

```javascript
// ❌ Bad — creates a new array reference on every state change
const expensiveTodos = computed(() => {
  return store.state.todos.items
    .filter(t => !t.completed)
    .sort((a, b) => a.title.localeCompare(b.title))
    .map(t => ({ ...t, formattedDate: formatDate(t.createdAt) }))
})

// ✅ Good — move expensive computation to a getter (cached by Vuex)
// In store:
getters: {
  sortedActiveTodos(state) {
    return state.items
      .filter(t => !t.completed)
      .sort((a, b) => a.title.localeCompare(b.title))
  }
}

// In component:
const sortedTodos = computed(() => store.getters['todos/sortedActiveTodos'])
```

### 2. Use `shallowRef` for Large Data Sets

```javascript
// In mutations, if setting large arrays, consider normalization
mutations: {
  SET_PRODUCTS(state, products) {
    // Normalize into a map for O(1) lookup
    state.productsById = Object.fromEntries(
      products.map(p => [p.id, p])
    )
    state.productIds = products.map(p => p.id)
  }
}
```

### 3. Avoid Accessing Store in Tight Loops

```javascript
// ❌ Bad
function processItems() {
  const items = store.state.items // Grab reference once instead
  for (let i = 0; i < 10000; i++) {
    doSomething(store.state.items[i]) // Accessed 10,000 times
  }
}

// ✅ Good
function processItems() {
  const items = store.state.items
  for (let i = 0; i < items.length; i++) {
    doSomething(items[i])
  }
}
```

---

## Common Pitfalls & Troubleshooting

### Pitfall 1: Missing `computed()` Wrapper

```javascript
// ❌ Value won't react to store changes
const count = store.state.count

// ✅ Reactive
const count = computed(() => store.state.count)
```

### Pitfall 2: Directly Mutating State

```javascript
// ❌ NEVER do this — bypasses Vuex devtools and mutation tracking
store.state.count = 5
store.state.todos.push(newTodo)

// ✅ Always use mutations
store.commit('SET_COUNT', 5)
store.commit('ADD_TODO', newTodo)
```

### Pitfall 3: Calling `useStore()` Outside `setup()`

```javascript
// ❌ Will throw error or return undefined
const store = useStore() // Outside component

function someUtilFunction() {
  const store = useStore() // Not in setup()
}

// ✅ Pass store as parameter, or call in setup/composable
function someUtilFunction(store) {
  store.dispatch('someAction')
}

// In setup:
const store = useStore()
someUtilFunction(store)
```

### Pitfall 4: Forgetting Namespace Prefix

```javascript
// If module is namespaced: true
// ❌ Won't work
store.getters.totalPrice
store.commit('ADD_ITEM', product)

// ✅ Must include namespace
store.getters['cart/totalPrice']
store.commit('cart/ADD_ITEM', product)
```

### Pitfall 5: Async in Mutations

```javascript
// ❌ Mutations must be synchronous
mutations: {
  async FETCH_DATA(state) { // WRONG
    const data = await fetch('/api/data')
    state.data = await data.json()
  }
}

// ✅ Use actions for async operations
actions: {
  async fetchData({ commit }) {
    const data = await fetch('/api/data')
    commit('SET_DATA', await data.json())
  }
}
```

### Pitfall 6: Destructuring Reactive State

```javascript
// ❌ Loses reactivity  
const { count, user } = store.state // These are plain values now

// ✅ Use computed for each property
const count = computed(() => store.state.count)
const user = computed(() => store.state.user)
```

---

## Migration from Options API to Composition API

### Before (Options API)

```javascript
export default {
  computed: {
    ...mapState('auth', ['user', 'isAuthenticated']),
    ...mapGetters('cart', ['totalItems', 'totalPrice']),
    ...mapState({
      count: state => state.count
    })
  },
  methods: {
    ...mapMutations('cart', ['ADD_ITEM', 'REMOVE_ITEM']),
    ...mapActions('auth', ['login', 'logout']),
    ...mapActions('cart', ['checkout']),
    addToCart(product) {
      this.ADD_ITEM(product)
    }
  },
  created() {
    if (!this.isAuthenticated) {
      this.$store.dispatch('auth/checkAuth')
    }
  }
}
```

### After (Composition API)

```vue
<script setup>
import { computed, onMounted } from 'vue'
import { useStore } from 'vuex'

const store = useStore()

// State
const user = computed(() => store.state.auth.user)
const isAuthenticated = computed(() => store.state.auth.isAuthenticated)
const count = computed(() => store.state.count)

// Getters
const totalItems = computed(() => store.getters['cart/totalItems'])
const totalPrice = computed(() => store.getters['cart/totalPrice'])

// Mutations
function addItem(product) {
  store.commit('cart/ADD_ITEM', product)
}
function removeItem(productId) {
  store.commit('cart/REMOVE_ITEM', productId)
}

// Actions
function login(credentials) {
  return store.dispatch('auth/login', credentials)
}
function logout() {
  return store.dispatch('auth/logout')
}
function checkout(paymentInfo) {
  return store.dispatch('cart/checkout', paymentInfo)
}

// Lifecycle
onMounted(() => {
  if (!isAuthenticated.value) {
    store.dispatch('auth/checkAuth')
  }
})

// Composed method
function addToCart(product) {
  addItem(product)
}
</script>
```

---

## Vuex vs Pinia — When to Use What

| Criteria | Vuex 4 | Pinia |
|----------|--------|-------|
| Official status | Legacy (still maintained) | Officially recommended for Vue 3 |
| Mutations | Required (separate from actions) | No mutations — only actions |
| TypeScript | Partial support, requires boilerplate | First-class TypeScript support |
| DevTools | Full support | Full support |
| Bundle size | ~6kb | ~1.5kb |
| Composition API DX | Requires `useStore()` + string keys | Native composable pattern |
| Module system | Nested modules with namespacing | Flat stores, composable |
| SSR | Supported | Supported |
| Code splitting | Dynamic module registration | Automatic code splitting |
| Hot reloading | Supported | Better support |

**Use Vuex when**: You have an existing Vuex codebase, your team is familiar with the Flux pattern, or you need strict mutation tracking.

**Use Pinia when**: Starting a new project, you want better TypeScript support, simpler API, or smaller bundle size.

---

## Real-World Application Example

### Complete E-Commerce Checkout Flow

```javascript
// store/modules/products.js
export default {
  namespaced: true,
  state: () => ({
    items: [],
    currentProduct: null,
    categories: [],
    filters: { category: null, minPrice: 0, maxPrice: Infinity, search: '' },
    pagination: { page: 1, perPage: 20, total: 0 },
    isLoading: false
  }),
  getters: {
    filteredProducts(state) {
      return state.items.filter(p => {
        if (state.filters.category && p.category !== state.filters.category) return false
        if (p.price < state.filters.minPrice) return false
        if (p.price > state.filters.maxPrice) return false
        if (state.filters.search && !p.name.toLowerCase().includes(state.filters.search.toLowerCase())) return false
        return true
      })
    },
    paginatedProducts(state, getters) {
      const start = (state.pagination.page - 1) * state.pagination.perPage
      return getters.filteredProducts.slice(start, start + state.pagination.perPage)
    },
    totalPages(state, getters) {
      return Math.ceil(getters.filteredProducts.length / state.pagination.perPage)
    }
  },
  mutations: {
    SET_PRODUCTS(state, products) { state.items = products },
    SET_CURRENT_PRODUCT(state, product) { state.currentProduct = product },
    SET_CATEGORIES(state, categories) { state.categories = categories },
    SET_FILTER(state, { key, value }) { state.filters[key] = value },
    SET_PAGE(state, page) { state.pagination.page = page },
    SET_LOADING(state, val) { state.isLoading = val }
  },
  actions: {
    async fetchProducts({ commit }) {
      commit('SET_LOADING', true)
      try {
        const res = await fetch('/api/products')
        commit('SET_PRODUCTS', await res.json())
      } finally {
        commit('SET_LOADING', false)
      }
    },
    async fetchProduct({ commit }, id) {
      commit('SET_LOADING', true)
      try {
        const res = await fetch(`/api/products/${id}`)
        commit('SET_CURRENT_PRODUCT', await res.json())
      } finally {
        commit('SET_LOADING', false)
      }
    },
    setFilter({ commit }, filter) {
      commit('SET_FILTER', filter)
      commit('SET_PAGE', 1)
    }
  }
}
```

```javascript
// composables/useProducts.js
import { computed, onMounted } from 'vue'
import { useStore } from 'vuex'

export function useProducts() {
  const store = useStore()

  const products = computed(() => store.getters['products/paginatedProducts'])
  const allProducts = computed(() => store.getters['products/filteredProducts'])
  const currentProduct = computed(() => store.state.products.currentProduct)
  const isLoading = computed(() => store.state.products.isLoading)
  const categories = computed(() => store.state.products.categories)
  const filters = computed(() => store.state.products.filters)
  const currentPage = computed(() => store.state.products.pagination.page)
  const totalPages = computed(() => store.getters['products/totalPages'])

  function fetchProducts() {
    return store.dispatch('products/fetchProducts')
  }

  function fetchProduct(id) {
    return store.dispatch('products/fetchProduct', id)
  }

  function setFilter(key, value) {
    store.dispatch('products/setFilter', { key, value })
  }

  function setPage(page) {
    store.commit('products/SET_PAGE', page)
  }

  return {
    products,
    allProducts,
    currentProduct,
    isLoading,
    categories,
    filters,
    currentPage,
    totalPages,
    fetchProducts,
    fetchProduct,
    setFilter,
    setPage
  }
}
```

```vue
<!-- ProductList.vue -->
<script setup>
import { onMounted } from 'vue'
import { useProducts } from '@/composables/useProducts'
import { useCart } from '@/composables/useCart'

const {
  products,
  isLoading,
  filters,
  currentPage,
  totalPages,
  fetchProducts,
  setFilter,
  setPage
} = useProducts()

const { addItem } = useCart()

onMounted(fetchProducts)

function handleSearch(event) {
  setFilter('search', event.target.value)
}

function handleCategoryChange(category) {
  setFilter('category', category)
}
</script>

<template>
  <div class="product-list">
    <div class="filters">
      <input
        type="text"
        placeholder="Search products..."
        :value="filters.search"
        @input="handleSearch"
      />
      <select @change="handleCategoryChange($event.target.value)">
        <option value="">All Categories</option>
        <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
      </select>
    </div>

    <div v-if="isLoading" class="loading">Loading products...</div>

    <div v-else class="grid">
      <div v-for="product in products" :key="product.id" class="product-card">
        <img :src="product.image" :alt="product.name" />
        <h3>{{ product.name }}</h3>
        <p class="price">${{ product.price.toFixed(2) }}</p>
        <button @click="addItem(product)" :disabled="product.stock === 0">
          {{ product.stock > 0 ? 'Add to Cart' : 'Out of Stock' }}
        </button>
      </div>
    </div>

    <div class="pagination" v-if="totalPages > 1">
      <button @click="setPage(currentPage - 1)" :disabled="currentPage === 1">Prev</button>
      <span>Page {{ currentPage }} of {{ totalPages }}</span>
      <button @click="setPage(currentPage + 1)" :disabled="currentPage === totalPages">Next</button>
    </div>
  </div>
</template>
```

---

## Best Practices Summary

### Do's ✅

1. **Always use `computed()`** when reading state or getters in Composition API
2. **Create composables** to encapsulate Vuex logic per feature domain
3. **Use namespaced modules** for medium-to-large applications
4. **Keep mutations simple** — synchronous, single-purpose state changes
5. **Use actions for business logic** — async operations, validation, multi-commit flows
6. **Define mutation type constants** for large codebases
7. **Type your store** with TypeScript when possible
8. **Unsubscribe** from store subscriptions in `onUnmounted`
9. **Normalize deeply nested data** for performance
10. **Test composables and store** in isolation

### Don'ts ❌

1. **Don't mutate state directly** — always use mutations via `commit()`
2. **Don't put async code in mutations** — use actions instead
3. **Don't call `useStore()` outside `setup()`** — it relies on the component injection context
4. **Don't destructure `store.state`** directly — you lose reactivity
5. **Don't put rendering logic in the store** — keep the store for data logic
6. **Don't create god-stores** — split into focused modules
7. **Don't forget namespace prefix** when accessing namespaced module members
8. **Don't over-use Vuex** — local component state is fine for component-specific data
9. **Don't duplicate state** — derive computed values from existing state via getters
10. **Don't ignore error handling** in actions — always catch and handle errors properly

### Store Structure for Large Applications

```
src/
├── store/
│   ├── index.js              # createStore, register modules
│   ├── types.ts              # TypeScript interfaces
│   ├── constants/
│   │   └── mutation-types.js # Mutation type constants
│   ├── modules/
│   │   ├── auth.js
│   │   ├── cart.js
│   │   ├── products.js
│   │   ├── orders.js
│   │   └── ui.js             # UI state (sidebar, modals, toasts)
│   └── plugins/
│       ├── persistence.js
│       └── logger.js
├── composables/
│   ├── useAuth.js
│   ├── useCart.js
│   ├── useProducts.js
│   ├── useOrders.js
│   └── vuexHelpers.js        # useState, useGetters utilities
└── ...
```

This structure provides clear separation of concerns, makes the codebase navigable, and allows teams to work on different modules independently. Each composable acts as a clean interface between the Vue component layer and the Vuex store, making components simpler and more testable.