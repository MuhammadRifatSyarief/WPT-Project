import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface User {
    id: number
    username: string
    role: string
    email?: string
}

interface AuthState {
    isAuthenticated: boolean
    user: User | null
    token: string | null

    login: (user: User, token: string) => void
    logout: () => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            isAuthenticated: false,
            user: null,
            token: null,

            login: (user, token) => {
                // Simpan token ke localStorage untuk axios interceptor
                localStorage.setItem('access_token', token)
                set({
                    isAuthenticated: true,
                    user,
                    token
                })
            },

            logout: () => {
                localStorage.removeItem('access_token')
                set({
                    isAuthenticated: false,
                    user: null,
                    token: null
                })
            },
        }),
        {
            name: 'auth-storage',
            storage: createJSONStorage(() => localStorage),
        }
    )
)
