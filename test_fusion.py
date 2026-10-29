import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.fusion_engine import MultimodalFusionEngine

class TestMultimodalFusion(unittest.TestCase):
    def setUp(self):
        self.engine = MultimodalFusionEngine()

    def test_fusion_calculation(self):
        vision_data = {
            "visual_attention_score": 80.0,
            "visual_motion_score": 0.05,
            "active_faces": 2,
            "present_students": 2
        }
        audio_data = {
            "interaction_score": 70.0,
            "acoustic_state": "INSTRUCTIONAL_MONOLOGUE"
        }

        snapshot = self.engine.fuse(vision_data, audio_data)
        self.assertIn("fused_score", snapshot)
        self.assertIn("category", snapshot)
        self.assertGreaterEqual(snapshot["fused_score"], 0.0)
        self.assertLessEqual(snapshot["fused_score"], 100.0)

    def test_attention_drop_alert_trigger(self):
        # Feed severe disengagement
        low_vision = {"visual_attention_score": 20.0, "visual_motion_score": 0.0, "active_faces": 1, "present_students": 1}
        low_audio = {"interaction_score": 15.0, "acoustic_state": "SILENT_LISTENING"}

        # Simulate 4 consecutive steps of deep drop
        last_snap = None
        for _ in range(4):
            last_snap = self.engine.fuse(low_vision, low_audio)

        self.assertIsNotNone(last_snap["alert"])
        self.assertEqual(last_snap["alert"]["type"], "ATTENTION_DROP_ALERT")

if __name__ == '__main__':
    unittest.main()
