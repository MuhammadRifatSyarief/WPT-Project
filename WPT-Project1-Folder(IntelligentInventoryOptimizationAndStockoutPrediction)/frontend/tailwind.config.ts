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
                // Background Layers - Synced with globals.css (Fintech V2)
                bg: {
                    deepest: '#0a0f1c', // Darkest Blue
                    deep: '#0f172a',    // Slate 900
                    card: '#1e293b',    // Slate 800 (Elevated)
                    elevated: '#1e293b', // Alias for card
                    surface: '#273548',  // Lighter Slate
                    hover: '#334155',
                },
                // Accents
                primary: {
                    DEFAULT: '#6366f1', // Indigo
                    foreground: '#ffffff',
                    glow: 'rgba(99, 102, 241, 0.5)',
                },
                secondary: {
                    DEFAULT: '#8b5cf6', // Violet
                },
                // Status Colors
                success: {
                    DEFAULT: '#10b981',
                    glow: 'rgba(16, 185, 129, 0.4)',
                },
                warning: {
                    DEFAULT: '#f59e0b',
                    glow: 'rgba(245, 158, 11, 0.4)',
                },
                error: {
                    DEFAULT: '#ef4444',
                    glow: 'rgba(239, 68, 68, 0.4)',
                },
                info: {
                    DEFAULT: '#3b82f6',
                    glow: 'rgba(59, 130, 246, 0.4)',
                },
                // Text
                text: {
                    primary: '#f8fafc',   // Slate 50
                    secondary: '#cbd5e1', // Slate 300
                    muted: '#94a3b8',     // Slate 400
                    dim: '#64748b',       // Slate 500
                }
            },
            backgroundImage: {
                'gradient-primary': 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)',
                'gradient-card': 'linear-gradient(145deg, #1a1a28 0%, #14141f 100%)',
                'gradient-danger': 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                'gradient-success': 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            },
            boxShadow: {
                'neu-raised': '8px 8px 16px rgba(0, 0, 0, 0.5), -4px -4px 12px rgba(255, 255, 255, 0.03)',
                'neu-inset': 'inset 6px 6px 12px rgba(0, 0, 0, 0.5), inset -3px -3px 8px rgba(255, 255, 255, 0.03)',
                'neu-floating': '12px 12px 24px rgba(0, 0, 0, 0.5), -6px -6px 16px rgba(255, 255, 255, 0.03)',
            },
        },
    },
    plugins: [],
}

export default config
