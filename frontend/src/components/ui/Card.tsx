import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  hoverable = false,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`erp-card p-6 ${hoverable ? 'hover:-translate-y-1 hover:shadow-lg cursor-pointer' : ''} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const CardHeader: React.FC<CardHeaderProps> = ({
  title,
  subtitle,
  action,
  className = '',
  ...props
}) => {
  return (
    <div className={`flex items-center justify-between pb-4 mb-4 border-b border-slate-100 ${className}`} {...props}>
      <div>
        <h3 className="section-title">{title}</h3>
        {subtitle && <p className="helper-text mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

export default Card;
