import unittest
import os
import openpyxl
from excel_exporter import registrar_posturas_excel

class TestExcelExporter(unittest.TestCase):
    def setUp(self):
        self.excel_path = "test_registro_posturas.xlsx"
        if os.path.exists(self.excel_path):
            os.remove(self.excel_path)

    def tearDown(self):
        if os.path.exists(self.excel_path):
            try:
                os.remove(self.excel_path)
            except:
                pass

    def test_exporter_headers_and_calculations(self):
        frames_data = [
            {
                "frame_idx": 0,
                "angulo_tronco": 20,
                "angulo_cabeza": 45,
                "angulo_cuello": 25,
                "angulo_hombro": 15,
                "angulo_muneca": 12,
                "lado_usado": "Derecho",
                "tiempo_postura": 0.033,
                "frames_acumulados": 1
            }
        ]
        
        # alfa = 15, beta = 10
        # tronco_ajustado = 20 - 15 = 5
        # cabeza_ajustada = 45 - 10 = 35
        # cuello_ajustado = 35 - 5 = 30
        
        num_regs = registrar_posturas_excel(
            excel_path=self.excel_path,
            nombre="Juan Pérez",
            archivo_origen="test_video.mp4",
            frames_data=frames_data,
            alfa=15.0,
            beta=10.0
        )
        
        self.assertEqual(num_regs, 1)
        self.assertTrue(os.path.exists(self.excel_path))
        
        # Leer el archivo Excel generado
        wb = openpyxl.load_workbook(self.excel_path)
        sheet = wb["Registro Posturas"]
        
        # Verificar cabeceras
        headers = [cell.value for cell in sheet[1]]
        expected_headers = [
            "Nombre de la persona",
            "Lado leído",
            "Ángulo de referencia del tronco (α)",
            "Ángulo del tronco del video",
            "Ángulo del tronco ajustado",
            "Ángulo de referencia de la cabeza (β)",
            "Ángulo de la cabeza del video",
            "Ángulo de la cabeza ajustado",
            "Ángulo del cuello ajustado",
            "Ángulo de brazo",
            "Ángulo de la muñeca",
            "Tiempo de postura",
            "Frames acumulados",
            "Nombre del archivo"
        ]
        self.assertEqual(headers, expected_headers)
        
        # Verificar datos escritos en la fila 2
        row_data = [cell.value for cell in sheet[2]]
        self.assertEqual(row_data[0], "Juan Pérez")
        self.assertEqual(row_data[1], "Derecho")
        self.assertEqual(row_data[2], 15)  # alfa
        self.assertEqual(row_data[3], 20)  # angulo del tronco del video
        self.assertEqual(row_data[4], 5)   # tronco_ajustado (20 - 15)
        self.assertEqual(row_data[5], 10)  # beta
        self.assertEqual(row_data[6], 45)  # angulo de la cabeza del video
        self.assertEqual(row_data[7], 35)  # cabeza_ajustada (45 - 10)
        self.assertEqual(row_data[8], 30)  # cuello_ajustado (35 - 5)
        self.assertEqual(row_data[9], 15)  # angulo_hombro
        self.assertEqual(row_data[10], 12)  # angulo_muneca
        self.assertAlmostEqual(row_data[11], 0.033, places=3)
        self.assertEqual(row_data[12], 1)
        self.assertEqual(row_data[13], "test_video.mp4")
        
        wb.close()

    def test_exporter_with_missing_reference_values(self):
        frames_data = [
            {
                "frame_idx": 0,
                "angulo_tronco": 20,
                "angulo_cabeza": None, # cabeza no detectada
                "angulo_cuello": None,
                "angulo_hombro": 15,
                "lado_usado": "Derecho",
                "tiempo_postura": 0.033,
                "frames_acumulados": 1
            }
        ]
        
        # alfa = 15, beta = None (sin referencia de cabeza)
        # tronco_ajustado = 20 - 15 = 5
        # cabeza_ajustada = "--"
        # cuello_ajustado = "--"
        
        num_regs = registrar_posturas_excel(
            excel_path=self.excel_path,
            nombre="Juan Pérez",
            archivo_origen="test_video.mp4",
            frames_data=frames_data,
            alfa=15.0,
            beta=None
        )
        
        self.assertEqual(num_regs, 1)
        self.assertTrue(os.path.exists(self.excel_path))
        
        wb = openpyxl.load_workbook(self.excel_path)
        sheet = wb["Registro Posturas"]
        
        row_data = [cell.value for cell in sheet[2]]
        self.assertEqual(row_data[2], 15)    # alfa
        self.assertEqual(row_data[3], 20)    # angulo del tronco del video
        self.assertEqual(row_data[4], 5)     # tronco_ajustado (20 - 15)
        self.assertEqual(row_data[5], "--")  # beta es None
        self.assertEqual(row_data[6], "--")  # cabeza del video es None
        self.assertEqual(row_data[7], "--")  # cabeza_ajustada es "--"
        self.assertEqual(row_data[8], "--")  # cuello_ajustado es "--"
        
        wb.close()

if __name__ == "__main__":
    unittest.main()
