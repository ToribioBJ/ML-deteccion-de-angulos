import os
import openpyxl

def registrar_posturas_excel(
    excel_path, 
    nombre, 
    archivo_origen, 
    es_video, 
    segmentos=None, 
    angulo_tronco=0.0, 
    angulo_cabeza=0.0,
    angulo_cuello=0.0, 
    angulo_hombro=0.0,
    lado_usado="--"
):
    """
    Registra datos de postura en un archivo Excel con 4 hojas independientes.
    
    Parámetros:
        excel_path: Ruta al archivo Excel.
        nombre: Nombre de la persona evaluada.
        archivo_origen: Nombre del archivo de imagen o video evaluado.
        es_video: Boolean indicando si es video (True) o imagen estática (False).
        segmentos: Lista de segmentos acumulados del video (requerido si es_video=True).
        angulo_tronco: Ángulo del tronco (usado si es_video=False).
        angulo_cabeza: Ángulo de la cabeza (usado si es_video=False).
        angulo_cuello: Ángulo del cuello (usado si es_video=False).
        angulo_hombro: Ángulo del hombro (usado si es_video=False).
        lado_usado: Lado del cuerpo medido (usado si es_video=False).
    """
    # Cargar o crear libro de trabajo
    if os.path.exists(excel_path):
        workbook = openpyxl.load_workbook(excel_path)
    else:
        workbook = openpyxl.Workbook()

    # Definir nombres de hojas y sus cabeceras
    sheet_names = {
        "tronco": "DATOS TRONCO",
        "cabeza": "CABEZA",
        "cuello": "DATOS CUELLO",
        "hombro": "DATOS BRAZO"
    }

    headers_map = {
        "tronco": [
            "Nombre de la Persona",
            "flexión del tronco",
            "Tiempo de flexion de tronco",
            "Lado del Cuerpo Medido",
            "Archivo de Origen"
        ],
        "cabeza": [
            "Nombre de la Persona",
            "flexión de la cabeza",
            "Tiempo de flexion de cabeza",
            "Lado del Cuerpo Medido",
            "Archivo de Origen"
        ],
        "cuello": [
            "Nombre de la Persona",
            "flexión del cuello",
            "Tiempo de flexion de cuello",
            "Lado del Cuerpo Medido",
            "Archivo de Origen"
        ],
        "hombro": [
            "Nombre de la Persona",
            "flexión del brazo",
            "Tiempo de flexion de brazo",
            "Lado del Cuerpo Medido",
            "Archivo de Origen"
        ]
    }

    # Asegurar que existan las cuatro hojas requeridas
    sheets = {}
    for key, name in sheet_names.items():
        if name not in workbook.sheetnames:
            # Si el libro es nuevo, podemos renombrar la primera hoja activa
            if not os.path.exists(excel_path) and key == "tronco":
                sheet = workbook.active
                sheet.title = name
            else:
                sheet = workbook.create_sheet(name)
        else:
            sheet = workbook[name]
        sheets[key] = sheet

    # Eliminar hojas antiguas o por defecto que no sean las cuatro oficiales
    for old_name in list(workbook.sheetnames):
        if old_name not in sheet_names.values():
            try:
                del workbook[old_name]
            except Exception:
                pass

    # Asegurar cabeceras en cada hoja
    for key, sheet in sheets.items():
        headers = headers_map[key]
        if sheet.max_row == 0 or (sheet.max_row == 1 and all(cell.value is None for cell in sheet[1])):
            sheet.delete_rows(1, sheet.max_row)
            sheet.append(headers)
        else:
            # Forzar cabeceras exactas en fila 1
            for col_idx, header in enumerate(headers, 1):
                sheet.cell(row=1, column=col_idx, value=header)

    num_registros = 0
    if es_video:
        if segmentos:
            tronco_list = segmentos.get("tronco", [])
            cabeza_list = segmentos.get("cabeza", [])
            cuello_list = segmentos.get("cuello", [])
            hombro_list = segmentos.get("hombro", [])
            lado = segmentos.get("lado", "--")
            
            # Filtrar segmentos con duración > 0
            tronco_list = [s for s in tronco_list if s.get("duracion", 0) > 0]
            cabeza_list = [s for s in cabeza_list if s.get("duracion", 0) > 0]
            cuello_list = [s for s in cuello_list if s.get("duracion", 0) > 0]
            hombro_list = [s for s in hombro_list if s.get("duracion", 0) > 0]
            
            # Escribir Tronco
            for t_seg in tronco_list:
                sheets["tronco"].append([
                    nombre,
                    t_seg["valor"] if t_seg["valor"] is not None else "--",
                    round(t_seg["duracion"], 5),
                    lado if lado is not None else "--",
                    archivo_origen
                ])
                num_registros += 1
                
            # Escribir Cabeza
            for cab_seg in cabeza_list:
                sheets["cabeza"].append([
                    nombre,
                    cab_seg["valor"] if cab_seg["valor"] is not None else "--",
                    round(cab_seg["duracion"], 5),
                    lado if lado is not None else "--",
                    archivo_origen
                ])
                num_registros += 1

            # Escribir Cuello
            for c_seg in cuello_list:
                sheets["cuello"].append([
                    nombre,
                    c_seg["valor"] if c_seg["valor"] is not None else "--",
                    round(c_seg["duracion"], 5),
                    lado if lado is not None else "--",
                    archivo_origen
                ])
                num_registros += 1
                
            # Escribir Brazo (hombro)
            for h_seg in hombro_list:
                sheets["hombro"].append([
                    nombre,
                    h_seg["valor"] if h_seg["valor"] is not None else "--",
                    round(h_seg["duracion"], 5),
                    lado if lado is not None else "--",
                    archivo_origen
                ])
                num_registros += 1
    else:
        # Imagen estática: duración 0.0 segundos
        sheets["tronco"].append([
            nombre,
            int(round(angulo_tronco)),
            0.0,
            lado_usado,
            archivo_origen
        ])
        
        sheets["cabeza"].append([
            nombre,
            int(round(angulo_cabeza)),
            0.0,
            lado_usado,
            archivo_origen
        ])

        sheets["cuello"].append([
            nombre,
            int(round(angulo_cuello)),
            0.0,
            lado_usado,
            archivo_origen
        ])
        
        sheets["hombro"].append([
            nombre,
            int(round(angulo_hombro)),
            0.0,
            lado_usado,
            archivo_origen
        ])
        num_registros = 4

    workbook.save(excel_path)
    workbook.close()
    return num_registros
