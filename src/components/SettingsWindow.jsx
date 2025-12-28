import React, { useState, useEffect } from 'react';
import { X, Mic, Square, Circle, Activity } from 'lucide-react';

const TOOLS = [
    { id: 'generate_cad', label: 'Generate CAD' },
    { id: 'run_web_agent', label: 'Web Agent' },
    { id: 'create_directory', label: 'Create Folder' },
    { id: 'write_file', label: 'Write File' },
    { id: 'read_directory', label: 'Read Directory' },
    { id: 'read_file', label: 'Read File' },
    { id: 'create_project', label: 'Create Project' },
    { id: 'switch_project', label: 'Switch Project' },
    { id: 'list_projects', label: 'List Projects' },
    { id: 'list_smart_devices', label: 'List Devices' },
    { id: 'control_light', label: 'Control Light' },
    { id: 'discover_printers', label: 'Discover Printers' },
    { id: 'print_stl', label: 'Print 3D Model' },
    { id: 'iterate_cad', label: 'Iterate CAD' },
];

const SettingsWindow = ({
    socket,
    micDevices,
    speakerDevices,
    webcamDevices,
    selectedMicId,
    setSelectedMicId,
    selectedSpeakerId,
    setSelectedSpeakerId,
    selectedWebcamId,
    setSelectedWebcamId,
    cursorSensitivity,
    setCursorSensitivity,
    isCameraFlipped,
    setIsCameraFlipped,
    handleFileUpload,
    onClose
}) => {
    const [permissions, setPermissions] = useState({});
    const [faceAuthEnabled, setFaceAuthEnabled] = useState(false);

    // Enhanced audio settings
    const [availableVoices, setAvailableVoices] = useState(['Kore']);
    const [selectedVoice, setSelectedVoice] = useState('Kore');
    const [noiseGateEnabled, setNoiseGateEnabled] = useState(true);
    const [wakeWordEnabled, setWakeWordEnabled] = useState(false);
    const [recordingEnabled, setRecordingEnabled] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [audioMetrics, setAudioMetrics] = useState(null);
    const [isTesting, setIsTesting] = useState(false);

    useEffect(() => {
        // Request initial data
        socket.emit('get_settings');
        socket.emit('get_available_voices');
        socket.emit('get_recording_status');

        // Listen for updates
        const handleSettings = (settings) => {
            console.log("Received settings:", settings);
            if (settings) {
                if (settings.tool_permissions) setPermissions(settings.tool_permissions);
                if (typeof settings.face_auth_enabled !== 'undefined') {
                    setFaceAuthEnabled(settings.face_auth_enabled);
                    localStorage.setItem('face_auth_enabled', settings.face_auth_enabled);
                }
                // Enhanced audio settings
                if (settings.voice_name) setSelectedVoice(settings.voice_name);
                if (typeof settings.enable_noise_gate !== 'undefined') setNoiseGateEnabled(settings.enable_noise_gate);
                if (typeof settings.enable_wake_word !== 'undefined') setWakeWordEnabled(settings.enable_wake_word);
                if (typeof settings.enable_recording !== 'undefined') setRecordingEnabled(settings.enable_recording);
            }
        };

        const handleAvailableVoices = (voices) => {
            console.log("Available voices:", voices);
            setAvailableVoices(voices);
        };

        const handleRecordingStatus = (status) => {
            setIsRecording(status.recording);
        };

        const handleAudioMetrics = (metrics) => {
            setAudioMetrics(metrics);
        };

        socket.on('settings', handleSettings);
        socket.on('available_voices', handleAvailableVoices);
        socket.on('recording_status', handleRecordingStatus);
        socket.on('audio_metrics', handleAudioMetrics);

        return () => {
            socket.off('settings', handleSettings);
            socket.off('available_voices', handleAvailableVoices);
            socket.off('recording_status', handleRecordingStatus);
            socket.off('audio_metrics', handleAudioMetrics);
        };
    }, [socket]);

    const togglePermission = (toolId) => {
        const currentVal = permissions[toolId] !== false; // Default True
        const nextVal = !currentVal;

        // Update local mostly for responsiveness, but socket roundtrip handles truth
        // setPermissions(prev => ({ ...prev, [toolId]: nextVal }));

        // Send update
        socket.emit('update_settings', { tool_permissions: { [toolId]: nextVal } });
    };

    const toggleFaceAuth = () => {
        const newVal = !faceAuthEnabled;
        setFaceAuthEnabled(newVal); // Optimistic Update
        localStorage.setItem('face_auth_enabled', newVal);
        socket.emit('update_settings', { face_auth_enabled: newVal });
    };

    const toggleCameraFlip = () => {
        const newVal = !isCameraFlipped;
        setIsCameraFlipped(newVal);
        socket.emit('update_settings', { camera_flipped: newVal });
    };

    const handleVoiceChange = (e) => {
        const newVoice = e.target.value;
        setSelectedVoice(newVoice);
        socket.emit('update_settings', { voice_name: newVoice });
    };

    const toggleNoiseGate = () => {
        const newVal = !noiseGateEnabled;
        setNoiseGateEnabled(newVal);
        socket.emit('update_settings', { enable_noise_gate: newVal });
    };

    const toggleWakeWord = () => {
        const newVal = !wakeWordEnabled;
        setWakeWordEnabled(newVal);
        socket.emit('update_settings', { enable_wake_word: newVal });
    };

    const toggleRecordingEnabled = () => {
        const newVal = !recordingEnabled;
        setRecordingEnabled(newVal);
        socket.emit('update_settings', { enable_recording: newVal });
    };

    const toggleRecording = () => {
        if (isRecording) {
            socket.emit('stop_recording');
        } else {
            socket.emit('start_recording');
        }
    };

    const testMicrophone = () => {
        setIsTesting(true);
        // Request audio stats for 3 seconds
        const interval = setInterval(() => {
            socket.emit('get_audio_stats');
        }, 100);

        setTimeout(() => {
            clearInterval(interval);
            setIsTesting(false);
        }, 3000);
    };

    return (
        <div className="absolute top-20 right-10 bg-black/90 border border-cyan-500/50 p-4 rounded-lg z-50 w-80 backdrop-blur-xl shadow-[0_0_30px_rgba(6,182,212,0.2)]">
            <div className="flex justify-between items-center mb-4 border-b border-cyan-900/50 pb-2">
                <h2 className="text-cyan-400 font-bold text-sm uppercase tracking-wider">Settings</h2>
                <button onClick={onClose} className="text-cyan-600 hover:text-cyan-400">
                    <X size={16} />
                </button>
            </div>

            {/* Authentication Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Security</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                    <span className="text-cyan-100/80">Face Authentication</span>
                    <button
                        onClick={toggleFaceAuth}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${faceAuthEnabled ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                    >
                        <div
                            className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${faceAuthEnabled ? 'translate-x-4' : 'translate-x-0'}`}
                        />
                    </button>
                </div>
            </div>

            {/* Voice Selection */}
            <div className="mb-4">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Ada Voice</h3>
                <select
                    value={selectedVoice}
                    onChange={handleVoiceChange}
                    className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                >
                    {availableVoices.map((voice) => (
                        <option key={voice} value={voice}>
                            {voice}
                        </option>
                    ))}
                </select>
                <p className="text-[10px] text-cyan-500/60 mt-1">Restart audio session to apply</p>
            </div>

            {/* Microphone Section */}
            <div className="mb-4">
                <div className="flex justify-between items-center mb-2">
                    <h3 className="text-cyan-400 font-bold text-xs uppercase tracking-wider opacity-80">Microphone</h3>
                    <button
                        onClick={testMicrophone}
                        disabled={isTesting}
                        className={`text-[10px] px-2 py-1 rounded ${
                            isTesting
                                ? 'bg-cyan-700 text-cyan-300'
                                : 'bg-cyan-900 text-cyan-400 hover:bg-cyan-800'
                        } transition-colors flex items-center gap-1`}
                    >
                        {isTesting ? <Activity size={10} className="animate-pulse" /> : <Mic size={10} />}
                        {isTesting ? 'Testing...' : 'Test'}
                    </button>
                </div>
                <select
                    value={selectedMicId}
                    onChange={(e) => setSelectedMicId(e.target.value)}
                    className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                >
                    {micDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Microphone ${i + 1}`}
                        </option>
                    ))}
                </select>
                {audioMetrics && isTesting && (
                    <div className="mt-2 p-2 bg-gray-900/70 rounded text-[10px]">
                        <div className="flex justify-between">
                            <span className="text-cyan-400">Level:</span>
                            <span className="text-cyan-100">{(audioMetrics.rms * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-cyan-400">Peak:</span>
                            <span className="text-cyan-100">{(audioMetrics.peak * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                            <span className={audioMetrics.clipping ? 'text-red-400' : 'text-cyan-400'}>
                                Clipping:
                            </span>
                            <span className={audioMetrics.clipping ? 'text-red-300' : 'text-green-300'}>
                                {audioMetrics.clipping ? 'YES' : 'NO'}
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Speaker Section */}
            <div className="mb-4">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Speaker</h3>
                <select
                    value={selectedSpeakerId}
                    onChange={(e) => setSelectedSpeakerId(e.target.value)}
                    className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                >
                    {speakerDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Speaker ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Webcam Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Webcam</h3>
                <select
                    value={selectedWebcamId}
                    onChange={(e) => setSelectedWebcamId(e.target.value)}
                    className="w-full bg-gray-900 border border-cyan-800 rounded p-2 text-xs text-cyan-100 focus:border-cyan-400 outline-none"
                >
                    {webcamDevices.map((device, i) => (
                        <option key={device.deviceId} value={device.deviceId}>
                            {device.label || `Camera ${i + 1}`}
                        </option>
                    ))}
                </select>
            </div>

            {/* Cursor Section */}
            <div className="mb-6">
                <div className="flex justify-between mb-2">
                    <h3 className="text-cyan-400 font-bold text-xs uppercase tracking-wider opacity-80">Cursor Sensitivity</h3>
                    <span className="text-xs text-cyan-500">{cursorSensitivity}x</span>
                </div>
                <input
                    type="range"
                    min="1.0"
                    max="5.0"
                    step="0.1"
                    value={cursorSensitivity}
                    onChange={(e) => setCursorSensitivity(parseFloat(e.target.value))}
                    className="w-full accent-cyan-400 cursor-pointer h-1 bg-gray-800 rounded-lg appearance-none"
                />
            </div>

            {/* Gesture Control Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Gesture Control</h3>
                <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                    <span className="text-cyan-100/80">Flip Camera Horizontal</span>
                    <button
                        onClick={toggleCameraFlip}
                        className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${isCameraFlipped ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                    >
                        <div
                            className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${isCameraFlipped ? 'translate-x-4' : 'translate-x-0'}`}
                        />
                    </button>
                </div>
            </div>

            {/* Audio Enhancement */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Audio Enhancement</h3>
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                        <span className="text-cyan-100/80">Noise Suppression</span>
                        <button
                            onClick={toggleNoiseGate}
                            className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${noiseGateEnabled ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                        >
                            <div
                                className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${noiseGateEnabled ? 'translate-x-4' : 'translate-x-0'}`}
                            />
                        </button>
                    </div>
                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                        <span className="text-cyan-100/80">Wake Word Detection</span>
                        <button
                            onClick={toggleWakeWord}
                            className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${wakeWordEnabled ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                        >
                            <div
                                className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${wakeWordEnabled ? 'translate-x-4' : 'translate-x-0'}`}
                            />
                        </button>
                    </div>
                    {wakeWordEnabled && (
                        <p className="text-[10px] text-yellow-500/80">Requires Porcupine API key in settings.json</p>
                    )}
                </div>
            </div>

            {/* Recording Controls */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Recording</h3>
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                        <span className="text-cyan-100/80">Enable Recording</span>
                        <button
                            onClick={toggleRecordingEnabled}
                            className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${recordingEnabled ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                        >
                            <div
                                className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${recordingEnabled ? 'translate-x-4' : 'translate-x-0'}`}
                            />
                        </button>
                    </div>
                    {recordingEnabled && (
                        <button
                            onClick={toggleRecording}
                            disabled={!recordingEnabled}
                            className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded transition-colors ${
                                isRecording
                                    ? 'bg-red-900/80 text-red-200 hover:bg-red-800/80'
                                    : 'bg-cyan-900 text-cyan-400 hover:bg-cyan-800'
                            }`}
                        >
                            {isRecording ? (
                                <>
                                    <Square size={12} className="fill-current" />
                                    <span className="text-xs">Stop Recording</span>
                                </>
                            ) : (
                                <>
                                    <Circle size={12} className="fill-current" />
                                    <span className="text-xs">Start Recording</span>
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>

            {/* Tool Permissions Section */}
            <div className="mb-6">
                <h3 className="text-cyan-400 font-bold mb-3 text-xs uppercase tracking-wider opacity-80">Tool Confirmations</h3>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                    {TOOLS.map(tool => {
                        const isRequired = permissions[tool.id] !== false; // Default True
                        return (
                            <div key={tool.id} className="flex items-center justify-between text-xs bg-gray-900/50 p-2 rounded border border-cyan-900/30">
                                <span className="text-cyan-100/80">{tool.label}</span>
                                <button
                                    onClick={() => togglePermission(tool.id)}
                                    className={`relative w-8 h-4 rounded-full transition-colors duration-200 ${isRequired ? 'bg-cyan-500/80' : 'bg-gray-700'}`}
                                >
                                    <div
                                        className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-200 ${isRequired ? 'translate-x-4' : 'translate-x-0'}`}
                                    />
                                </button>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Memory Section */}
            <div>
                <h3 className="text-cyan-400 font-bold mb-2 text-xs uppercase tracking-wider opacity-80">Memory Data</h3>
                <div className="flex flex-col gap-2">
                    <label className="text-[10px] text-cyan-500/60 uppercase">Upload Memory Text</label>
                    <input
                        type="file"
                        accept=".txt"
                        onChange={handleFileUpload}
                        className="text-xs text-cyan-100 bg-gray-900 border border-cyan-800 rounded p-2 file:mr-2 file:py-1 file:px-2 file:rounded-full file:border-0 file:text-[10px] file:font-semibold file:bg-cyan-900 file:text-cyan-400 hover:file:bg-cyan-800 cursor-pointer"
                    />
                </div>
            </div>
        </div>
    );
};

export default SettingsWindow;
