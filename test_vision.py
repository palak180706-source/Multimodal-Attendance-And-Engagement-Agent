import unittest
import numpy as np
import time
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.vision_tracker import VisionTracker, TrackedStudent

class TestVisionTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = VisionTracker()

    def test_sustained_presence_logic(self):
        # A student should start with PROVISIONAL status
        student = TrackedStudent(1, "STD-101", "Aarav Sharma", (100, 100, 80, 80))
        self.assertEqual(student.attendance_status, "PROVISIONAL")
        self.assertEqual(student.sustained_duration, 0.0)

        # Update with 1.5 seconds (less than 3.0s threshold)
        student.update((100, 100, 80, 80), attention=85.0, head_pose="FRONTAL", motion=0.05, dt=1.5)
        self.assertEqual(student.attendance_status, "PROVISIONAL")

        # Update with another 2.0 seconds (cumulative 3.5s >= 3.0s threshold)
        student.update((100, 100, 80, 80), attention=88.0, head_pose="FRONTAL", motion=0.05, dt=2.0)
        self.assertEqual(student.attendance_status, "PRESENT")
        self.assertGreaterEqual(student.sustained_duration, 3.0)

    def test_synthetic_frame_processing(self):
        # Process an empty blank frame
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = self.tracker.process_frame(blank_frame)
        
        self.assertIn("active_faces", result)
        self.assertIn("visual_attention_score", result)
        self.assertIn("annotated_frame", result)
        self.assertEqual(result["active_faces"], 0)

if __name__ == '__main__':
    unittest.main()
