# 🔄 State Management Migration

> **Tujuan**: Migrasi `st.session_state` ke React state management
> 
> **File Source**: `main.py`, `modules/session_manager.py`

---

## 📊 Session State Mapping

| Streamlit | React (Zustand) | Scope |
|-----------|-----------------|-------|
| `st.session_state.authenticated` | `useAuthStore()` | Global |
| `st.session_state.selected_groups` | `useFilterStore()` | Global |
| `st.session_state.activities` | `useActivityStore()` | Global |
| `st.session_state.show_email_form` | `useState()` | Local |

---

## 🏗️ State Structure

```
frontend/stores/
├── authStore.ts      # Authentication state
├── filterStore.ts    # Filter/group selection
├── activityStore.ts  # Activity logging
└── index.ts          # Export all stores
```

---

## 📄 Auth Store (Pengganti st.session_state authentication)

```typescript
// frontend/stores/authStore.ts

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  username: string
  role: 'admin' | 'user'
  user_id: number
}

interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  
  // Actions
  login: (user: User, token: string) => void
  logout: () => void
  isAdmin: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      isAuthenticated: false,
      user: null,
      token: null,

      login: (user, token) => {
        set({ 
          isAuthenticated: true, 
          user, 
          token 
        })
      },

      logout: () => {
        set({ 
          isAuthenticated: false, 
          user: null, 
          token: null 
        })
      },

      isAdmin: () => get().user?.role === 'admin',
    }),
    {
      name: 'auth-storage', // localStorage key
    }
  )
)

/*
Streamlit equivalent:

# Initialize
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None

# Check auth
if is_authenticated():
    ...

# Login
st.session_state.authenticated = True
st.session_state.username = user['username']
st.session_state.role = user['role']

# Logout
st.session_state.authenticated = False
*/
```

---

## 📄 Filter Store (Pengganti st.session_state.selected_groups)

```typescript
// frontend/stores/filterStore.ts

import { create } from 'zustand'

interface FilterState {
  selectedGroups: string[]
  searchQuery: string
  sortBy: string | null
  sortOrder: 'asc' | 'desc'
  
  // Actions
  setSelectedGroups: (groups: string[]) => void
  setSearchQuery: (query: string) => void
  setSorting: (column: string | null, order?: 'asc' | 'desc') => void
  clearFilters: () => void
}

export const useFilterStore = create<FilterState>()((set) => ({
  selectedGroups: [],
  searchQuery: '',
  sortBy: null,
  sortOrder: 'asc',

  setSelectedGroups: (groups) => set({ selectedGroups: groups }),
  
  setSearchQuery: (query) => set({ searchQuery: query }),
  
  setSorting: (column, order = 'asc') => set({ sortBy: column, sortOrder: order }),
  
  clearFilters: () => set({ 
    selectedGroups: [], 
    searchQuery: '', 
    sortBy: null,
    sortOrder: 'asc'
  }),
}))

/*
Streamlit equivalent:

# Initialize
if 'selected_groups' not in st.session_state:
    st.session_state.selected_groups = []

# Update
selected_groups = st.multiselect(
    "Select item groups",
    options=available_groups,
    default=st.session_state.selected_groups
)
st.session_state.selected_groups = selected_groups
*/
```

---

## 📄 Activity Store (Pengganti st.session_state.activities)

```typescript
// frontend/stores/activityStore.ts

import { create } from 'zustand'

interface Activity {
  id: string
  time: string
  action: string
  color: string
}

interface ActivityState {
  activities: Activity[]
  maxActivities: number
  
  // Actions
  logActivity: (action: string, color?: string) => void
  clearActivities: () => void
}

export const useActivityStore = create<ActivityState>()((set, get) => ({
  activities: [],
  maxActivities: 5,

  logActivity: (action, color = '#6366f1') => {
    const newActivity: Activity = {
      id: crypto.randomUUID(),
      time: new Date().toLocaleTimeString('id-ID'),
      action,
      color,
    }

    set((state) => ({
      activities: [newActivity, ...state.activities].slice(0, state.maxActivities),
    }))
  },

  clearActivities: () => set({ activities: [] }),
}))

/*
Streamlit equivalent:

# modules/activity_logger.py

def log_activity(action: str, color: str = '#6366f1'):
    new_activity = {
        'time': datetime.now().strftime('%H:%M:%S'), 
        'action': action, 
        'color': color
    }
    st.session_state.activities.insert(0, new_activity)
    st.session_state.activities = st.session_state.activities[:5]
*/
```

