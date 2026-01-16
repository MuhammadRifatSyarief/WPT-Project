'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { useDashboardFiltersStore } from '@/lib/store';

export default function FilterGroups() {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Global Filter State
    const { selectedGroups, setSelectedGroups } = useDashboardFiltersStore();

    // Fetch Groups
    const { data: groupsData } = useQuery<{ groups: string[] }>({
        queryKey: ['product-groups'],
        queryFn: async () => (await api.get('/dashboard/groups')).data,
    });

    const groups = groupsData?.groups || [];

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const toggleGroup = (group: string) => {
        if (selectedGroups.includes(group)) {
            setSelectedGroups(selectedGroups.filter(g => g !== group));
        } else {
            setSelectedGroups([...selectedGroups, group]);
        }
    };

    const selectAll = () => setSelectedGroups(groups);
    const clearAll = () => setSelectedGroups([]);

    return (
        <div className="relative z-[100]" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`neu-btn-secondary flex items-center gap-2 text-xs py-2 px-3 ${selectedGroups.length > 0 ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]' : ''}`}
            >
                <span>🌪️ Filter</span>
                <span className="font-bold">
                    {selectedGroups.length === 0 ? 'All Groups' : `${selectedGroups.length} Selected`}
                </span>
                <span className="text-[10px]">{isOpen ? '▲' : '▼'}</span>
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-64 neu-card z-[999] p-3 shadow-2xl animate-in fade-in slide-in-from-top-2" style={{ boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}>
                    <div className="flex justify-between mb-3 text-xs border-b border-[var(--border-visible)] pb-2">
                        <button onClick={selectAll} className="text-[var(--accent-primary)] hover:underline">Select All</button>
                        <button onClick={clearAll} className="text-[var(--text-muted)] hover:text-[var(--error)]">Clear</button>
                    </div>

                    <div className="max-h-60 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
                        {groups.map(group => (
                            <div
                                key={group}
                                onClick={() => toggleGroup(group)}
                                className={`
                                    cursor-pointer px-2 py-1.5 rounded flex items-center justify-between text-xs transition-colors
                                    ${selectedGroups.includes(group) ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)]' : 'text-[var(--text-muted)] hover:bg-[rgba(255,255,255,0.05)]'}
                                `}
                            >
                                <span>{group}</span>
                                {selectedGroups.includes(group) && <span className="text-[var(--success)]">✓</span>}
                            </div>
                        ))}
                        {groups.length === 0 && <div className="text-xs text-[var(--text-dim)] text-center py-2">Loading groups...</div>}
                    </div>
                </div>
            )}
        </div>
    );
}
