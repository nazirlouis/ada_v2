import React from 'react';
import { X, Keyboard } from 'lucide-react';

/**
 * Keyboard Shortcuts Help Overlay
 * Shows available keyboard shortcuts
 */
const KeyboardShortcutsHelp = ({ onClose, isOpen }) => {
    if (!isOpen) return null;

    const shortcuts = [
        { keys: ['Ctrl', 'M'], description: 'Toggle Mute/Unmute' },
        { keys: ['Ctrl', ','], description: 'Open Settings' },
        { keys: ['Ctrl', 'R'], description: 'Toggle Recording' },
        { keys: ['Ctrl', 'K'], description: 'Clear Chat' },
        { keys: ['Ctrl', '/'], description: 'Focus Text Input' },
        { keys: ['Esc'], description: 'Close Modals' },
        { keys: ['?'], description: 'Show This Help' }
    ];

    // Detect OS for display
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const modKey = isMac ? '⌘' : 'Ctrl';

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="bg-gray-900 border border-cyan-500/50 rounded-lg p-6 max-w-md w-full mx-4 shadow-[0_0_50px_rgba(6,182,212,0.3)]">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-2">
                        <Keyboard size={20} className="text-cyan-400" />
                        <h2 className="text-lg font-bold text-cyan-400 uppercase tracking-wide">
                            Keyboard Shortcuts
                        </h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-cyan-600 hover:text-cyan-400 transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Shortcuts List */}
                <div className="space-y-3">
                    {shortcuts.map((shortcut, index) => (
                        <div
                            key={index}
                            className="flex items-center justify-between p-3 bg-gray-800/50 rounded border border-cyan-900/30 hover:border-cyan-700/50 transition-colors"
                        >
                            <span className="text-sm text-cyan-100">{shortcut.description}</span>
                            <div className="flex items-center gap-1">
                                {shortcut.keys.map((key, keyIndex) => (
                                    <React.Fragment key={keyIndex}>
                                        <kbd className="px-2 py-1 bg-gray-700 text-cyan-300 rounded text-xs font-mono border border-cyan-800/50 shadow-inner min-w-[2rem] text-center">
                                            {key === 'Ctrl' ? modKey : key}
                                        </kbd>
                                        {keyIndex < shortcut.keys.length - 1 && (
                                            <span className="text-cyan-600 text-xs">+</span>
                                        )}
                                    </React.Fragment>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Footer */}
                <div className="mt-6 pt-4 border-t border-cyan-900/30">
                    <p className="text-xs text-cyan-500/70 text-center">
                        Press <kbd className="px-1.5 py-0.5 bg-gray-700 text-cyan-300 rounded text-[10px] font-mono">?</kbd> anytime to show this help
                    </p>
                </div>
            </div>
        </div>
    );
};

export default KeyboardShortcutsHelp;
