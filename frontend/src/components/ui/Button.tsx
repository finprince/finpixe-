import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  const baseClasses = 'inline-flex items-center justify-center font-semibold uppercase tracking-wider transition-all duration-150 active:scale-98 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none';
  
  const sizeClasses = {
    sm: 'h-9 px-3 text-xs rounded-lg gap-1.5',
    md: 'h-[44px] px-5 text-[13px] rounded-xl gap-2',
    lg: 'h-12 px-6 text-sm rounded-xl gap-2.5',
  };

  const variantClasses = {
    primary: 'bg-[#6366F1] text-white hover:bg-[#4F46E5] shadow-md shadow-indigo-500/20 hover:shadow-lg hover:shadow-indigo-500/30',
    secondary: 'bg-white text-slate-700 border border-slate-300 hover:bg-indigo-50 hover:border-slate-400 hover:text-[#4F46E5]',
    ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900',
    danger: 'bg-rose-600 text-white hover:bg-rose-700 shadow-md shadow-rose-500/20',
  };

  return (
    <button
      className={`${baseClasses} ${sizeClasses[size]} ${variantClasses[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      ) : (
        leftIcon
      )}
      <span>{children}</span>
      {!isLoading && rightIcon}
    </button>
  );
};

export default Button;