---

## 🔌 Using Stores in Components

### Auth Check (Protected Route)

```tsx
// frontend/app/dashboard/page.tsx

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import { useFilterStore } from '@/stores/filterStore'
import { useActivityStore } from '@/stores/activityStore'

export default function DashboardPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  const { selectedGroups } = useFilterStore()
  const { logActivity } = useActivityStore()

  // Auth check - replaces: if not is_authenticated(): st.stop()
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
    } else {
      logActivity('Navigated to Dashboard', '#6366f1')
    }
  }, [isAuthenticated, router, logActivity])

  if (!isAuthenticated) return null

  return (
    <div>
      <h1>Welcome, {user?.username}!</h1>
      {/* Dashboard content */}
    </div>
  )
}
```

### Filter Component

```tsx
// frontend/components/layout/GroupFilter.tsx

'use client'

import { useFilterStore } from '@/stores/filterStore'
import { useQuery } from '@tanstack/react-query'
import { inventoryApi } from '@/lib/api'

export function GroupFilter() {
  const { selectedGroups, setSelectedGroups } = useFilterStore()
  
  // Fetch available groups
  const { data: groups } = useQuery({
    queryKey: ['groups'],
    queryFn: () => inventoryApi.getGroups().then(res => res.data.groups),
  })

  return (
    <div className="p-4 border-b border-gray-700">
      <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
        🏷️ Filter by Group
      </h3>
      
      <select
        multiple
        value={selectedGroups}
        onChange={(e) => {
          const selected = Array.from(e.target.selectedOptions, opt => opt.value)
          setSelectedGroups(selected)
        }}
        className="w-full bg-dark-800 border border-gray-700 rounded-lg p-2 text-white"
      >
        {groups?.map((group: string) => (
          <option key={group} value={group}>{group}</option>
        ))}
      </select>
      
      {selectedGroups.length > 0 && (
        <p className="text-xs text-gray-400 mt-2">
          📌 {selectedGroups.length} group(s) selected
        </p>
      )}
    </div>
  )
}
```

### Activity Log Sidebar

```tsx
// frontend/components/layout/ActivityLog.tsx

'use client'

import { useActivityStore } from '@/stores/activityStore'

export function ActivityLog() {
  const { activities } = useActivityStore()

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">
        📋 Recent Activity
      </h3>
      
      <div className="space-y-2">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-center gap-2 text-sm"
            style={{ borderLeftColor: activity.color }}
          >
            <span className="text-xs text-gray-500">{activity.time}</span>
            <span className="text-gray-300">{activity.action}</span>
          </div>
        ))}
        
        {activities.length === 0 && (
          <p className="text-xs text-gray-500">No recent activity</p>
        )}
      </div>
    </div>
  )
}
```

---

## 🔄 Data Fetching with React Query

```tsx
// Pengganti @st.cache_data dengan React Query

import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/lib/api'
import { useFilterStore } from '@/stores/filterStore'

export function useDashboardMetrics() {
  const { selectedGroups } = useFilterStore()
  
  return useQuery({
    queryKey: ['dashboard', 'metrics', selectedGroups],
    queryFn: () => dashboardApi.getMetrics(selectedGroups).then(res => res.data),
    staleTime: 5 * 60 * 1000, // 5 menit (seperti cache timeout)
  })
}

// Penggunaan di component:
export function DashboardMetrics() {
  const { data, isLoading, refetch } = useDashboardMetrics()
  
  if (isLoading) return <div>Loading...</div>
  
  return (
    <div>
      <MetricCard label="Active Alerts" value={data.active_alerts} />
      <button onClick={() => refetch()}>🔄 Refresh</button>
    </div>
  )
}
```

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[10_DEPLOYMENT.md](./10_DEPLOYMENT.md)** untuk panduan deployment (opsional).
