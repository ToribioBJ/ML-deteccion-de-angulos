import unittest
from tracker import PostureTracker

class TestPostureTracker(unittest.TestCase):
    def test_initial_state(self):
        tracker = PostureTracker()
        self.assertIsNone(tracker.active_tronco)
        self.assertIsNone(tracker.active_cabeza)
        self.assertIsNone(tracker.active_cuello)
        self.assertIsNone(tracker.active_hombro)
        self.assertEqual(len(tracker.tronco_segments), 0)
        self.assertEqual(len(tracker.cabeza_segments), 0)
        self.assertEqual(len(tracker.cuello_segments), 0)
        self.assertEqual(len(tracker.hombro_segments), 0)
        self.assertEqual(tracker.tiempo_tronco, 0.0)
        self.assertEqual(tracker.tiempo_cabeza, 0.0)
        self.assertEqual(tracker.tiempo_cuello, 0.0)
        self.assertEqual(tracker.tiempo_hombro, 0.0)

    def test_update_pose_first_time(self):
        tracker = PostureTracker()
        # update_pose signature: tronco, cabeza, cuello, hombro, lado, t
        tracker.update_pose(10.0, 15.0, 5.0, 30.0, "Izquierdo", 1.0)
        
        self.assertIsNotNone(tracker.active_tronco)
        self.assertEqual(tracker.active_tronco["valor"], 10)
        self.assertEqual(tracker.active_tronco["t_inicio"], 1.0)
        self.assertEqual(tracker.active_tronco["t_fin"], 1.0)
        self.assertEqual(tracker.tiempo_tronco, 0.0)

        self.assertIsNotNone(tracker.active_cabeza)
        self.assertEqual(tracker.active_cabeza["valor"], 15)
        self.assertEqual(tracker.active_cabeza["t_inicio"], 1.0)
        self.assertEqual(tracker.active_cabeza["t_fin"], 1.0)
        self.assertEqual(tracker.tiempo_cabeza, 0.0)

        self.assertIsNotNone(tracker.active_cuello)
        self.assertEqual(tracker.active_cuello["valor"], 5)
        self.assertEqual(tracker.active_cuello["t_inicio"], 1.0)
        self.assertEqual(tracker.active_cuello["t_fin"], 1.0)
        self.assertEqual(tracker.tiempo_cuello, 0.0)

        self.assertIsNotNone(tracker.active_hombro)
        self.assertEqual(tracker.active_hombro["valor"], 30)
        self.assertEqual(tracker.active_hombro["t_inicio"], 1.0)
        self.assertEqual(tracker.active_hombro["t_fin"], 1.0)
        self.assertEqual(tracker.tiempo_hombro, 0.0)

    def test_update_pose_same_segment(self):
        tracker = PostureTracker()
        tracker.update_pose(10.0, 15.0, 5.0, 30.0, "Izquierdo", 1.0)
        tracker.update_pose(10.1, 14.9, 4.9, 29.8, "Izquierdo", 2.5)
        
        self.assertEqual(tracker.active_tronco["t_inicio"], 1.0)
        self.assertEqual(tracker.active_tronco["t_fin"], 2.5)
        self.assertEqual(tracker.tiempo_tronco, 1.5)

        self.assertEqual(tracker.active_cabeza["t_inicio"], 1.0)
        self.assertEqual(tracker.active_cabeza["t_fin"], 2.5)
        self.assertEqual(tracker.tiempo_cabeza, 1.5)

        self.assertEqual(tracker.active_cuello["t_inicio"], 1.0)
        self.assertEqual(tracker.active_cuello["t_fin"], 2.5)
        self.assertEqual(tracker.tiempo_cuello, 1.5)

    def test_update_pose_change_segment(self):
        tracker = PostureTracker()
        tracker.update_pose(10.0, 15.0, 5.0, 30.0, "Izquierdo", 1.0)
        tracker.update_pose(10.0, 15.0, 5.0, 30.0, "Izquierdo", 2.0)
        # Tronco cambia, los otros quedan igual
        tracker.update_pose(20.0, 15.0, 5.0, 30.0, "Izquierdo", 3.0)
        
        # Tronco debe haber guardado 1 segmento y empezado otro
        self.assertEqual(len(tracker.tronco_segments), 1)
        self.assertEqual(tracker.tronco_segments[0]["valor"], 10)
        self.assertEqual(tracker.tronco_segments[0]["duracion"], 1.0)
        
        self.assertEqual(tracker.active_tronco["valor"], 20)
        self.assertEqual(tracker.active_tronco["t_inicio"], 2.0)
        self.assertEqual(tracker.active_tronco["t_fin"], 3.0)
        self.assertEqual(tracker.tiempo_tronco, 1.0)
        
        # Cabeza, Cuello y Hombro no deben haber guardado segmentos
        self.assertEqual(len(tracker.cabeza_segments), 0)
        self.assertEqual(len(tracker.cuello_segments), 0)
        self.assertEqual(len(tracker.hombro_segments), 0)
        
        self.assertEqual(tracker.active_cabeza["valor"], 15)
        self.assertEqual(tracker.active_cabeza["t_inicio"], 1.0)
        self.assertEqual(tracker.active_cabeza["t_fin"], 3.0)
        self.assertEqual(tracker.tiempo_cabeza, 2.0)

    def test_update_no_pose(self):
        tracker = PostureTracker()
        tracker.update_pose(10.0, 15.0, 5.0, 30.0, "Izquierdo", 1.0)
        tracker.update_pose(10.0, 15.0, 5.0, 30.0, "Izquierdo", 2.0)
        tracker.update_no_pose(3.0)
        
        self.assertEqual(len(tracker.tronco_segments), 1)
        self.assertEqual(tracker.tronco_segments[0]["valor"], 10)
        self.assertEqual(tracker.tronco_segments[0]["duracion"], 1.0)
        
        self.assertIsNone(tracker.active_tronco["valor"])
        self.assertEqual(tracker.active_tronco["t_inicio"], 2.0)
        self.assertEqual(tracker.active_tronco["t_fin"], 3.0)
        self.assertEqual(tracker.tiempo_tronco, 1.0)

        self.assertIsNone(tracker.active_cabeza["valor"])
        self.assertEqual(tracker.active_cabeza["t_inicio"], 2.0)
        self.assertEqual(tracker.active_cabeza["t_fin"], 3.0)
        self.assertEqual(tracker.tiempo_cabeza, 1.0)

if __name__ == "__main__":
    unittest.main()
