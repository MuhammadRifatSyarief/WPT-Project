'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { useDashboardFiltersStore } from '@/lib/store';
import FilterGroups from '@/components/dashboard/FilterGroups';
import FilterABC from '@/components/dashboard/FilterABC';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, Cell, PieChart, Pie, Legend, LabelList, Sector, Area
} from 'recharts';
import { motion } from 'framer-motion';
import { GlowingCard } from '@/components/ui/GlowingCard';
import { BackgroundBeams } from '@/components/ui/BackgroundBeams';

// --- TYPES ---
interface DashboardMetrics {
    service_level: number;
    turnover_ratio: number;
    stockout_risk: { critical: number; high: number; medium: number; total: number };
    avg_stock_age: number;
    total_products: number;
    total_stock_value: number;
    slow_moving_count: number;
    abc_breakdown: { [key: string]: number };
}

interface AlertProduct {
    product_code: string;
    product_name: string;
    current_stock: number;
    daily_demand: number;
    days_coverage: number;
    risk_level: string;
    abc_class: string;
    category: string;
}

interface TopProduct {
    product_code: string;
    product_name: string;
    daily_demand: number;
    current_stock: number;
}

interface ABCPerformance {
    abc_class: string;
    product_count: number;
    total_stock: number;
    stock_value: number;
    avg_daily_demand: number;
    turnover_ratio: number;
}

interface CategorySummary {
    category: string;
    count: number;
    percentage: number;
}

