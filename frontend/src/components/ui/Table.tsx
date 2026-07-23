import React from 'react';

export interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {
  containerClassName?: string;
}

export const Table: React.FC<TableProps> = ({
  children,
  className = '',
  containerClassName = '',
  ...props
}) => {
  return (
    <div className={`erp-table-container ${containerClassName}`}>
      <table className={`erp-table ${className}`} {...props}>
        {children}
      </table>
    </div>
  );
};

export default Table;
