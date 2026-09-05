import React, { useState, useRef } from 'react';
import { apiService } from '../../services';
import Icon from '../../components/Icon';
import FinpixeLogo from '../../assets/finpixe_with_empty_bg.png';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Sparkles, ShieldCheck, Zap, Lock, ArrowRight, Building2, Eye, EyeOff } from 'lucide-react';

interface LoginPageProps {
    onLogin: (payload: any) => void;
    onSwitchToSignup: () => void;
    onForgotPassword: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin, onSwitchToSignup, onForgotPassword }) => {
    const [branchEmail, setBranchEmail] = useState('');
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    const usernameRef = useRef<HTMLInputElement>(null);
    const passwordRef = useRef<HTMLInputElement>(null);

    const [fieldErrors, setFieldErrors] = useState<{ email?: string; username?: string; password?: string }>({});
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const validate = () => {
        const errors: { email?: string; username?: string; password?: string } = {};
        if (!branchEmail) errors.email = 'Branch email is required.';
        else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(branchEmail)) errors.email = 'Enter a valid email address.';
        if (!username) errors.username = 'Username is required.';
        if (!password) errors.password = 'Password is required.';
        setFieldErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!validate()) return;

        setLoading(true);
        try {
            const data = await apiService.login(branchEmail, username, password);
            if (!data) throw new Error('Invalid response.');

            if (data.user?.tenant_id || data.user?.tenantId) {
                const tid = data.user.tenant_id ?? data.user.tenantId;
                sessionStorage.setItem('tenantId', tid);
            }
            if (data.user?.company_name) {
                sessionStorage.setItem('companyName', data.user.company_name);
            }

            onLogin(data);
        } catch (err: any) {
            const errorData = err?.data || err?.response?.data || err;
            const msg = errorData?.message || errorData?.detail || err?.message || 'Authentication failed.';
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleBackToPortal = () => {
        window.history.pushState({}, '', '/auth');
        window.dispatchEvent(new PopStateEvent('popstate'));
    };

    return (
        <div className="min-h-screen w-full flex bg-[#EEF2FF] overflow-hidden text-slate-900 font-sans">
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
                <div className="flex items-center gap-3.5 z-10">
                    <div className="w-24 h-24 flex items-center justify-center">
                        <img src={FinpixeLogo} alt="Finpixe logo" className="w-full h-full object-contain" />
                    </div>
                    <div>
                        <h2 className="text-4xl font-extrabold text-slate-900 tracking-widest leading-none">FINPIXE</h2>
                    </div>
                </div>

                {/* Center Value Proposition */}
                <div className="my-auto max-w-xl z-10 space-y-6">
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
                <div className="w-full max-w-md space-y-8">
                    {/* Header */}
                    <div className="space-y-2">
                        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold">
                            <Building2 className="w-3.5 h-3.5" />
                            <span>Business Branch Access</span>
                        </div>
                        <h2 className="text-3xl font-extrabold tracking-tight text-slate-900">Sign in to workspace</h2>
                        <p className="text-xs font-medium text-slate-500">Enter your branch credentials to access enterprise vouchers and ledgers.</p>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleLogin} className="space-y-5" noValidate>
                        {error && (
                            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-semibold flex items-center gap-2 animate-in fade-in">
                                <Icon name="x" size={16} />
                                <span>{error}</span>
                            </div>
                        )}

                        <Input
                            label="Branch Email Address"
                            type="email"
                            placeholder="branch@company.com"
                            value={branchEmail}
                            onChange={e => { setBranchEmail(e.target.value); setFieldErrors(p => ({ ...p, email: undefined })); }}
                            onKeyDown={e => {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    usernameRef.current?.focus();
                                }
                            }}
                            error={fieldErrors.email}
                            autoFocus
                        />

                        <Input
                            label="Username"
                            type="text"
                            placeholder="Your username"
                            value={username}
                            onChange={e => { setUsername(e.target.value); setFieldErrors(p => ({ ...p, username: undefined })); }}
                            ref={usernameRef}
                            onKeyDown={e => {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    passwordRef.current?.focus();
                                }
                            }}
                            error={fieldErrors.username}
                        />

                        <Input
                            label="Password"
                            type={showPassword ? 'text' : 'password'}
                            placeholder="••••••••"
                            value={password}
                            onChange={e => { setPassword(e.target.value); setFieldErrors(p => ({ ...p, password: undefined })); }}
                            ref={passwordRef}
                            error={fieldErrors.password}
                            rightIcon={
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="text-slate-400 hover:text-slate-600 transition-colors focus:outline-none cursor-pointer"
                                >
                                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            }
                        />

                        <Button
                            type="submit"
                            variant="primary"
                            size="md"
                            isLoading={loading}
                            className="w-full text-xs font-bold uppercase tracking-wider"
                        >
                            <span>Sign in to Enterprise Workspace</span>
                            <ArrowRight className="w-4 h-4 ml-2" />
                        </Button>
                    </form>

                    {/* Navigation Links */}
                    <div className="space-y-3 border-t border-slate-100 pt-6">
                        <button
                            type="button"
                            onClick={handleBackToPortal}
                            className="w-full py-2.5 px-4 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-700 transition-colors flex items-center justify-center gap-2"
                        >
                            <Icon name="arrow-left" size={14} />
                            <span>Return to Portal Selection</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => window.location.href = (import.meta as any).env?.VITE_LANDING_URL || 'http://localhost:3000'}
                            className="w-full text-center text-xs font-semibold text-slate-400 hover:text-[#4F46E5] transition-colors"
                        >
                            Return to Main Website
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;



