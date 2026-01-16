# 🎨 Frontend Setup (Next.js + TailwindCSS)

> **Tujuan**: Setup project Next.js dari awal
> 
> **Waktu**: ~20 menit

---

## 📁 Struktur Project Target

```
WPT-Project1-Folder/
├── backend/                   # Flask API (sudah dibuat)
├── frontend/                  # 🆕 Next.js Frontend
│   ├── app/                   # Next.js 14 App Router
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Landing/redirect
│   │   ├── login/
│   │   │   └── page.tsx       # Login page
│   │   ├── dashboard/
│   │   │   └── page.tsx       # Dashboard
│   │   ├── forecasting/
│   │   │   └── page.tsx       # Forecasting
│   │   └── ...
│   ├── components/            # React components
│   │   ├── ui/                # Base UI components
│   │   ├── layout/            # Layout components
│   │   └── charts/            # Chart components
│   ├── lib/                   # Utilities
│   │   ├── api.ts             # API client
│   │   ├── auth.ts            # Auth manager
│   │   └── utils.ts           # Helpers
│   ├── styles/
│   │   └── globals.css        # Global styles
│   ├── package.json
│   ├── tailwind.config.ts
│   └── next.config.js
└── modules/                   # Existing Streamlit
```

---

## 🚀 Step 1: Create Next.js Project

```powershell
# Di folder project
cd "d:\AA-WPT-PROJECT\AA-WPT-PROJECT\WPT-Project1-Folder(IntelligentInventoryOptimizationAndStockoutPrediction)"

# Create Next.js dengan flags (no interactive prompts)
npx -y create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm
```

**Pilihan saat setup (jika interactive):**
- TypeScript: **Yes**
- ESLint: **Yes**
- Tailwind CSS: **Yes**
- `src/` directory: **No** (kita pakai `app/` langsung)
- App Router: **Yes**
- Import alias: **@/***

---

## 📦 Step 2: Install Dependencies Tambahan

```powershell
cd frontend

# UI Components & Icons
npm install lucide-react clsx tailwind-merge

# Charts (alternatif Plotly)
npm install recharts

# Data Fetching & State
npm install @tanstack/react-query zustand axios

# Forms
npm install react-hook-form zod @hookform/resolvers

# Date handling
npm install date-fns
```

---

## ⚙️ Step 3: Configure Tailwind

### `frontend/tailwind.config.ts`

```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Warna dari CSS Streamlit app.py
        primary: {
          DEFAULT: '#6366f1',
          50: '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
        success: {
          DEFAULT: '#10b981',
          500: '#10b981',
        },
        warning: {
          DEFAULT: '#f59e0b',
          500: '#f59e0b',
        },
        danger: {
          DEFAULT: '#ef4444',
          500: '#ef4444',
        },
        dark: {
          DEFAULT: '#0f172a',
          50: '#f8fafc',
          100: '#f1f5f9',
          800: '#1e293b',
          900: '#0f172a',
        },
      },
      backgroundImage: {
        'gradient-card': 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        'gradient-sidebar': 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
        'gradient-primary': 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
      },
    },
  },
  plugins: [],
}

export default config
```

---

## 🎨 Step 4: Global Styles

### `frontend/app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* 
 * Global Styles
 * Migrasi dari: CSS di app.py (line 437-716)
 */

@layer base {
  :root {
    --primary-color: 99 102 241;
    --success-color: 16 185 129;
    --warning-color: 245 158 11;
    --danger-color: 239 68 68;
    --bg-dark: 15 23 42;
    --bg-card: 30 41 59;
  }
  
  body {
    @apply bg-dark-900 text-gray-100;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  }
}

