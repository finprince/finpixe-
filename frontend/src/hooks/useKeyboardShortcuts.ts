import { useEffect } from 'react';
import type { ShortcutConfig } from '../types/types';

export const useKeyboardShortcuts = (shortcuts: ShortcutConfig[]) => {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isInput = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);

      for (const config of shortcuts) {
        const keyMatch = event.key.toLowerCase() === config.key.toLowerCase();
        const ctrlMatch = config.ctrlKey ? (event.ctrlKey || event.metaKey) : true;
        const altMatch = config.altKey ? event.altKey : true;
        const shiftMatch = config.shiftKey ? event.shiftKey : true;

        if (keyMatch && ctrlMatch && altMatch && shiftMatch) {
          if (!isInput || (config.ctrlKey || config.metaKey || config.key.toLowerCase() === 'escape')) {
            event.preventDefault();
            config.action();
            break;
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
};
