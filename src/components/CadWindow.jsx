import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Canvas, useLoader, useFrame } from '@react-three/fiber';
import { OrbitControls, Center, Stage } from '@react-three/drei';
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import { Printer } from 'lucide-react';

const GeometryModel = ({ geometry }) => {
    return (
        <mesh geometry={geometry} castShadow receiveShadow>
            <meshStandardMaterial color="#06b6d4" roughness={0.3} metalness={0.8} />
        </mesh>
    );
};

const LoadingCube = () => {
    const meshRef = React.useRef();
    useFrame((state, delta) => {
        meshRef.current.rotation.x += delta;
        meshRef.current.rotation.y += delta;
    });
    return (
        <mesh ref={meshRef}>
            <boxGeometry args={[10, 10, 10]} />
            <meshStandardMaterial wireframe color="cyan" transparent opacity={0.5} />
        </mesh>
    );
};

const CadWindow = ({ data, thoughts, retryInfo = {}, onClose, socket }) => {
    // data format: { format: "stl", data: "base64..." }
    const [isIterating, setIsIterating] = useState(false);
    const [prompt, setPrompt] = useState("");
    const [isSending, setIsSending] = useState(false);
    const thoughtsEndRef = useRef(null);

    // Debug log
    useEffect(() => {
        if (data) console.log("CadWindow Data:", data.format);
    }, [data]);

    // Auto-scroll thoughts panel
    useEffect(() => {
        if (thoughtsEndRef.current) {
            thoughtsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [thoughts]);

    const geometry = useMemo(() => {
        if (!data || data.format !== 'stl' || !data.data) return null;

        try {
            // Convert Base64 to ArrayBuffer
            const byteCharacters = atob(data.data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);

            // Parse directly using THREE.STLLoader
            const loader = new STLLoader();
            const geom = loader.parse(byteArray.buffer);
            geom.center(); // Optional: Center the geometry
            return geom;
        } catch (e) {
            console.error("Failed to decode/parse STL:", e);
            return null;
        }
    }, [data]);

    const handleIterate = () => {
        if (!prompt.trim()) return;
        setIsSending(true);
        // Assuming socket is passed as prop or available globally. 
        // If not, we might need to emit via window event or refactor App.jsx to pass it.
        // For now, looking at App.jsx structure, socket might not be prop. 
        // If socket is missing, we can use window.socket if available or emit a custom event.

        if (socket) {
            socket.emit('iterate_cad', { prompt });
        } else {
            console.error("Socket not available in CadWindow");
        }

        setIsIterating(false);
        setPrompt("");
        setIsSending(false);
    };

    return (
        <div className="w-full h-full relative group bg-gray-900 rounded-lg overflow-hidden border border-cyan-500/30">
            {/* Close Button */}
            <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={onClose} className="bg-red-500/20 hover:bg-red-500/50 text-red-500 p-1 rounded">X</button>
            </div>

            {/* Top Toolbar */}
            <div className="absolute top-2 left-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                <button
                    onClick={() => setIsIterating(true)}
                    className="bg-cyan-500/20 hover:bg-cyan-500/50 text-cyan-400 text-xs px-2 py-1 rounded border border-cyan-500/30 backdrop-blur-sm"
                >
                    ITERATE
                </button>
                <button
                    onClick={() => {
                        // Trigger print from current available data if possible, or just open printer window
                        // Since slicing requires backend file, we ideally emit an event or show UI
                        // For now we'll rely on voice or tool window, but user requested button here.
                        // Best approach: Open Printer Window + Auto-populate / Trigger
                        if (socket) socket.emit('request_print_window');
                    }}
                    className="bg-green-500/20 hover:bg-green-500/50 text-green-400 text-xs px-2 py-1 rounded border border-green-500/30 backdrop-blur-sm flex items-center gap-1"
                >
                    <Printer size={12} /> PRINT
                </button>
            </div>

            {/* Iteration Overlay */}
            {isIterating && (
                <div className="absolute inset-0 z-20 bg-black/80 flex items-center justify-center p-4">
                    <div className="bg-gray-800 border border-cyan-500/50 rounded p-4 w-full max-w-sm pointer-events-auto shadow-[0_0_20px_rgba(6,182,212,0.2)]">
                        <h4 className="text-cyan-400 text-sm mb-2 font-mono">Refine Design</h4>
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="e.g., Make the wheels bigger..."
                            className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white text-sm mb-3 focus:outline-none focus:border-cyan-500 h-24"
                            autoFocus
                        />
                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => setIsIterating(false)}
                                className="text-gray-400 text-xs hover:text-white px-2 py-1"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleIterate}
                                disabled={isSending}
                                className="bg-cyan-600 hover:bg-cyan-500 text-white text-xs px-3 py-1 rounded"
                            >
                                {isSending ? "Sending..." : "Update"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <Canvas shadows camera={{ position: [4, 4, 4], fov: 45 }}>
                <color attach="background" args={['#101010']} />

                <Stage environment="city" intensity={0.5}>
                    {data?.format === 'loading' ? (
                        <LoadingCube />
                    ) : (
                        geometry && (
                            <Center>
                                <GeometryModel geometry={geometry} />
                            </Center>
                        )
                    )}
                </Stage>

                <OrbitControls autoRotate={!isIterating} autoRotateSpeed={1} makeDefault />
            </Canvas>

            {/* Streaming Thoughts Panel */}
            {data?.format === 'loading' && (
                <div className="absolute inset-y-0 right-0 w-2/5 p-4 bg-black/70 backdrop-blur-sm border-l border-green-500/30 overflow-hidden flex flex-col">
                    <div className="flex items-center justify-between mb-2">
                        <h4 className="text-green-400 text-xs font-mono tracking-widest uppercase flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                            Designer Thinking...
                        </h4>
                        {retryInfo.attempt && (
                            <span className={`text-xs font-mono px-2 py-0.5 rounded ${retryInfo.error ? 'bg-yellow-500/20 text-yellow-400' : 'bg-cyan-500/20 text-cyan-400'}`}>
                                Attempt {retryInfo.attempt}/{retryInfo.maxAttempts || 3}
                            </span>
                        )}
                    </div>
                    {retryInfo.error && (
                        <div className="mb-2 p-2 bg-red-500/10 border border-red-500/30 rounded text-red-400 text-xs font-mono">
                            <span className="text-red-500 font-bold">⚠ Error:</span> {retryInfo.error}
                        </div>
                    )}
                    <div className="flex-1 overflow-y-auto text-green-400/80 text-xs font-mono whitespace-pre-wrap leading-relaxed scrollbar-thin scrollbar-thumb-green-500/30">
                        {thoughts}
                        <div ref={thoughtsEndRef} />
                    </div>
                </div>
            )}

            <div className="absolute bottom-2 left-2 text-[10px] text-cyan-500/50 font-mono tracking-widest pointer-events-none">
                CAD_ENGINE_V2: {data?.format?.toUpperCase() || "READY"}
            </div>
        </div>
    );
};

export default CadWindow;
