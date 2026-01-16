'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/store';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';

interface NavItem {
    icon: string;
    label: string;
    href: string;
    description?: string;
}

const navItems: NavItem[] = [
    { icon: '🏠', label: 'Dashboard', href: '/dashboard', description: 'Overview & Analytics' },
    { icon: '📈', label: 'Forecasting', href: '/forecasting', description: 'Demand Prediction' },
    { icon: '📦', label: 'Inventory', href: '/inventory', description: 'Stock Management' },
    { icon: '📊', label: 'Health', href: '/health', description: 'Inventory Health' },
    { icon: '⚠️', label: 'Stockout Alerts', href: '/alerts', description: 'Risk Monitoring' },
    { icon: '🔄', label: 'Reorder', href: '/reorder', description: 'Optimization' },
    { icon: '📋', label: 'Slow-Moving', href: '/slow-moving', description: 'Dead Stock Analysis' },
    { icon: '🛒', label: 'MBA', href: '/mba', description: 'Market Basket' },
    { icon: '👥', label: 'RFM', href: '/rfm', description: 'Customer Segments' },
    { icon: '⚙️', label: 'Settings', href: '/settings', description: 'Configuration' },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuthStore();
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [hoveredItem, setHoveredItem] = useState<string | null>(null);
    const [time, setTime] = useState<string>('');

    // Clock Effect
    useEffect(() => {
        const timer = setInterval(() => {
            setTime(new Date().toLocaleTimeString('en-US', { hour12: false }));
        }, 1000);
        return () => clearInterval(timer);
    }, []);

    // Quick Stats Query
    const { data: metrics } = useQuery({
        queryKey: ['sidebar-stats'],
        queryFn: async () => (await api.get('/dashboard/metrics')).data,
        refetchInterval: 30000, // Refresh every 30s
        enabled: !isCollapsed // Only fetch when sidebar is open to save resources
    });

    const activeAlerts = (metrics?.stockout_risk?.critical || 0) + (metrics?.stockout_risk?.high || 0);
    const totalProducts = metrics?.total_products || 0;

    const handleLogout = () => {
        logout();
        localStorage.removeItem('access_token');
        router.push('/login');
    };

    return (
        <div
            className={`
                sidebar h-screen sticky top-0 flex flex-col transition-all duration-500 ease-out z-50
                ${isCollapsed ? 'w-20' : 'w-72'}
            `}
            style={{
                background: 'linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(30,41,59,0.98) 100%)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                borderRight: '1px solid rgba(255,255,255,0.08)',
                boxShadow: '4px 0 24px rgba(0,0,0,0.3)',
            }}
        >
            {/* Header with Glow Effect */}
            <div className="p-5 border-b border-[rgba(255,255,255,0.06)] relative overflow-hidden">
                {/* Ambient glow */}
                <div className="absolute -top-20 -left-20 w-40 h-40 bg-[var(--accent-primary)] opacity-10 blur-3xl rounded-full animate-pulse"></div>

                <div className="flex items-center justify-between relative z-10">
                    {!isCollapsed && (
                        <div className="flex items-center gap-3 group">
                            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center shadow-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-[0_0_25px_rgba(99,102,241,0.5)]">
                                <span className="text-white font-bold text-lg">W</span>
                            </div>
                            <div>
                                <h1 className="text-[var(--text-primary)] font-bold text-sm tracking-wide">WPT Inventory</h1>
                                <p className="text-[var(--accent-primary)] text-xs font-medium">Intelligence Hub</p>
                            </div>
                        </div>
                    )}

                    <button
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        className="p-2.5 rounded-xl bg-[rgba(255,255,255,0.05)] hover:bg-[rgba(255,255,255,0.1)] text-[var(--text-muted)] transition-all duration-300 hover:scale-110 hover:text-[var(--accent-primary)]"
                    >
                        <span className={`block transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`}>
                            ←
                        </span>
                    </button>
                </div>
            </div>

            {/* Navigation with Glass Effects */}
            <nav className="flex-1 p-3 overflow-y-auto custom-scrollbar">
                <div className="space-y-1.5">
                    {navItems.map((item, index) => {
                        const isActive = pathname === item.href;
                        const isHovered = hoveredItem === item.href;

                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                onMouseEnter={() => setHoveredItem(item.href)}
                                onMouseLeave={() => setHoveredItem(null)}
                                className={`
                                    relative flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300
                                    ${isCollapsed ? 'justify-center px-3' : ''}
                                    ${isActive
                                        ? 'bg-gradient-to-r from-[var(--accent-primary)]/20 to-transparent text-[var(--text-primary)] shadow-lg'
                                        : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[rgba(255,255,255,0.05)]'
                                    }
                                `}
                                style={{
                                    animationDelay: `${index * 50}ms`,
                                    transform: isHovered && !isActive ? 'translateX(4px)' : 'translateX(0)',
                                }}
                            >
                                {/* Active indicator */}
                                {isActive && (
                                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-[var(--accent-primary)] to-[var(--accent-secondary)] rounded-r-full shadow-[0_0_10px_var(--accent-primary)]"></div>
                                )}

                                {/* Icon with glow on active */}
                                <span className={`text-xl transition-all duration-300 ${isActive ? 'scale-110' : ''} ${isHovered ? 'animate-bounce-subtle' : ''}`}>
                                    {item.icon}
                                </span>

                                {!isCollapsed && (
                                    <div className="flex-1 min-w-0">
                                        <span className={`text-sm font-medium ${isActive ? 'text-[var(--text-primary)]' : ''}`}>
                                            {item.label}
                                        </span>
                                        {item.description && (
                                            <p className={`text-[10px] transition-all duration-200 ${isActive || isHovered ? 'text-[var(--text-muted)] opacity-100' : 'text-[var(--text-dim)] opacity-0'}`}>
                                                {item.description}
                                            </p>
                                        )}
                                    </div>
                                )}

                                {/* Hover glow effect */}
                                {(isActive || isHovered) && !isCollapsed && (
                                    <div className="absolute right-3 w-2 h-2 rounded-full bg-[var(--accent-primary)] shadow-[0_0_8px_var(--accent-primary)] animate-pulse"></div>
                                )}
                            </Link>
                        );
                    })}
                </div>
            </nav>

            {/* Quick Stats Section */}
            {!isCollapsed && (
                <div className="px-4 py-2">
                    <div className="rounded-xl p-4 border border-[rgba(255,255,255,0.08)] bg-[rgba(0,0,0,0.2)] backdrop-blur-md relative overflow-hidden group">
                        {/* Shimmer overlay */}
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[rgba(255,255,255,0.03)] to-transparent translate-x-[-200%] group-hover:animate-shimmer"></div>

                        <h3 className="text-[10px] uppercase tracking-widest text-[var(--text-dim)] font-bold mb-3 border-b border-[rgba(255,255,255,0.1)] pb-1">Quick Stats</h3>

                        <div className="space-y-3 relative z-10">
                            <div className="flex items-center justify-between group/item">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs animate-pulse">🔴</span>
                                    <span className="text-xs text-[var(--text-secondary)]">Active Alerts</span>
                                </div>
                                <span className="text-xs font-bold text-[#fca5a5]">{activeAlerts}</span>
                            </div>

                            <div className="flex items-center justify-between group/item">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs">📦</span>
                                    <span className="text-xs text-[var(--text-secondary)]">Products</span>
                                </div>
                                <span className="text-xs font-bold text-[var(--accent-secondary)]">{totalProducts.toLocaleString()}</span>
                            </div>

                            <div className="flex items-center justify-between group/item pt-1 border-t border-[rgba(255,255,255,0.05)]">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs">⏰</span>
                                    <span className="text-xs text-[var(--text-secondary)]">Time</span>
                                </div>
                                <span className="text-xs font-mono text-[var(--info)]">{time}</span>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* User Section with Glass Card */}
            <div className="p-4 border-t border-[rgba(255,255,255,0.06)]">
                {!isCollapsed ? (
                    <div className="space-y-3">
                        {/* User Info Card */}
                        <div
                            className="flex items-center gap-3 p-3 rounded-xl transition-all duration-300 hover:scale-[1.02] cursor-pointer group"
                            style={{
                                background: 'linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(139,92,246,0.05) 100%)',
                                border: '1px solid rgba(99,102,241,0.2)',
                            }}
                        >
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center shadow-lg group-hover:shadow-[0_0_20px_rgba(99,102,241,0.4)] transition-all duration-300">
                                <span className="text-white font-semibold">
                                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                                </span>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-[var(--text-primary)] text-sm font-medium truncate">
                                    {user?.username || 'User'}
                                </p>
                                <p className={`text-xs font-medium ${user?.role === 'admin' ? 'text-[#fca5a5]' : 'text-[#93c5fd]'}`}>
                                    {user?.role === 'admin' ? '👑 Admin' : '👤 User'}
                                </p>
                            </div>
                            <span className="text-[var(--text-dim)] text-xs group-hover:text-[var(--accent-primary)] transition-colors">→</span>
                        </div>

                        {/* Logout Button */}
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center justify-center gap-2 p-3 rounded-xl
                                bg-gradient-to-r from-[rgba(239,68,68,0.1)] to-[rgba(239,68,68,0.05)]
                                border border-[rgba(239,68,68,0.2)]
                                text-[#fca5a5] text-sm font-medium
                                hover:from-[rgba(239,68,68,0.2)] hover:to-[rgba(239,68,68,0.1)]
                                hover:border-[rgba(239,68,68,0.4)] hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]
                                transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
                        >
                            <span>🚪</span>
                            <span>Sign Out</span>
                        </button>
                    </div>
                ) : (
                    <div className="space-y-2">
                        <div className="w-10 h-10 mx-auto rounded-xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center">
                            <span className="text-white font-semibold text-sm">
                                {user?.username?.charAt(0).toUpperCase() || 'U'}
                            </span>
                        </div>
                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center justify-center p-2.5 rounded-xl
                                bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)]
                                text-[#fca5a5] hover:bg-[rgba(239,68,68,0.2)]
                                transition-all duration-300"
                            title="Sign Out"
                        >
                            <span>🚪</span>
                        </button>
                    </div>
                )}
            </div>

            {/* Version with Shimmer */}
            {!isCollapsed && (
                <div className="p-3 text-center border-t border-[rgba(255,255,255,0.06)] relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[rgba(255,255,255,0.03)] to-transparent animate-shimmer"></div>
                    <p className="text-[var(--text-dim)] text-xs relative z-10">
                        v4.3 • <span className="text-[var(--accent-primary)]">Flask</span> + <span className="text-[#10b981]">Next.js</span>
                    </p>
                </div>
            )}
        </div>
    );
}
