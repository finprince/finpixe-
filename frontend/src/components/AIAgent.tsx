import React from 'react';
import type { AgentMessage } from '../types';
import { KikiPanel } from './kiki';

interface AIAgentProps {
  isOpen: boolean;
  onClose: () => void;
  messages: AgentMessage[];
  onSendMessage: (message: string, useGrounding: boolean) => void;
  isLoading: boolean;
  queueStatus?: {
    queuePosition?: number;
    estimatedWaitSeconds?: number;
    code?: string;
    retryAfter?: number;
  };
  onNavigate?: (routeOrPage: string) => void;
}

const AIAgent: React.FC<AIAgentProps> = (props) => {
  return <KikiPanel {...props} />;
};

export default AIAgent;
