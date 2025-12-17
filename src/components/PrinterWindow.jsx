import React, { useState, useEffect } from 'react';
import { X, RefreshCw, Printer, Thermometer, Clock, FileText, CheckCircle, AlertTriangle } from 'lucide-react';

const PrinterWindow = ({
    socket,
    position,
    onClose,
    activeDragElement,
    setActiveDragElement,
    onMouseDown
}) => {
    const [isDiscovering, setIsDiscovering] = useState(false);
    const [printers, setPrinters] = useState([]); // [{ name, host, port, printer_type, status: {...} }]
    const [selectedPrinter, setSelectedPrinter] = useState(null);

    // Initial discovery on mount
    useEffect(() => {
        if (socket) {
            handleDiscover();

            socket.on('printer_list', (list) => {
                setPrinters(list);
                setIsDiscovering(false);
            });

            socket.on('print_status_update', (data) => {
                // Update specific printer status in list
                setPrinters(prev => prev.map(p =>
                    p.name === data.printer ? { ...p, status: data } : p
                ));
            });
        }
        return () => {
            if (socket) {
                socket.off('printer_list');
                socket.off('print_status_update');
            }
        };
    }, [socket]);

    const handleDiscover = () => {
        setIsDiscovering(true);
        socket.emit('discover_printers');
        // Fallback timeout
        setTimeout(() => setIsDiscovering(false), 5000);
    };

    const getStatusColor = (state) => {
        if (!state) return 'text-gray-400';
        const s = state.toLowerCase();
        if (s.includes('print')) return 'text-green-400';
        if (s.includes('paus')) return 'text-yellow-400';
        if (s.includes('error') || s.includes('fail')) return 'text-red-400';
        return 'text-cyan-400';
    };

    return (
        <div
            id="printer-window"
            onMouseDown={onMouseDown}
            style={{
                position: 'absolute',
                left: position.x,
                top: position.y,
                transform: 'translate(-50%, -50%)',
                width: '400px',
                zIndex: activeDragElement === 'printer-window' ? 50 : 10
            }}
            className="pointer-events-auto backdrop-blur-xl bg-black/80 border border-green-500/30 rounded-2xl shadow-[0_0_30px_rgba(74,222,128,0.1)] overflow-hidden flex flex-col"
        >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10 bg-white/5 cursor-grab active:cursor-grabbing">
                <div className="flex items-center gap-2">
                    <Printer size={16} className="text-green-400" />
                    <span className="text-xs font-bold tracking-widest text-green-100 uppercase">3D Printers</span>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleDiscover}
                        disabled={isDiscovering}
                        className={`p-1.5 hover:bg-white/10 rounded-full transition-colors ${isDiscovering ? 'animate-spin text-green-400' : 'text-gray-400 hover:text-green-400'}`}
                    >
                        <RefreshCw size={14} />
                    </button>
                    <button
                        onClick={onClose}
                        className="p-1.5 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-colors"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="p-4 max-h-[400px] overflow-y-auto">
                {printers.length === 0 ? (
                    <div className="text-center py-8 text-white/30 text-xs">
                        {isDiscovering ? (
                            <div className="flex flex-col items-center gap-2">
                                <RefreshCw className="animate-spin" size={20} />
                                <span>Scanning Network...</span>
                            </div>
                        ) : (
                            "No printers found. Make sure OctoPrint/Moonraker is running."
                        )}
                    </div>
                ) : (
                    <div className="space-y-3">
                        {printers.map((printer, idx) => (
                            <div key={idx} className="bg-white/5 border border-white/10 rounded-lg p-3 hover:border-green-500/30 transition-all">
                                <div className="flex justify-between items-start mb-2">
                                    <div>
                                        <div className="font-bold text-sm text-green-50">{printer.name}</div>
                                        <div className="text-[10px] text-white/40 uppercase tracking-wider">{printer.host}:{printer.port} • {printer.printer_type}</div>
                                    </div>
                                    {printer.status && (
                                        <div className={`text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/5 ${getStatusColor(printer.status.state)}`}>
                                            {printer.status.state?.toUpperCase() || "IDLE"}
                                        </div>
                                    )}
                                </div>

                                {printer.status && (
                                    <div className="space-y-2 mt-3 pt-3 border-t border-white/5">
                                        {/* Progress Bar */}
                                        {printer.status.progress_percent > 0 && (
                                            <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-green-500 transition-all duration-500"
                                                    style={{ width: `${printer.status.progress_percent}%` }}
                                                />
                                            </div>
                                        )}

                                        {/* Stats Grid */}
                                        <div className="grid grid-cols-2 gap-2 text-[10px] text-white/60">
                                            {printer.status.filename && (
                                                <div className="col-span-2 flex items-center gap-1.5 truncate">
                                                    <FileText size={10} className="text-green-400" />
                                                    <span className="truncate">{printer.status.filename}</span>
                                                </div>
                                            )}
                                            {printer.status.temperatures?.hotend && (
                                                <div className="flex items-center gap-1.5">
                                                    <Thermometer size={10} className="text-red-400" />
                                                    <span>E: {Math.round(printer.status.temperatures.hotend.current)}°C</span>
                                                </div>
                                            )}
                                            {printer.status.temperatures?.bed && (
                                                <div className="flex items-center gap-1.5">
                                                    <Thermometer size={10} className="text-blue-400" />
                                                    <span>B: {Math.round(printer.status.temperatures.bed.current)}°C</span>
                                                </div>
                                            )}
                                            {printer.status.time_remaining && (
                                                <div className="flex items-center gap-1.5">
                                                    <Clock size={10} className="text-yellow-400" />
                                                    <span>{printer.status.time_remaining} left</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PrinterWindow;
