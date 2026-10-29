import unittest
import numpy as np
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.audio_utils import compute_rms, compute_zero_crossing_rate, classify_acoustic_state

class TestAudioModule(unittest.TestCase):
    def test_compute_rms(self):
        # Silence
        silence = np.zeros(1600, dtype=np.float32)
        self.assertEqual(compute_rms(silence), 0.0)

        # Sine wave with amplitude 0.5 -> RMS = 0.5 / sqrt(2) ≈ 0.3535
        t = np.linspace(0, 1, 16000, endpoint=False)
        sine = 0.5 * np.sin(2 * np.pi * 440 * t)
        self.assertAlmostEqual(compute_rms(sine), 0.3535, places=3)

    def test_zero_crossing_rate(self):
        # Alternating signal should have high ZCR
        alternating = np.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0], dtype=np.float32)
        zcr = compute_zero_crossing_rate(alternating)
        self.assertGreater(zcr, 0.5)

    def test_classify_acoustic_state(self):
        # Low energy -> Silent listening
        state, score = classify_acoustic_state(0.005, 0.05)
        self.assertEqual(state, "SILENT_LISTENING")
        self.assertEqual(score, 25.0)

        # Conversational energy -> Instructional monologue
        state, score = classify_acoustic_state(0.04, 0.08)
        self.assertEqual(state, "INSTRUCTIONAL_MONOLOGUE")
        self.assertEqual(score, 60.0)

        # Discussion peak -> Active discussion
        state, score = classify_acoustic_state(0.12, 0.12)
        self.assertEqual(state, "ACTIVE_DISCUSSION_PEAK")
        self.assertEqual(score, 92.0)

if __name__ == '__main__':
    unittest.main()
