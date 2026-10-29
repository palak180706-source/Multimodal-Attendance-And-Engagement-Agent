import numpy as np
from typing import Tuple, Dict

def compute_rms(audio_samples: np.ndarray) -> float:
    """Computes Root Mean Square (RMS) energy of audio signal"""
    if len(audio_samples) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio_samples))))

def compute_zero_crossing_rate(audio_samples: np.ndarray) -> float:
    """Computes Zero Crossing Rate (ZCR) to distinguish speech from ambient noise"""
    if len(audio_samples) < 2:
        return 0.0
    signs = np.sign(audio_samples)
    crossings = np.sum(np.abs(np.diff(signs))) / (2 * len(audio_samples))
    return float(crossings)

def estimate_spectral_flux(audio_samples: np.ndarray) -> float:
    """Approximates spectral dynamics between adjacent segments"""
    if len(audio_samples) < 64:
        return 0.0
    fft_vals = np.abs(np.fft.rfft(audio_samples))
    flux = float(np.mean(np.diff(fft_vals)**2))
    return flux

def classify_acoustic_state(rms: float, zcr: float) -> Tuple[str, float]:
    """
    Classifies classroom acoustic atmosphere:
    - SILENT_DEAD_AIR: Prolonged silence (attention drop / hesitation)
    - PASSIVE_LECTURE: Regular instructor talking, students listening quietly
    - INTERACTIVE_DISCUSSION: High conversational overlap, lively Q&A
    - AMBIENT_COMMOTION: Background noise / chatter
    
    Returns: (acoustic_state, interaction_index [0-100%])
    """
    if rms < 0.015:
        # Prolonged silence / dead air
        return "SILENT_LISTENING", 25.0
    elif rms < 0.06:
        # Normal instructional speech
        return "INSTRUCTIONAL_MONOLOGUE", 60.0
    elif rms < 0.18:
        # Vibrant classroom participation / interactive discussion
        return "ACTIVE_DISCUSSION_PEAK", 92.0
    else:
        # High volume commotion or noise
        return "HIGH_CLASS_COMMOTION", 45.0
