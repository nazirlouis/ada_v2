import { useEffect } from 'react';

/**
 * Custom hook for keyboard shortcuts
 * Provides quick access to common ADA functions
 */
const useKeyboardShortcuts = ({
    onToggleMute,
    onToggleSettings,
    onStartRecording,
    onStopRecording,
    onClearChat,
    onFocusInput,
    isRecording = false
}) => {
    useEffect(() => {
        const handleKeyPress = (event) => {
            // Check if user is typing in an input field
            const isInputFocused =
                event.target.tagName === 'INPUT' ||
                event.target.tagName === 'TEXTAREA' ||
                event.target.isContentEditable;

            // Ctrl/Cmd + M: Toggle Mute
            if ((event.ctrlKey || event.metaKey) && event.key === 'm') {
                event.preventDefault();
                if (onToggleMute) onToggleMute();
                return;
            }

            // Ctrl/Cmd + ,: Open Settings
            if ((event.ctrlKey || event.metaKey) && event.key === ',') {
                event.preventDefault();
                if (onToggleSettings) onToggleSettings();
                return;
            }

            // Ctrl/Cmd + R: Toggle Recording
            if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
                event.preventDefault();
                if (isRecording && onStopRecording) {
                    onStopRecording();
                } else if (!isRecording && onStartRecording) {
                    onStartRecording();
                }
                return;
            }

            // Ctrl/Cmd + K: Clear Chat (when not in input)
            if ((event.ctrlKey || event.metaKey) && event.key === 'k' && !isInputFocused) {
                event.preventDefault();
                if (onClearChat) onClearChat();
                return;
            }

            // Ctrl/Cmd + /: Focus Input
            if ((event.ctrlKey || event.metaKey) && event.key === '/') {
                event.preventDefault();
                if (onFocusInput) onFocusInput();
                return;
            }

            // Escape: Close modals/settings
            if (event.key === 'Escape') {
                if (onToggleSettings) onToggleSettings(false);
                return;
            }
        };

        window.addEventListener('keydown', handleKeyPress);

        return () => {
            window.removeEventListener('keydown', handleKeyPress);
        };
    }, [onToggleMute, onToggleSettings, onStartRecording, onStopRecording, onClearChat, onFocusInput, isRecording]);
};

export default useKeyboardShortcuts;

/**
 * Keyboard Shortcuts Reference:
 *
 * Ctrl/Cmd + M - Toggle Mute
 * Ctrl/Cmd + , - Open Settings
 * Ctrl/Cmd + R - Toggle Recording
 * Ctrl/Cmd + K - Clear Chat
 * Ctrl/Cmd + / - Focus Input
 * Escape - Close Settings
 */
