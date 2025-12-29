"""
Enhanced Audio Processing Module for ADA V2
Provides advanced voice activity detection, noise suppression, and audio quality monitoring.
"""

import numpy as np
import struct
import time
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False
    print("[AUDIO] webrtcvad not available, falling back to RMS-based VAD")

try:
    from scipy import signal as scipy_signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("[AUDIO] scipy not available, advanced filtering disabled")


@dataclass
class AudioMetrics:
    """Audio quality metrics"""
    rms_level: float
    peak_level: float
    latency_ms: float
    vad_confidence: float
    clipping_detected: bool


class NoiseGate:
    """Simple noise gate to reduce background noise"""

    def __init__(self, threshold_db: float = -45.0, attack_ms: float = 5.0, release_ms: float = 150.0, sample_rate: int = 16000):
        self.threshold = 10 ** (threshold_db / 20.0)  # Convert dB to linear
        self.attack_samples = int(sample_rate * attack_ms / 1000.0)
        self.release_samples = int(sample_rate * release_ms / 1000.0)
        self.envelope = 0.0
        self.is_open = False

    def process(self, audio_data: bytes) -> bytes:
        """Apply noise gate to audio data"""
        # Convert bytes to numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

        # Calculate envelope
        rms = np.sqrt(np.mean(samples ** 2))

        # Update gate state
        if rms > self.threshold:
            # Attack phase
            target = 1.0
            self.envelope += (target - self.envelope) / max(1, self.attack_samples)
            self.is_open = True
        else:
            # Release phase
            target = 0.0
            self.envelope += (target - self.envelope) / max(1, self.release_samples)
            if self.envelope < 0.01:
                self.is_open = False

        # Apply envelope
        processed = samples * self.envelope

        # Convert back to int16
        processed = np.clip(processed * 32768.0, -32768, 32767).astype(np.int16)

        return processed.tobytes()


