import React, { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react';

/**
 * Toast Notification System
 * Shows temporary notifications for errors, success, warnings, and info
 */
const Toast = ({ message, type = 'info', duration = 3000, onClose }) => {
    const [isVisible, setIsVisible] = useState(true);
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => {
            handleClose();
        }, duration);

        return () => clearTimeout(timer);
    }, [duration]);

    const handleClose = () => {
        setIsExiting(true);
        setTimeout(() => {
            setIsVisible(false);
            if (onClose) onClose();
        }, 300);
    };

    if (!isVisible) return null;

    const getConfig = () => {
        switch (type) {
            case 'success':
                return {
                    icon: CheckCircle,
                    bgColor: 'bg-green-500/90',
                    borderColor: 'border-green-400',
                    iconColor: 'text-green-100'
                };
            case 'error':
                return {
                    icon: XCircle,
                    bgColor: 'bg-red-500/90',
                    borderColor: 'border-red-400',
                    iconColor: 'text-red-100'
                };
            case 'warning':
                return {
                    icon: AlertCircle,
                    bgColor: 'bg-yellow-500/90',
                    borderColor: 'border-yellow-400',
                    iconColor: 'text-yellow-100'
                };
            default:
                return {
                    icon: Info,
                    bgColor: 'bg-cyan-500/90',
                    borderColor: 'border-cyan-400',
                    iconColor: 'text-cyan-100'
                };
        }
    };

    const config = getConfig();
    const Icon = config.icon;

    return (
        <div
            className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${config.bgColor} ${config.borderColor} backdrop-blur-xl shadow-2xl ${
                isExiting ? 'animate-slide-out-right' : 'animate-slide-in-right'
            }`}
        >
            <Icon size={20} className={config.iconColor} />
            <span className="text-sm text-white font-medium flex-1">{message}</span>
            <button
                onClick={handleClose}
                className="text-white/70 hover:text-white transition-colors"
            >
                <X size={16} />
            </button>
        </div>
    );
};

/**
 * Toast Container - Manages multiple toasts
 */
export const ToastContainer = ({ toasts = [], onRemove }) => {
    return (
        <div className="fixed top-20 right-4 z-[60] flex flex-col gap-2 max-w-sm">
            {toasts.map((toast) => (
                <Toast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    duration={toast.duration}
                    onClose={() => onRemove(toast.id)}
                />
            ))}
        </div>
    );
};

/**
 * Hook to manage toasts
 */
export const useToast = () => {
    const [toasts, setToasts] = useState([]);

    const addToast = (message, type = 'info', duration = 3000) => {
        const id = Date.now() + Math.random();
        setToasts((prev) => [...prev, { id, message, type, duration }]);
    };

    const removeToast = (id) => {
        setToasts((prev) => prev.filter((toast) => toast.id !== id));
    };

    return {
        toasts,
        addToast,
        removeToast,
        success: (msg, duration) => addToast(msg, 'success', duration),
        error: (msg, duration) => addToast(msg, 'error', duration),
        warning: (msg, duration) => addToast(msg, 'warning', duration),
        info: (msg, duration) => addToast(msg, 'info', duration)
    };
};

export default Toast;
