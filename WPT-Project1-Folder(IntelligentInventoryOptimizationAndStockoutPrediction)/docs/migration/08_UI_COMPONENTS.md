# 🧩 UI Components Migration

> **Tujuan**: Convert Streamlit components ke React components
> 
> **File Source**: `modules/ui_components.py` (752 lines)

---

## 📊 Component Mapping

| Streamlit Function | React Component | Props |
|--------------------|-----------------|-------|
| `render_metric_card()` | `<MetricCard />` | label, value, delta, insight |
| `render_alert_box()` | `<AlertBox />` | type, title, count, desc |
| `render_filter_row()` | `<FilterRow />` | columns config |
| `render_data_table()` | `<DataTable />` | data, columns, searchable |
| `render_sidebar_header()` | `<SidebarHeader />` | title, subtitle |
| `render_quick_stat_box()` | `<QuickStat />` | label, value, type |
| `render_page_header()` | `<PageHeader />` | title, desc, icon |

---

## 🏗️ Components Structure

```
frontend/components/
├── ui/
│   ├── MetricCard.tsx
│   ├── AlertBox.tsx
│   ├── Button.tsx
│   ├── Input.tsx
│   └── Badge.tsx
├── layout/
│   ├── Sidebar.tsx
│   ├── PageHeader.tsx
│   └── MainLayout.tsx
├── data/
│   ├── DataTable.tsx
│   ├── FilterRow.tsx
│   └── Pagination.tsx
└── charts/
    ├── PieChart.tsx
    ├── BarChart.tsx
    └── LineChart.tsx
```

---

## 📄 MetricCard Component

### Streamlit Original (`ui_components.py` line 18-64)
```python
def render_metric_card(label, value, delta='', delta_positive=True, insight='', popover_info=''):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-delta {'positive' if delta_positive else 'negative'}">{delta}</div>
    </div>
    """, unsafe_allow_html=True)
```

### React Version

```tsx
// frontend/components/ui/MetricCard.tsx

import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: string | number
  delta?: string
  deltaPositive?: boolean
  insight?: string
  icon?: LucideIcon
  className?: string
}

export function MetricCard({
  label,
  value,
  delta,
  deltaPositive = true,
  insight,
  icon: Icon,
  className,
}: MetricCardProps) {
  return (
    <div className={cn('metric-card', className)}>
      <div className="metric-label">
        {Icon && <Icon className="w-4 h-4" />}
        {label}
      </div>
      <div className="metric-value">{value}</div>
      {delta && (
        <div className={cn('metric-delta', deltaPositive ? 'positive' : 'negative')}>
          {deltaPositive ? '↑' : '↓'} {delta}
        </div>
      )}
      {insight && (
        <div className="text-xs text-gray-500 mt-2 italic">
          {insight}
        </div>
      )}
    </div>
  )
}

// Penggunaan:
// <MetricCard 
//   label="Active Alerts" 
//   value={25} 
//   delta="5 dari kemarin" 
//   deltaPositive={false}
//   icon={AlertTriangle}
// />
```

---

## 📄 AlertBox Component

### Streamlit Original (`ui_components.py` line 67-106)
```python
def render_alert_box(alert_type, title, count, description=''):
    color_map = {'critical': '#ef4444', 'warning': '#f59e0b', ...}
    st.markdown(f"""
    <div class="alert-{alert_type}">
        <div>{title}: {count}</div>
        <div>{description}</div>
    </div>
    """, unsafe_allow_html=True)
```

### React Version

```tsx
// frontend/components/ui/AlertBox.tsx

import { cn } from '@/lib/utils'
import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react'

type AlertType = 'critical' | 'warning' | 'info' | 'success'

interface AlertBoxProps {
  type: AlertType
  title: string
  count?: number
  description?: string
  className?: string
}

const alertConfig = {
  critical: {
    icon: AlertTriangle,
    class: 'alert-critical',
    color: 'text-red-400',
  },
  warning: {
    icon: AlertCircle,
    class: 'alert-warning',
    color: 'text-amber-400',
  },
  info: {
    icon: Info,
    class: 'alert-info',
    color: 'text-blue-400',
  },
  success: {
    icon: CheckCircle,
    class: 'alert-success',
    color: 'text-green-400',
  },
}

export function AlertBox({
  type,
  title,
  count,
  description,
  className,
}: AlertBoxProps) {
  const config = alertConfig[type]
  const Icon = config.icon

  return (
    <div className={cn('alert-box', config.class, className)}>
      <div className="flex items-center gap-3">
        <Icon className={cn('w-6 h-6', config.color)} />
        <div>
          <div className="font-semibold text-white flex items-center gap-2">
            {title}
            {count !== undefined && (
              <span className="text-2xl font-bold">{count}</span>
            )}
          </div>
          {description && (
            <div className="text-sm text-gray-400 mt-1">{description}</div>
          )}
        </div>
      </div>
    </div>
  )
}
```

---

## 📄 DataTable Component

### Streamlit Original (`ui_components.py` line 198-241)
```python
def render_data_table(df, title='', max_rows=100, searchable=True):
    if searchable:
        search = st.text_input("🔍 Search")
        df = df[df.apply(lambda row: search in str(row), axis=1)]
    st.dataframe(df.head(max_rows))
```

### React Version

