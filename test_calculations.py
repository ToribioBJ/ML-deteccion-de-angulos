import unittest
from detector import calcular_flexion_tronco, calcular_flexion_hombro

class TestAngleCalculations(unittest.TestCase):
    def test_vertical_alignment(self):
        # Hombro directamente arriba de la cadera
        # En coordenadas de imagen, y disminuye hacia arriba
        cadera = [100, 500]
        hombro = [100, 200]
        
        angulo = calcular_flexion_tronco(hombro, cadera)
        self.assertAlmostEqual(angulo, 0.0, places=2)

    def test_forward_flexion_left(self):
        # Hombro inclinado a la izquierda (adelante si mira a la izquierda)
        cadera = [200, 500]
        hombro = [100, 200]  # dx = -100, dy = -300
        
        # Vector tronco = [-100, -300], Vector vertical = [0, -1]
        # Coseno = (-100*0 + -300*-1) / (sqrt(100000)*1) = 300 / 316.2277 = 0.94868
        # arccos(0.94868) = 18.43 grados
        angulo = calcular_flexion_tronco(hombro, cadera)
        self.assertAlmostEqual(angulo, 18.4349, places=2)

    def test_forward_flexion_right(self):
        # Hombro inclinado a la derecha
        cadera = [200, 500]
        hombro = [300, 200]  # dx = 100, dy = -300
        
        # Debe dar el mismo ángulo positivo (18.43 grados)
        angulo = calcular_flexion_tronco(hombro, cadera)
        self.assertAlmostEqual(angulo, 18.4349, places=2)

    def test_horizontal_flexion(self):
        # Hombro al mismo nivel horizontal que la cadera (90 grados)
        cadera = [200, 500]
        hombro = [100, 500]
        
        angulo = calcular_flexion_tronco(hombro, cadera)
        self.assertAlmostEqual(angulo, 90.0, places=2)

    def test_head_angle(self):
        from detector import calcular_angulo_cabeza
        # 1. Alineación vertical recta: oreja [100, 200], ojo [100, 100] (dx=0, dy=-100)
        oreja = [100, 200]
        ojo = [100, 100]
        angulo = calcular_angulo_cabeza(oreja, ojo)
        self.assertAlmostEqual(angulo, 0.0, places=2)

        # 2. Ojo a 45 grados adelante y arriba: oreja [100, 200], ojo [200, 100] (dx=100, dy=-100)
        oreja2 = [100, 200]
        ojo2 = [200, 100]
        angulo2 = calcular_angulo_cabeza(oreja2, ojo2)
        self.assertAlmostEqual(angulo2, 45.0, places=2)

        # 3. Ojo horizontal a 90 grados: oreja [100, 200], ojo [200, 200] (dx=100, dy=0)
        oreja3 = [100, 200]
        ojo3 = [200, 200]
        angulo3 = calcular_angulo_cabeza(oreja3, ojo3)
        self.assertAlmostEqual(angulo3, 90.0, places=2)

    def test_shoulder_flexion(self):
        # 1. Straight arm (180 degrees)
        hombro = [100, 100]
        codo = [100, 200]
        muneca = [100, 300]
        angulo = calcular_flexion_hombro(hombro, codo, muneca)
        self.assertAlmostEqual(angulo, 180.0, places=2)

        # 2. Bent arm (90 degrees)
        hombro2 = [100, 100]
        codo2 = [100, 200]
        muneca2 = [200, 200]
        angulo2 = calcular_flexion_hombro(hombro2, codo2, muneca2)
        self.assertAlmostEqual(angulo2, 90.0, places=2)

        # 3. Folded arm (0 degrees)
        hombro3 = [100, 100]
        codo3 = [100, 200]
        muneca3 = [100, 100]
        angulo3 = calcular_flexion_hombro(hombro3, codo3, muneca3)
        self.assertAlmostEqual(angulo3, 0.0, places=2)

if __name__ == "__main__":
    unittest.main()
