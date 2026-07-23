import React from 'react';
import { WorkspaceToolbar } from '../ui/WorkspaceToolbar';
import { InspectorDrawer } from '../ui/InspectorDrawer';
import type { WorkspaceProps } from '../../types';

export const UniversalWorkspaceLayout: React.FC<WorkspaceProps> = ({
  title,
  subtitle,
  badgeText,
  children,
  onSearchChange,
  onFilterClick,
  onExportExcel,
  onExportPdf,
  inspectorState,
  onCloseInspector
}) => {
  return (
    <div className="flex min-h-screen bg-[#FAFAFA] relative">
      {/* Main Workspace Canvas Container */}
      <div className="flex-1 flex flex-col gap-6 transition-all duration-300">
        {/* Context Header */}
        <div className="flex justify-between items-center pb-4 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-extrabold tracking-tight text-slate-900 leading-none">{title}</h1>
              {badgeText && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-orange-50 text-[#EA580C] border border-orange-200">
                  {badgeText}
                </span>
              )}
            </div>
            {subtitle && (
              <p className="text-sm font-medium text-slate-500 mt-1">{subtitle}</p>
            )}
          </div>
        </div>

        {/* Toolbar */}
        {(onSearchChange || onFilterClick || onExportExcel || onExportPdf) && (
          <WorkspaceToolbar
            onSearchChange={onSearchChange}
            onFilterClick={onFilterClick}
            onExportExcel={onExportExcel}
            onExportPdf={onExportPdf}
          />
        )}

        {/* Primary Content Canvas */}
        <div className="flex-1 animate-in fade-in duration-300">
          {children}
        </div>
      </div>

      {/* Inspector Drawer */}
      {inspectorState && onCloseInspector && (
        <InspectorDrawer state={inspectorState} onClose={onCloseInspector} />
      )}
    </div>
  );
};
