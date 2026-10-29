import time
import numpy as np
from typing import Dict, Any, List
from config import (
    WEIGHT_VISUAL_ATTENTION,
    WEIGHT_VISUAL_ACTIVITY,
    WEIGHT_AUDIO_INTERACTION,
    ENGAGEMENT_EXPONENTIAL_SMOOTHING,
    ENGAGEMENT_LEVELS
)

class MultimodalFusionEngine:
    def __init__(self):
        self.wv = WEIGHT_VISUAL_ATTENTION
        self.wm = WEIGHT_VISUAL_ACTIVITY
        self.wa = WEIGHT_AUDIO_INTERACTION
        self.alpha = ENGAGEMENT_EXPONENTIAL_SMOOTHING
        
        self.smoothed_engagement = 75.0
        self.history: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.attention_drop_counter = 0
        self.peak_counter = 0

    def reset_session(self):
        self.smoothed_engagement = 75.0
        self.history.clear()
        self.start_time = time.time()
        self.attention_drop_counter = 0
        self.peak_counter = 0

    def fuse(self, vision_data: Dict[str, Any], audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fuses visual attention, motion pattern, and acoustic dynamics.
        Computes weighted raw score, applies EMA smoothing, and evaluates triggers.
        """
        now = time.time()
        sec_from_start = round(now - self.start_time, 1)

        v_attn = vision_data.get("visual_attention_score", 70.0)
        v_mot_raw = vision_data.get("visual_motion_score", 0.1)
        
        # Normalize motion to 0-100 scale: ideal movement is gentle (0.02 - 0.15)
        # 0 motion = stagnant/drowsy (score 40), optimal gentle motion = 90, violent motion = 30
        if v_mot_raw < 0.01:
            v_motion_score = 40.0
        elif 0.01 <= v_mot_raw <= 0.20:
            v_motion_score = 85.0 + (0.20 - v_mot_raw) * 50.0
        else:
            v_motion_score = max(20.0, 85.0 - (v_mot_raw - 0.20) * 150.0)
        v_motion_score = min(100.0, max(0.0, v_motion_score))

        a_int = audio_data.get("interaction_score", 60.0)

        # Multimodal Weighted Fusion
        raw_fused = (self.wv * v_attn) + (self.wm * v_motion_score) + (self.wa * a_int)
        
        # Exponential Moving Average Smoothing
        self.smoothed_engagement = (self.alpha * raw_fused) + ((1.0 - self.alpha) * self.smoothed_engagement)
        final_score = round(float(np.clip(self.smoothed_engagement, 0.0, 100.0)), 1)

        # Categorization
        if final_score >= ENGAGEMENT_LEVELS["HIGH"]:
            category = "HIGH_ENGAGEMENT"
            category_label = "High Interaction"
            badge_color = "emerald"
        elif final_score >= ENGAGEMENT_LEVELS["MODERATE"]:
            category = "MODERATE_ENGAGEMENT"
            category_label = "Focused Listening"
            badge_color = "blue"
        elif final_score >= ENGAGEMENT_LEVELS["LOW"]:
            category = "LOW_ENGAGEMENT"
            category_label = "Attention Dropping"
            badge_color = "amber"
        else:
            category = "CRITICAL_DISENGAGEMENT"
            category_label = "Disengaged / Restless"
            badge_color = "rose"

        # Anomaly & Trigger Detection
        alert_event = None
        if final_score < ENGAGEMENT_LEVELS["MODERATE"]:
            self.attention_drop_counter += 1
            if self.attention_drop_counter >= 3:
                alert_event = {
                    "type": "ATTENTION_DROP_ALERT",
                    "severity": "WARNING",
                    "message": f"Engagement dipped to {final_score}%! Consider an interactive question or pacing change.",
                    "score": final_score
                }
        else:
            self.attention_drop_counter = max(0, self.attention_drop_counter - 1)

        if a_int >= 85.0 and v_attn >= 70.0:
            self.peak_counter += 1
            if self.peak_counter >= 2:
                alert_event = {
                    "type": "INTERACTION_PEAK",
                    "severity": "SUCCESS",
                    "message": f"Interaction spike detected ({final_score}%)! Classroom is actively engaged in discussion.",
                    "score": final_score
                }
        else:
            self.peak_counter = 0

        snapshot = {
            "timestamp": now,
            "seconds_from_start": sec_from_start,
            "visual_attention": round(v_attn, 1),
            "visual_motion": round(v_motion_score, 1),
            "audio_interaction": round(a_int, 1),
            "fused_score": final_score,
            "category": category,
            "category_label": category_label,
            "badge_color": badge_color,
            "active_faces": vision_data.get("active_faces", 0),
            "present_students": vision_data.get("present_students", 0),
            "acoustic_state": audio_data.get("acoustic_state", "INSTRUCTIONAL_MONOLOGUE"),
            "alert": alert_event
        }

        self.history.append(snapshot)
        if len(self.history) > 300:
            self.history.pop(0)

        return snapshot
