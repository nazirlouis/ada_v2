import React from 'react';
import { Wifi, WifiOff, AlertCircle } from 'lucide-react';

/**
 * Connection Status Indicator
 * Shows the current connection state to Gemini API
 */
const ConnectionStatus = ({ status = 'disconnected', latency = 0, reconnecting = false }) => {
    const getStatusConfig = () => {
        switch (status) {
            case 'connected':
                return {
                    icon: Wifi,
                    text: 'Connected',
                    color: 'text-green-400',
                    bgColor: 'bg-green-500/10',
                    borderColor: 'border-green-500/30',
                    pulseColor: 'bg-green-500'
                };
            case 'connecting':
            case 'reconnecting':
                return {
                    icon: AlertCircle,
                    text: reconnecting ? 'Reconnecting...' : 'Connecting...',
                    color: 'text-yellow-400',
                    bgColor: 'bg-yellow-500/10',
                    borderColor: 'border-yellow-500/30',
                    pulseColor: 'bg-yellow-500'
                };
            case 'error':
                return {
                    icon: WifiOff,
                    text: 'Connection Error',
                    color: 'text-red-400',
                    bgColor: 'bg-red-500/10',
                    borderColor: 'border-red-500/30',
                    pulseColor: 'bg-red-500'
                };
            default:
                return {
                    icon: WifiOff,
                    text: 'Disconnected',
                    color: 'text-gray-400',
                    bgColor: 'bg-gray-500/10',
                    borderColor: 'border-gray-500/30',
                    pulseColor: 'bg-gray-500'
                };
        }
    };

    const config = getStatusConfig();
    const Icon = config.icon;

    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${config.bgColor} ${config.borderColor} backdrop-blur-sm`}>
            {/* Pulse indicator */}
            <div className="relative flex h-2 w-2">
                {status === 'connected' && (
                    <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${config.pulseColor} opacity-75`}></span>
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${config.pulseColor}`}></span>
            </div>

            {/* Icon */}
            <Icon
                size={14}
                className={`${config.color} ${status === 'connecting' || status === 'reconnecting' ? 'animate-pulse' : ''}`}
            />

            {/* Status text */}
            <span className={`text-[10px] font-medium ${config.color} uppercase tracking-wide`}>
                {config.text}
            </span>

            {/* Latency indicator (only show when connected) */}
            {status === 'connected' && latency > 0 && (
                <span className="text-[9px] text-cyan-500/70 ml-1">
                    {latency}ms
                </span>
            )}
        </div>
    );
};

export default ConnectionStatus;
