import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, X, Building2 } from 'lucide-react';

interface KikiCrudCardProps {
  entityType: string; // e.g. "Vendor" or "Customer"
  initialData?: Record<string, any>;
  onSubmit: (data: Record<string, any>) => void;
  onCancel: () => void;
}

export const KikiCrudCard: React.FC<KikiCrudCardProps> = ({
  entityType,
  initialData = {},
  onSubmit,
  onCancel
}) => {
  const [formData, setFormData] = useState({
    name: initialData.name || '',
    gstin: initialData.gstin || '',
    address: initialData.address || '',
    phone: initialData.phone || ''
  });

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md my-3 space-y-3"
    >
      <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800">
        <div className="p-1.5 rounded-lg bg-[#5B5CEB]/10 text-[#5B5CEB]">
          <Building2 className="w-4 h-4" />
        </div>
        <h4 className="text-xs font-semibold text-slate-900 dark:text-white">
          Create New {entityType}
        </h4>
      </div>

      <div className="space-y-2.5 text-xs">
        <div>
          <label className="block text-[10px] font-medium text-slate-500 mb-1">
            {entityType} Name *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            placeholder={`Enter ${entityType.toLowerCase()} name...`}
            className="w-full px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-[#5B5CEB]"
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-[10px] font-medium text-slate-500 mb-1">
              GSTIN
            </label>
            <input
              type="text"
              value={formData.gstin}
              onChange={(e) => handleChange('gstin', e.target.value)}
              placeholder="GSTIN number..."
              className="w-full px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-[#5B5CEB]"
            />
          </div>
          <div>
            <label className="block text-[10px] font-medium text-slate-500 mb-1">
              Phone
            </label>
            <input
              type="text"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              placeholder="Contact phone..."
              className="w-full px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-[#5B5CEB]"
            />
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-medium text-slate-500 mb-1">
            Address
          </label>
          <input
            type="text"
            value={formData.address}
            onChange={(e) => handleChange('address', e.target.value)}
            placeholder="Registered address..."
            className="w-full px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-[#5B5CEB]"
          />
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
        <button
          onClick={onCancel}
          className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={() => onSubmit(formData)}
          disabled={!formData.name.trim()}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-[#5B5CEB] hover:bg-[#4b4cd4] rounded-lg shadow-xs disabled:opacity-40 transition-colors"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Save {entityType}</span>
        </button>
      </div>
    </motion.div>
  );
};
