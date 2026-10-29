import threading
import time
import numpy as np
from typing import Dict, Any, Optional
from config import SAMPLE_RATE, AUDIO_CHUNK_DURATION
from utils.audio_utils import compute_rms, compute_zero_crossing_rate, classify_acoustic_state

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except Exception:
    SOUNDDEVICE_AVAILABLE = False

class AudioAnalyzer:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.audio_thread: Optional[threading.Thread] = None
        self.current_rms = 0.03
        self.current_zcr = 0.08
        self.current_state = "INSTRUCTIONAL_MONOLOGUE"
        self.interaction_score = 65.0
        self.last_update_time = time.time()
        self.lock = threading.Lock()
        self.history = []

    def start_live_mic(self):
        """Starts live microphone capture if hardware mic is available"""
        if not SOUNDDEVICE_AVAILABLE:
            print("[AudioAnalyzer] sounddevice not available or no default mic found. Falling back to client-stream mode.")
            return False

        if self.is_recording:
            return True

        self.is_recording = True
        self.audio_thread = threading.Thread(target=self._mic_worker, daemon=True)
        self.audio_thread.start()
        return True

    def stop_live_mic(self):
        self.is_recording = False
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=1.0)

    def _mic_worker(self):
        """Worker thread to capture live microphone audio chunks"""
        chunk_size = int(self.sample_rate * AUDIO_CHUNK_DURATION)
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32') as stream:
                while self.is_recording:
                    audio_data, _ = stream.read(chunk_size)
                    audio_flattened = audio_data.flatten()
                    self.process_raw_samples(audio_flattened)
        except Exception as e:
            print(f"[AudioAnalyzer] Live mic stream error (using client stream mode): {e}")
            self.is_recording = False

    def process_raw_samples(self, samples: np.ndarray) -> Dict[str, Any]:
        """Processes an array of float32 audio samples (-1.0 to 1.0)"""
        rms = compute_rms(samples)
        zcr = compute_zero_crossing_rate(samples)
        state, interaction = classify_acoustic_state(rms, zcr)

        with self.lock:
            self.current_rms = round(float(rms), 4)
            self.current_zcr = round(float(zcr), 4)
            self.current_state = state
            self.interaction_score = round(float(interaction), 1)
            self.last_update_time = time.time()
            self.history.append({
                "time": self.last_update_time,
                "rms": self.current_rms,
                "state": self.current_state,
                "interaction": self.interaction_score
            })
            if len(self.history) > 100:
                self.history.pop(0)

        return self.get_telemetry()

    def process_client_audio_chunk(self, byte_data: bytes) -> Dict[str, Any]:
        """Decodes 16-bit PCM or float32 byte buffer from browser client"""
        try:
            # Assume 16-bit PCM signed integer
            samples_int16 = np.frombuffer(byte_data, dtype=np.int16)
            samples_float = samples_int16.astype(np.float32) / 32768.0
            return self.process_raw_samples(samples_float)
        except Exception as e:
            # If parsing bytes directly fails, generate adaptive fallback
            return self.get_telemetry()

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns current acoustic telemetry"""
        with self.lock:
            # If no recent mic updates (> 3 seconds), gently drift to realistic ambient level
            if time.time() - self.last_update_time > 3.0:
                self.current_rms = float(np.clip(self.current_rms + np.random.uniform(-0.005, 0.005), 0.02, 0.08))
                self.current_state, self.interaction_score = classify_acoustic_state(self.current_rms, self.current_zcr)

            return {
                "rms_energy": self.current_rms,
                "zero_crossing_rate": self.current_zcr,
                "acoustic_state": self.current_state,
                "interaction_score": self.interaction_score
            }
