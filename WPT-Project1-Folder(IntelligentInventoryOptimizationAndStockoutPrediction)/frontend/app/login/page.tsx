'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import api from '@/lib/api';

const features = [
    { icon: '🏠', title: 'Dashboard', detail: 'Real-time inventory metrics, KPIs, service levels, turnover ratios, and comprehensive visual analytics dashboard.' },
    { icon: '📈', title: 'Forecasting', detail: 'Machine learning demand prediction.' },
    { icon: '📊', title: 'Health', detail: 'Inventory health scores & ABC analysis.' },
    { icon: '⚠️', title: 'Stockout', detail: 'Early warning stockout risk alerts.' },
    { icon: '🔄', title: 'Reorder', detail: 'Smart Reorder Point & Safety Stock optimization.' },
    { icon: '📋', title: 'Slow-Moving', detail: 'Dead stock identification & analysis.' },
    { icon: '👥', title: 'RFM', detail: 'Recency, Frequency, Monetary segmentation.' },
    { icon: '🛒', title: 'MBA', detail: 'Market Basket Analysis associations.' },
];

const benefits = [
    { icon: '🔒', title: 'Secure Authentication', desc: 'Role-based access control with encrypted credentials' },
    { icon: '📊', title: 'Real-time Analytics', desc: 'Live data synchronization and instant insights' },
    { icon: '🤖', title: 'AI-Powered Predictions', desc: 'Machine learning models for accurate forecasting' },
    { icon: '⚡', title: 'High Performance', desc: 'Optimized for speed and scalability' },
];

