import { useState, useCallback } from 'react';
import { useKeyboardShortcuts } from './useKeyboardShortcuts';

export const useCommandPalette = () => {
  const [isOpen, setIsOpen] = useState(false);

  const toggle = useCallback(() => setIsOpen(prev => !prev), []);
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  useKeyboardShortcuts([
    {
      key: 'k',
      ctrlKey: true,
      action: toggle,
      description: 'Toggle Command Palette'
    },
    {
      key: 'Escape',
      action: close,
      description: 'Close Command Palette'
    }
  ]);

  return { isOpen, open, close, toggle };
};