class EnhancedAudioProcessor:
    """
    Enhanced audio processing with:
    - WebRTC VAD for improved speech detection
    - Noise gate for background noise reduction
    - Audio quality monitoring
    - Latency tracking
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        vad_aggressiveness: int = 2,  # 0-3, higher = more aggressive filtering
        enable_noise_gate: bool = True,
        noise_gate_threshold_db: float = -40.0,
        fallback_rms_threshold: int = 800
    ):
        self.sample_rate = sample_rate
        self.fallback_rms_threshold = fallback_rms_threshold

        # WebRTC VAD (works only with 8kHz, 16kHz, 32kHz, 48kHz and frame sizes of 10, 20, or 30 ms)
        self.vad = None
        if WEBRTCVAD_AVAILABLE and sample_rate in [8000, 16000, 32000, 48000]:
            try:
                self.vad = webrtcvad.Vad(vad_aggressiveness)
                print(f"[AUDIO] WebRTC VAD initialized (aggressiveness: {vad_aggressiveness})")
            except Exception as e:
                print(f"[AUDIO] Failed to initialize WebRTC VAD: {e}")
                self.vad = None

        # Noise gate
        self.noise_gate = None
        if enable_noise_gate:
            self.noise_gate = NoiseGate(
                threshold_db=noise_gate_threshold_db,
                sample_rate=sample_rate
            )
            print(f"[AUDIO] Noise gate enabled (threshold: {noise_gate_threshold_db} dB)")

        # Metrics tracking
        self.last_process_time = time.time()
        self.total_frames_processed = 0
        self.speech_frames = 0

    def preprocess_audio(self, audio_data: bytes) -> bytes:
        """
        Preprocess audio with noise gate and filtering
        """
        if self.noise_gate:
            return self.noise_gate.process(audio_data)
        return audio_data

    def detect_speech(self, audio_data: bytes, frame_duration_ms: int = 30) -> Tuple[bool, float]:
        """
        Detect speech in audio using WebRTC VAD or fallback RMS method

        Returns:
            Tuple of (is_speech: bool, confidence: float)
        """
        start_time = time.time()

        # Try WebRTC VAD first
        if self.vad is not None:
            try:
                # WebRTC VAD requires specific frame durations (10, 20, or 30 ms)
                # Ensure audio_data matches the expected length
                expected_length = int(self.sample_rate * frame_duration_ms / 1000) * 2  # 2 bytes per sample

                if len(audio_data) == expected_length:
                    is_speech = self.vad.is_speech(audio_data, self.sample_rate)
                    confidence = 1.0 if is_speech else 0.0

                    # Update metrics
                    latency_ms = (time.time() - start_time) * 1000
                    self.total_frames_processed += 1
                    if is_speech:
                        self.speech_frames += 1

                    return is_speech, confidence
            except Exception as e:
                print(f"[AUDIO] WebRTC VAD error: {e}, falling back to RMS")

        # Fallback to RMS-based detection
        is_speech, rms = self._detect_speech_rms(audio_data)
        confidence = min(rms / (self.fallback_rms_threshold * 2), 1.0) if is_speech else 0.0

        return is_speech, confidence

    def _detect_speech_rms(self, audio_data: bytes) -> Tuple[bool, int]:
        """Fallback RMS-based speech detection"""
        count = len(audio_data) // 2
        if count > 0:
            shorts = struct.unpack(f"<{count}h", audio_data)
            sum_squares = sum(s**2 for s in shorts)
            rms = int(np.sqrt(sum_squares / count))
        else:
            rms = 0

        return rms > self.fallback_rms_threshold, rms

    def calculate_metrics(self, audio_data: bytes) -> AudioMetrics:
        """
        Calculate comprehensive audio quality metrics
        """
        # Convert to numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

        # RMS level
        rms = np.sqrt(np.mean(samples ** 2))

        # Peak level
        peak = np.max(np.abs(samples))

        # Clipping detection
        clipping = peak > 0.99

        # VAD confidence
        is_speech, confidence = self.detect_speech(audio_data)

        # Latency
        latency_ms = (time.time() - self.last_process_time) * 1000
        self.last_process_time = time.time()

        return AudioMetrics(
            rms_level=rms,
            peak_level=peak,
            latency_ms=latency_ms,
            vad_confidence=confidence,
            clipping_detected=clipping
        )

    def get_statistics(self) -> dict:
        """Get processing statistics"""
        if self.total_frames_processed > 0:
            speech_ratio = self.speech_frames / self.total_frames_processed
        else:
            speech_ratio = 0.0

        return {
            "total_frames": self.total_frames_processed,
            "speech_frames": self.speech_frames,
            "speech_ratio": speech_ratio,
            "vad_enabled": self.vad is not None,
            "noise_gate_enabled": self.noise_gate is not None
        }


class WakeWordDetector:
    """
    Wake word detection using Porcupine
    """

    def __init__(self, access_key: Optional[str] = None, keywords: list = None):
        self.porcupine = None
        self.enabled = False

        if keywords is None:
            keywords = ["hey google"]  # Default wake word (built-in)

        try:
            import pvporcupine

            if access_key:
                # Initialize with custom keywords
                self.porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=keywords
                )
                self.enabled = True
                print(f"[WAKE] Porcupine wake word detector initialized with keywords: {keywords}")
            else:
                print("[WAKE] No Porcupine access key provided. Wake word detection disabled.")
                print("[WAKE] Get a free key at: https://console.picovoice.ai/")
        except ImportError:
            print("[WAKE] pvporcupine not installed. Wake word detection disabled.")
        except Exception as e:
            print(f"[WAKE] Failed to initialize Porcupine: {e}")

    def process(self, audio_frame: bytes) -> bool:
        """
        Process audio frame and detect wake word

        Returns:
            True if wake word detected, False otherwise
        """
        if not self.enabled or not self.porcupine:
            return False

        try:
            # Convert bytes to int16 array
            pcm = np.frombuffer(audio_frame, dtype=np.int16)

            # Process frame
            keyword_index = self.porcupine.process(pcm)

            if keyword_index >= 0:
                print(f"[WAKE] Wake word detected! (index: {keyword_index})")
                return True
        except Exception as e:
            print(f"[WAKE] Error processing wake word: {e}")

        return False

    def cleanup(self):
        """Clean up Porcupine resources"""
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None


class AudioRecorder:
    """
    Records audio conversations to file
    """

    def __init__(self, sample_rate: int = 16000, output_dir: str = "recordings"):
        self.sample_rate = sample_rate
        self.output_dir = output_dir
        self.recording = False
        self.frames = []
        self.start_time = None

        import os
        os.makedirs(output_dir, exist_ok=True)

    def start(self):
        """Start recording"""
        self.recording = True
        self.frames = []
        self.start_time = time.time()
        print(f"[RECORDER] Started recording")

    def add_frame(self, audio_data: bytes):
        """Add audio frame to recording"""
        if self.recording:
            self.frames.append(audio_data)

    def stop(self) -> Optional[str]:
        """
        Stop recording and save to file

        Returns:
            Path to saved file, or None if recording was empty
        """
        if not self.recording or not self.frames:
            self.recording = False
            return None

        self.recording = False

        # Generate filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/recording_{timestamp}.wav"

        # Save as WAV file
        try:
            import wave
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))

            duration = time.time() - self.start_time
            print(f"[RECORDER] Saved recording to {filename} (duration: {duration:.1f}s, frames: {len(self.frames)})")
            return filename
        except Exception as e:
            print(f"[RECORDER] Failed to save recording: {e}")
            return None

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self.recording
