import axios from 'axios'

// URL Backend Flask
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api'

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
    // Kita akan simpan token di localStorage
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
    }
    return config
})

// Handle 401 responses (Token expired)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            if (typeof window !== 'undefined') {
                localStorage.removeItem('access_token')
                // Optional: Redirect to login
                if (!window.location.pathname.includes('/login')) {
                    window.location.href = '/login'
                }
            }
        }
        return Promise.reject(error)
    }
)

export const authApi = {
    login: (username: string, password: string) =>
        api.post('/auth/login', { username, password }),

    getMe: () => api.get('/auth/me'),

    // Forecasting endpoints
    getForecastingData: (params?: { search?: string; category?: string; abc_class?: string }) =>
        api.get('/forecasting/data', { params }),
}

// Default export for convenience
export default api

