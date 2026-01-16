import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
    id: number
    username: string
    email?: string
    role: 'admin' | 'user'
}

interface AuthState {
    user: User | null
    token: string | null
    isAuthenticated: boolean
    setUser: (user: User | null) => void
    setToken: (token: string | null) => void
    logout: () => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            isAuthenticated: false,

            setUser: (user) => set({
                user,
                isAuthenticated: !!user
            }),

            setToken: (token) => set({ token }),

            logout: () => set({
                user: null,
                token: null,
                isAuthenticated: false
            }),
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                user: state.user,
                token: state.token,
                isAuthenticated: state.isAuthenticated
            }),
        }
    )
)

// Dashboard filters store
interface DashboardFiltersState {
    selectedGroups: string[]
    // ABC Filter
    selectedABC: string[]
    dateRange: { start: Date | null; end: Date | null }
    setSelectedGroups: (groups: string[]) => void
    setSelectedABC: (abc: string[]) => void
    setDateRange: (range: { start: Date | null; end: Date | null }) => void
    resetFilters: () => void
}

export const useDashboardFiltersStore = create<DashboardFiltersState>((set) => ({
    selectedGroups: [],
    selectedABC: [],
    dateRange: { start: null, end: null },

    setSelectedGroups: (groups) => set({ selectedGroups: groups }),
    setSelectedABC: (abc) => set({ selectedABC: abc }),
    setDateRange: (range) => set({ dateRange: range }),
    resetFilters: () => set({
        selectedGroups: [],
        selectedABC: [],
        dateRange: { start: null, end: null }
    }),
}))

// UI State store
interface UIState {
    sidebarCollapsed: boolean
    toggleSidebar: () => void
    setSidebarCollapsed: (collapsed: boolean) => void
}

export const useUIStore = create<UIState>((set) => ({
    sidebarCollapsed: false,
    toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
    setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
}))
