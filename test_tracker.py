import unittest
from tracker import PostureTracker

class TestPostureTracker(unittest.TestCase):
    def test_initial_state(self):
        tracker = PostureTracker()
        self.assertEqual(len(tracker.frames_data), 0)
        self.assertIsNone(tracker.last_angles)
        self.assertEqual(tracker.current_posture_count, 0)

    def test_update_pose_duration_accumulation(self):
        tracker = PostureTracker()
        fps = 30.0
        
        # Frame 1: first pose
        dur1 = tracker.update_pose(0, 12.0, 67.0, 56.0, 48.0, "Derecho", fps)
        self.assertAlmostEqual(dur1, 1 / 30.0) # 0.0333s
        self.assertEqual(tracker.current_posture_count, 1)
        self.assertAlmostEqual(tracker.frames_data[0]["tiempo_postura"], 1 / 30.0)
        self.assertEqual(tracker.frames_data[0]["frames_acumulados"], 1)
        
        # Frame 2: same pose (exact angles)
        dur2 = tracker.update_pose(1, 12.0, 67.0, 56.0, 48.0, "Derecho", fps)
        self.assertAlmostEqual(dur2, 2 / 30.0) # 0.0666s
        self.assertEqual(tracker.current_posture_count, 2)
        self.assertAlmostEqual(tracker.frames_data[1]["tiempo_postura"], 2 / 30.0)
        self.assertEqual(tracker.frames_data[1]["frames_acumulados"], 2)
        
        # Frame 3: changed pose (trunk 12 to 13)
        dur3 = tracker.update_pose(2, 13.0, 67.0, 56.0, 48.0, "Derecho", fps)
        self.assertAlmostEqual(dur3, 1 / 30.0) # 0.0333s (resets to 1 frame)
        self.assertEqual(tracker.current_posture_count, 1)
        self.assertAlmostEqual(tracker.frames_data[2]["tiempo_postura"], 1 / 30.0)
        self.assertEqual(tracker.frames_data[2]["frames_acumulados"], 1)

    def test_update_no_pose_resets_posture(self):
        tracker = PostureTracker()
        fps = 30.0
        
        tracker.update_pose(0, 12.0, 67.0, 56.0, 48.0, "Derecho", fps)
        tracker.update_pose(1, 12.0, 67.0, 56.0, 48.0, "Derecho", fps)
        self.assertEqual(tracker.current_posture_count, 2)
        
        # Lost pose
        dur_none = tracker.update_no_pose(2)
        self.assertEqual(dur_none, 0.0)
        self.assertIsNone(tracker.last_angles)
        self.assertEqual(tracker.current_posture_count, 0)
        self.assertEqual(tracker.frames_data[2]["tiempo_postura"], 0.0)
        self.assertEqual(tracker.frames_data[2]["frames_acumulados"], 0)

        # Pose found again
        dur_new = tracker.update_pose(3, 12.0, 67.0, 56.0, 48.0, "Derecho", fps)
        self.assertAlmostEqual(dur_new, 1 / 30.0)
        self.assertEqual(tracker.current_posture_count, 1)
        self.assertAlmostEqual(tracker.frames_data[3]["tiempo_postura"], 1 / 30.0)
        self.assertEqual(tracker.frames_data[3]["frames_acumulados"], 1)

    def test_update_pose_with_none_values(self):
        tracker = PostureTracker()
        fps = 30.0
        dur = tracker.update_pose(0, None, 67.0, None, 48.0, "Derecho", fps)
        self.assertAlmostEqual(dur, 1 / 30.0)
        self.assertIsNone(tracker.frames_data[0]["angulo_tronco"])
        self.assertIsNone(tracker.frames_data[0]["angulo_cuello"])
        self.assertEqual(tracker.frames_data[0]["angulo_cabeza"], 67)

    def test_update_pose_with_wrist_angle(self):
        tracker = PostureTracker()
        fps = 30.0
        dur = tracker.update_pose(0, 12.0, 67.0, 56.0, 48.0, "Derecho", fps, angulo_muneca=15.0)
        self.assertAlmostEqual(dur, 1 / 30.0)
        self.assertEqual(tracker.frames_data[0]["angulo_muneca"], 15)

    def test_clear_history(self):
        tracker = PostureTracker()
        tracker.update_pose(0, 10.0, 15.0, 5.0, 30.0, "Izquierdo")
        self.assertEqual(len(tracker.frames_data), 1)
        
        tracker.clear_history_after_save()
        self.assertEqual(len(tracker.frames_data), 0)

if __name__ == "__main__":
    unittest.main()
