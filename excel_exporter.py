import os
import openpyxl
from datetime import datetime
from openpyxl.styles import PatternFill, Font

def registrar_posturas_excel(
    excel_path, 
    nombre, 
    archivo_origen, 
    frames_data,
    alfa,
    beta
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
        alfa: Ángulo de tronco de referencia (imagen de referencia).
        beta: Ángulo de cabeza de referencia (imagen de referencia).
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
        "Ángulo de referencia del tronco (α)",
        "Ángulo del tronco del video",
        "Ángulo del tronco ajustado",
        "Ángulo de referencia de la cabeza (β)",
        "Ángulo de la cabeza del video",
        "Ángulo de la cabeza ajustado",
        "Ángulo del cuello ajustado",
        "Ángulo de brazo",
        "Lado leído",
        "Tiempo de postura",
        "Frames acumulados",
        "Fecha y hora del análisis"
    ]

    # Estilos de formato: letra blanca, fondo color #215967
    dark_blue_fill = PatternFill(start_color="215967", end_color="215967", fill_type="solid")
    white_font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    white_font_data = Font(name="Calibri", size=11, color="FFFFFF")

    # Asegurar cabeceras en la hoja
    if sheet.max_row == 0 or (sheet.max_row == 1 and all(cell.value is None for cell in sheet[1])):
        sheet.delete_rows(1, sheet.max_row)
        sheet.append(headers)
    else:
        # Forzar cabeceras exactas en fila 1
        for col_idx, header in enumerate(headers, 1):
            sheet.cell(row=1, column=col_idx, value=header)

    # Aplicar formato de cabecera a las columnas seleccionadas
    for col_idx in [5, 8, 9, 10]:
        cell = sheet.cell(row=1, column=col_idx)
        cell.fill = dark_blue_fill
        cell.font = white_font_header

    # Fecha y hora del análisis para este lote de registros
    fecha_hora_analisis = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    alfa_val = int(round(alfa)) if alfa is not None else None
    beta_val = int(round(beta)) if beta is not None else None

    # Escribir cada frame
    for f_data in frames_data:
        t_vid = f_data.get("angulo_tronco")
        c_vid = f_data.get("angulo_cabeza")
        
        # Calcular tronco ajustado (Ángulo del tronco del video - Alfa)
        if t_vid is not None and t_vid != "--" and alfa_val is not None:
            try:
                t_vid_int = int(round(float(t_vid)))
                tronco_ajustado = t_vid_int - alfa_val
            except (ValueError, TypeError):
                tronco_ajustado = "--"
        else:
            tronco_ajustado = "--"

        # Calcular cabeza ajustada (Ángulo de la cabeza del video - Beta)
        if c_vid is not None and c_vid != "--" and beta_val is not None:
            try:
                c_vid_int = int(round(float(c_vid)))
                cabeza_ajustada = c_vid_int - beta_val
            except (ValueError, TypeError):
                cabeza_ajustada = "--"
        else:
            cabeza_ajustada = "--"

        # Calcular cuello ajustado si ambos están calculados
        if cabeza_ajustada != "--" and tronco_ajustado != "--":
            cuello_ajustado = cabeza_ajustada - tronco_ajustado
        else:
            cuello_ajustado = "--"

        sheet.append([
            nombre,
            archivo_origen,
            alfa_val if alfa_val is not None else "--",
            t_vid if t_vid is not None else "--",
            tronco_ajustado,
            beta_val if beta_val is not None else "--",
            c_vid if c_vid is not None else "--",
            cabeza_ajustada,
            cuello_ajustado,
            f_data.get("angulo_hombro") if f_data.get("angulo_hombro") is not None else "--",
            f_data.get("lado_usado") if f_data.get("lado_usado") is not None else "--",
            f_data.get("tiempo_postura") if f_data.get("tiempo_postura") is not None else 0.0,
            f_data.get("frames_acumulados") if f_data.get("frames_acumulados") is not None else 0,
            fecha_hora_analisis
        ])

        # Aplicar formato de datos a las celdas de la fila agregada
        last_row = sheet.max_row
        for col_idx in [5, 8, 9, 10]:
            cell = sheet.cell(row=last_row, column=col_idx)
            cell.fill = dark_blue_fill
            cell.font = white_font_data

    workbook.save(excel_path)
    workbook.close()
    return len(frames_data)

