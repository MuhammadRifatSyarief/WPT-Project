'use client';

import { useState, useRef, useEffect } from 'react';
import { useDashboardFiltersStore } from '@/lib/store';

const ABC_CLASSES = ['A', 'B', 'C'];

export default function FilterABC() {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Global Filter State
    const { selectedABC, setSelectedABC } = useDashboardFiltersStore();

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

    const toggleClass = (abc: string) => {
        if (selectedABC.includes(abc)) {
            setSelectedABC(selectedABC.filter(c => c !== abc));
        } else {
            setSelectedABC([...selectedABC, abc]);
        }
    };

    return (
        <div className="relative z-[100]" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`neu-btn-secondary flex items-center gap-2 text-xs py-2 px-3 ${selectedABC.length > 0 ? 'border-[var(--accent-primary)] text-[var(--accent-primary)]' : ''}`}
            >
                <span>📊 Class</span>
                <span className="font-bold">
                    {selectedABC.length === 0 ? 'All' : selectedABC.join(', ')}
                </span>
                <span className="text-[10px]">{isOpen ? '▲' : '▼'}</span>
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-32 neu-card z-[999] p-2 shadow-2xl animate-in fade-in slide-in-from-top-2" style={{ boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)' }}>
                    <div className="space-y-1">
                        {ABC_CLASSES.map(cls => (
                            <div
                                key={cls}
                                onClick={() => toggleClass(cls)}
                                className={`
                                    cursor-pointer px-2 py-1.5 rounded flex items-center justify-between text-xs transition-colors
                                    ${selectedABC.includes(cls) ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)]' : 'text-[var(--text-muted)] hover:bg-[rgba(255,255,255,0.05)]'}
                                `}
                            >
                                <span>Class {cls}</span>
                                {selectedABC.includes(cls) && <span className="text-[var(--success)]">✓</span>}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
