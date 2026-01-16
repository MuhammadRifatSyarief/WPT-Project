import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import DashboardLayout from '@/components/layout/DashboardLayout'
import Providers from '@/components/providers/Providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Inventory Intelligence Hub',
    description: 'PT Wahana Piranti Teknologi',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="dark">
            <body className={inter.className}>
                <Providers>
                    <DashboardLayout>
                        {children}
                    </DashboardLayout>
                </Providers>
            </body>
        </html>
    )
}