export default function LoginPage() {
    const router = useRouter();
    const { setUser, setToken } = useAuthStore();

    const [activeTab, setActiveTab] = useState<'signin' | 'signup'>('signin');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');

    const [newUsername, setNewUsername] = useState('');
    const [newEmail, setNewEmail] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [role, setRole] = useState<'admin' | 'user'>('user');

    const handleSignIn = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            const response = await api.post('/auth/login', { username, password });
            const { access_token, user } = response.data;
            setToken(access_token);
            setUser(user);
            localStorage.setItem('access_token', access_token);
            setSuccess('Login successful! Redirecting...');
            setTimeout(() => router.push('/dashboard'), 1000);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Invalid credentials');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSignUp = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);
        try {
            await api.post('/auth/register', { username: newUsername, email: newEmail, password: newPassword, role });
            setSuccess('Account created! You can now sign in.');
            setActiveTab('signin');
            setUsername(newUsername);
        } catch (err: any) {
            setError(err.response?.data?.error || 'Registration failed');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2 lg:h-screen">

            {/* LEFT COLUMN: Login Form & Highlights */}
            <div className="p-8 lg:p-12 overflow-y-auto bg-[var(--bg-deepest)] flex flex-col justify-center relative">
                <div className="max-w-md mx-auto w-full">

                    <div className="mb-8 animate-slide-up">
                        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2 relative z-10">🔐 Welcome Back</h1>
                        <p className="text-[var(--text-muted)] relative z-10">Sign in to access your inventory intelligence dashboard</p>

                        {/* Ambient Glow */}
                        <div className="absolute top-10 left-10 w-32 h-32 bg-[var(--accent-primary)] rounded-full blur-[80px] opacity-20 animate-pulse"></div>
                        <div className="absolute bottom-10 right-10 w-40 h-40 bg-[var(--accent-secondary)] rounded-full blur-[80px] opacity-20 animate-pulse" style={{ animationDelay: '1s' }}></div>
                    </div>

                    {/* TABS */}
                    <div className="flex gap-2 mb-6 p-1 bg-[var(--bg-elevated)] rounded-xl border border-[var(--border-visible)] animate-slide-up animate-delay-100">
                        <button
                            onClick={() => setActiveTab('signin')}
                            className={`flex-1 py-2 rounded-lg font-medium text-sm transition-all duration-300 ${activeTab === 'signin'
                                ? 'bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white shadow-lg'
                                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                                }`}
                        >
                            Sign In
                        </button>
                        <button
                            onClick={() => setActiveTab('signup')}
                            className={`flex-1 py-2 rounded-lg font-medium text-sm transition-all duration-300 ${activeTab === 'signup'
                                ? 'bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-secondary)] text-white shadow-lg'
                                : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                                }`}
                        >
                            Sign Up
                        </button>
                    </div>

                    {/* MESSAGES */}
                    {error && <div className="p-3 mb-4 rounded-lg bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.2)] text-[#fca5a5] text-sm flex items-center gap-2"><span>❌</span>{error}</div>}
                    {success && <div className="p-3 mb-4 rounded-lg bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.2)] text-[#6ee7b7] text-sm flex items-center gap-2"><span>✅</span>{success}</div>}

                    {/* FORMS */}
                    {activeTab === 'signin' ? (
                        <form onSubmit={handleSignIn} className="space-y-5 animate-slide-up animate-delay-200">
                            <div className="group">
                                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5 uppercase tracking-wide group-focus-within:text-[var(--accent-primary)] transition-colors">Username</label>
                                <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="neu-input" placeholder="admin1" required />
                            </div>
                            <div className="group">
                                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1.5 uppercase tracking-wide group-focus-within:text-[var(--accent-primary)] transition-colors">Password</label>
                                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="neu-input" placeholder="••••••••" required />
                            </div>
                            <button type="submit" disabled={isLoading} className="neu-btn w-full mt-2 hover:scale-[1.02] active:scale-[0.98] transition-all relative overflow-hidden">
                                {isLoading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <span className="animate-spin text-lg">↻</span> Authenticating...
                                    </span>
                                ) : 'Sign In →'}
                            </button>
                        </form>
                    ) : (
                        <form onSubmit={handleSignUp} className="space-y-4 animate-slide-up animate-delay-200">
                            <div className="bg-[rgba(59,130,246,0.1)] p-3 rounded-lg border border-[rgba(59,130,246,0.2)] text-xs text-[#93c5fd] mb-4">
                                <strong>Format:</strong> user/admin + number (e.g., admin2). Password: {`{username}!wahana25`}
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">New Username</label>
                                <input type="text" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} className="neu-input" placeholder="user2" required />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Email</label>
                                <input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} className="neu-input" placeholder="email@domain.com" required />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Password</label>
                                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="neu-input" placeholder="••••••••" required />
                            </div>
                            <div>
                                <label className="block text-xs font-semibold text-[var(--text-secondary)] mb-1">Role</label>
                                <select value={role} onChange={(e) => setRole(e.target.value as any)} className="neu-input cursor-pointer">
                                    <option value="user">User</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <button type="submit" disabled={isLoading} className="neu-btn w-full mt-2">Create Account</button>
                        </form>
                    )}

                    {/* BELOW FORM: Highlights & Stats */}
                    <div className="mt-10 pt-8 border-t border-[var(--border-visible)]">
                        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">✨ System Highlights</h3>
                        <div className="grid grid-cols-1 gap-3">
                            {benefits.map((b, i) => (
                                <div key={i} className="flex items-start gap-3 p-2 rounded-lg hover:bg-[var(--bg-elevated)] transition-colors">
                                    <span className="text-xl">{b.icon}</span>
                                    <div>
                                        <div className="text-[var(--text-primary)] font-medium text-sm">{b.title}</div>
                                        <div className="text-[var(--text-dim)] text-xs">{b.desc}</div>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="mt-6 flex gap-4">
                            <div className="bg-[var(--bg-elevated)] p-3 rounded-xl border border-[var(--border-visible)] flex-1 text-center">
                                <div className="text-lg font-bold text-[var(--accent-primary)]">2,136+</div>
                                <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Products</div>
                            </div>
                            <div className="bg-[var(--bg-elevated)] p-3 rounded-xl border border-[var(--border-visible)] flex-1 text-center">
                                <div className="text-lg font-bold text-[var(--accent-secondary)]">8</div>
                                <div className="text-[10px] uppercase tracking-wider text-[var(--text-muted)]">Modules</div>
                            </div>
                        </div>

                        <div className="mt-6">
                            <h4 className="text-xs font-semibold text-[var(--text-muted)] mb-3 uppercase">Tech Stack</h4>
                            <div className="flex flex-wrap gap-2">
                                {['React', 'Next.js', 'Flask', 'PostgreSQL', 'ML/AI', 'Pandas'].map(t => (
                                    <span key={t} className="px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border-visible)] text-[10px] text-[var(--text-secondary)]">{t}</span>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* RIGHT COLUMN: Company Overview (Hidden on Mobile) */}
            <div className="hidden lg:block relative overflow-hidden p-12 border-l border-[var(--border-visible)]">
                {/* Background with Glass Effect */}
                <div className="absolute inset-0 bg-gradient-to-br from-[#0f172a] to-[#1e293b] z-0"></div>

                {/* Animated Gradient Orbs */}
                <div className="absolute top-[-10%] right-[-10%] w-[600px] h-[600px] bg-[var(--accent-primary)] rounded-full blur-[120px] opacity-10 animate-float-fast"></div>
                <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-[var(--accent-secondary)] rounded-full blur-[100px] opacity-10 animate-float-fast" style={{ animationDelay: '2s' }}></div>

                {/* Content Container */}
                <div className="relative z-10 max-w-lg mx-auto h-full flex flex-col justify-center animate-slide-up animate-delay-100">

                    <div className="mb-10">
                        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">🏢 Wahana Piranti Teknologi</h2>
                        <p className="text-[var(--text-muted)]">Indonesia's leading IT & Technology Solutions Distributor</p>
                    </div>

                    <div className="neu-card mb-8 backdrop-blur-md bg-white/5 border-white/10 hover:bg-white/10 transition-colors">
                        <div className="flex items-center gap-4">
                            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center text-2xl shadow-lg shadow-[var(--accent-glow)] relative z-10">
                                📦
                            </div>
                            <div>
                                <div className="text-[var(--text-primary)] font-bold text-lg relative z-10">Inventory Intelligence Hub</div>
                                <div className="text-[var(--text-secondary)] text-sm relative z-10">Comprehensive platform for stock optimization</div>

                                {/* Static Header - Removed Animation */}
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-8">
                        {features.map((f, i) => (
                            <div key={i} className="group p-3 rounded-xl border border-[var(--border-visible)] hover:border-[var(--accent-primary)] hover:bg-[rgba(99,102,241,0.05)] transition-all cursor-default">
                                <div className="flex items-center gap-2 mb-2">
                                    <span>{f.icon}</span>
                                    <span className="text-[var(--text-primary)] font-medium text-sm group-hover:text-[var(--accent-primary)] transition-colors">{f.title}</span>
                                </div>
                                <p className="text-[var(--text-dim)] text-xs leading-relaxed line-clamp-2">{f.detail}</p>
                            </div>
                        ))}
                    </div>

                    <div className="space-y-6 text-sm text-[var(--text-muted)]">
                        <div className="p-4 rounded-xl bg-[var(--bg-deep)] border border-[var(--border-visible)]">
                            <h4 className="text-[var(--text-primary)] font-semibold mb-2 flex items-center gap-2">📖 About Us</h4>
                            <p className="leading-relaxed text-xs">
                                Founded in 2015, Wahana Piranti Teknologi started as a distributor of premium IT solutions within Jakarta. Through professionalism and customer focus, Wahana has been entrusted by international brands seeking to expand in Indonesia.
                            </p>
                        </div>

                        <div className="p-4 rounded-xl bg-[var(--bg-deep)] border border-[var(--border-visible)]">
                            <h4 className="text-[var(--text-primary)] font-semibold mb-2 flex items-center gap-2">🎯 Vision & Mission</h4>
                            <p className="mb-2 text-xs"><strong className="text-[var(--accent-secondary)]">Vision:</strong> To be Indonesia's trusted one-stop distributor for affordable enterprise IT solutions.</p>
                            <p className="text-xs"><strong className="text-[var(--accent-secondary)]">Mission:</strong> Deliver the latest, reliable, and affordable IT solutions for enterprises.</p>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <h5 className="text-[var(--text-primary)] font-semibold text-xs mb-1">📍 Office</h5>
                                <p className="text-[var(--text-dim)] text-xs">
                                    Grand Puri Niaga K6 2M-2L<br />Jl. Puri Kencana, Kembangan<br />Jakarta Barat, 11610
                                </p>
                            </div>
                            <div>
                                <h5 className="text-[var(--text-primary)] font-semibold text-xs mb-1">📞 Contact</h5>
                                <p className="text-[var(--text-dim)] text-xs">
                                    <span className="text-[var(--accent-primary)]">sales@wpteknologi.com</span><br />
                                    021 38771011<br />+62 858 1075 7246
                                </p>
                            </div>
                        </div>
                    </div>

                </div>
            </div>

        </div>
    );
}
