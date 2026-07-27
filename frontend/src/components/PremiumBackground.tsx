import React from 'react';

/**
 * PremiumBackground — Futuristic AI Circuit Board Authentication Background.
 * Abstract circuit paths with animated signal pulses and glowing nodes.
 * Inspired by AI infrastructure, neural processors, and enterprise cloud computing.
 * NO waves. NO ribbons. NO blobs. Pure digital elegance.
 */
const PremiumBackground: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    return (
        <div
            className="relative min-h-screen w-full overflow-hidden flex items-center justify-center p-4"
            style={{ background: 'linear-gradient(150deg, #FFFFFF 0%, #EEF2FF 55%, #E0E7FF 100%)' }}
        >
            {/* ── LAYER 1: Soft Ambient Cream Gradient ──────────────────── */}
            <div
                className="absolute inset-0 pointer-events-none z-[1]"
                style={{
                    background: 'radial-gradient(ellipse 80% 60% at 50% 50%, rgba(99, 102, 241,0.05) 0%, transparent 70%)',
                }}
            />

            {/* ── LAYER 2: Abstract AI Circuit SVG ──────────────────────── */}
            <svg
                className="absolute inset-0 w-full h-full pointer-events-none z-[2]"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 1440 900"
                preserveAspectRatio="xMidYMid slice"
                aria-hidden="true"
            >
                <defs>
                    {/* Signal gradient — glowing dot */}
                    <radialGradient id="signalGrad" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#818CF8" stopOpacity="1" />
                        <stop offset="100%" stopColor="#818CF8" stopOpacity="0" />
                    </radialGradient>

                    {/* Node glow filter */}
                    <filter id="nodeGlow" x="-80%" y="-80%" width="260%" height="260%">
                        <feGaussianBlur stdDeviation="3" result="blur" />
                        <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>

                    {/* Soft path glow filter */}
                    <filter id="pathGlow" x="-10%" y="-100%" width="120%" height="300%">
                        <feGaussianBlur stdDeviation="1.5" result="blur" />
                        <feMerge>
                            <feMergeNode in="blur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                </defs>

                {/* ── CIRCUIT PATHS ────────────────────────────────────────
                    All paths: 1px stroke, rgba(99, 102, 241,0.12), rounded corners
                    Distributed across all four quadrants for balance.
                ───────────────────────────────────────────────────────── */}

                {/* TOP-LEFT QUADRANT — Horizontal + vertical grid routing */}
                <g stroke="rgba(99, 102, 241,0.35)" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M 60 80 L 200 80 L 200 160 L 340 160" />
                    <path d="M 60 160 L 120 160 L 120 240 L 340 240 L 340 300" />
                    <path d="M 200 80 L 200 40 L 400 40" />
                    <path d="M 120 240 L 120 340 L 280 340" />
                    <path d="M 40 300 L 180 300 L 180 380 L 320 380" />
                    <path d="M 340 160 L 440 160 L 440 100 L 520 100" />
                    <path d="M 340 240 L 420 240" />
                    <path d="M 280 340 L 360 340 L 360 420 L 440 420" />
                </g>

                {/* TOP-RIGHT QUADRANT */}
                <g stroke="rgba(99, 102, 241,0.30)" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M 1380 60 L 1240 60 L 1240 140 L 1100 140" />
                    <path d="M 1380 160 L 1300 160 L 1300 240 L 1160 240 L 1160 300" />
                    <path d="M 1240 60 L 1240 20 L 1040 20" />
                    <path d="M 1100 140 L 1020 140 L 1020 220 L 940 220" />
                    <path d="M 1160 300 L 1080 300 L 1080 380" />
                    <path d="M 940 220 L 860 220 L 860 300 L 780 300" />
                    <path d="M 1300 240 L 1300 320 L 1200 320" />
                </g>

                {/* BOTTOM-LEFT QUADRANT */}
                <g stroke="rgba(99, 102, 241,0.32)" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M 60 820 L 200 820 L 200 740 L 340 740" />
                    <path d="M 60 720 L 160 720 L 160 640 L 300 640" />
                    <path d="M 200 740 L 200 680 L 400 680" />
                    <path d="M 300 640 L 380 640 L 380 560 L 460 560" />
                    <path d="M 160 640 L 160 540 L 280 540 L 280 480" />
                    <path d="M 400 680 L 480 680 L 480 600" />
                    <path d="M 280 480 L 380 480 L 380 420" />
                </g>

                {/* BOTTOM-RIGHT QUADRANT */}
                <g stroke="rgba(99, 102, 241,0.30)" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M 1380 820 L 1240 820 L 1240 740 L 1100 740" />
                    <path d="M 1380 720 L 1280 720 L 1280 640 L 1140 640" />
                    <path d="M 1100 740 L 1020 740 L 1020 660 L 900 660" />
                    <path d="M 1140 640 L 1060 640 L 1060 560 L 960 560" />
                    <path d="M 900 660 L 820 660 L 820 580 L 740 580" />
                    <path d="M 960 560 L 880 560 L 880 480 L 800 480" />
                    <path d="M 1280 640 L 1280 560 L 1180 560" />
                </g>

                {/* CENTER BRIDGE paths — connecting quadrants */}
                <g stroke="rgba(99, 102, 241,0.22)" strokeWidth="1" fill="none" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M 520 100 L 600 100 L 600 180" />
                    <path d="M 440 420 L 520 420 L 520 500 L 600 500" />
                    <path d="M 780 300 L 700 300 L 700 380 L 620 380" />
                    <path d="M 1080 380 L 1080 460 L 1000 460 L 1000 500 L 920 500" />
                    <path d="M 740 580 L 660 580 L 660 500 L 580 500" />
                    <path d="M 800 480 L 720 480 L 720 400 L 660 400" />
                    <path d="M 480 600 L 560 600 L 560 520" />
                </g>

                {/* ── CIRCUIT NODES (Junction points) ─────────────────────── */}
                <g fill="rgba(99, 102, 241,0.55)" filter="url(#nodeGlow)">
                    {/* Top-left nodes */}
                    <rect x="196" y="76" width="8" height="8" rx="2" className="node-pulse-1" />
                    <rect x="116" y="236" width="8" height="8" rx="2" className="node-pulse-2" />
                    <rect x="336" y="156" width="8" height="8" rx="2" className="node-pulse-3" />
                    <circle cx="340" cy="300" r="4" className="node-pulse-1" />
                    <circle cx="440" cy="160" r="4" className="node-pulse-4" />
                    <rect x="276" y="336" width="8" height="8" rx="2" className="node-pulse-2" />

                    {/* Top-right nodes */}
                    <rect x="1236" y="56" width="8" height="8" rx="2" className="node-pulse-3" />
                    <rect x="1096" y="136" width="8" height="8" rx="2" className="node-pulse-1" />
                    <circle cx="940" cy="220" r="4" className="node-pulse-2" />
                    <rect x="1156" y="236" width="8" height="8" rx="2" className="node-pulse-4" />
                    <circle cx="1080" cy="380" r="4" className="node-pulse-3" />

                    {/* Bottom-left nodes */}
                    <rect x="196" y="736" width="8" height="8" rx="2" className="node-pulse-2" />
                    <rect x="296" y="636" width="8" height="8" rx="2" className="node-pulse-4" />
                    <circle cx="160" cy="640" r="4" className="node-pulse-1" />
                    <rect x="276" y="476" width="8" height="8" rx="2" className="node-pulse-3" />
                    <circle cx="480" cy="600" r="4" className="node-pulse-2" />

                    {/* Bottom-right nodes */}
                    <rect x="1236" y="736" width="8" height="8" rx="2" className="node-pulse-4" />
                    <rect x="1096" y="736" width="8" height="8" rx="2" className="node-pulse-1" />
                    <circle cx="900" cy="660" r="4" className="node-pulse-3" />
                    <rect x="956" y="556" width="8" height="8" rx="2" className="node-pulse-2" />
                    <circle cx="740" cy="580" r="4" className="node-pulse-4" />
                    <rect x="796" y="476" width="8" height="8" rx="2" className="node-pulse-1" />
                </g>

                {/* ── SIGNAL PULSES (animated dots along paths) ──────────── */}

                {/* Signal 1 — Top-left horizontal */}
                <circle r="3" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                    <animateMotion
                        dur="12s"
                        repeatCount="indefinite"
                        path="M 60 80 L 200 80 L 200 160 L 340 160 L 440 160 L 440 100 L 520 100"
                        calcMode="linear"
                    />
                </circle>

                {/* Signal 2 — Top-right routing */}
                <circle r="3" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                    <animateMotion
                        dur="15s"
                        repeatCount="indefinite"
                        path="M 1380 60 L 1240 60 L 1240 140 L 1100 140 L 1020 140 L 1020 220 L 940 220 L 860 220 L 860 300 L 780 300"
                        calcMode="linear"
                    />
                </circle>

                {/* Signal 3 — Bottom-left routing */}
                <circle r="4" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                    <animateMotion
                        dur="18s"
                        repeatCount="indefinite"
                        path="M 60 720 L 160 720 L 160 640 L 300 640 L 380 640 L 380 560 L 460 560"
                        calcMode="linear"
                    />
                </circle>

                {/* Signal 4 — Bottom-right routing */}
                <circle r="4" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                    <animateMotion
                        dur="14s"
                        repeatCount="indefinite"
                        path="M 1380 820 L 1240 820 L 1240 740 L 1100 740 L 1020 740 L 1020 660 L 900 660 L 820 660 L 820 580 L 740 580"
                        calcMode="linear"
                    />
                </circle>

                {/* Signal 5 — Center vertical connector */}
                <circle r="3" fill="url(#signalGrad)" filter="url(#nodeGlow)">
                    <animateMotion
                        dur="10s"
                        repeatCount="indefinite"
                        path="M 160 640 L 160 540 L 280 540 L 280 480 L 380 480 L 380 420"
                        calcMode="linear"
                    />
                </circle>

                {/* Signal 6 — Secondary top-left */}
                <circle r="3.5" fill="#4F46E5" opacity="0.9" filter="url(#nodeGlow)">
                    <animateMotion
                        dur="20s"
                        repeatCount="indefinite"
                        begin="-6s"
                        path="M 60 160 L 120 160 L 120 240 L 340 240 L 340 300"
                        calcMode="linear"
                    />
                </circle>

                {/* Signal 7 — Secondary bottom-right */}
                <circle r="3.5" fill="#4F46E5" opacity="0.9" filter="url(#nodeGlow)">
                    <animateMotion
                        dur="16s"
                        repeatCount="indefinite"
                        begin="-10s"
                        path="M 1380 720 L 1280 720 L 1280 640 L 1140 640 L 1060 640 L 1060 560 L 960 560 L 880 560 L 880 480 L 800 480"
                        calcMode="linear"
                    />
                </circle>
            </svg>

            {/* ── LAYER 3: Soft Orange Glow behind card ─────────────────── */}
            <div
                className="absolute pointer-events-none z-[3]"
                style={{
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: '700px',
                    height: '500px',
                    borderRadius: '50%',
                    background: 'radial-gradient(ellipse at center, rgba(99, 102, 241,0.07) 0%, rgba(99, 102, 241,0.03) 45%, transparent 70%)',
                    filter: 'blur(50px)',
                    animation: 'glowPulse 8s ease-in-out infinite alternate',
                }}
            />

            {/* ── LAYER 4: Login Card ────────────────────────────────────── */}
            <div className="relative z-[10] w-full flex items-center justify-center">
                {children}
            </div>

            {/* ── CSS Animations ────────────────────────────────────────── */}
            <style>{`
                /* Node illumination pulses — staggered timing */
                .node-pulse-1 { animation: nodePulse 4s ease-in-out infinite; }
                .node-pulse-2 { animation: nodePulse 4s ease-in-out infinite; animation-delay: -1.3s; }
                .node-pulse-3 { animation: nodePulse 4s ease-in-out infinite; animation-delay: -2.7s; }
                .node-pulse-4 { animation: nodePulse 4s ease-in-out infinite; animation-delay: -0.8s; }

                @keyframes nodePulse {
                    0%,  100% { opacity: 0.20; }
                    50%        { opacity: 0.80; }
                }

                @keyframes glowPulse {
                    0%   { opacity: 0.6; transform: translate(-50%, -50%) scale(1); }
                    100% { opacity: 1.0; transform: translate(-50%, -50%) scale(1.04); }
                }

                /* Respect user motion preference */
                @media (prefers-reduced-motion: reduce) {
                    .node-pulse-1,
                    .node-pulse-2,
                    .node-pulse-3,
                    .node-pulse-4 {
                        animation: none;
                        opacity: 0.35;
                    }
                    circle[r] {
                        display: none;
                    }
                }

                /* Reduce circuit density on mobile */
                @media (max-width: 768px) {
                    svg > g:nth-child(3),
                    svg > g:nth-child(4),
                    svg > g:nth-child(5),
                    svg > g:nth-child(6) {
                        opacity: 0.4;
                    }
                }
            `}</style>
        </div>
    );
};

export default PremiumBackground;
