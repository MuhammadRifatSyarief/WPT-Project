'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Filter, Warehouse } from 'lucide-react'
import InventoryTable from '@/components/inventory/InventoryTable'
import { InventoryItem, PaginatedResponse } from '@/types'

export default function InventoryPage() {
    const [page, setPage] = useState(1)
    const [selectedGroup, setSelectedGroup] = useState('All Groups')

    // Fetch Groups List
    const { data: groupsData } = useQuery({
        queryKey: ['groups'],
        queryFn: async () => {
            const res = await api.get('/inventory/groups')
            return res.data
        }
    })

    // Fetch Inventory Data filtered by Group
    const { data, isLoading } = useQuery<PaginatedResponse<InventoryItem>>({
        queryKey: ['inventory', page, selectedGroup],
        queryFn: async () => {
            const res = await api.get('/inventory', {
                params: {
                    page,
                    per_page: 20,
                    group: selectedGroup
                }
            })
            return res.data
        }
    })

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-text-primary">Inventory Data</h1>
                    <p className="text-text-muted mt-1">Filtered View by Product Group (CSV Source)</p>
                </div>
            </div>

            {/* Group Filter Dropdown */}
            <div className="flex gap-4 mb-8">
                <div className="relative min-w-[250px]">
                    <Warehouse className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted" size={20} />
                    <select
                        className="neu-input pl-12 pr-10 appearance-none cursor-pointer w-full"
                        value={selectedGroup}
                        onChange={(e) => {
                            setSelectedGroup(e.target.value)
                            setPage(1)
                        }}
                    >
                        <option value="All Groups">All Groups ({groupsData?.count || 0})</option>
                        {groupsData?.groups?.map((group: string) => (
                            <option key={group} value={group}>{group}</option>
                        ))}
                    </select>
                    {/* Custom Arrow */}
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-text-muted">
                        <Filter size={16} />
                    </div>
                </div>
            </div>

            {/* Main Table */}
            <InventoryTable
                data={data?.items || []}
                isLoading={isLoading}
            />

            {/* Pagination */}
            {data && (
                <div className="flex justify-between items-center text-sm text-text-secondary mt-4">
                    <span>Showing {data.items.length} of {data.total} items</span>
                    <div className="flex gap-2">
                        <button
                            disabled={page === 1}
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            className="px-4 py-2 rounded-lg bg-bg-elevated hover:bg-bg-hover disabled:opacity-50 transition-colors"
                        >
                            Previous
                        </button>
                        <div className="px-4 py-2 bg-bg-deep rounded-lg border border-white/5">
                            Page {page} of {data.pages}
                        </div>
                        <button
                            disabled={page === data.pages}
                            onClick={() => setPage(p => p + 1)}
                            className="px-4 py-2 rounded-lg bg-bg-elevated hover:bg-bg-hover disabled:opacity-50 transition-colors"
                        >
                            Next
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
