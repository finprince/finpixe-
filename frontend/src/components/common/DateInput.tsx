import React, { useState, useEffect, useRef } from 'react';
import { PatternFormat } from 'react-number-format';
import { Calendar } from 'lucide-react';

interface DateInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange'> {
    value?: string;
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const DateInput: React.FC<DateInputProps> = ({ value, onChange, className, ...props }) => {
    const [displayValue, setDisplayValue] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (value) {
            // Check if it's an ISO string or standard YYYY-MM-DD
            const datePart = value.includes('T') ? value.split('T')[0] : value;
            const parts = datePart.split('-');
            if (parts.length === 3 && parts[0].length === 4) {
                const [year, month, day] = parts;
                setDisplayValue(`${day}${month}${year}`);
            } else if (parts.length === 3 && parts[2].length === 4) {
                // Already DD-MM-YYYY (safety check)
                const [day, month, year] = parts;
                setDisplayValue(`${day}${month}${year}`);
            } else {
                setDisplayValue(value);
            }
        } else {
            setDisplayValue('');
        }
    }, [value]);

    const handleValueChange = (values: any) => {
        const formattedDisplay = values.formattedValue; // DD-MM-YYYY

        let outputValue = '';
        if (formattedDisplay && formattedDisplay.length === 10) {
            const [day, month, year] = formattedDisplay.split('-');
            if (day && month && year && year.length === 4) {
                outputValue = `${year}-${month}-${day}`;
            }
        }

        if (onChange) {
            // Mock event to maintain compatibility with standard onChange handlers
            const event = {
                target: {
                    value: outputValue
                }
            } as React.ChangeEvent<HTMLInputElement>;
            onChange(event);
        }
    };

    const handleNativeDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (onChange) {
            onChange(e);
        }
    };

    // Calculate the standard value for the native date input (must be YYYY-MM-DD)
    let nativeValue = '';
    if (value) {
        const datePart = value.includes('T') ? value.split('T')[0] : value;
        const parts = datePart.split('-');
        if (parts.length === 3 && parts[0].length === 4) {
            nativeValue = datePart;
        } else if (parts.length === 3 && parts[2].length === 4) {
            const [day, month, year] = parts;
            nativeValue = `${year}-${month}-${day}`;
        }
    }

    return (
        <div className="relative flex items-center w-full">
            <PatternFormat
                format="##-##-####"
                mask="_"
                placeholder="DD-MM-YYYY"
                value={displayValue}
                onValueChange={handleValueChange}
                className={className || "w-full px-4 py-2 border border-gray-300 rounded-[4px] focus:ring-indigo-500 focus:border-indigo-500 text-sm"}
                getInputRef={inputRef}
                {...props as any}
            />
            <div className="absolute right-3 pointer-events-none text-gray-400">
                <Calendar size={18} />
            </div>
            <input
                type="date"
                className="absolute right-2 w-8 h-full opacity-0 cursor-pointer"
                value={nativeValue}
                onChange={handleNativeDateChange}
            />
        </div>
    );
};

export default DateInput;