// --- CUSTOM ACTIVE SHAPE FOR PIE CHART ---
const renderActiveShape = (props: any) => {
    const { cx, cy, midAngle, innerRadius, outerRadius, startAngle, endAngle, fill, payload, percent, value } = props;
    const sin = Math.sin(-RADIAN * midAngle);
    const cos = Math.cos(-RADIAN * midAngle);
    const sx = cx + (outerRadius + 10) * cos;
    const sy = cy + (outerRadius + 10) * sin;
    const mx = cx + (outerRadius + 30) * cos;
    const my = cy + (outerRadius + 30) * sin;
    const ex = mx + (cos >= 0 ? 1 : -1) * 22;
    const ey = my;
    const textAnchor = cos >= 0 ? 'start' : 'end';

    return (
        <g>
            {/* Glow Effect Filter Definition usually needs to be in <defs> but we can simulate glow with multiple layers or just a larger opaque sector behind */}
            <defs>
                <filter id="glow-pie" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="6" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
            </defs>

            {/* Removed center percentage to avoid overlap with Total Products count */}

            {/* Expanded Sector with Glow */}
            <Sector
                cx={cx}
                cy={cy}
                innerRadius={innerRadius}
                outerRadius={outerRadius + 8}
                startAngle={startAngle}
                endAngle={endAngle}
                fill={fill}
                filter="url(#glow-pie)"
                stroke="#fff"
                strokeWidth={2}
            />

            {/* Connecting Lines & Labels */}
            <path d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`} stroke={fill} fill="none" strokeWidth={2} />
            <circle cx={ex} cy={ey} r={2} fill={fill} stroke="none" />
            <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} textAnchor={textAnchor} fill="var(--text-primary)" fontSize={12} fontWeight="bold">{payload.name}</text>
            <text x={ex + (cos >= 0 ? 1 : -1) * 12} y={ey} dy={14} textAnchor={textAnchor} fill="var(--text-muted)" fontSize={10}>
                {`${value} Products (${(percent * 100).toFixed(0)}%)`}
            </text>
        </g>
    );
};

const RADIAN = Math.PI / 180;

// --- METRIC TOOLTIP DATA ---
const METRIC_TOOLTIPS = {
    serviceLevel: {
        title: 'Service Level Calculation',
        formula: '(Products with Stock > 0) / Total Products × 100%',
        description: 'Percentage of products currently in stock and available for fulfillment. Target is >95%.'
    },
    turnover: {
        title: 'Turnover Ratio (30d)',
        formula: 'Σ(Turnover × Stock Value) / Σ(Stock Value)',
        description: 'Weighted average inventory turnover over 30 days. Higher = faster moving inventory.'
    },
    stockoutRisk: {
        title: 'Stockout Risk Index',
        formula: 'Count of products where Days Until Stockout < 30',
        description: 'Number of products at risk of stockout. Critical <7d, High 7-14d, Medium 14-30d.'
    },
    stockAge: {
        title: 'Average Stock Age',
        formula: 'Median(Days in Inventory)',
        description: 'Median number of days products have been in inventory. Target is <60 days.'
    }
};

// --- COLORS ---
const COLORS = {
    primary: '#6366f1',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
};

const ABC_COLORS: Record<string, string> = { 'A': '#10b981', 'B': '#3b82f6', 'C': '#f59e0b' };
const HEALTH_COLORS: Record<string, string> = { Healthy: '#10b981', Stable: '#6366f1', Warning: '#f59e0b', Critical: '#ef4444' };

// Mock Performance Data
const performanceData = [
    { month: 'Aug', serviceLevel: 89.5, turnover: 3.2 },
    { month: 'Sep', serviceLevel: 91.2, turnover: 3.5 },
    { month: 'Oct', serviceLevel: 92.8, turnover: 3.3 },
    { month: 'Nov', serviceLevel: 91.5, turnover: 3.6 },
    { month: 'Dec', serviceLevel: 93.4, turnover: 3.8 },
    { month: 'Jan', serviceLevel: 94.1, turnover: 3.9 },
];

// --- TOOLTIP COMPONENT ---
// --- METRIC CARD COMPONENT (Replaces Tooltip) ---
function MetricCard({
    tooltip,
    value,
    prefix = '',
    suffix = '',
    colorClass = 'text-[var(--text-primary)]',
    delta,
    deltaClass,
    deltaText
}: {
    tooltip: typeof METRIC_TOOLTIPS.serviceLevel;
    value: string | number;
    prefix?: string;
    suffix?: string;
    colorClass?: string;
    delta?: React.ReactNode;
    deltaClass?: string;
    deltaText?: string;
}) {
    return (
        <GlowingCard className="h-[150px] !p-0" glowColor={colorClass.includes('f59e0b') ? '#f59e0b' : colorClass.includes('ef4444') ? '#ef4444' : '#6366f1'}>
            {/* FRONT FACE (Value) */}
            <div className="absolute inset-0 p-5 flex flex-col justify-between transition-all duration-300 group-hover:opacity-0 group-hover:-translate-y-2 z-20">
                <div>
                    <div className="text-sm font-medium text-[var(--text-secondary)] mb-1">{tooltip.title.split(' (')[0]}</div>
                    <div className="text-[10px] text-[var(--accent-primary)] opacity-0 group-hover/glow:opacity-100 transition-opacity animate-pulse">Hover for info</div>
                    <div className={`text-3xl font-bold ${colorClass} tracking-tight`}>
                        {prefix}{value}{suffix}
                    </div>
                </div>

                {(delta || deltaText) && (
                    <div className={`metric-delta ${deltaClass} flex items-center gap-1 text-xs font-semibold`}>
                        {delta} {deltaText}
                    </div>
                )}
            </div>

            {/* BACK FACE (Details - Overlay on Hover) */}
            <div className="absolute inset-0 z-30 p-5 flex flex-col justify-center opacity-0 translate-y-4 group-hover/glow:opacity-100 group-hover/glow:translate-y-0 transition-all duration-300 bg-[var(--bg-elevated)]/95 backdrop-blur-md">
                <div className="text-xs font-bold text-[var(--text-primary)] mb-2 border-b border-[var(--border-subtle)] pb-1">{tooltip.title}</div>

                <p className="text-[10px] leading-relaxed text-[var(--text-secondary)] mb-2">
                    {tooltip.description}
                </p>

                <div className="text-[9px] font-mono bg-[var(--bg-base)] p-1.5 rounded text-[var(--success)] opacity-90 break-all border border-[var(--border-subtle)]">
                    {tooltip.formula}
                </div>
            </div>
        </GlowingCard>
    );
}

// --- RISK FILTER TYPE ---
type RiskFilter = 'all' | 'Critical' | 'High' | 'Slow-Moving';

// --- COMPONENT ---
export default function DashboardPage() {
    const [showAllAlerts, setShowAllAlerts] = useState(false);
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' }>({ key: 'days_coverage', direction: 'asc' });
    const [riskFilter, setRiskFilter] = useState<RiskFilter>('all'); // NEW: Risk filter state

    const [activeIndex, setActiveIndex] = useState(0); // For Pie Chart interactions

    // Filter State
    const { selectedGroups, selectedABC } = useDashboardFiltersStore();
    const groupsParam = selectedGroups.length > 0 ? selectedGroups.join(',') : undefined;

    // --- QUERIES ---
    const { data: metrics, isLoading } = useQuery<DashboardMetrics>({
        queryKey: ['dashboard-metrics', groupsParam],
        queryFn: async () => (await api.get('/dashboard/metrics', { params: { groups: groupsParam } })).data,
    });

    // Fetch ALL alerts (no limit)
    const { data: topAlerts } = useQuery<AlertProduct[]>({
        queryKey: ['top-alerts', groupsParam],
        queryFn: async () => (await api.get('/dashboard/top-alerts', { params: { limit: 500, groups: groupsParam } })).data,
    });

    const { data: topProducts } = useQuery<TopProduct[]>({
        queryKey: ['top-products', groupsParam],
        queryFn: async () => (await api.get('/dashboard/top-products', { params: { limit: 5, groups: groupsParam } })).data,
    });

    const { data: healthData } = useQuery<CategorySummary[]>({
        queryKey: ['category-summary', groupsParam],
        queryFn: async () => (await api.get('/dashboard/category-summary', { params: { groups: groupsParam } })).data,
    });

    const { data: abcPerformance } = useQuery<ABCPerformance[]>({
        queryKey: ['abc-performance', groupsParam],
        queryFn: async () => (await api.get('/dashboard/abc-performance', { params: { groups: groupsParam } })).data,
    });

    // --- DERIVED DATA ---
    const stockoutRisk = metrics?.stockout_risk || { critical: 0, high: 0, medium: 0, total: 0 };
    const serviceLevel = metrics?.service_level || 0;
    const turnover = metrics?.turnover_ratio || 0;
    const stockAge = metrics?.avg_stock_age || 0;
    const slowMovingCount = metrics?.slow_moving_count || 0;

    // Filter & Sort Alerts with Risk Filter
    const filteredAlerts = useMemo(() => {
        let data = (topAlerts || []);

        // Apply ABC filter
        if (selectedABC.length > 0) {
            data = data.filter(alert => selectedABC.includes(alert.abc_class));
        }

        // Apply Risk filter (from clicking alert boxes)
        if (riskFilter !== 'all') {
            if (riskFilter === 'Slow-Moving') {
                // Slow moving doesn't have a risk_level, filter by low turnover indicator (days_coverage might be high but turnover low)
                // Since backend returns risk_level, let's check if it contains 'Slow' or filter differently
                data = data.filter(alert =>
                    alert.risk_level.toLowerCase().includes('slow') ||
                    alert.risk_level === 'Low' ||
                    (alert.days_coverage > 30 && alert.current_stock > 0)
                );
            } else {
                data = data.filter(alert => alert.risk_level === riskFilter);
            }
        }

        // Sort
        data = [...data].sort((a, b) => {
            const aVal = a[sortConfig.key as keyof AlertProduct];
            const bVal = b[sortConfig.key as keyof AlertProduct];

            // Special handling for ABC class sorting (A=1, B=2, C=3)
            if (sortConfig.key === 'abc_class') {
                const abcOrder: Record<string, number> = { 'A': 1, 'B': 2, 'C': 3 };
                const aOrder = abcOrder[String(aVal)] || 99;
                const bOrder = abcOrder[String(bVal)] || 99;
                return sortConfig.direction === 'asc' ? aOrder - bOrder : bOrder - aOrder;
            }

            if (typeof aVal === 'number' && typeof bVal === 'number') {
                return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
            }
            return sortConfig.direction === 'asc'
                ? String(aVal).localeCompare(String(bVal))
                : String(bVal).localeCompare(String(aVal));
        });
        return data;
    }, [topAlerts, selectedABC, sortConfig, riskFilter]);

    // Show ALL filtered alerts (no limit)
    const displayAlerts = filteredAlerts;

    const handleSort = (key: string) => {
        setSortConfig(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
        }));
    };

    const onPieEnter = (_: any, index: number) => {
        setActiveIndex(index);
    };

    // Handle alert box click - filter and show table
    const handleAlertClick = (filter: RiskFilter) => {
        setRiskFilter(filter);
        setShowAllAlerts(true);
    };

    const pieData = useMemo(() => {
        return (healthData || []).map(item => ({
            name: item.category,
            value: item.count,
            percentage: item.percentage
        }));
    }, [healthData]);

    const totalProducts = metrics?.total_products || pieData.reduce((sum, d) => sum + d.value, 0);

    const abcChartData = useMemo(() => {
        return (abcPerformance || []).map(item => ({
            name: `Class ${item.abc_class}`,
            stockValue: item.stock_value / 1_000_000,
            abc_class: item.abc_class
        }));
    }, [abcPerformance]);

    // Loading State
    if (isLoading) {
        return (
            <div className="flex h-screen items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-[var(--accent-primary)] mx-auto mb-4"></div>
                    <p className="text-[var(--text-muted)] animate-pulse">Loading Intelligence Hub...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8 p-4 pb-16">

            <BackgroundBeams />

            {/* ========== HEADER ========== */}
            <motion.header
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 relative z-[50]"
            >
                <div>
                    <h1 className="text-3xl font-bold text-gradient bg-clip-text animate-text-shimmer bg-[size:200%]">Inventory Intelligence Hub</h1>
                    <p className="text-[var(--text-muted)] mt-1">Real-time overview of your inventory health</p>
                    <p className="text-[var(--text-dim)] text-xs mt-2 border-l-2 border-[var(--accent-primary)] pl-2 opacity-80">
                        💡 Hover over metric cards for details | Click alert boxes to filter table
                    </p>
                </div>
                <div className="flex items-center gap-3 relative z-[100]">
                    <FilterGroups />
                    <FilterABC />
                    <button className="neu-btn text-sm px-4 py-2 flex items-center gap-2 transition-all hover:scale-105 active:scale-95">
                        <span className="animate-spin-slow">↻</span> Refresh
                    </button>
                </div>
            </motion.header>

            {/* ========== 1. TOP METRICS WITH FLIP CARDS ========== */}
            <motion.div
                initial="hidden"
                animate="visible"
                variants={{
                    hidden: { opacity: 0 },
                    visible: {
                        opacity: 1,
                        transition: {
                            staggerChildren: 0.1
                        }
                    }
                }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
            >
                <MetricCard
                    tooltip={METRIC_TOOLTIPS.serviceLevel}
                    value={serviceLevel.toFixed(1)}
                    suffix="%"
                    colorClass="bg-clip-text text-transparent bg-gradient-to-r from-[#10b981] to-[#34d399]"
                    delta={serviceLevel > 92 ? '↑' : '↓'}
                    deltaClass={serviceLevel > 92 ? 'positive' : 'negative'}
                    deltaText="vs 95% target"
                />

                <MetricCard
                    tooltip={METRIC_TOOLTIPS.turnover}
                    value={turnover.toFixed(2)}
                    suffix="x"
                    colorClass="bg-clip-text text-transparent bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)]"
                    delta=""
                    deltaClass="positive"
                    deltaText="Weighted Avg"
                />

                <MetricCard
                    tooltip={METRIC_TOOLTIPS.stockoutRisk}
                    value={stockoutRisk.total}
                    colorClass="text-[#ef4444]"
                    delta={`${stockoutRisk.critical}`}
                    deltaClass="negative"
                    deltaText="critical items"
                />

                <MetricCard
                    tooltip={METRIC_TOOLTIPS.stockAge}
                    value={stockAge}
                    suffix="d"
                    colorClass="text-[var(--text-primary)]"
                    delta="Median"
                    deltaClass="info"
                    deltaText="Age"
                />
            </motion.div>

            {/* ========== 2. CHARTS ROW: Performance + Alerts ========== */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 fade-in" style={{ animationDelay: '0.1s' }}>
                {/* Performance Trends */}
                {/* Performance Trends */}
                {/* Performance Trends */}
                <GlowingCard className="lg:col-span-3 !p-0">
                    <div className="chart-container border-none shadow-none h-full !p-6">
                        {/* Ambient Background Gradient */}
                        <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--accent-primary)]/5 blur-[100px] rounded-full pointer-events-none group-hover:bg-[var(--accent-primary)]/10 transition-colors duration-500"></div>

                        <h3 className="chart-title relative z-10 flex items-center gap-2">
                            <span className="text-xl">📈</span>
                            <span className="bg-clip-text text-transparent bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)] font-bold">Performance Trends</span>
                        </h3>
                        <div className="h-[280px] w-full relative z-10 mt-2">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={performanceData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="colorService" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor={COLORS.success} stopOpacity={0.8} />
                                            <stop offset="95%" stopColor={COLORS.success} stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="colorTurnover" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor={COLORS.primary} stopOpacity={0.8} />
                                            <stop offset="95%" stopColor={COLORS.primary} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                    <XAxis dataKey="month" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                                    <YAxis yAxisId="left" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} domain={[85, 100]} />
                                    <YAxis yAxisId="right" orientation="right" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-visible)', borderRadius: '8px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }} />
                                    <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                                    {/* Using Area for a glow effect under the line? Or stick to Line with thick stroke */}
                                    <Line
                                        yAxisId="left"
                                        type="monotone"
                                        dataKey="serviceLevel"
                                        name="Service Level (%)"
                                        stroke={COLORS.success}
                                        strokeWidth={4}
                                        dot={{ r: 4, strokeWidth: 0, fill: COLORS.success }}
                                        activeDot={{ r: 8, fill: COLORS.success, stroke: '#fff', strokeWidth: 2, className: "animate-pulse" }}
                                        filter="url(#glow-line-success)"
                                    />
                                    <Line
                                        yAxisId="right"
                                        type="monotone"
                                        dataKey="turnover"
                                        name="Turnover Rate"
                                        stroke={COLORS.primary}
                                        strokeWidth={4}
                                        dot={{ r: 4, strokeWidth: 0, fill: COLORS.primary }}
                                        activeDot={{ r: 8, fill: COLORS.primary, stroke: '#fff', strokeWidth: 2, className: "animate-pulse" }}
                                        filter="url(#glow-line-primary)"
                                    />
                                    {/* Definitions for filters */}
                                    <defs>
                                        <filter id="glow-line-success" height="300%" width="300%" x="-75%" y="-75%">
                                            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                                            <feMerge>
                                                <feMergeNode in="coloredBlur" />
                                                <feMergeNode in="SourceGraphic" />
                                            </feMerge>
                                        </filter>
                                        <filter id="glow-line-primary" height="300%" width="300%" x="-75%" y="-75%">
                                            <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                                            <feMerge>
                                                <feMergeNode in="coloredBlur" />
                                                <feMergeNode in="SourceGraphic" />
                                            </feMerge>
                                        </filter>
                                    </defs>
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </GlowingCard>

                {/* Today's Alerts - VERTICAL STACKED Layout */}
                <div className="lg:col-span-2 space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-xl font-bold text-[var(--text-primary)] flex items-center gap-2">
                            Today's Alerts
                            <a href="#" onClick={(e) => { e.preventDefault(); setShowAllAlerts(true); }} className="text-[var(--text-dim)] hover:text-[var(--accent-primary)] transition-colors">
                                ⇢
                            </a>
                        </h3>
                    </div>
                    <p className="text-xs text-[var(--text-dim)] mb-4">Critical: &lt;7 days | High: 7-14 days | Medium: 14-30 days</p>

                    {/* Critical */}
                    <div
                        onClick={() => handleAlertClick('Critical')}
                        className={`alert-critical flex items-center justify-between group cursor-pointer transition-all duration-300 relative overflow-hidden
                            ${riskFilter === 'Critical' ? 'ring-2 ring-[#ef4444] scale-[1.02] shadow-[0_0_20px_rgba(239,68,68,0.4)]' : 'hover:scale-[1.01] hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]'}`}
                    >
                        <div className="relative z-10">
                            <div className="text-[#fca5a5] font-bold">Critical</div>
                            <div className="text-[#fca5a5] text-xs opacity-80">Stockout in &lt; 7 days</div>
                        </div>
                        <div className="text-3xl font-bold text-white group-hover:scale-110 transition-transform relative z-10">{stockoutRisk.critical}</div>
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:animate-shimmer pointer-events-none"></div>
                    </div>

                    {/* High Risk */}
                    <div
                        onClick={() => handleAlertClick('High')}
                        className={`alert-warning flex items-center justify-between group cursor-pointer transition-all duration-300 relative overflow-hidden
                            ${riskFilter === 'High' ? 'ring-2 ring-[#f59e0b] scale-[1.02] shadow-[0_0_20px_rgba(245,158,11,0.4)]' : 'hover:scale-[1.01] hover:shadow-[0_0_15px_rgba(245,158,11,0.2)]'}`}
                    >
                        <div className="relative z-10">
                            <div className="text-[#fcd34d] font-bold">High Risk</div>
                            <div className="text-[#fcd34d] text-xs opacity-80">Need reorder soon</div>
                        </div>
                        <div className="text-3xl font-bold text-white group-hover:scale-110 transition-transform relative z-10">{stockoutRisk.high}</div>
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:animate-shimmer pointer-events-none"></div>
                    </div>

                    {/* Slow Moving */}
                    <div
                        onClick={() => handleAlertClick('Slow-Moving')}
                        className={`alert-info flex items-center justify-between group cursor-pointer transition-all duration-300 relative overflow-hidden
                            ${riskFilter === 'Slow-Moving' ? 'ring-2 ring-[#3b82f6] scale-[1.02] shadow-[0_0_20px_rgba(59,130,246,0.4)]' : 'hover:scale-[1.01] hover:shadow-[0_0_15px_rgba(59,130,246,0.2)]'}`}
                    >
                        <div className="relative z-10">
                            <div className="text-[#93c5fd] font-bold">Slow-Moving</div>
                            <div className="text-[#93c5fd] text-xs opacity-80">Low turnover products</div>
                        </div>
                        <div className="text-3xl font-bold text-white group-hover:scale-110 transition-transform relative z-10">{slowMovingCount}</div>
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent translate-x-[-100%] group-hover:animate-shimmer pointer-events-none"></div>
                    </div>

                    {/* View All Button */}
                    <button
                        onClick={() => { setRiskFilter('all'); setShowAllAlerts(!showAllAlerts); }}
                        className="w-full neu-btn-secondary text-center text-sm py-3 transition-all hover:bg-[var(--accent-primary)] hover:text-white hover:border-transparent"
                    >
                        {showAllAlerts && riskFilter === 'all' ? '← Hide Table' : 'View All Alerts →'}
                    </button>
                </div>

            </div>


            {/* ========== 3. EXPANDABLE ALERTS TABLE (ALL PRODUCTS) ========== */}
            {
                showAllAlerts && (
                    <div className="glass-card p-0 border-[var(--accent-primary)]/20 animate-slide-up overflow-hidden">
                        <div className="p-4 border-b border-[var(--border-subtle)] flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <h3 className="text-lg font-bold flex items-center gap-2">
                                <span className="text-xl">📋</span>
                                <span className="bg-clip-text text-transparent bg-gradient-to-r from-[var(--text-primary)] to-[var(--text-secondary)]">
                                    {riskFilter === 'all' ? 'All Products' : `${riskFilter} Products`}
                                </span>
                            </h3>

                            <div className="flex items-center gap-4">
                                <span className="text-xs text-[var(--text-dim)]">
                                    Showing {displayAlerts.length} products
                                </span>
                                <button className="neu-btn text-xs px-3 py-1.5 flex items-center gap-2 opacity-80 hover:opacity-100">
                                    <span>📥</span> Export CSV
                                </button>
                            </div>
                        </div>

                        <div className="overflow-x-auto">
                            <div className="max-h-[450px] overflow-y-auto custom-scrollbar">
                                <table className="w-full text-sm text-left border-collapse" style={{ minWidth: '900px', tableLayout: 'fixed' }}>
                                    <colgroup>
                                        <col style={{ width: '100px' }} />  {/* SKU */}
                                        <col style={{ width: '280px' }} />  {/* Product Name */}
                                        <col style={{ width: '120px' }} />  {/* Category */}
                                        <col style={{ width: '60px' }} />   {/* ABC */}
                                        <col style={{ width: '80px' }} />   {/* Stock */}
                                        <col style={{ width: '60px' }} />   {/* Cov */}
                                        <col style={{ width: '90px' }} />   {/* Risk */}
                                        <col style={{ width: '60px' }} />   {/* Action */}
                                    </colgroup>
                                    <thead className="text-xs text-[var(--text-muted)] uppercase bg-[var(--bg-surface)] sticky top-0 z-10">
                                        <tr className="border-b border-[var(--border-subtle)]">
                                            <th className="px-3 py-3 text-left font-semibold whitespace-nowrap cursor-pointer hover:text-[var(--accent-primary)]" onClick={() => handleSort('product_code')}>
                                                SKU {sortConfig.key === 'product_code' && <span className="text-[var(--accent-primary)]">{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>}
                                            </th>
                                            <th className="px-3 py-3 text-left font-semibold whitespace-nowrap cursor-pointer hover:text-[var(--accent-primary)]" onClick={() => handleSort('product_name')}>
                                                Product
                                            </th>
                                            <th className="px-3 py-3 text-left font-semibold whitespace-nowrap">Category</th>
                                            <th className="px-3 py-3 text-center font-semibold whitespace-nowrap cursor-pointer hover:text-[var(--accent-primary)]" onClick={() => handleSort('abc_class')}>ABC</th>
                                            <th className="px-3 py-3 text-right font-semibold whitespace-nowrap cursor-pointer hover:text-[var(--accent-primary)]" onClick={() => handleSort('current_stock')}>Stock</th>
                                            <th className="px-3 py-3 text-right font-semibold whitespace-nowrap cursor-pointer hover:text-[var(--accent-primary)]" onClick={() => handleSort('days_coverage')}>Cov.</th>
                                            <th className="px-3 py-3 text-center font-semibold whitespace-nowrap cursor-pointer hover:text-[var(--accent-primary)]" onClick={() => handleSort('risk_level')}>Risk</th>
                                            <th className="px-3 py-3 text-center font-semibold whitespace-nowrap">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody className="text-[var(--text-secondary)]">
                                        {displayAlerts.length > 0 ? (
                                            displayAlerts.map((item, idx) => (
                                                <tr key={idx} className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-elevated)] transition-colors text-xs">
                                                    <td className="px-3 py-2.5 font-mono text-[var(--text-dim)] truncate">{item.product_code}</td>
                                                    <td className="px-3 py-2.5 font-medium text-[var(--text-primary)] truncate" title={item.product_name}>{item.product_name}</td>
                                                    <td className="px-3 py-2.5 text-[var(--text-secondary)] truncate">{item.category}</td>
                                                    <td className="px-3 py-2.5 text-center">
                                                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${item.abc_class === 'A' ? 'bg-emerald-500/20 text-emerald-400' : item.abc_class === 'B' ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-500/20 text-slate-400'}`}>
                                                            {item.abc_class}
                                                        </span>
                                                    </td>
                                                    <td className="px-3 py-2.5 text-right font-mono">{item.current_stock.toLocaleString()}</td>
                                                    <td className="px-3 py-2.5 text-right font-mono">
                                                        <span className={item.days_coverage < 7 ? 'text-red-400 font-bold' : item.days_coverage < 14 ? 'text-amber-400' : 'text-slate-400'}>
                                                            {item.days_coverage}d
                                                        </span>
                                                    </td>
                                                    <td className="px-3 py-2.5 text-center">
                                                        <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold ${item.risk_level === 'Critical' ? 'bg-red-500/20 text-red-400' : item.risk_level === 'High' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                                            {item.risk_level}
                                                        </span>
                                                    </td>
                                                    <td className="px-3 py-2.5 text-center">
                                                        <button className="text-[var(--accent-primary)] hover:text-white transition-colors text-sm">
                                                            \u279c
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))
                                        ) : (
                                            <tr>
                                                <td colSpan={8} className="px-6 py-10 text-center text-[var(--text-dim)] italic">
                                                    No products found matching filters.
                                                </td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] text-xs text-[var(--text-dim)] flex justify-between items-center px-4 pb-4">
                            <span>Total: {displayAlerts.length} products</span>
                            <span>Scroll to see all • Use filters to narrow results</span>
                        </div>
                    </div>
                )}

            {/* ========== 4. STOCK HEALTH + TOP PRODUCTS ========== */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 fade-in" style={{ animationDelay: '0.2s' }}>
                {/* Stock Health Pie */}
                <GlowingCard>
                    <h3 className="chart-title">🏥 Stock Health Distribution</h3>
                    <p className="text-[var(--text-dim)] text-xs mb-4">Healthy: &gt;2x turnover + &gt;30d | Stable: &gt;1x + &gt;14d</p>
                    <div className="flex items-center justify-center relative h-[280px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <defs>
                                    <linearGradient id="gradHealthy" x1="0" y1="0" x2="1" y2="1">
                                        <stop offset="0%" stopColor="#10b981" />
                                        <stop offset="100%" stopColor="#059669" />
                                    </linearGradient>
                                    <linearGradient id="gradStable" x1="0" y1="0" x2="1" y2="1">
                                        <stop offset="0%" stopColor="#6366f1" />
                                        <stop offset="100%" stopColor="#4f46e5" />
                                    </linearGradient>
                                    <linearGradient id="gradWarning" x1="0" y1="0" x2="1" y2="1">
                                        <stop offset="0%" stopColor="#f59e0b" />
                                        <stop offset="100%" stopColor="#d97706" />
                                    </linearGradient>
                                    <linearGradient id="gradCritical" x1="0" y1="0" x2="1" y2="1">
                                        <stop offset="0%" stopColor="#ef4444" />
                                        <stop offset="100%" stopColor="#dc2626" />
                                    </linearGradient>
                                </defs>
                                <Pie
                                    activeIndex={activeIndex}
                                    activeShape={renderActiveShape}
                                    data={pieData}
                                    cx="50%" cy="50%"
                                    innerRadius={70}
                                    outerRadius={90}
                                    paddingAngle={4}
                                    dataKey="value"
                                    nameKey="name"
                                    stroke="none"
                                    onMouseEnter={onPieEnter}
                                >
                                    {pieData.map((entry, index) => {
                                        let fillId = 'gradStable';
                                        if (entry.name === 'Healthy') fillId = 'gradHealthy';
                                        if (entry.name === 'Warning') fillId = 'gradWarning';
                                        if (entry.name === 'Critical') fillId = 'gradCritical';

                                        return <Cell key={`cell-${index}`} fill={`url(#${fillId})`} stroke="rgba(255,255,255,0.05)" strokeWidth={1} />;
                                    })}
                                </Pie>
                                {/* Removed tooltip since activeShape shows info, or keep for simple view? ActiveShape is better */}
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none fade-in">
                            <span className="text-4xl font-black text-[var(--text-primary)] drop-shadow-[0_0_15px_rgba(99,102,241,0.5)]">{totalProducts}</span>
                            <span className="text-xs text-[var(--text-muted)] tracking-widest uppercase">Products</span>
                        </div>
                    </div>
                </GlowingCard>

                {/* Top 5 Fast-Moving */}
                <GlowingCard>
                    <h3 className="chart-title">🏆 Top 5 Fast-Moving Products</h3>
                    <div className="h-[280px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart layout="vertical" data={topProducts || []} margin={{ top: 0, right: 30, left: 10, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="barGradient" x1="0" y1="0" x2="1" y2="0">
                                        <stop offset="0%" stopColor={COLORS.primary} stopOpacity={0.6} />
                                        <stop offset="100%" stopColor={COLORS.primary} stopOpacity={1} />
                                    </linearGradient>
                                    <linearGradient id="barGradientTop" x1="0" y1="0" x2="1" y2="0">
                                        <stop offset="0%" stopColor={COLORS.success} stopOpacity={0.6} />
                                        <stop offset="100%" stopColor={COLORS.success} stopOpacity={1} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                                <XAxis type="number" stroke="var(--text-muted)" fontSize={12} tickLine={false} axisLine={false} />
                                <YAxis type="category" dataKey="product_code" stroke="var(--text-muted)" fontSize={10} tickLine={false} axisLine={false} width={70} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-visible)', borderRadius: '8px' }}
                                    formatter={(value) => [`${Number(value).toFixed(2)} units/day`, 'Daily Demand']}
                                    labelFormatter={(label, payload) => payload?.[0]?.payload?.product_name || label}
                                />
                                <Bar dataKey="daily_demand" radius={[0, 4, 4, 0]} barSize={20} animationDuration={1500}>
                                    {(topProducts || []).map((_, index) => (
                                        <Cell key={`cell-${index}`} fill={index === 0 ? 'url(#barGradientTop)' : 'url(#barGradient)'} />
                                    ))}
                                    <LabelList dataKey="product_name" position="insideLeft" fill="white" fontSize={9} formatter={(v: string) => v.length > 18 ? v.substring(0, 15) + '...' : v} style={{ textShadow: '0 0 4px rgba(0,0,0,0.8)' }} />
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </GlowingCard>
            </div>

            {/* ========== 5. CATEGORY SUMMARY CARDS ========== */}
            <div className="fade-in py-2" style={{ animationDelay: '0.3s' }}>
                <h3 className="text-[var(--text-primary)] font-bold text-lg mb-4">📊 Category Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 p-2">
                    {(healthData || []).map((cat, idx) => (
                        <div
                            key={idx}
                            className={`category-card ${cat.category.toLowerCase()} group cursor-pointer transition-all duration-300 hover:scale-[1.05] hover:shadow-[0_15px_30px_rgba(0,0,0,0.4)] relative overflow-hidden`}
                        >
                            {/* FRONT FACE (Stats) */}
                            <div className="relative z-10 transition-all duration-300 group-hover:opacity-0 group-hover:-translate-y-4 backface-hidden">
                                <div className="text-sm font-semibold text-[var(--text-primary)] mb-2 group-hover:tracking-wider transition-all">{cat.category}</div>
                                <div className="text-3xl font-bold transition-all origin-left" style={{ color: HEALTH_COLORS[cat.category] }}>{cat.count}</div>
                                <div className="text-xs text-[var(--text-dim)] mt-1 transition-colors">{cat.percentage}% of total</div>
                            </div>

                            {/* BACK FACE (Details) - Switches on Hover */}
                            <div className="absolute inset-0 z-20 p-4 flex flex-col justify-center opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 bg-[var(--bg-elevated)]/95 backdrop-blur-sm">
                                <div className="text-xs font-bold mb-2 pb-1 border-b border-[var(--border-subtle)]" style={{ color: HEALTH_COLORS[cat.category] }}>Definisi {cat.category}</div>
                                <div className="text-[10px] leading-relaxed text-[var(--text-secondary)]">
                                    {cat.category === 'Healthy' && "Turnover > 2x dan stok cukup untuk > 30 hari. Performa optimal."}
                                    {cat.category === 'Stable' && "Turnover > 1x dan stok cukup untuk > 14 hari. Kondisi aman."}
                                    {cat.category === 'Warning' && "Low turnover atau stok menipis (< 7 hari). Perlu perhatian."}
                                    {cat.category === 'Critical' && "Dead stock atau stockout imminent. Tindakan segera diperlukan."}
                                </div>
                            </div>

                            {/* Animated ring on hover */}
                            <div className="absolute inset-0 rounded-xl border border-transparent group-hover:border-[var(--accent-primary)]/30 transition-all duration-500 scale-95 group-hover:scale-100 pointer-events-none"></div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ========== 6. STOCK VALUE BY ABC CLASS ========== */}
            <GlowingCard className="hover:border-[var(--warning)]/30 transition-all duration-300" style={{ animationDelay: '0.4s' }}>
                <h3 className="chart-title">💰 Stock Value & Performance by ABC Class</h3>
                <div className="h-[300px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={abcChartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                            <defs>
                                <linearGradient id="gradA" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                                    <stop offset="100%" stopColor="#059669" stopOpacity={0.3} />
                                </linearGradient>
                                <linearGradient id="gradB" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.8} />
                                    <stop offset="100%" stopColor="#2563eb" stopOpacity={0.3} />
                                </linearGradient>
                                <linearGradient id="gradC" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.8} />
                                    <stop offset="100%" stopColor="#d97706" stopOpacity={0.3} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                            <YAxis stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `Rp ${v}M`} />
                            <Tooltip
                                cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-visible)', borderRadius: '8px' }}
                                formatter={(value) => [`Rp ${Number(value).toFixed(1)}M`, 'Stock Value']}
                            />
                            <Bar dataKey="stockValue" radius={[4, 4, 0, 0]} barSize={80} animationDuration={1500}>
                                {abcChartData.map((entry, index) => {
                                    let fillId = 'gradC';
                                    if (entry.abc_class === 'A') fillId = 'gradA';
                                    if (entry.abc_class === 'B') fillId = 'gradB';
                                    return <Cell key={`cell-${index}`} fill={`url(#${fillId})`} />;
                                })}
                                <LabelList dataKey="stockValue" position="top" formatter={(v: number) => `Rp ${v.toFixed(1)}M`} fill="var(--text-primary)" fontSize={12} fontWeight="bold" />
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </GlowingCard>

            {/* ========== 7. ABC CLASS PERFORMANCE SUMMARY ========== */}
            <div className="fade-in py-2" style={{ animationDelay: '0.5s' }}>
                <h3 className="text-[var(--text-primary)] font-bold text-lg mb-4">📈 ABC Class Performance Summary</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 p-2">
                    {(abcPerformance || []).map((item, idx) => (
                        <GlowingCard
                            key={idx}
                            className={`abc-card class-${item.abc_class.toLowerCase()} cursor-pointer relative !p-6`}
                            glowColor={ABC_COLORS[item.abc_class]}
                            title={`Class ${item.abc_class}: ${item.product_count} products, Rp ${(item.stock_value / 1_000_000).toFixed(1)}M value, ${item.turnover_ratio.toFixed(2)}x turnover`}
                        >
                            <div className="relative z-10">
                                <div className="abc-label group-hover:scale-110 transition-transform">Class {item.abc_class}</div>
                                <div className="grid grid-cols-2 gap-4 mt-4 text-left">
                                    <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.02)] group-hover:bg-[rgba(255,255,255,0.05)] transition-colors">
                                        <div className="text-xs text-[var(--text-dim)]">Stock Value</div>
                                        <div className="text-lg font-bold text-[var(--success)]">Rp {(item.stock_value / 1_000_000).toFixed(1)}M</div>
                                    </div>
                                    <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.02)] group-hover:bg-[rgba(255,255,255,0.05)] transition-colors">
                                        <div className="text-xs text-[var(--text-dim)]">Products</div>
                                        <div className="text-lg font-bold text-[var(--text-primary)]">{item.product_count}</div>
                                    </div>
                                    <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.02)] group-hover:bg-[rgba(255,255,255,0.05)] transition-colors">
                                        <div className="text-xs text-[var(--text-dim)]">Avg Demand</div>
                                        <div className="text-lg font-bold text-[var(--info)]">{item.avg_daily_demand.toFixed(1)} units</div>
                                    </div>
                                    <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.02)] group-hover:bg-[rgba(255,255,255,0.05)] transition-colors">
                                        <div className="text-xs text-[var(--text-dim)]">Turnover</div>
                                        <div className="text-lg font-bold text-[var(--warning)]">{item.turnover_ratio.toFixed(2)}x</div>
                                    </div>
                                </div>
                            </div>
                        </GlowingCard>
                    ))}
                </div>
            </div>

            {/* ========== 8. CLASSIFICATION LEGEND ========== */}
            <div className="neu-card fade-in" style={{ animationDelay: '0.6s' }}>
                <h3 className="text-[var(--text-primary)] font-bold text-lg mb-4">📚 Classification Legend</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 p-2">
                    <div className="insight-card group hover:border-[var(--success)]/50 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_10px_40px_rgba(16,185,129,0.15)]">
                        <h4 className="text-[var(--success)] font-bold mb-3 text-lg group-hover:scale-105 transition-transform origin-left">Class A - Fast Moving</h4>
                        <ul className="text-sm text-[var(--text-secondary)] space-y-2">
                            <li className="flex items-start gap-2"><span className="text-[var(--success)]">●</span> High revenue contribution (80%)</li>
                            <li className="flex items-start gap-2"><span className="text-[var(--success)]">●</span> Priority stock availability</li>
                            <li className="flex items-start gap-2"><span className="text-[var(--success)]">●</span> Daily monitoring, fast reorder</li>
                        </ul>
                    </div>
                    <div className="insight-card group hover:border-[var(--info)]/50 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_10px_40px_rgba(59,130,246,0.15)]">
                        <h4 className="text-[var(--info)] font-bold mb-3 text-lg group-hover:scale-105 transition-transform origin-left">Class B - Moderate Moving</h4>
                        <ul className="text-sm text-[var(--text-secondary)] space-y-2">
                            <li className="flex items-start gap-2"><span className="text-[var(--info)]">●</span> Medium revenue contribution (15%)</li>
                            <li className="flex items-start gap-2"><span className="text-[var(--info)]">●</span> Medium priority</li>
                            <li className="flex items-start gap-2"><span className="text-[var(--info)]">●</span> Weekly monitoring</li>
                        </ul>
                    </div>
                    <div className="insight-card group hover:border-[var(--warning)]/50 transition-all duration-300 hover:scale-[1.02] hover:shadow-[0_10px_40px_rgba(245,158,11,0.15)]">
                        <h4 className="text-[var(--warning)] font-bold mb-3 text-lg group-hover:scale-105 transition-transform origin-left">Class C - Slow Moving</h4>
                        <ul className="text-sm text-[var(--text-secondary)] space-y-2">
                            <li className="flex items-start gap-2"><span className="text-[var(--warning)]">●</span> Low revenue contribution (5%)</li>
                            <li className="flex items-start gap-2"><span className="text-[var(--warning)]">●</span> Low priority, needs evaluation</li>
                            <li className="flex items-start gap-2"><span className="text-[var(--warning)]">●</span> Consider promotions or discontinue</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div >
    );
}