```tsx
// frontend/components/data/DataTable.tsx

'use client'

import { useState, useMemo } from 'react'
import { Search, ChevronUp, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Column {
  key: string
  label: string
  sortable?: boolean
  render?: (value: any, row: any) => React.ReactNode
}

interface DataTableProps {
  data: Record<string, any>[]
  columns: Column[]
  title?: string
  searchable?: boolean
  pageSize?: number
  className?: string
}

export function DataTable({
  data,
  columns,
  title,
  searchable = true,
  pageSize = 50,
  className,
}: DataTableProps) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [page, setPage] = useState(1)

  // Filter data
  const filteredData = useMemo(() => {
    if (!search) return data
    
    return data.filter((row) =>
      columns.some((col) =>
        String(row[col.key]).toLowerCase().includes(search.toLowerCase())
      )
    )
  }, [data, search, columns])

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData
    
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortKey]
      const bVal = b[sortKey]
      
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1
      return 0
    })
  }, [filteredData, sortKey, sortOrder])

  // Paginate
  const paginatedData = useMemo(() => {
    const start = (page - 1) * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, page, pageSize])

  const totalPages = Math.ceil(sortedData.length / pageSize)

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortOrder('asc')
    }
  }

  return (
    <div className={cn('data-table overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        {title && <h3 className="text-lg font-semibold text-white">{title}</h3>}
        
        {searchable && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="pl-10 pr-4 py-2 bg-dark-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
            />
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  onClick={() => col.sortable && handleSort(col.key)}
                  className={cn(
                    'bg-primary-500/20 text-white p-4 text-left font-semibold border-b-2 border-gray-700',
                    col.sortable && 'cursor-pointer hover:bg-primary-500/30'
                  )}
                >
                  <div className="flex items-center gap-2">
                    {col.label}
                    {col.sortable && sortKey === col.key && (
                      sortOrder === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, idx) => (
              <tr key={idx} className="hover:bg-primary-500/10">
                {columns.map((col) => (
                  <td key={col.key} className="p-4 border-b border-gray-700 text-gray-200">
                    {col.render ? col.render(row[col.key], row) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between p-4 border-t border-gray-700">
          <span className="text-sm text-gray-400">
            Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, sortedData.length)} of {sortedData.length}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn btn-secondary disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn btn-secondary disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

## 📄 Sidebar Component

```tsx
// frontend/components/layout/Sidebar.tsx

'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  Home,
  TrendingUp,
  Activity,
  AlertTriangle,
  RefreshCw,
  Archive,
  Users,
  ShoppingCart,
  Settings,
  LogOut,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard Overview', href: '/dashboard', icon: Home },
  { name: 'Demand Forecasting', href: '/forecasting', icon: TrendingUp },
  { name: 'Inventory Health', href: '/health', icon: Activity },
  { name: 'Stockout Alerts', href: '/alerts', icon: AlertTriangle },
  { name: 'Reorder Optimization', href: '/reorder', icon: RefreshCw },
  { name: 'Slow-Moving Analysis', href: '/slow-moving', icon: Archive },
  { name: 'RFM Analysis', href: '/rfm', icon: Users },
  { name: 'Market Basket Analysis', href: '/mba', icon: ShoppingCart },
  { name: 'Settings', href: '/settings', icon: Settings },
]

interface SidebarProps {
  quickStats?: {
    activeAlerts: number
    totalProducts: number
    lastUpdated: string
  }
  onLogout?: () => void
}

export function Sidebar({ quickStats, onLogout }: SidebarProps) {
  const pathname = usePathname()

  return (
    <aside className="sidebar w-64 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-800">
        <div className="text-xl font-bold text-white">📦 Inventory Intelligence</div>
        <div className="text-sm text-gray-400">PT Wahana Piranti Teknologi</div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                isActive
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* Quick Stats */}
      {quickStats && (
        <div className="p-4 border-t border-gray-800">
          <h3 className="text-sm font-semibold text-gray-400 uppercase mb-3">Quick Stats</h3>
          <div className="space-y-3">
            <div className="bg-red-900/30 border-l-4 border-red-500 p-3 rounded">
              <div className="text-xs text-gray-400">Active Alerts</div>
              <div className="text-xl font-bold text-red-400">{quickStats.activeAlerts}</div>
            </div>
            <div className="bg-primary-500/10 border-l-4 border-primary-500 p-3 rounded">
              <div className="text-xs text-gray-400">Products Monitored</div>
              <div className="text-xl font-bold text-white">{quickStats.totalProducts.toLocaleString()}</div>
            </div>
            <div className="bg-gray-800 border-l-4 border-gray-600 p-3 rounded">
              <div className="text-xs text-gray-400">Last Updated</div>
              <div className="text-lg font-semibold text-gray-300">{quickStats.lastUpdated}</div>
            </div>
          </div>
        </div>
      )}

      {/* Logout */}
      <div className="p-4 border-t border-gray-800">
        <button
          onClick={onLogout}
          className="flex items-center gap-3 w-full px-4 py-3 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          Logout
        </button>
      </div>
    </aside>
  )
}
```

---

## 📄 Utility Function

```typescript
// frontend/lib/utils.ts

import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

---

## ⏭️ Langkah Selanjutnya

Lanjut ke **[09_STATE_MANAGEMENT.md](./09_STATE_MANAGEMENT.md)** untuk migrasi state management.
