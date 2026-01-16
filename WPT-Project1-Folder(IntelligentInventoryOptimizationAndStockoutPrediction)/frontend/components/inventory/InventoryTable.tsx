'use client'

import { useState } from 'react'
import {
    Edit2,
    Trash2,
    AlertTriangle,
    CheckCircle,
    XCircle,
    Package
} from 'lucide-react'
import { InventoryItem } from '@/types'
import { cn } from '@/lib/utils'

interface InventoryTableProps {
    data: InventoryItem[]
    isLoading: boolean
}

const StatusBadge = ({ status }: { status: string }) => {
    const styles = {
        'Optimal': 'badge-success',
        'Low Stock': 'badge-warning',
        'Stockout': 'badge-critical',
        'Overstock': 'bg-info/20 text-info border border-info/40 shadow-[0_0_12px_theme(colors.info.glow)]'
    }

    const icon = {
        'Optimal': CheckCircle,
        'Low Stock': AlertTriangle,
        'Stockout': XCircle,
        'Overstock': Package
    }

    const IconComponent = icon[status as keyof typeof icon] || Package

    return (
        <span className={cn("badge flex items-center gap-1.5 w-fit", styles[status as keyof typeof styles])}>
            <IconComponent size={12} />
            {status}
        </span>
    )
}

export default function InventoryTable({ data, isLoading }: InventoryTableProps) {
    if (isLoading) {
        return (
            <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                    <div key={i} className="h-16 bg-bg-card/50 rounded-xl animate-pulse" />
                ))}
            </div>
        )
    }

    if (data.length === 0) {
        return (
            <div className="text-center py-20 bg-bg-card rounded-2xl border border-white/5 border-dashed">
                <Package size={48} className="mx-auto text-text-muted mb-4 opacity-20" />
                <h3 className="text-xl font-bold text-text-muted">No Items Found</h3>
                <p className="text-text-secondary mt-2">Check your data source.</p>
            </div>
        )
    }

    return (
        <div className="overflow-x-auto rounded-2xl border border-white/5 bg-bg-card shadow-neu-raised">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="border-b border-white/10 text-text-muted text-sm uppercase tracking-wider">
                        <th className="p-4 font-semibold">Product</th>
                        <th className="p-4 font-semibold">Category</th>
                        <th className="p-4 font-semibold text-center">Stock</th>
                        <th className="p-4 font-semibold text-center">Levels (Min/Max)</th>
                        <th className="p-4 font-semibold text-right">Price</th>
                        <th className="p-4 font-semibold text-center">Status</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                    {data.map((item) => (
                        <tr key={item.id} className="group hover:bg-white/5 transition-colors">
                            <td className="p-4">
                                <div className="font-medium text-text-primary">{item.product_name}</div>
                                <div className="text-xs text-text-muted font-mono mt-0.5">{item.product_id}</div>
                            </td>
                            <td className="p-4 text-text-secondary">{item.category}</td>
                            <td className="p-4 text-center">
                                <span className={cn(
                                    "font-bold text-lg",
                                    item.current_stock <= item.min_stock_level ? "text-danger" : "text-text-primary"
                                )}>
                                    {item.current_stock.toLocaleString()}
                                </span>
                                <span className="text-xs text-text-muted ml-1">units</span>
                            </td>
                            <td className="p-4 text-center text-sm text-text-muted">
                                {item.min_stock_level} / {item.max_stock_level}
                            </td>
                            <td className="p-4 text-right font-mono text-text-primary">
                                ${item.unit_price.toFixed(2)}
                            </td>
                            <td className="p-4 flex justify-center">
                                <StatusBadge status={item.status} />
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
