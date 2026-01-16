'use client'

import Sidebar from './Sidebar'
import { usePathname } from 'next/navigation'

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const pathname = usePathname()

    // Pages that don't need sidebar
    const isLoginPage = pathname === '/login' || pathname === '/'

    // Don't render sidebar on login page
    if (isLoginPage) return <>{children}</>

    return (
        <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 overflow-y-auto h-screen">
                <div className="max-w-[1920px] mx-auto p-6 md:p-8">
                    {children}
                </div>
            </main>
        </div>
    )
}

