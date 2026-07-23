import React from 'react';
import Icon from './Icon';

interface StatCardProps {
    title: string;
    value: string;
    icon?: string;
    trend?: string;
    /** @deprecated use trend instead */
    change?: string;
    isPositive?: boolean;
    trendLabel?: string;
    color?: 'emerald' | 'rose' | 'amber' | 'blue' | 'orange' | 'slate' | 'cyan' | 'green' | 'purple' | 'indigo';
    className?: string;
    onClick?: () => void;
    subValue?: string;
}

const colorMap: Record<string, { accent: string; iconBg: string; iconColor: string }> = {
    emerald: { accent: '#10B981', iconBg: '#ECFDF5', iconColor: '#059669' },
    rose: { accent: '#F43F5E', iconBg: '#FFF1F2', iconColor: '#E11D48' },
    amber: { accent: '#F59E0B', iconBg: '#FFFBEB', iconColor: '#D97706' },
    blue: { accent: '#3B82F6', iconBg: '#EFF6FF', iconColor: '#2563EB' },
    orange: { accent: '#F97316', iconBg: '#FFF7ED', iconColor: '#EA580C' },
    indigo: { accent: '#6366F1', iconBg: '#EEF2FF', iconColor: '#4F46E5' },
    purple: { accent: '#8B5CF6', iconBg: '#F5F3FF', iconColor: '#7C3AED' },
    slate: { accent: '#64748B', iconBg: '#F1F5F9', iconColor: '#475569' },
    cyan: { accent: '#06B6D4', iconBg: '#ECFEFF', iconColor: '#0891B2' },
    green: { accent: '#10B981', iconBg: '#ECFDF5', iconColor: '#059669' },
};

const StatCard: React.FC<StatCardProps> = ({
    title, value, icon, trend, change, isPositive, trendLabel = 'vs last period',
    color = 'orange', className = '', onClick, subValue
}) => {
    const effectiveTrend = trend ?? change;
    const theme = colorMap[color] || colorMap.orange;

    return (
        <div
            onClick={onClick}
            className={`erp-kpi-card group shadow-sm ${onClick ? 'cursor-pointer hover:shadow-lg hover:-translate-y-1' : ''} ${className}`}
            style={{ border: `1.5px solid ${theme.accent}` }}
        >
            {/* Top Row: Title & Icon */}
            <div className="flex justify-between items-center w-full gap-4 mb-2">
                <p className="erp-kpi-label truncate">
                    {title}
                </p>
                {icon && (
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-110 shadow-sm"
                        style={{ background: theme.iconBg }}
                    >
                        <Icon
                            name={icon as any}
                            className="w-5.5 h-5.5"
                            style={{ color: theme.iconColor }}
                        />
                    </div>
                )}
            </div>

            {/* Value Row */}
            <div className="min-w-0 w-full">
                <h3 className="erp-kpi-value select-all tracking-tight leading-none text-slate-950 font-bold">
                    {value}
                </h3>
                {subValue && (
                    <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mt-1.5">
                        {subValue}
                    </p>
                )}
            </div>

            {/* Trend Row */}
            {(effectiveTrend || trendLabel) && (
                <div className="flex items-center mt-5 pt-3.5 border-t border-slate-100">
                    {effectiveTrend && (
                        <span className={`erp-badge ${effectiveTrend.startsWith('+') ? 'erp-badge-success' : 'erp-badge-danger'}`}>
                            {effectiveTrend}
                        </span>
                    )}
                    <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider ml-2">
                        {trendLabel}
                    </span>
                </div>
            )}
        </div>
    );
};

export default StatCard;
