import React, { useState } from 'react';
import { apiService } from '../../services';
import Icon from '../../components/Icon';
import FinpixeLogo from '../../assets/finpixe_with_empty_bg.png';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Sparkles, ShieldCheck, Zap, Lock, ArrowRight, ShieldAlert, ArrowLeft, KeyRound } from 'lucide-react';

interface MasterLoginPageProps {
    /** Called on successful authentication — passes the API response */
    onLogin: (data: any) => void;
}

const MasterLoginPage: React.FC<MasterLoginPageProps> = ({ onLogin }) => {
    const [email, setEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    const [view, setView] = useState<'login' | 'forgot' | 'otp' | 'reset_password' | 'success'>('login');
    const [otp, setOtp] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (view === 'forgot') {
            if (!email.trim()) {
                setError('Email is required to reset password.');
                return;
            }
            setLoading(true);
            try {
                await apiService.masterRequestResetOTP(email);
                setView('otp');
            } catch (err: any) {
                setError(err?.response?.data?.message || err?.message || 'Failed to send OTP.');
            } finally {
                setLoading(false);
            }
            return;
        }

        if (view === 'otp') {
            if (!otp.trim()) {
                setError('OTP is required.');
                return;
            }
            setLoading(true);
            try {
                await apiService.masterVerifyOTPOnly(email, otp);
                setView('reset_password');
            } catch (err: any) {
                setError(err?.response?.data?.message || err?.message || 'Invalid OTP.');
            } finally {
                setLoading(false);
            }
            return;
        }

        if (view === 'reset_password') {
            if (!newPassword) {
                setError('New password is required.');
                return;
            }
            setLoading(true);
            try {
                await apiService.masterResetPassword({ email, otp, new_password: newPassword });
                setView('success');
            } catch (err: any) {
                setError(err?.response?.data?.message || err?.message || 'Failed to update password.');
            } finally {
                setLoading(false);
            }
            return;
        }

        if (!email.trim() || !username.trim() || !password) {
            setError('All fields are required.');
            return;
        }

        setLoading(true);
        try {
            const data = await apiService.masterLogin(email, username, password);
            if (!data) throw new Error('Invalid response from server.');
            onLogin(data);
        } catch (err: any) {
            const errorData = err?.data || err?.response?.data || err;
            const msg = errorData?.message || errorData?.detail || err?.message || 'Authentication failed.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleNavigate = (path: string) => {
        window.history.pushState({}, '', path);
        window.dispatchEvent(new PopStateEvent('popstate'));
    };

    return (        <div className="min-h-screen w-full flex bg-[#EEF2FF] overflow-hidden text-slate-900 font-sans">
            {/* Left Hero Graphic Section (Desktop >= 1024px) - Light Orange Theme */}
            <div className="hidden lg:flex flex-1 flex-col justify-between p-12 relative bg-gradient-to-br from-white via-[#EEF2FF] to-[#E0E7FF] border-r border-indigo-100">
                
                {/* ── LAYER 2: Abstract AI Circuit SVG ──────────────────────── */}
                <svg
                    className="absolute inset-0 w-full h-full pointer-events-none z-[1] opacity-70"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 800 900"
                    preserveAspectRatio="xMidYMid slice"
                    aria-hidden="true"
                >
                    <defs>
                        <radialGradient id="signalGrad" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#818CF8" stopOpacity="1" />
                            <stop offset="100%" stopColor="#818CF8" stopOpacity="0" />
                        </radialGradient>
                        <filter id="nodeGlow" x="-80%" y="-80%" width="260%" height="260%">
                            <feGaussianBlur stdDeviation="3" result="blur" />
                            <feMerge>
                                <feMergeNode in="blur" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>

                    {/* Circuit Paths */}
                    <g stroke="rgba(99, 102, 241,0.2)" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round">
                        {/* Top-Left */}
                        <path d="M 60 80 L 200 80 L 200 160 L 340 160" />
                        <path d="M 60 160 L 120 160 L 120 240 L 340 240 L 340 300" />
                        <path d="M 200 80 L 200 40 L 400 40" />
                        <path d="M 120 240 L 120 340 L 280 340" />
                        <path d="M 40 300 L 180 300 L 180 380 L 320 380" />
                        <path d="M 340 160 L 440 160 L 440 100 L 520 100" />
                        <path d="M 340 240 L 420 240" />
                        <path d="M 280 340 L 360 340 L 360 420 L 440 420" />
                        
                        {/* Bottom-Left */}
                        <path d="M 60 820 L 200 820 L 200 740 L 340 740" />
                        <path d="M 60 720 L 160 720 L 160 640 L 300 640" />
                        <path d="M 200 740 L 200 680 L 400 680" />
                        <path d="M 300 640 L 380 640 L 380 560 L 460 560" />
                        <path d="M 160 640 L 160 540 L 280 540 L 280 480" />
                        <path d="M 400 680 L 480 680 L 480 600" />
                        <path d="M 280 480 L 380 480 L 380 420" />

                        {/* Top-Right (Shifted x-630) */}
                        <path d="M 750 60 L 610 60 L 610 140 L 470 140" />
                        <path d="M 750 160 L 670 160 L 670 240 L 530 240 L 530 300" />
                        <path d="M 610 60 L 610 20 L 410 20" />
                        <path d="M 470 140 L 390 140 L 390 220 L 310 220" />
                        <path d="M 530 300 L 450 300 L 450 380" />
                        <path d="M 670 240 L 670 320 L 570 320" />

                        {/* Bottom-Right (Shifted x-630) */}
                        <path d="M 750 820 L 610 820 L 610 740 L 470 740" />
                        <path d="M 750 720 L 650 720 L 650 640 L 510 640" />
                        <path d="M 650 640 L 650 560 L 550 560" />

                        {/* Connectors */}
                        <path d="M 520 100 L 600 100 L 600 180" />
                        <path d="M 440 420 L 520 420 L 520 500 L 600 500" />
                        <path d="M 480 600 L 560 600 L 560 520" />
                    </g>

                    {/* Glowing Junction Nodes with pulses */}
                    <g fill="rgba(99, 102, 241,0.55)" filter="url(#nodeGlow)">
                        {/* Top-Left */}
                        <rect x="196" y="76" width="8" height="8" rx="2" className="node-pulse-1" />
                        <rect x="116" y="236" width="8" height="8" rx="2" className="node-pulse-2" />
                        <rect x="336" y="156" width="8" height="8" rx="2" className="node-pulse-3" />
                        <circle cx="340" cy="300" r="4" className="node-pulse-1" />
                        <circle cx="440" cy="160" r="4" className="node-pulse-4" />
                        <rect x="276" y="336" width="8" height="8" rx="2" className="node-pulse-2" />

                        {/* Bottom-Left */}
                        <rect x="196" y="736" width="8" height="8" rx="2" className="node-pulse-2" />
                        <rect x="296" y="636" width="8" height="8" rx="2" className="node-pulse-4" />
                        <circle cx="160" cy="640" r="4" className="node-pulse-1" />
                        <rect x="276" y="476" width="8" height="8" rx="2" className="node-pulse-3" />
                        <circle cx="480" cy="600" r="4" className="node-pulse-2" />

                        {/* Top-Right (Shifted x-630) */}
                        <rect x="606" y="56" width="8" height="8" rx="2" className="node-pulse-3" />
                        <rect x="466" y="136" width="8" height="8" rx="2" className="node-pulse-1" />
                        <rect x="526" y="236" width="8" height="8" rx="2" className="node-pulse-4" />
                        <circle cx="450" cy="380" r="4" className="node-pulse-3" />

                        {/* Bottom-Right (Shifted x-630) */}
                        <rect x="606" y="736" width="8" height="8" rx="2" className="node-pulse-4" />
                        <rect x="466" y="736" width="8" height="8" rx="2" className="node-pulse-1" />
                        <circle cx="270" cy="660" r="4" className="node-pulse-3" />
                    </g>

                    {/* ── SIGNAL PULSES (animated dots along paths) ──────────── */}
                    {/* Top-Left */}
                    <circle r="3" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="6s"
                            repeatCount="indefinite"
                            path="M 60 80 L 200 80 L 200 160 L 340 160"
                            calcMode="linear"
                        />
                    </circle>
                    <circle r="3.5" fill="#4F46E5" opacity="0.9" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="8s"
                            repeatCount="indefinite"
                            path="M 60 160 L 120 160 L 120 240 L 340 240 L 340 300"
                            calcMode="linear"
                        />
                    </circle>
                    
                    {/* Bottom-Left */}
                    <circle r="4" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="7s"
                            repeatCount="indefinite"
                            path="M 120 240 L 120 340 L 280 340"
                            calcMode="linear"
                        />
                    </circle>
                    <circle r="3" fill="#4F46E5" opacity="0.8" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="9s"
                            repeatCount="indefinite"
                            path="M 40 300 L 180 300 L 180 380 L 320 380"
                            calcMode="linear"
                        />
                    </circle>

                    {/* Top-Right Shifted */}
                    <circle r="3" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="8s"
                            repeatCount="indefinite"
                            path="M 750 60 L 610 60 L 610 140 L 470 140"
                            calcMode="linear"
                        />
                    </circle>
                    <circle r="3.5" fill="#4F46E5" opacity="0.9" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="10s"
                            repeatCount="indefinite"
                            path="M 750 160 L 670 160 L 670 240 L 530 240 L 530 300"
                            calcMode="linear"
                        />
                    </circle>

                    {/* Bottom-Right Shifted */}
                    <circle r="3" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="9s"
                            repeatCount="indefinite"
                            path="M 750 820 L 610 820 L 610 740 L 470 740"
                            calcMode="linear"
                        />
                    </circle>
                    <circle r="4" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                        <animateMotion
                            dur="11s"
                            repeatCount="indefinite"
                            path="M 750 720 L 650 720 L 650 640 L 510 640"
                            calcMode="linear"
                        />
                    </circle>
                </svg>

                <style>{`
                    .node-pulse-1 { animation: nodePulse 4s ease-in-out infinite; }
                    .node-pulse-2 { animation: nodePulse 4s ease-in-out infinite 1s; }
                    .node-pulse-3 { animation: nodePulse 4s ease-in-out infinite 2s; }
                    .node-pulse-4 { animation: nodePulse 4s ease-in-out infinite 3s; }

                    @keyframes nodePulse {
                        0%, 100% { fill: rgba(99, 102, 241,0.4); filter: drop-shadow(0 0 2px rgba(99, 102, 241,0.4)); }
                        50% { fill: rgba(99, 102, 241,0.95); filter: drop-shadow(0 0 8px rgba(99, 102, 241,0.95)); }
                    }
                `}</style>

                {/* Top Brand Header */}
                <div className="flex items-center gap-3.5 z-10 text-left">
                    <div className="w-24 h-24 flex items-center justify-center">
                        <img src={FinpixeLogo} alt="Finpixe logo" className="w-full h-full object-contain" />
                    </div>
                    <div>
                        <h2 className="text-4xl font-extrabold text-slate-900 tracking-widest leading-none">FINPIXE</h2>
                    </div>
                </div>

                {/* Center Value Proposition */}
                <div className="my-auto max-w-xl z-10 space-y-6 text-left">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-100/50 border border-indigo-200/60 text-indigo-800 text-xs font-semibold">
                        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                        <span>AI-Powered Continuous Accounting & Compliance</span>
                    </div>
                    <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
                        Next-Generation Intelligent Financial Operating System
                    </h1>
                    <p className="text-sm text-slate-600 font-medium leading-relaxed">
                        Automate GST reconciliation, OCR voucher extraction, and real-time ledger intelligence with enterprise bank-grade security.
                    </p>

                    {/* Security Feature Highlights */}
                    <div className="grid grid-cols-2 gap-4 pt-4">
                        <div className="p-4 rounded-xl bg-white/80 border border-indigo-100 flex items-center gap-3 shadow-xs">
                            <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0" />
                            <div>
                                <h4 className="text-xs font-bold text-slate-800">ISO & GST Compliance</h4>
                                <p className="text-[10px] text-slate-500">Automated GSTR-2B matching</p>
                            </div>
                        </div>
                        <div className="p-4 rounded-xl bg-white/80 border border-indigo-100 flex items-center gap-3 shadow-xs">
                            <Zap className="w-5 h-5 text-indigo-600 shrink-0" />
                            <div>
                                <h4 className="text-xs font-bold text-slate-800">Real-Time OCR Stream</h4>
                                <p className="text-[10px] text-slate-500">Gemini AI document pipeline</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer Security Badges */}
                <div className="flex items-center justify-between text-xs text-slate-500 font-medium z-10 border-t border-indigo-100 pt-6">
                    <div className="flex items-center gap-2">
                        <Lock className="w-4 h-4 text-indigo-600" />
                        <span>256-bit SSL Encrypted Session</span>
                    </div>
                    <span>v2.0 Enterprise Release</span>
                </div>
            </div>

            {/* Right Authentication Form Workspace */}
            <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12 bg-white text-slate-900">
                <div className="w-full max-w-md space-y-8 text-left">
                    {/* Header */}
                    <div className="space-y-2">
                        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold">
                            <ShieldAlert className="w-3.5 h-3.5" />
                            <span>{view === 'login' ? 'Master Admin Control' : 'Account Recovery'}</span>
                        </div>
                        <h2 className="text-3xl font-extrabold tracking-tight text-slate-900">
                            {view === 'login' ? 'Sign in to Console' : 'Recover Account'}
                        </h2>
                        <p className="text-xs font-medium text-slate-500">
                            {view === 'login' ? 'Enter administrative credentials to manage ERP tenants and global configs.' : 'Recover your platform root credentials safely.'}
                        </p>
                    </div>

                    {/* View States */}
                    {view === 'success' ? (
                        <div className="w-full text-center space-y-4 py-4 animate-in fade-in slide-in-from-bottom-2">
                            <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <ShieldCheck className="w-6 h-6" />
                            </div>
                            <h3 className="text-sm font-black text-slate-900 tracking-widest uppercase">Password Reset</h3>
                            <p className="text-xs font-semibold text-slate-500">
                                Your password has been successfully reset!
                            </p>
                            <Button
                                type="button"
                                variant="primary"
                                onClick={() => { setView('login'); setPassword(''); setNewPassword(''); setOtp(''); }}
                                className="w-full h-12 text-xs font-bold uppercase tracking-wider mt-4"
                            >
                                Back to Login
                            </Button>
                        </div>
                    ) : (
                        <form className="space-y-5" onSubmit={handleSubmit} noValidate>
                            {error && (
                                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-semibold flex items-center gap-2 animate-in fade-in">
                                    <Icon name="x" size={16} />
                                    <span>{error}</span>
                                </div>
                            )}

                            {view === 'otp' && (
                                <div className="space-y-4">
                                    <div className="text-center p-4 bg-slate-50 rounded-2xl border border-slate-200">
                                        <KeyRound className="w-8 h-8 text-[#6366F1] mx-auto mb-2" />
                                        <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">
                                            OTP sent to {email}
                                        </p>
                                    </div>

                                    <Input
                                        label="6-Digit OTP"
                                        type="text"
                                        maxLength={6}
                                        placeholder="••••••"
                                        value={otp}
                                        onChange={e => setOtp(e.target.value)}
                                        className="text-center tracking-[0.5em] text-lg font-bold"
                                        required
                                        autoFocus
                                    />
                                </div>
                            )}

                            {view === 'reset_password' && (
                                <div className="space-y-4">
                                    <Input
                                        label="New Password"
                                        type={showPassword ? 'text' : 'password'}
                                        placeholder="••••••••"
                                        value={newPassword}
                                        onChange={e => setNewPassword(e.target.value)}
                                        required
                                        autoFocus
                                        rightIcon={
                                            <button
                                                type="button"
                                                className="text-slate-400 hover:text-[#6366F1] transition-colors"
                                                onClick={() => setShowPassword(!showPassword)}
                                            >
                                                <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
                                            </button>
                                        }
                                    />
                                </div>
                            )}

                            {(view === 'login' || view === 'forgot') && (
                                <div className="space-y-4">
                                    <Input
                                        label="Admin Email Address"
                                        type="email"
                                        placeholder="admin@platform.com"
                                        value={email}
                                        onChange={e => setEmail(e.target.value)}
                                        required
                                        autoFocus
                                    />

                                    {view === 'login' && (
                                        <>
                                            <Input
                                                label="Username"
                                                type="text"
                                                placeholder="master_root"
                                                value={username}
                                                onChange={e => setUsername(e.target.value)}
                                                required
                                            />

                                            <div className="space-y-1.5 w-full">
                                                <div className="flex justify-between items-center ml-0.5">
                                                    <label className="erp-label">Password</label>
                                                    <button
                                                        type="button"
                                                        onClick={() => setView('forgot')}
                                                        className="text-[10px] font-bold text-indigo-600 uppercase tracking-widest hover:underline"
                                                    >
                                                        Forgot?
                                                    </button>
                                                </div>
                                                <div className="relative flex items-center w-full">
                                                    <input
                                                        type={showPassword ? 'text' : 'password'}
                                                        className="erp-input pr-10 w-full"
                                                        placeholder="••••••••"
                                                        value={password}
                                                        onChange={e => setPassword(e.target.value)}
                                                        required
                                                    />
                                                    <button
                                                        type="button"
                                                        className="absolute right-3.5 text-slate-400 hover:text-[#6366F1] transition-colors"
                                                        onClick={() => setShowPassword(!showPassword)}
                                                    >
                                                        <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
                                                    </button>
                                                </div>
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}

                            <Button
                                type="submit"
                                variant="primary"
                                isLoading={loading}
                                className="w-full text-xs font-bold uppercase tracking-wider h-12"
                            >
                                <span>{view === 'login' ? 'Enter Admin Console' : view === 'otp' ? 'Validate OTP' : view === 'reset_password' ? 'Update Password' : 'Request OTP'}</span>
                                <ArrowRight className="w-4 h-4 ml-2" />
                            </Button>

                            {view === 'forgot' && (
                                <button
                                    type="button"
                                    onClick={() => setView('login')}
                                    className="w-full text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-[#6366F1] transition-colors mt-3"
                                >
                                    Return to Login
                                </button>
                            )}
                            {view === 'otp' && (
                                <button
                                    type="button"
                                    onClick={() => setView('forgot')}
                                    className="w-full text-center text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-[#6366F1] transition-colors mt-3"
                                >
                                    Cancel & Go Back
                                </button>
                            )}
                        </form>
                    )}

                    <div className="pt-6 border-t border-slate-100 flex flex-col gap-3">
                        <button
                            onClick={() => handleNavigate('/auth')}
                            className="w-full h-12 rounded-xl bg-slate-50 border border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-widest hover:bg-slate-100 hover:text-indigo-600 transition-all flex items-center justify-center gap-2"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Back to Portal Selection
                        </button>

                        <p className="text-center text-slate-400 text-[8px] font-bold uppercase tracking-widest opacity-40">
                            Authorized Personnel Only — Access is Monitored.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MasterLoginPage;



