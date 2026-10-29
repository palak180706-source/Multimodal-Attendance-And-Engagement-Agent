import time
from typing import Dict, Any, List, Optional
from collections import deque

class SessionReasoningEngine:
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.metric_window = deque(maxlen=window_size)
        self.last_suggestion_time = 0.0
        self.cooldown_period = 25.0  # seconds between suggestions to avoid spamming instructor

    def add_metric(self, metric: Dict[str, Any]):
        self.metric_window.append(metric)

    def evaluate_dynamics(self) -> Optional[Dict[str, Any]]:
        """
        Evaluates session dynamics and detects triggerable pedagogical events.
        """
        now = time.time()
        if now - self.last_suggestion_time < self.cooldown_period:
            return None

        if len(self.metric_window) < 5:
            return None

        recent_metrics = list(self.metric_window)
        recent_fused = [m["fused_score"] for m in recent_metrics[-6:]]
        recent_attn = [m["visual_attention"] for m in recent_metrics[-6:]]
        recent_audio_states = [m["acoustic_state"] for m in recent_metrics[-6:]]
        
        avg_recent_fused = sum(recent_fused) / len(recent_fused)
        avg_recent_attn = sum(recent_attn) / len(recent_attn)

        # Trigger Case 1: Steep Attention Drop
        if avg_recent_fused < 45.0 or (recent_fused[0] - recent_fused[-1] > 20.0):
            self.last_suggestion_time = now
            return {
                "trigger_reason": "ATTENTION_DROP_DETECTED",
                "fused_score": round(avg_recent_fused, 1),
                "visual_attention": round(avg_recent_attn, 1),
                "acoustic_state": recent_audio_states[-1],
                "duration_sec": int(recent_metrics[-1]["seconds_from_start"])
            }

        # Trigger Case 2: Prolonged Monotone / Silence
        if recent_audio_states.count("SILENT_LISTENING") >= 5:
            self.last_suggestion_time = now
            return {
                "trigger_reason": "PROLONGED_SILENCE",
                "fused_score": round(avg_recent_fused, 1),
                "visual_attention": round(avg_recent_attn, 1),
                "acoustic_state": "SILENT_LISTENING",
                "duration_sec": int(recent_metrics[-1]["seconds_from_start"])
            }

        # Trigger Case 3: Prolonged High Commotion
        if recent_audio_states.count("HIGH_CLASS_COMMOTION") >= 4:
            self.last_suggestion_time = now
            return {
                "trigger_reason": "CLASSROOM_COMMOTION",
                "fused_score": round(avg_recent_fused, 1),
                "visual_attention": round(avg_recent_attn, 1),
                "acoustic_state": "HIGH_CLASS_COMMOTION",
                "duration_sec": int(recent_metrics[-1]["seconds_from_start"])
            }

        return None
