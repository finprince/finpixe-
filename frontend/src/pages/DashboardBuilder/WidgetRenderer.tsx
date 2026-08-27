import React from 'react';
import {
    LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    AreaChart, Area, ScatterChart, Scatter, ZAxis
} from 'recharts';
import { Widget, useDashboardStore } from '../../store/dashboardStore';
import { MoreHorizontal, Maximize2, Filter, Info, Download, Share2, Trash2 } from 'lucide-react';
import { confirm, showSuccess, showInfo } from '../../utils/toast';


interface WidgetRendererProps {
    widget: Widget;
    data: any[];
}

// Power BI Default "Executive" Palette
const PBI_PALETTE = [
    '#118DFF', // Cyan Blue
    '#12239E', // Royal Blue
    '#6366F1', // Orange
    '#6B007B', // Purple
    '#E044A7', // Pink
    '#744EC2', // Lavender
    '#D9B300', // Gold
    '#065A82', // Dark Teal
];

const WidgetRenderer: React.FC<WidgetRendererProps> = ({ widget, data }) => {
    const { setGlobalFilters, selectedWidgetId, deleteWidget, selectWidget } = useDashboardStore();
    const isSelected = selectedWidgetId === widget.id;

    const handleChartClick = (entry: any) => {
        if (!entry) return;
        const payload = entry.activePayload?.[0]?.payload || entry;

        // Cross-filtering logic
        if (widget.dataset === 'Sales' && widget.xField === 'Customer') {
            setGlobalFilters({ customer: payload.Customer || payload.name });
        } else if (widget.dataset === 'Expenses' && widget.xField === 'Vendor') {
            setGlobalFilters({ vendor: payload.Vendor || payload.name });
        }
    };

    const formatValue = (val: any) => {
        const num = Number(val) || 0;
        if (widget.properties.numberFormat === 'Currency' && widget.aggregation !== 'count') {
            return `₹${num.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
        }
        return num.toLocaleString('en-IN', { maximumFractionDigits: 2 });
    };

    const formatAxisValue = (val: any) => {
        const num = Number(val) || 0;
        if (widget.properties.numberFormat === 'Currency' && widget.aggregation !== 'count') {
            if (num >= 10000000) return `₹${(num / 10000000).toFixed(1)}Cr`;
            if (num >= 100000) return `₹${(num / 100000).toFixed(1)}L`;
            if (num >= 1000) return `₹${(num / 1000).toFixed(0)}k`;
            return `₹${num}`;
        }
        if (num >= 10000000) return `${(num / 10000000).toFixed(1)}Cr`;
        if (num >= 100000) return `${(num / 100000).toFixed(1)}L`;
        if (num >= 1000) return `${(num / 1000).toFixed(0)}k`;
        return num.toString();
    };

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-slate-900 text-white p-3 rounded-lg shadow-2xl border border-slate-700 min-w-[140px] animate-in fade-in zoom-in duration-200">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1">{label}</p>
                    <div className="flex items-center justify-between gap-4">
                        <span className="text-xs font-bold">{payload[0].name}:</span>
                        <span className="text-xs font-black text-indigo-400">
                            {formatValue(payload[0].value)}
                        </span>
                    </div>
                </div>
            );
        }
        return null;
    };

    const renderKPI = () => {
        const total = data.reduce((acc, curr) => Number(acc) + Number(curr[widget.yField || 'Amount'] || 0), 0);
        return (
            <div className="flex flex-col items-center justify-center h-full text-center">
                <h2 className="text-5xl font-black text-slate-800 tracking-tighter mb-1">
                    {formatValue(total)}
                </h2>
                <div className="flex items-center gap-3">
                    <div className="h-px w-8 bg-slate-200" />
                    <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 whitespace-nowrap">
                        {widget.aggregation} of {widget.yField}
                    </span>
                    <div className="h-px w-8 bg-slate-200" />
                </div>
            </div>
        );
    };

    const renderVisual = () => {
        const chartColor = widget.properties.colorTheme || PBI_PALETTE[0];

        switch (widget.type) {
            case 'area':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={data} onClick={handleChartClick}>
                            <defs>
                                <linearGradient id={`color-${widget.id}`} x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor={chartColor} stopOpacity={0.1} />
                                    <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            {widget.properties.showGridlines && <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />}
                            <XAxis
                                dataKey={widget.xField}
                                fontSize={9}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#94a3b8', fontWeight: 700 }}
                                dy={10}
                            />
                            <YAxis
                                fontSize={9}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#94a3b8', fontWeight: 700 }}
                                tickFormatter={formatAxisValue}
                            />
                            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#e2e8f0', strokeWidth: 1 }} />
                            <Area
                                type="monotone"
                                dataKey={widget.yField || 'Amount'}
                                stroke={chartColor}
                                strokeWidth={3}
                                fillOpacity={1}
                                fill={`url(#color-${widget.id})`}
                                animationDuration={1500}
                                activeDot={{ r: 6, strokeWidth: 0, fill: chartColor }}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                );
            case 'line':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data} onClick={handleChartClick}>
                            {widget.properties.showGridlines && <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />}
                            <XAxis
                                dataKey={widget.xField}
                                fontSize={9}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#94a3b8', fontWeight: 700 }}
                                dy={10}
                            />
                            <YAxis
                                fontSize={9}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#94a3b8', fontWeight: 700 }}
                                tickFormatter={formatAxisValue}
                            />
                            <Tooltip content={<CustomTooltip />} cursor={{ stroke: '#e2e8f0', strokeWidth: 1 }} />
                            <Line
                                type="monotone"
                                dataKey={widget.yField || 'Amount'}
                                stroke={chartColor}
                                strokeWidth={3}
                                dot={{ r: 4, fill: chartColor, strokeWidth: 0 }}
                                activeDot={{ r: 6, strokeWidth: 0, fill: chartColor }}
                                animationDuration={1500}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                );
            case 'bar':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} onClick={handleChartClick}>
                            {widget.properties.showGridlines && <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />}
                            <XAxis dataKey={widget.xField} fontSize={9} axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontWeight: 700 }} dy={10} />
                            <YAxis
                                fontSize={9}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#94a3b8', fontWeight: 700 }}
                                tickFormatter={formatAxisValue}
                            />
                            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f8fafc' }} />
                            <Bar
                                dataKey={widget.yField || 'Amount'}
                                fill={chartColor}
                                radius={[4, 4, 0, 0]}
                                barSize={32}
                                animationDuration={1500}
                            />
                        </BarChart>
                    </ResponsiveContainer>
                );
            case 'pie':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                innerRadius="0%"
                                outerRadius="85%"
                                paddingAngle={2}
                                dataKey={widget.yField || 'Amount'}
                                nameKey={widget.xField || 'name'}
                                onClick={handleChartClick}
                                animationDuration={1500}
                            >
                                {data.map((entry, index) => <Cell key={index} fill={PBI_PALETTE[index % PBI_PALETTE.length]} stroke="none" />)}
                            </Pie>
                            <Tooltip content={<CustomTooltip />} />
                            {widget.properties.showLegend && (
                                <Legend
                                    verticalAlign="bottom"
                                    height={36}
                                    iconType="circle"
                                    wrapperStyle={{ fontSize: '9px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.1em', paddingTop: '20px' }}
                                />
                            )}
                        </PieChart>
                    </ResponsiveContainer>
                );
            case 'donut':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                            <Pie
                                data={data}
                                innerRadius="65%"
                                outerRadius="85%"
                                paddingAngle={4}
                                dataKey={widget.yField || 'Amount'}
                                nameKey={widget.xField || 'name'}
                                onClick={handleChartClick}
                                animationDuration={1500}
                            >
                                {data.map((entry, index) => <Cell key={index} fill={PBI_PALETTE[index % PBI_PALETTE.length]} stroke="none" />)}
                            </Pie>
                            <Tooltip content={<CustomTooltip />} />
                            {widget.properties.showLegend && (
                                <Legend
                                    verticalAlign="bottom"
                                    height={36}
                                    iconType="circle"
                                    wrapperStyle={{ fontSize: '9px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.1em', paddingTop: '20px' }}
                                />
                            )}
                        </PieChart>
                    </ResponsiveContainer>
                );
            case 'scatter':
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart onClick={handleChartClick}>
                            {widget.properties.showGridlines && <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />}
                            <XAxis
                                dataKey={widget.xField}
                                fontSize={9}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#94a3b8', fontWeight: 700 }}
                            />
                            <YAxis
                                dataKey={widget.yField || 'Amount'}
                                fontSize={9}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fill: '#94a3b8', fontWeight: 700 }}
                                tickFormatter={formatAxisValue}
                            />
                            <ZAxis range={[60, 400]} />
                            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
                            <Scatter name={widget.title} data={data} fill={chartColor} animationDuration={1500} />
                        </ScatterChart>
                    </ResponsiveContainer>
                );
            case 'table':
                return (
                    <div className="w-full h-full overflow-auto custom-scrollbar">
                        <table className="w-full text-left border-collapse">
                            <thead className="sticky top-0 bg-white shadow-sm z-10">
                                <tr>
                                    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100">{widget.xField || 'Dimension'}</th>
                                    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100 text-right">{widget.yField || 'Measure'}</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.map((row, i) => (
                                    <tr key={i} className="hover:bg-slate-50 transition-colors group cursor-default">
                                        <td className="px-4 py-2.5 text-xs font-bold text-slate-700 border-b border-slate-50">{row[widget.xField || 'name']}</td>
                                        <td className="px-4 py-2.5 text-xs font-black text-indigo-600 border-b border-slate-50 text-right">
                                            {formatValue(row[widget.yField || 'value'] || 0)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                );
            case 'kpi':
                return renderKPI();
            default:
                return (
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} onClick={handleChartClick}>
                            {widget.properties.showGridlines && <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />}
                            <XAxis dataKey={widget.xField} fontSize={9} axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontWeight: 700 }} dy={10} />
                            <YAxis fontSize={9} axisLine={false} tickLine={false} tick={{ fill: '#94a3b8', fontWeight: 700 }} tickFormatter={formatAxisValue} />
                            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f8fafc' }} />
                            <Bar dataKey={widget.yField || 'Amount'} fill={chartColor} radius={[4, 4, 0, 0]} barSize={32} animationDuration={1500} />
                        </BarChart>
                    </ResponsiveContainer>
                );
        }
    };

    const [isEditingTitle, setIsEditingTitle] = React.useState(false);
    const [titleInput, setTitleInput] = React.useState(widget.title);
    const [isFocusMode, setIsFocusMode] = React.useState(false);
    const { updateWidget } = useDashboardStore();

    const handleTitleSave = () => {
        setIsEditingTitle(false);
        if (titleInput.trim()) {
            updateWidget(widget.id, { title: titleInput.trim() });
        }
    };

    const handleExportCSV = (e: React.MouseEvent) => {
        e.stopPropagation();
        const headers = listHeaders();
        const csvRows = [headers.join(',')];
        data.forEach(row => {
            const vals = headers.map(h => `"${row[h] !== undefined ? row[h] : ''}"`);
            csvRows.push(vals.join(','));
        });
        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${widget.title.toLowerCase().replace(/\s+/g, '_')}_data.csv`;
        a.click();
        showSuccess(`Exported ${widget.title} data to CSV`);
    };

    const listHeaders = () => {
        if (!data || data.length === 0) return ['Name', 'Value'];
        return Object.keys(data[0]);
    };

    return (
        <>
            <div
                onClick={(e) => {
                    e.stopPropagation();
                    selectWidget(widget.id);
                }}
                className={`w-full h-full bg-white flex flex-col group transition-all duration-500 rounded-2xl ${isSelected ? 'shadow-[0_25px_60px_rgba(17,141,255,0.2)] ring-2 ring-indigo-600' : 'shadow-sm border border-slate-100 hover:border-slate-300'} cursor-pointer`}
            >
                {/* Power BI Desktop Style Header */}
                <div className="h-11 px-5 flex items-center justify-between border-b border-slate-50 bg-white select-none rounded-t-2xl">
                    {isEditingTitle ? (
                        <input
                            type="text"
                            autoFocus
                            value={titleInput}
                            onChange={(e) => setTitleInput(e.target.value)}
                            onBlur={handleTitleSave}
                            onKeyDown={(e) => e.key === 'Enter' && handleTitleSave()}
                            onClick={(e) => e.stopPropagation()}
                            className="text-[10px] font-black text-slate-800 uppercase tracking-[0.2em] bg-indigo-50 px-2 py-1 rounded border border-indigo-200 outline-none w-full font-mono"
                        />
                    ) : (
                        <h3
                            onDoubleClick={(e) => {
                                e.stopPropagation();
                                setIsEditingTitle(true);
                            }}
                            title="Double-click to edit title"
                            className="text-[10px] font-black text-slate-800 uppercase tracking-[0.2em] truncate flex-1 leading-tight hover:text-indigo-600 transition-colors"
                        >
                            {widget.title}
                        </h3>
                    )}

                    {/* Power BI Quick Action Bar */}
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all duration-300">
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setIsFocusMode(true);
                            }}
                            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-indigo-600 transition-colors"
                            title="Focus Mode (Full Screen Visual)"
                        >
                            <Maximize2 size={13} strokeWidth={2.5} />
                        </button>
                        <button
                            onClick={handleExportCSV}
                            className="p-1.5 hover:bg-slate-100 rounded-lg text-slate-400 hover:text-indigo-600 transition-colors"
                            title="Export Data (CSV)"
                        >
                            <Download size={13} strokeWidth={2.5} />
                        </button>
                        <button
                            onMouseDown={async (e) => {
                                e.stopPropagation();
                                if (await confirm('Are you sure you want to remove this visual?')) {
                                    deleteWidget(widget.id);
                                    showSuccess('Visual removed');
                                }
                            }}
                            className="p-1.5 hover:bg-rose-50 rounded-lg text-slate-400 hover:text-rose-600 transition-colors"
                            title="Remove Visual"
                        >
                            <Trash2 size={13} strokeWidth={2.5} />
                        </button>
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 p-6 min-h-[200px] relative">
                    {renderVisual()}
                </div>
            </div>

            {/* Power BI Focus Mode Dialog */}
            {isFocusMode && (
                <div className="fixed inset-0 bg-slate-900/80 backdrop-blur-md z-[200] flex items-center justify-center p-8 animate-in fade-in duration-200">
                    <div className="bg-white rounded-3xl w-full max-w-5xl h-[80vh] flex flex-col shadow-2xl overflow-hidden border border-slate-200">
                        <div className="px-8 py-5 bg-slate-900 text-white flex items-center justify-between">
                            <div>
                                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-indigo-400">Power BI Focus Mode</p>
                                <h2 className="text-lg font-black uppercase tracking-tight">{widget.title}</h2>
                            </div>
                            <div className="flex items-center gap-3">
                                <button onClick={handleExportCSV} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all">
                                    <Download size={14} /> Export CSV
                                </button>
                                <button onClick={() => setIsFocusMode(false)} className="p-2 hover:bg-white/10 rounded-xl text-slate-400 hover:text-white transition-colors">
                                    <Maximize2 size={18} />
                                </button>
                            </div>
                        </div>
                        <div className="flex-1 p-8 bg-slate-50 flex gap-8 overflow-hidden">
                            <div className="flex-1 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                                {renderVisual()}
                            </div>
                            <div className="w-80 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
                                <h4 className="text-xs font-black uppercase tracking-widest text-slate-800 mb-4 border-b border-slate-100 pb-2">Underlying Data</h4>
                                <div className="flex-1 overflow-auto custom-scrollbar">
                                    <table className="w-full text-left border-collapse">
                                        <thead>
                                            <tr>
                                                <th className="py-2 text-[9px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100">{widget.xField || 'Dimension'}</th>
                                                <th className="py-2 text-[9px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-100 text-right">{widget.yField || 'Measure'}</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {data.map((r, i) => (
                                                <tr key={i} className="hover:bg-slate-50 border-b border-slate-50">
                                                    <td className="py-2 text-xs font-bold text-slate-700">{r[widget.xField || 'name']}</td>
                                                    <td className="py-2 text-xs font-black text-indigo-600 text-right">{formatValue(r[widget.yField || 'value'] || 0)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default WidgetRenderer;
