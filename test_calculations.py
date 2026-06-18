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

    def test_neck_relative_flexion(self):
        from detector import calcular_flexion_cuello
        # Trunk is straight vertical: cadera [100, 500], hombro [100, 200]
        # Neck is bent forward at 45 degrees: ear at [200, 100] (dx=100, dy=-100)
        # Vector trunk = [0, -300] -> straight up
        # Vector neck = [100, -100] -> 45 degrees from vertical
        # Relative angle should be 45 degrees
        cadera = [100, 500]
        hombro = [100, 200]
        oreja = [200, 100]
        
        angulo = calcular_flexion_cuello(cadera, hombro, oreja)
        self.assertAlmostEqual(angulo, 45.0, places=2)

        # Trunk is bent at 45 degrees: cadera [0, 100], hombro [100, 0] (dx=100, dy=-100)
        # Neck is in line with trunk (straight): ear at [200, -100] (dx=100, dy=-100)
        # Relative angle should be 0 degrees
        cadera_bent = [0, 100]
        hombro_bent = [100, 0]
        oreja_inline = [200, -100]
        angulo_inline = calcular_flexion_cuello(cadera_bent, hombro_bent, oreja_inline)
        self.assertAlmostEqual(angulo_inline, 0.0, places=2)

    def test_shoulder_flexion(self):
        # 1. Straight down (parallel): cadera and codo below hombro
        cadera = [100, 500]
        hombro = [100, 200]
        codo = [100, 300]
        angulo = calcular_flexion_hombro(cadera, hombro, codo)
        self.assertAlmostEqual(angulo, 0.0, places=2)

        # 2. Arm raised horizontal (90 degrees)
        cadera2 = [100, 500]
        hombro2 = [100, 200]
        codo2 = [200, 200]
        angulo2 = calcular_flexion_hombro(cadera2, hombro2, codo2)
        self.assertAlmostEqual(angulo2, 90.0, places=2)

        # 3. Arm raised vertical (180 degrees)
        cadera3 = [100, 500]
        hombro3 = [100, 200]
        codo3 = [100, 100]
        angulo3 = calcular_flexion_hombro(cadera3, hombro3, codo3)
        self.assertAlmostEqual(angulo3, 180.0, places=2)

if __name__ == "__main__":
    unittest.main()
