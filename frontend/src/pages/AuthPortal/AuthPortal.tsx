import React from 'react';
import Icon from '../../components/Icon';
import PremiumBackground from '../../components/PremiumBackground';
import KIKILogo from '../../assets/branding/logo';

/**
 * AUTH PORTAL - ENTRY POINT CHOOSER
 * Upgraded to Primary Enterprise Orange Theme.
 */
const AuthPortal: React.FC = () => {
    const handleNavigate = (path: string) => {
        window.history.pushState({}, '', path);
        window.dispatchEvent(new PopStateEvent('popstate'));
    };

    return (
        <PremiumBackground>
            <div className="z-10 w-full max-w-2xl p-6 flex flex-col items-center animate-in fade-in zoom-in-[0.98] duration-700">
                {/* Header Branding */}
                <div className="text-center mb-10">
                    <div className="flex items-center justify-center gap-3 mb-3 scale-90">
                        <div className="w-12 h-12 rounded-[14px] bg-[#FFF3E8] border border-[#FED7AA] shadow-[0_12px_28px_rgba(249,115,22,0.15)] flex items-center justify-center overflow-hidden">
                            <img
                                src={KIKILogo}
                                alt="KIKI logo"
                                className="w-10 h-10 object-contain drop-shadow-[0_2px_4px_rgba(249,115,22,0.15)]"
                            />
                        </div>
                        <h1 className="text-5xl font-black text-[#111827] tracking-widest">
                            KIKI
                        </h1>
                    </div>
                    <p className="text-[10px] font-black text-[#EA580C] uppercase tracking-[0.5em] leading-none">
                        Advanced Accounting
                    </p>
                </div>

                {/* Portal Cards Container */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 w-full mb-8">
                    {/* Master Admin Portal */}
                    <button
                        onClick={() => handleNavigate('/master/login')}
                        className="group relative rounded-[16px] border border-white/15 bg-[#FFF6EE]/92 backdrop-blur-xl hover:translate-y-[-2px] shadow-[0_12px_32px_rgba(15,23,42,0.08)] hover:shadow-[0_24px_64px_rgba(15,23,42,0.12)] active:scale-[0.98] focus:outline-none transition-all duration-300 overflow-hidden"
                    >
                        <div className="p-8 flex flex-col items-center text-center w-full h-full">
                            <div className="w-16 h-16 rounded-2xl bg-[#FFF7ED] flex items-center justify-center mb-6 border border-[#FED7AA] group-hover:bg-[#F97316] group-hover:text-white transition-all duration-300">
                                <Icon name="users" className="w-8 h-8 text-[#F97316] group-hover:text-white transition-colors" />
                            </div>
                            <h2 className="text-xl font-black text-[#111827] tracking-tight mb-2 uppercase">
                                Master Admin
                            </h2>
                            <p className="text-[11px] font-bold text-[#6B7280] leading-relaxed max-w-[180px] uppercase tracking-wider">
                                Global Platform Control
                            </p>
                        </div>
                    </button>

                    {/* Client Login Portal */}
                    <button
                        onClick={() => handleNavigate('/login')}
                        className="group relative rounded-[16px] border border-white/15 bg-[#FFF6EE]/92 backdrop-blur-xl hover:translate-y-[-2px] shadow-[0_12px_32px_rgba(15,23,42,0.08)] hover:shadow-[0_24px_64px_rgba(15,23,42,0.12)] active:scale-[0.98] focus:outline-none transition-all duration-300 overflow-hidden"
                    >
                        <div className="p-8 flex flex-col items-center text-center w-full h-full">
                            <div className="w-16 h-16 rounded-2xl bg-[#FFF7ED] flex items-center justify-center mb-6 border border-[#FED7AA] group-hover:bg-[#F97316] group-hover:text-white transition-all duration-300">
                                <Icon name="ledger" className="w-8 h-8 text-[#F97316] group-hover:text-white transition-colors" />
                            </div>
                            <h2 className="text-xl font-black text-[#111827] tracking-tight mb-2 uppercase">
                                Business Login
                            </h2>
                            <p className="text-[11px] font-bold text-[#6B7280] leading-relaxed max-w-[180px] uppercase tracking-wider">
                                Secure Branch Access
                            </p>
                        </div>
                    </button>
                </div>

                <button
                    onClick={() => handleNavigate('/register')}
                    className="group relative w-full rounded-[16px] border border-white/15 bg-[#FFF6EE]/92 backdrop-blur-xl hover:translate-y-[-2px] shadow-[0_12px_32px_rgba(15,23,42,0.08)] hover:shadow-[0_24px_64px_rgba(15,23,42,0.12)] active:scale-[0.98] focus:outline-none transition-all duration-300 overflow-hidden"
                >
                    <div className="bg-[#FFF6EE]/85 backdrop-blur-md rounded-[14.5px] py-6 px-10 flex flex-col items-center text-center w-full h-full">
                        <span className="text-[9px] font-black text-[#6B7280] uppercase tracking-[0.4em] mb-1">
                            New Organization?
                        </span>
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-[#F97316] uppercase tracking-[0.3em]">
                                Register Platform Account
                            </span>
                            <Icon name="arrow-right" className="w-4 h-4 text-[#F97316] group-hover:translate-x-1 transition-transform" />
                        </div>
                    </div>
                </button>

                {/* Landing Page Link */}
                <button
                    onClick={() => window.location.href = (import.meta as any).env?.VITE_LANDING_URL || 'http://localhost:3000'}
                    className="mt-8 text-[10px] font-black text-[#6B7280] uppercase tracking-[0.3em] hover:text-[#F97316] transition-all flex items-center gap-2 group"
                >
                    <Icon name="arrow-left" size={14} className="group-hover:-translate-x-1 transition-transform" />
                    Back to Home
                </button>
            </div>
        </PremiumBackground>
    );
};

export default AuthPortal;