@layer components {
  /* Metric Card - dari .metric-card di Streamlit */
  .metric-card {
    @apply bg-gradient-card p-5 rounded-xl border border-gray-700;
    @apply shadow-lg transition-all duration-200;
    @apply hover:-translate-y-0.5 hover:border-primary-500;
  }
  
  .metric-value {
    @apply text-4xl font-bold text-white my-1;
  }
  
  .metric-label {
    @apply text-sm text-gray-400 uppercase tracking-wider;
    @apply flex items-center gap-2;
  }
  
  .metric-delta {
    @apply text-sm font-semibold mt-1;
  }
  
  .metric-delta.positive {
    @apply text-success;
  }
  
  .metric-delta.negative {
    @apply text-danger;
  }
  
  /* Alert Box - dari .alert-* di Streamlit */
  .alert-box {
    @apply p-4 rounded-lg border-l-4 my-2;
  }
  
  .alert-critical {
    @apply bg-red-900/50 border-red-500;
  }
  
  .alert-warning {
    @apply bg-amber-900/50 border-amber-500;
  }
  
  .alert-info {
    @apply bg-blue-900/50 border-blue-500;
  }
  
  .alert-success {
    @apply bg-green-900/50 border-green-500;
  }
  
  /* Button - dari .stButton>button */
  .btn {
    @apply px-6 py-2.5 rounded-lg font-semibold;
    @apply transition-all duration-200;
  }
  
  .btn-primary {
    @apply bg-gradient-primary text-white;
    @apply hover:shadow-lg hover:shadow-primary-500/40;
  }
  
  .btn-secondary {
    @apply bg-dark-800 text-gray-300 border border-gray-600;
    @apply hover:bg-gray-700;
  }
  
  /* Sidebar - dari [data-testid="stSidebar"] */
  .sidebar {
    @apply bg-gradient-sidebar min-h-screen;
    @apply border-r border-gray-800;
  }
  
  /* Table - dari .improved-table */
  .data-table {
    @apply bg-dark-800/80 rounded-lg border border-gray-700;
  }
  
  .data-table th {
    @apply bg-primary-500/20 text-white p-4 text-left font-semibold;
    @apply border-b-2 border-gray-700;
  }
  
  .data-table td {
    @apply p-4 border-b border-gray-700 text-gray-200;
  }
  
  .data-table tr:hover {
    @apply bg-primary-500/10;
  }
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-dark-900;
}

::-webkit-scrollbar-thumb {
  @apply bg-gray-700 rounded;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-600;
}
```

---

## 📄 Step 5: Root Layout

### `frontend/app/layout.tsx`

```tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Inventory Intelligence Hub',
  description: 'PT Wahana Piranti Teknologi - Inventory Management System',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
```

### `frontend/app/providers.tsx`

```tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        refetchOnWindowFocus: false,
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
```

---

## 🔌 Step 6: API Client Setup

### `frontend/lib/api.ts`

```typescript
import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// API functions
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  
  getMe: () => api.get('/auth/me'),
}

export const dashboardApi = {
  getMetrics: (groups?: string[]) =>
    api.get('/dashboard/metrics', { params: { groups: groups?.join(',') } }),
  
  getAlertsSummary: (groups?: string[]) =>
    api.get('/dashboard/alerts-summary', { params: { groups: groups?.join(',') } }),
}

export const inventoryApi = {
  getProducts: (params: { page?: number; perPage?: number; groups?: string[]; search?: string }) =>
    api.get('/inventory/products', { 
      params: { 
        page: params.page,
        per_page: params.perPage,
        groups: params.groups?.join(','),
        search: params.search
      } 
    }),
  
  getGroups: () => api.get('/inventory/groups'),
}

export const forecastingApi = {
  getPredictions: (groups?: string[]) =>
    api.get('/forecasting/predictions', { params: { groups: groups?.join(',') } }),
}

export const alertsApi = {
  getStockoutAlerts: (groups?: string[], severity?: string) =>
    api.get('/alerts/stockout', { params: { groups: groups?.join(','), severity } }),
  
  getHealthMetrics: (groups?: string[]) =>
    api.get('/alerts/health', { params: { groups: groups?.join(',') } }),
}
```

---

## 🧪 Step 7: Test Running

```powershell
# Terminal 1: Jalankan Flask backend
cd backend
python run.py

# Terminal 2: Jalankan Next.js frontend
cd frontend
npm run dev
```

**Buka browser:** `http://localhost:3000`

---

## 📱 Environment Variables

### `frontend/.env.local`

```env
# API URL
NEXT_PUBLIC_API_URL=http://localhost:5000/api
```

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[08_UI_COMPONENTS.md](./08_UI_COMPONENTS.md)** untuk pembuatan React components.
