import React, { useState, useEffect } from "react";
import { apiService } from "../../services";
import Icon from "../../components/Icon";
import KIKILogo from '../../assets/finpixe_with_empty_bg.png';
import { Input } from "../../components/ui/Input";
import { Button } from "../../components/ui/Button";
import { Sparkles, ShieldCheck, Zap, Lock, ArrowRight, ArrowLeft, KeyRound, Globe, Check, Eye, EyeOff } from "lucide-react";

interface SignupPageProps {
  onSwitchToLogin: () => void;
  onBack?: () => void;
}

const SignupPage: React.FC<SignupPageProps> = ({ onSwitchToLogin, onBack }) => {
  // Step state: 1: Administrative, 2: Regional, 3: Platform Access
  const [step, setStep] = useState(1);
  
  // Geograhpical Data logic
  const [geoData, setGeoData] = useState<any[]>([]);
  
  // Form state - Step 1
  const [name, setName] = useState('');
  const [pan, setPan] = useState('');
  const [phone, setPhone] = useState('');

  // Form state - Step 2
  const [addressLine1, setAddressLine1] = useState('');
  const [addressLine2, setAddressLine2] = useState('');
  const [addressLine3, setAddressLine3] = useState('');
  const [selectedCountry, setSelectedCountry] = useState('India');
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [pincode, setPincode] = useState('');

  // Form state - Step 3
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // UI state
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    fetchGeoData();
  }, []);

  const fetchGeoData = async () => {
    try {
      const resp = await fetch('/data/geo.json');
      const data = await resp.json();
      setGeoData(data);
    } catch (err) {
      console.error("Failed to fetch geo data", err);
    }
  };

  const validateStep = () => {
    setError('');
    if (step === 1) {
      if (!name || !pan) {
        setError('Please complete all identification fields.');
        return false;
      }
      if (pan.length !== 10) {
        setError('Invalid PAN number. Must be 10 characters.');
        return false;
      }
      if (phone && (phone.length !== 10 || !/^\d+$/.test(phone))) {
        setError('Contact Phone must be 10 digits.');
        return false;
      }
    } else if (step === 2) {
      if (!addressLine1 || !selectedState || !selectedDistrict || !pincode) {
        setError('Please complete the regional context fields.');
        return false;
      }
    }
    return true;
  };

  const nextStep = () => {
    if (validateStep()) setStep(prev => prev + 1);
  };

  const prevStep = () => {
    setError('');
    setStep(prev => prev - 1);
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    setError('');
    setSuccessMessage('');

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        name,
        pan_number: pan,
        username,
        email,
        phone,
        address_line1: addressLine1,
        address_line2: addressLine2,
        address_line3: addressLine3,
        country: selectedCountry,
        state: selectedState,
        district: selectedDistrict,
        pincode: pincode,
        password
      };

      const response = await apiService.masterRegister(payload);

      if (response.access && response.refresh) {
        setSuccessMessage('Master Admin account created successfully! Accessing platform...');
        setTimeout(() => { 
          window.location.href = '/master/dashboard'; 
        }, 1500);
      } else {
        setSuccessMessage('Account created! Redirecting to login...');
        setTimeout(() => { onSwitchToLogin(); }, 1500);
      }
    } catch (err: any) {
      console.error('Registration failed:', err);
      setError(err?.message || 'Registration failed. Credentials may already exist.');
    } finally {
      setLoading(false);
    }
  };

  const currentCountry = geoData.find(c => c.name === selectedCountry);
  const currentState = currentCountry?.states.find((s: any) => s.name === selectedState);
  const districtOptions = currentState?.districts || [];

  const handleEnter = (e: React.KeyboardEvent, nextId?: string, isStepFinal?: boolean) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (nextId) {
        document.getElementById(nextId)?.focus();
      } else if (isStepFinal) {
        if (step < 3) {
          nextStep();
        } else {
          const submitBtn = document.querySelector('button[type="submit"]') as HTMLButtonElement;
          submitBtn?.click();
        }
      }
    }
  };

  const StepIndicator = () => (
    <div className="flex items-center justify-between w-full relative mb-8">
      {[1, 2, 3].map((s) => (
        <div key={s} className="flex items-center gap-2 relative z-10">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-black shadow-md border-2 ${step >= s ? 'bg-[#6366F1] border-[#6366F1] text-white' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
            {step > s ? <Check className="w-4.5 h-4.5 text-white" size={16} /> : s}
          </div>
          <span className={`text-[10px] font-bold uppercase tracking-wider hidden sm:inline ${step >= s ? 'text-slate-900' : 'text-slate-400'}`}>
            {s === 1 ? 'Identity' : s === 2 ? 'Regional' : 'Access'}
          </span>
        </div>
      ))}
      <div className="absolute top-4 left-4 right-4 h-[2px] bg-slate-100 -z-0">
        <div className="h-full bg-[#6366F1] transition-all duration-500" style={{ width: `${(step - 1) * 50}%` }} />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen w-full flex bg-[#EEF2FF] overflow-hidden text-slate-900 font-sans">
      {/* Left Hero Graphic Section - Light Orange Theme */}
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
                <path d="M 60 80 L 200 80 L 200 160 L 340 160" />
                <path d="M 60 160 L 120 160 L 120 240 L 340 240 L 340 300" />
                <path d="M 200 80 L 200 40 L 400 40" />
                <path d="M 120 240 L 120 340 L 280 340" />
                <path d="M 40 300 L 180 300 L 180 380 L 320 380" />
                <path d="M 340 160 L 440 160 L 440 100 L 520 100" />
                <path d="M 340 240 L 420 240" />
                <path d="M 280 340 L 360 340 L 360 420 L 440 420" />
                <path d="M 520 100 L 600 100 L 600 180" />
                <path d="M 440 420 L 520 420 L 520 500 L 600 500" />
            </g>

            {/* Glowing Junction Nodes with pulses */}
            <g fill="rgba(99, 102, 241,0.55)" filter="url(#nodeGlow)">
                <rect x="196" y="76" width="8" height="8" rx="2" className="node-pulse-1" />
                <rect x="116" y="236" width="8" height="8" rx="2" className="node-pulse-2" />
                <rect x="336" y="156" width="8" height="8" rx="2" className="node-pulse-3" />
                <circle cx="340" cy="300" r="4" className="node-pulse-1" />
                <circle cx="440" cy="160" r="4" className="node-pulse-4" />
                <rect x="276" y="336" width="8" height="8" rx="2" className="node-pulse-2" />
            </g>

            {/* ── SIGNAL PULSES (animated dots along paths) ──────────── */}
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
            <circle r="3" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                <animateMotion
                    dur="5s"
                    repeatCount="indefinite"
                    path="M 200 80 L 200 40 L 400 40"
                    calcMode="linear"
                />
            </circle>
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
            <circle r="3.5" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                <animateMotion
                    dur="10s"
                    repeatCount="indefinite"
                    path="M 280 340 L 360 340 L 360 420 L 440 420"
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
            <img src={KIKILogo} alt="Finpixe logo" className="w-full h-full object-contain" />
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

      {/* Right Form Workspace */}
      <div className="flex-1 flex flex-col justify-center items-center p-6 sm:p-12 bg-white text-slate-900 overflow-y-auto">
        <div className="w-full max-w-lg space-y-6 text-left py-6">
          {/* Header */}
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold">
              <Globe className="w-3.5 h-3.5" />
              <span>Platform Node Initialization</span>
            </div>
            <h2 className="text-3xl font-extrabold tracking-tight text-slate-900">
              {step === 1 ? 'Verify Your Identity' : step === 2 ? 'Define Regional Context' : 'Secure Your Access'}
            </h2>
            <p className="text-xs font-medium text-slate-500">
              {step === 1 ? 'Basic administrative credentials to begin initialization.' : 
               step === 2 ? 'Global location and HQ specifications for local compliance.' : 
               'Finalize platform security and login credentials.'}
            </p>
          </div>

          <StepIndicator />

          <form onSubmit={handleRegister} className="space-y-5">
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs font-semibold flex items-center gap-2 animate-in fade-in">
                <Icon name="x" size={16} />
                <span>{error}</span>
              </div>
            )}
            {successMessage && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 text-xs font-semibold flex items-center gap-2 animate-in fade-in">
                <Icon name="check" size={16} />
                <span>{successMessage}</span>
              </div>
            )}

            {/* STEP 1: IDENTITY */}
            {step === 1 && (
              <div className="space-y-4 animate-in fade-in duration-300">
                <Input
                  id="name"
                  label="Full Legal Name"
                  type="text"
                  placeholder="e.g. Johnathan Doe"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  onKeyDown={e => handleEnter(e, 'pan')}
                  required
                  autoFocus
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    id="pan"
                    label="PAN Number"
                    type="text"
                    placeholder="10-digit PAN"
                    value={pan}
                    onChange={e => setPan(e.target.value.toUpperCase())}
                    maxLength={10}
                    onKeyDown={e => handleEnter(e, 'phone')}
                    required
                  />

                  <Input
                    id="phone"
                    label="Contact Phone"
                    type="tel"
                    placeholder="Phone Number"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    onKeyDown={e => handleEnter(e, undefined, true)}
                  />
                </div>
              </div>
            )}

            {/* STEP 2: REGIONAL */}
            {step === 2 && (
              <div className="space-y-4 animate-in fade-in duration-300">
                <Input
                  id="addr1"
                  label="Address Line 1"
                  type="text"
                  placeholder="Enter address line 1"
                  value={addressLine1}
                  onChange={e => setAddressLine1(e.target.value)}
                  onKeyDown={e => handleEnter(e, 'addr2')}
                  required
                  autoFocus
                />

                <Input
                  id="addr2"
                  label="Address Line 2"
                  type="text"
                  placeholder="Enter address line 2"
                  value={addressLine2}
                  onChange={e => setAddressLine2(e.target.value)}
                  onKeyDown={e => handleEnter(e, 'addr3')}
                />

                <Input
                  id="addr3"
                  label="Address Line 3"
                  type="text"
                  placeholder="Enter address line 3"
                  value={addressLine3}
                  onChange={e => setAddressLine3(e.target.value)}
                  onKeyDown={e => handleEnter(e, 'pincode')}
                />

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5 w-full">
                    <label className="erp-label">Country</label>
                    <select
                      id="country"
                      className="erp-input w-full bg-white border border-slate-200 text-slate-900 rounded-xl px-3.5 h-[52px] text-sm font-semibold focus:border-[#6366F1] transition-all focus:outline-none"
                      value={selectedCountry}
                      onChange={e => { setSelectedCountry(e.target.value); setSelectedState(''); setSelectedDistrict(''); }}
                    >
                      {geoData.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
                    </select>
                  </div>

                  <div className="flex flex-col gap-1.5 w-full">
                    <label className="erp-label">State / Province</label>
                    <select
                      id="state"
                      className="erp-input w-full bg-white border border-slate-200 text-slate-900 rounded-xl px-3.5 h-[52px] text-sm font-semibold focus:border-[#6366F1] transition-all focus:outline-none"
                      value={selectedState}
                      onChange={e => { setSelectedState(e.target.value); setSelectedDistrict(''); }}
                      required
                    >
                      <option value="">Select State</option>
                      {currentCountry?.states.map((s: any) => <option key={s.name} value={s.name}>{s.name}</option>)}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5 w-full">
                    <label className="erp-label">District</label>
                    <select
                      id="district"
                      className="erp-input w-full bg-white border border-slate-200 text-slate-900 rounded-xl px-3.5 h-[52px] text-sm font-semibold focus:border-[#6366F1] transition-all focus:outline-none"
                      value={selectedDistrict}
                      onChange={e => setSelectedDistrict(e.target.value)}
                      disabled={!selectedState}
                      required
                    >
                      <option value="">Select District</option>
                      {districtOptions.map((d: string) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>

                  <Input
                    id="pincode"
                    label="Pincode / ZIP"
                    type="text"
                    placeholder="e.g. 400001"
                    value={pincode}
                    onChange={e => setPincode(e.target.value)}
                    onKeyDown={e => handleEnter(e, undefined, true)}
                    required
                  />
                </div>
              </div>
            )}

            {/* STEP 3: ACCESS */}
            {step === 3 && (
              <div className="space-y-4 animate-in fade-in duration-300">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    id="username"
                    label="System Username"
                    type="text"
                    placeholder="Unique admin ID"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    onKeyDown={e => handleEnter(e, 'email')}
                    required
                    autoFocus
                  />

                  <Input
                    id="email"
                    label="Admin Email"
                    type="email"
                    placeholder="admin@KIKI.com"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    onKeyDown={e => handleEnter(e, 'pwd')}
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Input
                    id="pwd"
                    label="Global Password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    onKeyDown={e => handleEnter(e, 'pwd2')}
                    required
                    rightIcon={
                      <button type="button" className="text-slate-400 hover:text-[#6366F1] transition-colors" onClick={() => setShowPassword(!showPassword)}>
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    }
                  />

                  <Input
                    id="pwd2"
                    label="Confirm Password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    onKeyDown={e => handleEnter(e, undefined, true)}
                    required
                    rightIcon={
                      <button type="button" className="text-slate-400 hover:text-[#6366F1] transition-colors" onClick={() => setShowConfirmPassword(!showConfirmPassword)}>
                        {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    }
                  />
                </div>

                <div className="p-4 rounded-xl bg-indigo-50/50 border border-indigo-100 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center text-sm shrink-0">🔒</div>
                  <p className="text-[10px] font-medium text-slate-500 leading-normal">
                    Your master admin account holds global authority. Ensure your password is stored securely and MFA is enabled after initialization.
                  </p>
                </div>
              </div>
            )}

            {/* Form actions */}
            <div className="pt-4 flex items-center gap-3">
              {step > 1 && (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={prevStep}
                  className="flex-1 h-12 text-xs font-bold uppercase tracking-wider"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back
                </Button>
              )}

              {step < 3 ? (
                <Button
                  type="button"
                  variant="primary"
                  onClick={nextStep}
                  className="flex-[2] h-12 text-xs font-bold uppercase tracking-wider"
                >
                  Next Step
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={loading}
                  className="flex-[2] h-12 text-xs font-bold uppercase tracking-wider"
                >
                  Finalize Setup
                  <Check className="w-4 h-4 ml-2" />
                </Button>
              )}
            </div>
          </form>

          {/* Footer Back links */}
          <div className="pt-6 border-t border-slate-100 text-center space-y-3">
            <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">
              Already registered? <button onClick={() => { window.location.href = '/master/login'; }} className="text-[#6366F1] ml-1 hover:underline font-black">Sign In to Dashboard</button>
            </p>

            <button
              onClick={() => window.location.href = (import.meta as any).env?.VITE_LANDING_URL || 'http://localhost:3000'}
              className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-[#6366F1] transition-all flex items-center justify-center gap-2 mx-auto"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Return to Main Website
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;



