import os
from datetime import datetime
import openpyxl

def registrar_posturas_excel(
    excel_path, 
    nombre, 
    archivo_origen, 
    es_video, 
    segmentos=None, 
    angulo_tronco=0.0, 
    angulo_cuello=0.0, 
    angulo_hombro=0.0,
    lado_usado="--"
):
    """
    Registra datos de postura en un archivo Excel.
    
    Parámetros:
        excel_path: Ruta al archivo Excel.
        nombre: Nombre de la persona evaluada.
        archivo_origen: Nombre del archivo de imagen o video evaluado.
        es_video: Boolean indicando si es video (True) o imagen estática (False).
        segmentos: Lista de segmentos acumulados del video (requerido si es_video=True).
        angulo_tronco: Ángulo del tronco (usado si es_video=False).
        angulo_cuello: Ángulo del cuello (usado si es_video=False).
        angulo_hombro: Ángulo del hombro (usado si es_video=False).
        lado_usado: Lado del cuerpo medido (usado si es_video=False).
    """
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Cargar o crear libro de trabajo
    if os.path.exists(excel_path):
        workbook = openpyxl.load_workbook(excel_path)
        sheet = workbook.active
        
        # Si la hoja está totalmente vacía, añadimos cabeceras
        if sheet.max_row == 0 or (sheet.max_row == 1 and all(cell.value is None for cell in sheet[1])):
            sheet.delete_rows(1, sheet.max_row)
            sheet.append([
                "Fecha y Hora",
                "Nombre de la Persona",
                "flexión del tronco",
                "Tiempo de flexión de tronco",
                "flexión del cuello",
                "Tiempo de flexión de cuello",
                "flexión del brazo",
                "Tiempo de flexión de brazo",
                "Lado del Cuerpo Medido",
                "Archivo de Origen"
            ])
        else:
            # Limpiar columnas viejas si existen
            headers = [cell.value for cell in sheet[1]]
            for col in ["Estado del Cuello", "Estado del Tronco", "Tiempo de Video (Segundos)", "Tiempo en Mismo Ángulo (Segundos)"]:
                if col in headers:
                    col_idx = headers.index(col) + 1
                    sheet.delete_cols(col_idx, 1)
                    headers = [cell.value for cell in sheet[1]]
            
            # Si falta "Tiempo Tronco (Segundos)", insertarla como columna 4
            if "Tiempo de flexión de tronco" not in headers:
                sheet.insert_cols(4, 1)
                headers = [cell.value for cell in sheet[1]]

            # Si falta "Tiempo Cuello (Segundos)", insertarla como columna 6
            if "Tiempo de flexión de cuello" not in headers:
                sheet.insert_cols(6, 1)
                headers = [cell.value for cell in sheet[1]]
                
            # Si falta "Ángulo Hombro (Grados)", insertarla como columna 7
            if "flexión de brazo" not in headers:
                sheet.insert_cols(7, 1)
                headers = [cell.value for cell in sheet[1]]

            # Si falta "Tiempo Hombro (Segundos)", insertarla como columna 8
            if "Tiempo de flexion de brazo" not in headers:
                sheet.insert_cols(8, 1)
                headers = [cell.value for cell in sheet[1]]
                
            # Forzar los nombres exactos en la fila 1 para cabeceras limpias
            sheet.cell(row=1, column=1, value="Fecha y Hora")
            sheet.cell(row=1, column=2, value="Nombre de la Persona")
            sheet.cell(row=1, column=3, value="flexión del tronco")
            sheet.cell(row=1, column=4, value="Tiempo de flexion de tronco")
            sheet.cell(row=1, column=5, value="flexión del cuello")
            sheet.cell(row=1, column=6, value="Tiempo de flexion de cuello")
            sheet.cell(row=1, column=7, value="flexión del brazo")
            sheet.cell(row=1, column=8, value="Tiempo de flexion de brazo")
            sheet.cell(row=1, column=9, value="Lado del Cuerpo Medido")
            sheet.cell(row=1, column=10, value="Archivo de Origen")
    else:
        # Crear nuevo archivo y agregar cabeceras
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Registro de Posturas"
        sheet.append([
            "Fecha y Hora",
            "Nombre de la Persona",
            "flexión del tronco",
            "Tiempo de flexion de tronco",
            "flexión del cuello",
            "Tiempo de flexion de cuello",
            "flexión del brazo",
            "Tiempo de flexion de brazo",
            "Lado del Cuerpo Medido",
            "Archivo de Origen"
        ])

    num_registros = 0
    if es_video:
        if segmentos:
            tronco_list = segmentos.get("tronco", [])
            cuello_list = segmentos.get("cuello", [])
            hombro_list = segmentos.get("hombro", [])
            lado = segmentos.get("lado", "--")
            
            # Filtrar segmentos con duración > 0
            tronco_list = [s for s in tronco_list if s.get("duracion", 0) > 0]
            cuello_list = [s for s in cuello_list if s.get("duracion", 0) > 0]
            hombro_list = [s for s in hombro_list if s.get("duracion", 0) > 0]
            
            max_len = max(len(tronco_list), len(cuello_list), len(hombro_list))
            
            for i in range(max_len):
                t_seg = tronco_list[i] if i < len(tronco_list) else None
                c_seg = cuello_list[i] if i < len(cuello_list) else None
                h_seg = hombro_list[i] if i < len(hombro_list) else None
                
                sheet.append([
                    fecha_hora,
                    nombre,
                    t_seg["valor"] if (t_seg and t_seg["valor"] is not None) else "--",
                    round(t_seg["duracion"], 5) if t_seg else "--",
                    c_seg["valor"] if (c_seg and c_seg["valor"] is not None) else "--",
                    round(c_seg["duracion"], 5) if c_seg else "--",
                    h_seg["valor"] if (h_seg and h_seg["valor"] is not None) else "--",
                    round(h_seg["duracion"], 5) if h_seg else "--",
                    lado if lado is not None else "--",
                    archivo_origen
                ])
                num_registros += 1
    else:
        # Imagen estática: duración 0.0 segundos
        sheet.append([
            fecha_hora,
            nombre,
            int(round(angulo_tronco)),
            0.0,
            int(round(angulo_cuello)),
            0.0,
            int(round(angulo_hombro)),
            0.0,
            lado_usado,
            archivo_origen
        ])
        num_registros = 1

    workbook.save(excel_path)
    workbook.close()
    return num_registros

