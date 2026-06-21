import os
import openpyxl
from datetime import datetime

def registrar_posturas_excel(
    excel_path, 
    nombre, 
    archivo_origen, 
    frames_data
):
    """
    Registra datos de postura por frame en un archivo Excel.
    Cada fila representa un frame del video o una imagen estática.
    
    Parámetros:
        excel_path: Ruta al archivo Excel.
        nombre: Nombre de la persona evaluada.
        archivo_origen: Nombre del archivo de imagen o video evaluado.
        frames_data: Lista de diccionarios, donde cada uno contiene la información de un frame:
                     [{"frame_idx": int/str, "angulo_tronco": int, "angulo_cabeza": int, 
                       "angulo_cuello": int, "angulo_hombro": int, "lado_usado": str,
                       "tiempo_postura": float, "frames_acumulados": int}]
    """
    # Cargar o crear libro de trabajo
    if os.path.exists(excel_path):
        workbook = openpyxl.load_workbook(excel_path)
    else:
        workbook = openpyxl.Workbook()

    sheet_name = "Registro Posturas"
    
    # Asegurar que exista la hoja requerida
    if sheet_name not in workbook.sheetnames:
        if not os.path.exists(excel_path) and len(workbook.sheetnames) == 1 and workbook.active.title == "Sheet":
            sheet = workbook.active
            sheet.title = sheet_name
        else:
            sheet = workbook.create_sheet(sheet_name)
    else:
        sheet = workbook[sheet_name]

    # Eliminar hojas antiguas si existen (para migración limpia del sistema anterior)
    old_sheet_names = ["DATOS TRONCO", "CABEZA", "DATOS CUELLO", "DATOS BRAZO", "Sheet"]
    for name in list(workbook.sheetnames):
        if name in old_sheet_names and name != sheet_name:
            try:
                del workbook[name]
            except Exception:
                pass

    # Cabeceras requeridas por el usuario
    headers = [
        "Nombre de la persona",
        "Nombre del video",
        "Ángulo de tronco",
        "Ángulo de cabeza",
        "Ángulo de cuello",
        "Ángulo de brazo",
        "Lado leído",
        "Tiempo de postura",
        "Frames acumulados",
        "Fecha y hora del análisis"
    ]

    # Asegurar cabeceras en la hoja
    if sheet.max_row == 0 or (sheet.max_row == 1 and all(cell.value is None for cell in sheet[1])):
        sheet.delete_rows(1, sheet.max_row)
        sheet.append(headers)
    else:
        # Forzar cabeceras exactas en fila 1
        for col_idx, header in enumerate(headers, 1):
            sheet.cell(row=1, column=col_idx, value=header)

    # Fecha y hora del análisis para este lote de registros
    fecha_hora_analisis = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Escribir cada frame
    for f_data in frames_data:
        sheet.append([
            nombre,
            archivo_origen,
            f_data.get("angulo_tronco") if f_data.get("angulo_tronco") is not None else "--",
            f_data.get("angulo_cabeza") if f_data.get("angulo_cabeza") is not None else "--",
            f_data.get("angulo_cuello") if f_data.get("angulo_cuello") is not None else "--",
            f_data.get("angulo_hombro") if f_data.get("angulo_hombro") is not None else "--",
            f_data.get("lado_usado") if f_data.get("lado_usado") is not None else "--",
            f_data.get("tiempo_postura") if f_data.get("tiempo_postura") is not None else 0.0,
            f_data.get("frames_acumulados") if f_data.get("frames_acumulados") is not None else 0,
            fecha_hora_analisis
        ])

    workbook.save(excel_path)
    workbook.close()
    return len(frames_data)
