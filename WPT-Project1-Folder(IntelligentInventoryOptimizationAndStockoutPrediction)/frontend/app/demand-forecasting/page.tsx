'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, authApi } from '@/lib/api'; // Correct import
import { GlowingCard } from '@/components/ui/GlowingCard'; // Reuse existing component
import { BackgroundBeams } from '@/components/ui/BackgroundBeams'; // Reuse existing component
import { motion, AnimatePresence } from 'framer-motion';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
    Histogram, Scatter
} from 'recharts';
import * as XLSX from 'xlsx'; // You might need to install xlsx if not present, but for now I will simulate or use if existing. 
// Actually I'll use simple CSV export logic without extra lib if possible to avoid install issues, or just a mock button.

// --- TYPES ---
interface ForecastingItem {
    product_code: string;
    product_name: string;
    product_category: string;
    ABC_class: string;
    current_stock_qty: number;
    stock_value: number;
    avg_daily_demand: number;
    forecast_30d: number | null;
    forecast_model: string | null;
    forecast_mape: number | null;
}

const COLORS = {
    primary: '#6366f1',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    text: '#f8fafc',
    textMuted: '#94a3b8'
};

export default function DemandForecastingPage() {
    // --- STATE ---
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [selectedABC, setSelectedABC] = useState('All');
    const [forecastDays, setForecastDays] = useState(14);
    const [topN, setTopN] = useState(10);
    const [showEmailForm, setShowEmailForm] = useState(false);
    const [selectedBin, setSelectedBin] = useState<{ start: number; end: number; products: any[] } | null>(null);

    // --- QUERIES ---
    const { data: rawData, isLoading, error, status, fetchStatus } = useQuery({
        queryKey: ['forecasting-data', searchQuery, selectedCategory, selectedABC],
        queryFn: async () => {
            console.log('📡 Fetching data...');
            // Use direct api call to avoid any wrapper issues
            const res = await api.get('/forecasting/data', {
                params: {
                    search: searchQuery,
                    category: selectedCategory,
                    abc_class: selectedABC
                }
            });
            console.log('✅ Data fetched length:', res.data?.length);

            // Fix: If axis/flask returns string (because of content-type mismatch?), parse it manually
            let safeData = res.data;
            if (typeof safeData === 'string') {
                try {
                    // Handle Python NaN values which are invalid in JSON
                    const cleanJson = safeData.replace(/: NaN/g, ': null');
                    safeData = JSON.parse(cleanJson);
                } catch (e) {
                    console.error('Failed to parse JSON string:', e);
                    safeData = [];
                }
            }

            return safeData;
        }
    });

    const { data: groupsData } = useQuery({
        queryKey: ['groups-list'],
        queryFn: async () => (await api.get('/dashboard/groups')).data
    });

    // --- DERIVED DATA ---
    // Ensure data is always a valid array, even if API returns an object or undefined
    const data = (rawData && Array.isArray(rawData)) ? rawData : [];

    // Filtered Categories
    const categories = ['All', ...(groupsData?.groups || [])];

    // Chart Data 1: Demand Distribution (Filtered > 1, with Low Demand Metric)
    const { distributionData, lowDemandCount } = useMemo(() => {
        if (!data || !Array.isArray(data) || !data.length) return { distributionData: [], lowDemandCount: 0 };
        // Use daily demand
        const allValues = data.map(d => Number(d.forecast_30d || d.avg_daily_demand || 0)).filter(v => v > 0);
        if (!allValues.length) return { distributionData: [], lowDemandCount: 0 };

        allValues.sort((a, b) => a - b);

        // Split data: 0-1 (Low Demand) vs > 1 (Chart Data)
        const lowDemand = allValues.filter(v => v < 1);
        const chartValues = allValues.filter(v => v >= 1);

        const lowDemandCount = lowDemand.length;

        // Generate bins for > 1
        if (chartValues.length === 0) return { distributionData: [], lowDemandCount };

        const max = Math.ceil(Math.max(...chartValues));
        // Start from 1 since we excluded < 1
        // Bins: 1-2, 2-3, ...

        const binSize = 1;
        const binCount = Math.max(max, 5); // Ensure at least a few bins

        const bins = Array.from({ length: binCount }, (_, i) => ({
            binStart: 1 + i, // Start at 1
            binEnd: 2 + i,
            count: 0,
            name: `${1 + i}-${2 + i}`
        }));

        chartValues.forEach(v => {
            // v=1.5 -> index 0 (1-2)
            // v=1.0 -> index 0
            // v=2.5 -> index 1
            const binIndex = Math.min(Math.floor(v - 1), binCount - 1);
            if (bins[binIndex]) bins[binIndex].count++;
        });

        return { distributionData: bins, lowDemandCount };
    }, [data]);

    // Chart Data 2: Top Products
    // Filter out items without a valid model forecast (forecast_30d is not null)
    const topProductsData = useMemo(() => {
        if (!data || !Array.isArray(data) || !data.length) return [];

        // Filter valid forecasts only
        const validForecasts = data.filter(item =>
            item.forecast_30d !== null &&
            item.forecast_30d !== undefined &&
            !isNaN(Number(item.forecast_30d))
        );

        // Add calculated fields
        const processed = validForecasts.map(item => {
            const dailyForecast = Number(item.forecast_30d) || 0;
            const forecastDemand = dailyForecast * forecastDays;
            return {
                ...item,
                forecast_demand: forecastDemand,
                stock_coverage_days: item.current_stock_qty / (dailyForecast || 0.01)
            };
        });

        return processed
            .sort((a, b) => b.forecast_demand - a.forecast_demand)
            .slice(0, topN);
    }, [data, forecastDays, topN]);

    // Summary Stats
    const totalForecastDemand = topProductsData.reduce((sum, item) => sum + (item.forecast_demand || 0), 0);
    // Replaced MAPE with Critical Items (Stockout Risk < 7 days)
    // We check ALL data for risk, not just top filtered ones. Fallback is valid for risk calc.
    const criticalItemsCount = data.filter(item => {
        const demand = Number(item.forecast_30d || item.avg_daily_demand || 0);
        if (demand <= 0) return false; // Infinite coverage
        const coverage = item.current_stock_qty / demand;
        return coverage < 7;
    }).length;

    // --- HANDLERS ---
    const handleBarClick = (entry: any) => {
        if (!entry || typeof entry.binStart !== 'number' || !data || !Array.isArray(data)) return;

        const start = entry.binStart;
        const end = entry.binEnd;

        // Filter products in this range: [start, end)
        // Note: For integers, demand >= 1 and demand < 2 handles strictly 1.0 - 1.99.
        const matchingProducts = data.filter(item => {
            const demand = Number(item.forecast_30d || item.avg_daily_demand || 0);
            return demand >= start && demand < end;
        });

        setSelectedBin({
            start,
            end,
            products: matchingProducts.sort((a, b) => Number(b.forecast_30d || 0) - Number(a.forecast_30d || 0))
        });
    };

    const handleDownload = () => {
        // Simple CSV Export
        const headers = ['Product Code', 'Name', 'Category', 'ABC', 'Current Stock', 'Daily Demand', 'Forecast (Days)', 'Total Forecast'];
        const csvContent = [
            headers.join(','),
            ...topProductsData.map(row => [
                row.product_code,
                `"${row.product_name}"`,
                row.product_category,
                row.ABC_class,
                row.current_stock_qty,
                (row.forecast_30d || row.avg_daily_demand).toFixed(2),
                forecastDays,
                ((row.forecast_30d || row.avg_daily_demand) * forecastDays).toFixed(2)
            ].join(','))
        ].join('\\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `forecast_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
    };

    return (
        <div className="min-h-screen space-y-8 p-4 pb-20 relative overflow-hidden text-slate-100">
            <BackgroundBeams /> {/* Pretty background */}

            {/* HEADER */}
            <motion.header
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8"
            >
                <div>
                    <h1 className="text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-purple-400 to-indigo-400 animate-text-shimmer bg-[size:200%]">
                        Demand Forecasting
                    </h1>
                    <p className="text-slate-400 mt-2 max-w-2xl">
                        Predict future product demand using historical sales and AI models.
                        Optimize your cash flow by preventing stockouts and overstock.
                    </p>
                </div>

                <div className="flex gap-3">
                    <div className="glass-card px-4 py-2 flex flex-col items-center">
                        <span className="text-xs text-slate-400 uppercase tracking-wider">Total Forecast ({forecastDays}d)</span>
                        <span className="text-xl font-bold text-indigo-400">{Math.round(totalForecastDemand).toLocaleString()} units</span>
                    </div>
                    <div className="glass-card px-4 py-2 flex flex-col items-center">
                        <span className="text-xs text-slate-400 uppercase tracking-wider">Stockout Risk (&lt;7d)</span>
                        <span className={`text-xl font-bold ${criticalItemsCount > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {criticalItemsCount} items
                        </span>
                    </div>
                </div>
            </motion.header>

            {/* FILTERS */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-card p-6 rounded-2xl border border-white/5 bg-white/5 backdrop-blur-xl relative z-10 grid grid-cols-1 md:grid-cols-4 gap-6"
            >
                {/* Search */}
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Search Product</label>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Code or Name..."
                        className="w-full bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-600"
                    />
                </div>

                {/* Category */}
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Product Group</label>
                    <select
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        className="w-full bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all appearance-none cursor-pointer"
                    >
                        {categories.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                </div>

                {/* Days Slider */}
                <div className="space-y-2">
                    <div className="flex justify-between">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Forecast Horizon</label>
                        <span className="text-xs font-bold text-indigo-400">{forecastDays} Days</span>
                    </div>
                    <input
                        type="range"
                        min="7" max="90"
                        value={forecastDays}
                        onChange={(e) => setForecastDays(parseInt(e.target.value))}
                        className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                        <span>7d</span>
                        <span>30d</span>
                        <span>90d</span>
                    </div>
                </div>

                {/* ABC Class */}
                <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">ABC Class</label>
                    <div className="flex gap-2">
                        {['All', 'A', 'B', 'C'].map(cls => (
                            <button
                                key={cls}
                                onClick={() => setSelectedABC(cls)}
                                className={`flex-1 py-2 rounded-lg text-sm font-bold transition-all ${selectedABC === cls
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 scale-105'
                                    : 'bg-slate-800/50 text-slate-400 hover:bg-slate-700'
                                    }`}
                            >
                                {cls}
                            </button>
                        ))}
                    </div>
                </div>
            </motion.div>

            {/* CHARTS */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                    className="glass-card p-6 rounded-2xl border border-white/5 bg-[#0f172a]/50 backdrop-blur-xl"
                >
                    <div className="flex justify-between items-start mb-6">
                        <div>
                            <h3 className="text-lg font-bold text-slate-200">Daily Demand Distribution</h3>
                            <p className="text-xs text-slate-400 mt-1">Showing demand {'>'} 1 unit/day</p>
                        </div>
                        <div className="flex flex-col items-end">
                            <span className="text-xs text-slate-400 uppercase tracking-wider">Low Demand (0-1)</span>
                            <span className="text-lg font-bold text-slate-200">{lowDemandCount} items</span>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="h-[300px] flex items-center justify-center animate-pulse text-indigo-400">Loading data...</div>
                    ) : (
                        <div className="overflow-x-auto pb-4 custom-scrollbar">
                            <div className="h-[300px]" style={{ minWidth: '100%', width: `${Math.max(100, distributionData.length * 5)}%` }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={distributionData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.5} vertical={false} />
                                        <XAxis
                                            dataKey="name"
                                            stroke="#94a3b8"
                                            tick={{ fill: '#94a3b8', fontSize: 10 }}
                                            tickLine={false}
                                            interval={0}
                                            angle={-45}
                                            textAnchor="end"
                                            height={60}
                                        />
                                        <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 12 }} tickLine={false} />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                                            itemStyle={{ color: '#818cf8' }}
                                            cursor={{ fill: '#334155', opacity: 0.4 }}
                                        />
                                        <Bar dataKey="count" fill="url(#colorGradient)" radius={[4, 4, 0, 0]} animationDuration={1500} onClick={handleBarClick} cursor="pointer">
                                            {distributionData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={`hsl(${230 + (index * 5) % 40}, 80%, 65%)`} />
                                            ))}
                                        </Bar>
                                        <defs>
                                            <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="0%" stopColor="#818cf8" stopOpacity={1} />
                                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.6} />
                                            </linearGradient>
                                        </defs>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}
                </motion.div>

                {/* Top Products Forecast */}
                <GlowingCard className="h-[400px]">
                    <div className="flex justify-between items-center mb-4">
                        <h3 className="text-lg font-bold flex items-center gap-2">
                            <span className="text-xl">🏆</span> Top Forecast ({forecastDays}d)
                        </h3>
                        <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-400">Show:</span>
                            <select
                                value={topN}
                                onChange={(e) => setTopN(parseInt(e.target.value))}
                                className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-300 focus:outline-none"
                            >
                                <option value={5}>Top 5</option>
                                <option value={10}>Top 10</option>
                                <option value={20}>Top 20</option>
                            </select>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="h-full flex items-center justify-center animate-pulse text-indigo-400">Loading data...</div>
                    ) : (
                        <ResponsiveContainer width="100%" height="85%">
                            <BarChart data={topProductsData} layout="vertical" margin={{ left: 20 }}>
                                <defs>
                                    <linearGradient id="topColor" x1="0" y1="0" x2="1" y2="0">
                                        <stop offset="5%" stopColor="#34d399" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#10b981" stopOpacity={1} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                                <XAxis type="number" stroke="rgba(255,255,255,0.3)" fontSize={10} tickLine={false} axisLine={false} />
                                <YAxis type="category" dataKey="product_code" stroke="rgba(255,255,255,0.3)" fontSize={10} tickLine={false} axisLine={false} width={80} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }}
                                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                                    formatter={(val: number) => [val.toFixed(0), 'Forecast Demand']}
                                />
                                <Bar dataKey="forecast_demand" fill="url(#topColor)" radius={[0, 4, 4, 0]} barSize={20} />
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </GlowingCard>
            </div >

            {/* TABLE */}
            <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="glass-card p-0 rounded-2xl border border-white/5 bg-white/5 backdrop-blur-xl relative z-10 overflow-hidden"
            >
                <div className="p-6 border-b border-white/5 flex flex-col sm:flex-row justify-between items-center gap-4">
                    <h3 className="text-lg font-bold">📋 Detailed Forecast</h3>
                    <div className="flex gap-3">
                        <button
                            onClick={handleDownload}
                            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm rounded-lg transition-colors flex items-center gap-2 border border-slate-700"
                        >
                            <span>📥</span> Download CSV
                        </button>
                        <button
                            onClick={() => setShowEmailForm(!showEmailForm)}
                            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-indigo-500/25"
                        >
                            <span>✉️</span> Email Report
                        </button>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm whitespace-nowrap">
                        <thead className="bg-slate-900/50 text-slate-400 uppercase text-xs">
                            <tr>
                                <th className="px-6 py-4 font-semibold">SKU</th>
                                <th className="px-6 py-4 font-semibold">Product Name</th>
                                <th className="px-6 py-4 font-semibold">Category</th>
                                <th className="px-6 py-4 font-semibold text-center">ABC</th>
                                <th className="px-6 py-4 font-semibold text-right">Daily Demand</th>
                                <th className="px-6 py-4 font-semibold text-right">Forecast ({forecastDays}d)</th>
                                <th className="px-6 py-4 font-semibold text-right">Stock</th>
                                <th className="px-6 py-4 font-semibold text-right">Coverage</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {isLoading ? (
                                <tr><td colSpan={8} className="px-6 py-8 text-center text-slate-500">Loading data...</td></tr>
                            ) : data.length === 0 ? (
                                <tr><td colSpan={8} className="px-6 py-8 text-center text-slate-500 italic">No products found matching filters.</td></tr>
                            ) : (
                                // Show top 50 in table to perform well
                                topProductsData.slice(0, 50).map((row, idx) => (
                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                        <td className="px-6 py-4 font-mono text-slate-400">{row.product_code}</td>
                                        <td className="px-6 py-4 text-slate-200 font-medium max-w-[200px] truncate" title={row.product_name}>{row.product_name}</td>
                                        <td className="px-6 py-4 text-slate-400">{row.product_category}</td>
                                        <td className="px-6 py-4 text-center">
                                            <span className={`px-2 py-1 rounded text-xs font-bold ${row.ABC_class === 'A' ? 'bg-emerald-500/20 text-emerald-400' :
                                                row.ABC_class === 'B' ? 'bg-blue-500/20 text-blue-400' :
                                                    'bg-slate-500/20 text-slate-400'
                                                }`}>
                                                {row.ABC_class}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-slate-300">
                                            {(Number(row.forecast_30d) || 0).toFixed(2)}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono font-bold text-indigo-400">
                                            {(row.forecast_demand || 0).toFixed(0)}
                                        </td>
                                        <td className="px-6 py-4 text-right font-mono text-slate-300">
                                            {row.current_stock_qty.toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            {(() => {
                                                const coverage = row.stock_coverage_days || 0;
                                                return (
                                                    <span className={`font-mono ${coverage < 7 ? 'text-red-400 font-bold' :
                                                        coverage < 14 ? 'text-amber-400' : 'text-emerald-400'
                                                        }`}>
                                                        {coverage.toFixed(1)}d
                                                    </span>
                                                );
                                            })()}
                                        </td>

                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
                {/* Footer or Pagination could go here */}
                {
                    topProductsData.length > 50 && (
                        <div className="p-4 text-center text-xs text-slate-500 border-t border-white/5">
                            Showing top 50 of {topProductsData.length} products sorted by forecast.
                        </div>
                    )
                }
            </motion.div >

            {/* EMAIL FORM OVERLAY (Simulated) */}
            <AnimatePresence>
                {
                    showEmailForm && (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
                        >
                            <div className="glass-card w-full max-w-md p-6 rounded-2xl border border-white/10 bg-[#0f172a] shadow-2xl">
                                <h3 className="text-xl font-bold mb-4">Email Forecast Report</h3>
                                <p className="text-sm text-slate-400 mb-6">Send the top {topN} forecast products report to stakeholders.</p>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-xs font-semibold text-slate-400 mb-1">To Residents/Stakeholders</label>
                                        <input type="text" placeholder="email@hospital.com" className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500" />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-semibold text-slate-400 mb-1">Message (Optional)</label>
                                        <textarea placeholder="Please review the forecast..." className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 h-24"></textarea>
                                    </div>
                                    <div className="flex gap-3 justify-end mt-6">
                                        <button onClick={() => setShowEmailForm(false)} className="px-4 py-2 text-slate-400 hover:text-white transition-colors">Cancel</button>
                                        <button onClick={() => { setShowEmailForm(false); alert('Email sent!'); }} className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg shadow-lg shadow-indigo-500/25">Send Report</button>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    )
                }
            </AnimatePresence >

            {/* DRILL DOWN MODAL */}
            <AnimatePresence>
                {selectedBin && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
                        onClick={() => setSelectedBin(null)}
                    >
                        <div
                            className="glass-card w-full max-w-4xl max-h-[80vh] flex flex-col rounded-2xl border border-white/10 bg-[#0f172a] shadow-2xl overflow-hidden"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="p-6 border-b border-white/10 flex justify-between items-center">
                                <div>
                                    <h3 className="text-xl font-bold text-slate-200">
                                        Products with Daily Demand {selectedBin.start} - {selectedBin.end}
                                    </h3>
                                    <p className="text-sm text-slate-400 mt-1">
                                        Found {selectedBin.products.length} items in this range.
                                    </p>
                                </div>
                                <button
                                    onClick={() => setSelectedBin(null)}
                                    className="p-2 hover:bg-white/10 rounded-full transition-colors"
                                >
                                    ❌
                                </button>
                            </div>

                            <div className="flex-1 overflow-auto p-0">
                                <table className="w-full text-left text-sm whitespace-nowrap">
                                    <thead className="sticky top-0 bg-[#0f172a] z-10 text-slate-400 uppercase text-xs font-semibold">
                                        <tr>
                                            <th className="px-6 py-3 bg-[#0f172a]">SKU</th>
                                            <th className="px-6 py-3 bg-[#0f172a]">Name</th>
                                            <th className="px-6 py-3 bg-[#0f172a] text-right">Daily Demand</th>
                                            <th className="px-6 py-3 bg-[#0f172a] text-right">Forecast (30d)</th>
                                            <th className="px-6 py-3 bg-[#0f172a] text-right">Stock</th>
                                            <th className="px-6 py-3 bg-[#0f172a] text-right">Coverage</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {selectedBin.products.map((row, idx) => (
                                            <tr key={idx} className="hover:bg-white/5 transition-colors">
                                                <td className="px-6 py-3 font-mono text-slate-400">{row.product_code}</td>
                                                <td className="px-6 py-3 text-slate-200 font-medium">{row.product_name}</td>
                                                <td className="px-6 py-3 text-right font-mono text-slate-300">
                                                    {(Number(row.forecast_30d || row.avg_daily_demand || 0)).toFixed(2)}
                                                </td>
                                                <td className="px-6 py-3 text-right font-mono text-indigo-400 font-bold">
                                                    {(Number(row.forecast_30d || row.avg_daily_demand || 0) * 30).toFixed(0)}
                                                </td>
                                                <td className="px-6 py-3 text-right font-mono text-slate-300">
                                                    {row.current_stock_qty.toLocaleString()}
                                                </td>
                                                <td className="px-6 py-3 text-right">
                                                    {(() => {
                                                        const demand = Number(row.forecast_30d || row.avg_daily_demand || 0);
                                                        const coverage = demand > 0 ? row.current_stock_qty / demand : 999;
                                                        return (
                                                            <span className={`font-mono ${coverage < 7 ? 'text-red-400 font-bold' : coverage < 14 ? 'text-amber-400' : 'text-emerald-400'}`}>
                                                                {coverage > 365 ? '>1y' : coverage.toFixed(1) + 'd'}
                                                            </span>
                                                        );
                                                    })()}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            <div className="p-4 border-t border-white/10 bg-[#0f172a] text-right">
                                <button
                                    onClick={() => setSelectedBin(null)}
                                    className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* LEGENDS */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
                <div className="glass-card p-6 rounded-xl border border-white/5">
                    <h4 className="text-sm font-bold text-slate-300 mb-3 border-b border-white/10 pb-2">ABC Classification Guide</h4>
                    <div className="space-y-2 text-xs">
                        <div className="flex justify-between"><span className="text-emerald-400 font-bold">Class A</span> <span className="text-slate-400">High Value (~80% revenue). Tight control needed.</span></div>
                        <div className="flex justify-between"><span className="text-blue-400 font-bold">Class B</span> <span className="text-slate-400">Medium Value (~15% revenue). Regular control.</span></div>
                        <div className="flex justify-between"><span className="text-slate-400 font-bold">Class C</span> <span className="text-slate-500">Low Value (~5% revenue). Bulk order/loose control.</span></div>
                    </div>
                </div>
                <div className="glass-card p-6 rounded-xl border border-white/5">
                    <h4 className="text-sm font-bold text-slate-300 mb-3 border-b border-white/10 pb-2">Segment Guide</h4>
                    <div className="space-y-2 text-xs">
                        <div className="flex justify-between"><span className="text-indigo-400 font-bold">Healthy</span> <span className="text-slate-400">High turnover & sufficient stock coverage.</span></div>
                        <div className="flex justify-between"><span className="text-amber-400 font-bold">Warning</span> <span className="text-slate-400">Low stock coverage (&lt;14d) or low turnover.</span></div>
                        <div className="flex justify-between"><span className="text-red-400 font-bold">Critical</span> <span className="text-slate-400">Imminent stockout (&lt;7d) or dead stock.</span></div>
                    </div>
                </div>
            </div>

        </div >
    );
}
