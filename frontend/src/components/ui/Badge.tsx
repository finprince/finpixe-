import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'gst-mismatch' | 'neutral';
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  icon,
  className = '',
  ...props
}) => {
  const variantClasses = {
    primary: 'erp-badge-primary',
    success: 'erp-badge-success',
    warning: 'erp-badge-warning',
    danger: 'erp-badge-danger',
    info: 'erp-badge-info',
    'gst-mismatch': 'erp-badge-gst-mismatch',
    neutral: 'bg-slate-100 text-slate-700 border border-slate-200',
  };

  return (
    <span
      className={`erp-badge ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};

export default Badge;
