import React, { useEffect, useRef } from 'react';

/**
 * Real-time VU (Volume Unit) Meter for audio visualization
 * Shows input/output levels with peak indicators
 */
const AudioVUMeter = ({ level = 0, peak = 0, label = "Audio", clipping = false }) => {
    const canvasRef = useRef(null);
    const animationRef = useRef(null);
    const peakHoldRef = useRef(0);
    const peakHoldTimeRef = useRef(0);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        const drawMeter = () => {
            // Clear canvas
            ctx.fillStyle = '#0a0a0a';
            ctx.fillRect(0, 0, width, height);

            // Calculate bar width based on level (0-1)
            const barWidth = Math.min(level * width, width);

            // Determine color based on level
            let gradient;
            if (clipping) {
                gradient = ctx.createLinearGradient(0, 0, width, 0);
                gradient.addColorStop(0, '#ef4444'); // Red
                gradient.addColorStop(1, '#dc2626');
            } else if (level > 0.9) {
                gradient = ctx.createLinearGradient(0, 0, width, 0);
                gradient.addColorStop(0, '#f59e0b'); // Orange
                gradient.addColorStop(1, '#ef4444'); // Red
            } else if (level > 0.7) {
                gradient = ctx.createLinearGradient(0, 0, width, 0);
                gradient.addColorStop(0, '#22d3ee'); // Cyan
                gradient.addColorStop(0.7, '#f59e0b'); // Orange
                gradient.addColorStop(1, '#ef4444'); // Red
            } else {
                gradient = ctx.createLinearGradient(0, 0, width, 0);
                gradient.addColorStop(0, '#06b6d4'); // Cyan
                gradient.addColorStop(1, '#22d3ee');
            }

            // Draw level bar
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, barWidth, height);

            // Peak hold logic
            const currentTime = Date.now();
            if (peak > peakHoldRef.current) {
                peakHoldRef.current = peak;
                peakHoldTimeRef.current = currentTime;
            } else if (currentTime - peakHoldTimeRef.current > 1500) {
                // Decay peak after 1.5 seconds
                peakHoldRef.current = Math.max(peakHoldRef.current - 0.01, level);
            }

            // Draw peak indicator
            if (peakHoldRef.current > 0) {
                const peakX = peakHoldRef.current * width;
                ctx.fillStyle = clipping ? '#dc2626' : '#fbbf24';
                ctx.fillRect(peakX - 2, 0, 3, height);
            }

            // Draw scale marks
            ctx.strokeStyle = '#374151';
            ctx.lineWidth = 1;
            for (let i = 0.1; i <= 0.9; i += 0.1) {
                const x = i * width;
                ctx.beginPath();
                ctx.moveTo(x, height - 3);
                ctx.lineTo(x, height);
                ctx.stroke();
            }

            // Draw red zone indicator
            const redZoneStart = 0.9 * width;
            ctx.fillStyle = 'rgba(239, 68, 68, 0.1)';
            ctx.fillRect(redZoneStart, 0, width - redZoneStart, height);

            animationRef.current = requestAnimationFrame(drawMeter);
        };

        drawMeter();

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [level, peak, clipping]);

    return (
        <div className="flex flex-col gap-1">
            <div className="flex justify-between items-center">
                <span className="text-[10px] text-cyan-400 font-semibold uppercase tracking-wide">
                    {label}
                </span>
                <div className="flex items-center gap-2">
                    <span className="text-[9px] text-cyan-500">
                        {(level * 100).toFixed(0)}%
                    </span>
                    {clipping && (
                        <span className="text-[9px] text-red-400 font-bold animate-pulse">
                            CLIP!
                        </span>
                    )}
                </div>
            </div>
            <canvas
                ref={canvasRef}
                width={200}
                height={16}
                className="w-full h-4 rounded border border-cyan-900/50 shadow-inner"
            />
        </div>
    );
};

export default AudioVUMeter;
